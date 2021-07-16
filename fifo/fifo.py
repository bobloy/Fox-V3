import itertools
import logging
from datetime import MAXYEAR, datetime, timedelta, tzinfo
from typing import Optional, Union

import discord
import pytz
from apscheduler.job import Job
from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.base import STATE_PAUSED, STATE_RUNNING
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.commands import TimedeltaConverter
from redbot.core.utils.chat_formatting import humanize_timedelta, pagify

from .datetime_cron_converters import CronConverter, DatetimeConverter, TimezoneConverter
from .task import Task

schedule_log = logging.getLogger("red.fox_v3.fifo.scheduler")
schedule_log.setLevel(logging.DEBUG)

log = logging.getLogger("red.fox_v3.fifo")


async def _execute_task(**task_state):
    log.info(f"Executing {task_state.get('name')}")
    task = Task(**task_state)
    if await task.load_from_config():
        return await task.execute()
    log.warning(f"Failed to load data on {task_state=}")
    return False


def _assemble_job_id(task_name, guild_id):
    return f"{task_name}_{guild_id}"


def _disassemble_job_id(job_id: str):
    return job_id.split("_")


def _get_run_times(job: Job, now: datetime = None):
    """
    Computes the scheduled run times between ``next_run_time`` and ``now`` (inclusive).

    Modified to be asynchronous and yielding instead of all-or-nothing

    """
    if not job.next_run_time:
        raise StopIteration()

    if now is None:
        now = datetime(MAXYEAR, 12, 31, 23, 59, 59, 999999, tzinfo=job.next_run_time.tzinfo)
        yield from _get_run_times(job, now)  # Recursion
        raise StopIteration()

    next_run_time = job.next_run_time
    while next_run_time and next_run_time <= now:
        yield next_run_time
        next_run_time = job.trigger.get_next_fire_time(next_run_time, now)


class CapturePrint:
    """Silly little class to get `print` output"""

    def __init__(self):
        self.string = None

    def write(self, string):
        self.string = string if self.string is None else self.string + "\n" + string


class FIFO(commands.Cog):
    """
    Simple Scheduling Cog

    Named after the simplest scheduling algorithm: First In First Out
    """

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=70737079, force_registration=True)

        default_global = {"jobs": []}
        default_guild = {"tasks": {}}

        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

        self.scheduler: Optional[AsyncIOScheduler] = None
        self.jobstore = None

        self.tz_cog = None

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    def cog_unload(self):
        # self.scheduler.remove_all_jobs()
        if self.scheduler is not None:
            self.scheduler.shutdown()

    async def initialize(self):

        job_defaults = {
            "coalesce": True,  # Multiple missed triggers within the grace time will only fire once
            "max_instances": 5,  # This is probably way too high, should likely only be one
            "misfire_grace_time": 15,  # 15 seconds ain't much, but it's honest work
            "replace_existing": True,  # Very important for persistent data
        }

        # executors = {"default": AsyncIOExecutor()}

        # Default executor is already AsyncIOExecutor
        self.scheduler = AsyncIOScheduler(job_defaults=job_defaults, logger=schedule_log)

        from .redconfigjobstore import RedConfigJobStore  # Wait to import to prevent cyclic import

        self.jobstore = RedConfigJobStore(self.config, self.bot)
        await self.jobstore.load_from_config()
        self.scheduler.add_jobstore(self.jobstore, "default")

        self.scheduler.start()

    async def _check_parsable_command(self, ctx: commands.Context, command_to_parse: str):
        message: discord.Message = ctx.message

        message.content = ctx.prefix + command_to_parse
        message.author = ctx.author

        new_ctx: commands.Context = await self.bot.get_context(message)

        return new_ctx.valid

    async def _delete_task(self, task: Task):
        job: Union[Job, None] = await self._get_job(task)
        if job is not None:
            job.remove()

        await task.delete_self()

    async def _process_task(self, task: Task):
        # None of this is necessar, we have `replace_existing` already
        # job: Union[Job, None] = await self._get_job(task)
        # if job is not None:
        #     combined_trigger_ = await task.get_combined_trigger()
        #     if combined_trigger_ is None:
        #         job.remove()
        #     else:
        #         job.reschedule(combined_trigger_)
        #     return job
        return await self._add_job(task)

    async def _get_job(self, task: Task) -> Job:
        return self.scheduler.get_job(_assemble_job_id(task.name, task.guild_id))

    async def _add_job(self, task: Task):
        combined_trigger_ = await task.get_combined_trigger()
        if combined_trigger_ is None:
            return None

        return self.scheduler.add_job(
            _execute_task,
            kwargs=task.__getstate__(),
            id=_assemble_job_id(task.name, task.guild_id),
            trigger=combined_trigger_,
            name=task.name,
            replace_existing=True,
        )

    async def _resume_job(self, task: Task):
        job: Union[Job, None] = await self._get_job(task)
        if job is not None:
            job.resume()
        else:
            job = await self._process_task(task)
        return job

    async def _pause_job(self, task: Task):
        try:
            return self.scheduler.pause_job(job_id=_assemble_job_id(task.name, task.guild_id))
        except JobLookupError:
            return False

    async def _remove_job(self, task: Task):
        try:
            self.scheduler.remove_job(job_id=_assemble_job_id(task.name, task.guild_id))
        except JobLookupError:
            pass

    async def _get_tz(self, user: Union[discord.User, discord.Member]) -> Union[None, tzinfo]:
        if self.tz_cog is None:
            self.tz_cog = self.bot.get_cog("Timezone")
        if self.tz_cog is None:
            self.tz_cog = False  # only try once to get the timezone cog

        if not self.tz_cog:
            return None
        try:
            usertime = await self.tz_cog.config.user(user).usertime()
        except AttributeError:
            return None

        if usertime:
            return await TimezoneConverter().convert(None, usertime)
        else:
            return None

    @checks.is_owner()
    @commands.guild_only()
    @commands.command()
    async def fifoclear(self, ctx: commands.Context):
        """Debug command to clear all current fifo data"""
        self.scheduler.remove_all_jobs()
        await self.config.guild(ctx.guild).tasks.clear()
        await self.config.jobs.clear()
        # await self.config.jobs_index.clear()
        await ctx.tick()

    @checks.is_owner()  # Will be reduced when I figure out permissions later
    @commands.guild_only()
    @commands.group()
    async def fifo(self, ctx: commands.Context):
        """
        Base command for handling scheduling of tasks
        """
        pass

    @fifo.command(name="wakeup")
    async def fifo_wakeup(self, ctx: commands.Context):
        """Debug command to fix missed executions.

        If you see a negative "Next run time" when adding a trigger, this may help resolve it.
        Check the logs when using this command.
        """

        self.scheduler.wakeup()
        await ctx.tick()

    @fifo.command(name="checktask", aliases=["checkjob", "check"])
    async def fifo_checktask(self, ctx: commands.Context, task_name: str):
        """Returns the next 10 scheduled executions of the task"""
        task = Task(task_name, ctx.guild.id, self.config, bot=self.bot)
        await task.load_from_config()

        if task.data is None:
            await ctx.maybe_send_embed(
                f"Task by the name of {task_name} is not found in this guild"
            )
            return

        job = await self._get_job(task)
        if job is None:
            await ctx.maybe_send_embed("No job scheduled for this task")
            return
        now = datetime.now(job.next_run_time.tzinfo)

        times = [
            humanize_timedelta(timedelta=x - now)
            for x in itertools.islice(_get_run_times(job), 10)
        ]
        await ctx.maybe_send_embed("\n\n".join(times))

    @fifo.command(name="set")
    async def fifo_set(
        self,
        ctx: commands.Context,
        task_name: str,
        author_or_channel: Union[discord.Member, discord.TextChannel],
    ):
        """
        Sets a different author or in a different channel for execution of a task.
        """
        task = Task(task_name, ctx.guild.id, self.config, bot=self.bot)
        await task.load_from_config()

        if task.data is None:
            await ctx.maybe_send_embed(
                f"Task by the name of {task_name} is not found in this guild"
            )
            return

        if isinstance(author_or_channel, discord.Member):
            if task.author_id == author_or_channel.id:
                await ctx.maybe_send_embed("Already executing as that member")
                return

            await task.set_author(author_or_channel)  # also saves
        elif isinstance(author_or_channel, discord.TextChannel):
            if task.channel_id == author_or_channel.id:
                await ctx.maybe_send_embed("Already executing in that channel")
                return

            await task.set_channel(author_or_channel)
        else:
            await ctx.maybe_send_embed("Unsupported result")
            return

        await ctx.tick()

    @fifo.command(name="resume")
    async def fifo_resume(self, ctx: commands.Context, task_name: Optional[str] = None):
        """
        Provide a task name to resume execution of a task.

        Otherwise resumes execution of all tasks on all guilds
        If the task isn't currently scheduled, will schedule it
        """
        if task_name is None:
            if self.scheduler.state == STATE_PAUSED:
                self.scheduler.resume()
                await ctx.maybe_send_embed("All task execution for all guilds has been resumed")
            else:
                await ctx.maybe_send_embed("Task execution is not paused, can't resume")
        else:
            task = Task(task_name, ctx.guild.id, self.config, bot=self.bot)
            await task.load_from_config()

            if task.data is None:
                await ctx.maybe_send_embed(
                    f"Task by the name of {task_name} is not found in this guild"
                )
                return

            if await self._resume_job(task):
                await ctx.maybe_send_embed(f"Execution of {task_name=} has been resumed")
            else:
                await ctx.maybe_send_embed(f"Failed to resume {task_name=}")

    @fifo.command(name="pause")
    async def fifo_pause(self, ctx: commands.Context, task_name: Optional[str] = None):
        """
        Provide a task name to pause execution of a task

        Otherwise pauses execution of all tasks on all guilds
        """
        if task_name is None:
            if self.scheduler.state == STATE_RUNNING:
                self.scheduler.pause()
                await ctx.maybe_send_embed("All task execution for all guilds has been paused")
            else:
                await ctx.maybe_send_embed("Task execution is not running, can't pause")
        else:
            task = Task(task_name, ctx.guild.id, self.config, bot=self.bot)
            await task.load_from_config()

            if task.data is None:
                await ctx.maybe_send_embed(
                    f"Task by the name of {task_name} is not found in this guild"
                )
                return

            if await self._pause_job(task):
                await ctx.maybe_send_embed(f"Execution of {task_name=} has been paused")
            else:
                await ctx.maybe_send_embed(f"Failed to pause {task_name=}")

    @fifo.command(name="details")
    async def fifo_details(self, ctx: commands.Context, task_name: str):
        """
        Provide all the details on the specified task name
        """
        task = Task(task_name, ctx.guild.id, self.config, bot=self.bot)
        await task.load_from_config()

        if task.data is None:
            await ctx.maybe_send_embed(
                f"Task by the name of {task_name} is not found in this guild"
            )
            return

        embed = discord.Embed(title=f"Task: {task_name}")

        embed.add_field(
            name="Task command", value=f"{ctx.prefix}{task.get_command_str()}", inline=False
        )

        guild: discord.Guild = self.bot.get_guild(task.guild_id)

        if guild is not None:
            author: discord.Member = guild.get_member(task.author_id)
            channel: discord.TextChannel = guild.get_channel(task.channel_id)
            embed.add_field(name="Server", value=guild.name)
            if author is not None:
                embed.add_field(name="Author", value=author.mention)
            if channel is not None:
                embed.add_field(name="Channel", value=channel.mention)

        else:
            embed.add_field(name="Server", value="Server not found", inline=False)
        triggers, expired_triggers = await task.get_triggers()

        trigger_str = "\n".join(str(t) for t in triggers)
        expired_str = "\n".join(str(t) for t in expired_triggers)
        if trigger_str:
            embed.add_field(name="Triggers", value=trigger_str, inline=False)
        if expired_str:
            embed.add_field(name="Expired Triggers", value=expired_str, inline=False)

        job = await self._get_job(task)
        if job and job.next_run_time:
            embed.timestamp = job.next_run_time

        await ctx.send(embed=embed)

    @fifo.command(name="list")
    async def fifo_list(self, ctx: commands.Context, all_guilds: bool = False):
        """
        Lists all current tasks and their triggers.

        Do `[p]fifo list True` to see tasks from all guilds
        """
        if all_guilds:
            pass  # TODO: All guilds
        else:
            out = ""
            all_tasks = await self.config.guild(ctx.guild).tasks()
            for task_name, task_data in all_tasks.items():
                out += f"{task_name}: {task_data}\n\n"

            if out:
                if len(out) > 2000:
                    for page in pagify(out):
                        await ctx.maybe_send_embed(page)
                else:
                    await ctx.maybe_send_embed(out)
            else:
                await ctx.maybe_send_embed("No tasks to list")

    @fifo.command(name="printschedule")
    async def fifo_printschedule(self, ctx: commands.Context):
        """
        Print the current schedule of execution.

        Useful for debugging.
        """
        cp = CapturePrint()
        self.scheduler.print_jobs(out=cp)

        out = cp.string

        if out:
            if len(out) > 2000:
                for page in pagify(out):
                    await ctx.maybe_send_embed(page)
            else:
                await ctx.maybe_send_embed(out)
        else:
            await ctx.maybe_send_embed("Failed to get schedule from scheduler")

    @fifo.command(name="add")
    async def fifo_add(self, ctx: commands.Context, task_name: str, *, command_to_execute: str):
        """
        Add a new task to this guild's task list
        """
        if (await self.config.guild(ctx.guild).tasks.get_raw(task_name, default=None)) is not None:
            await ctx.maybe_send_embed(f"Task already exists with {task_name=}")
            return

        if "_" in task_name:  # See _disassemble_job_id
            await ctx.maybe_send_embed("Task name cannot contain underscores")
            return

        if not await self._check_parsable_command(ctx, command_to_execute):
            await ctx.maybe_send_embed(
                "Failed to parse command. Make sure not to include the prefix"
            )
            return

        task = Task(task_name, ctx.guild.id, self.config, ctx.author.id, ctx.channel.id, self.bot)
        await task.set_commmand_str(command_to_execute)
        await task.save_all()
        await ctx.tick()

    @fifo.command(name="delete")
    async def fifo_delete(self, ctx: commands.Context, task_name: str):
        """
        Deletes a task from this guild's task list
        """
        task = Task(task_name, ctx.guild.id, self.config, bot=self.bot)
        await task.load_from_config()

        if task.data is None:
            await ctx.maybe_send_embed(
                f"Task by the name of {task_name} is not found in this guild"
            )
            return

        await self._delete_task(task)
        await ctx.maybe_send_embed(f"Task[{task_name}] has been deleted from this guild")

    @fifo.command(name="cleartriggers", aliases=["cleartrigger"])
    async def fifo_cleartriggers(self, ctx: commands.Context, task_name: str):
        """
        Removes all triggers from specified task

        Useful to start over with new trigger
        """

        task = Task(task_name, ctx.guild.id, self.config, bot=self.bot)
        await task.load_from_config()

        if task.data is None:
            await ctx.maybe_send_embed(
                f"Task by the name of {task_name} is not found in this guild"
            )
            return

        await task.clear_triggers()
        await self._remove_job(task)
        await ctx.tick()

    @fifo.group(name="addtrigger", aliases=["trigger"])
    async def fifo_trigger(self, ctx: commands.Context):
        """
        Add a new trigger for a task from the current guild.
        """
        pass

    @fifo_trigger.command(name="interval")
    async def fifo_trigger_interval(
        self, ctx: commands.Context, task_name: str, *, interval_str: TimedeltaConverter
    ):
        """
        Add an interval trigger to the specified task
        """

        task = Task(task_name, ctx.guild.id, self.config, bot=self.bot)
        await task.load_from_config()  # Will set the channel and author

        if task.data is None:
            await ctx.maybe_send_embed(
                f"Task by the name of {task_name} is not found in this guild"
            )
            return

        result = await task.add_trigger("interval", interval_str)
        if not result:
            await ctx.maybe_send_embed(
                "Failed to add an interval trigger to this task, see console for logs"
            )
            return
        await task.save_data()
        job: Job = await self._process_task(task)
        delta_from_now: timedelta = job.next_run_time - datetime.now(job.next_run_time.tzinfo)
        await ctx.maybe_send_embed(
            f"Task `{task_name}` added interval of {interval_str} to its scheduled runtimes\n\n"
            f"Next run time: {job.next_run_time} ({delta_from_now.total_seconds()} seconds)"
        )

    @fifo_trigger.command(name="relative")
    async def fifo_trigger_relative(
        self, ctx: commands.Context, task_name: str, *, time_from_now: TimedeltaConverter
    ):
        """
        Add a "run once" trigger at a time relative from now to the specified task
        """

        task = Task(task_name, ctx.guild.id, self.config, bot=self.bot)
        await task.load_from_config()

        if task.data is None:
            await ctx.maybe_send_embed(
                f"Task by the name of {task_name} is not found in this guild"
            )
            return

        time_to_run = datetime.now(pytz.utc) + time_from_now

        result = await task.add_trigger("date", time_to_run, time_to_run.tzinfo)
        if not result:
            await ctx.maybe_send_embed(
                "Failed to add a date trigger to this task, see console for logs"
            )
            return

        await task.save_data()
        job: Job = await self._process_task(task)
        delta_from_now: timedelta = job.next_run_time - datetime.now(job.next_run_time.tzinfo)
        await ctx.maybe_send_embed(
            f"Task `{task_name}` added {time_to_run} to its scheduled runtimes\n"
            f"Next run time: {job.next_run_time} ({delta_from_now.total_seconds()} seconds)"
        )

    @fifo_trigger.command(name="date")
    async def fifo_trigger_date(
        self, ctx: commands.Context, task_name: str, *, datetime_str: DatetimeConverter
    ):
        """
        Add a "run once" datetime trigger to the specified task
        """

        task = Task(task_name, ctx.guild.id, self.config, bot=self.bot)
        await task.load_from_config()

        if task.data is None:
            await ctx.maybe_send_embed(
                f"Task by the name of {task_name} is not found in this guild"
            )
            return

        maybe_tz = await self._get_tz(ctx.author)

        result = await task.add_trigger("date", datetime_str, maybe_tz)
        if not result:
            await ctx.maybe_send_embed(
                "Failed to add a date trigger to this task, see console for logs"
            )
            return

        await task.save_data()
        job: Job = await self._process_task(task)
        delta_from_now: timedelta = job.next_run_time - datetime.now(job.next_run_time.tzinfo)
        await ctx.maybe_send_embed(
            f"Task `{task_name}` added {datetime_str} to its scheduled runtimes\n"
            f"Next run time: {job.next_run_time} ({delta_from_now.total_seconds()} seconds)"
        )

    @fifo_trigger.command(name="cron")
    async def fifo_trigger_cron(
        self,
        ctx: commands.Context,
        task_name: str,
        optional_tz: Optional[TimezoneConverter] = None,
        *,
        cron_str: CronConverter,
    ):
        """
        Add a cron "time of day" trigger to the specified task

        See https://crontab.guru/ for help generating the cron_str
        """
        task = Task(task_name, ctx.guild.id, self.config, bot=self.bot)
        await task.load_from_config()

        if task.data is None:
            await ctx.maybe_send_embed(
                f"Task by the name of {task_name} is not found in this guild"
            )
            return

        if optional_tz is None:
            optional_tz = await self._get_tz(ctx.author)  # might still be None

        result = await task.add_trigger("cron", cron_str, optional_tz)
        if not result:
            await ctx.maybe_send_embed(
                "Failed to add a cron trigger to this task, see console for logs"
            )
            return

        await task.save_data()
        job: Job = await self._process_task(task)
        delta_from_now: timedelta = job.next_run_time - datetime.now(job.next_run_time.tzinfo)
        await ctx.maybe_send_embed(
            f"Task `{task_name}` added cron_str to its scheduled runtimes\n"
            f"Next run time: {job.next_run_time} ({delta_from_now.total_seconds()} seconds)"
        )
