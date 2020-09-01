import logging
from datetime import datetime, timedelta
from typing import Dict, List, Union

import discord
from apscheduler.job import Job
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.base import BaseTrigger
from apscheduler.triggers.combining import OrTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.commands import DictConverter, TimedeltaConverter

from .datetimeconverter import DatetimeConverter

log = logging.getLogger("red.fox_v3.fifo")
schedule_log = logging.getLogger("red.fox_v3.fifo.scheduler")
schedule_log.setLevel(logging.DEBUG)
log.setLevel(logging.DEBUG)


async def _do_nothing(*args, **kwargs):
    pass


async def _execute_task(task_state):
    log.info(f"Executing {task_state=}")
    task = Task(**task_state)
    if await task.load_from_config():
        return await task.execute()
    return False


def get_trigger(data):
    if data["type"] == "interval":
        parsed_time = data["time_data"]
        return IntervalTrigger(days=parsed_time.days, seconds=parsed_time.seconds)

    if data["type"] == "date":
        return DateTrigger(data["time_data"])

    if data["type"] == "cron":
        return None  # TODO: Cron parsing

    return False


def parse_triggers(data: Union[Dict, None]):
    if data is None or not data.get("triggers", False):  # No triggers
        return None

    if len(data["triggers"]) > 1:  # Multiple triggers
        return OrTrigger(get_trigger(t_data) for t_data in data["triggers"])

    return get_trigger(data["triggers"][0])


class FakeMessage2(discord.Message):
    __slots__ = ("__dict__",)


class FakeMessage:
    def __init__(self, message: discord.Message):
        d = {k: getattr(message, k, None) for k in dir(message)}
        self.__dict__.update(**d)


class Task:
    default_task_data = {"triggers": [], "command_str": ""}

    default_trigger = {
        "type": "",
        "time_data": None,  # Used for Interval and Date Triggers
    }

    def __init__(
        self, name: str, guild_id, config: Config, author_id=None, channel_id=None, bot: Red = None
    ):
        self.name = name
        self.guild_id = guild_id
        self.config = config
        self.bot = bot
        self.author_id = author_id
        self.channel_id = channel_id
        self.data = None

    async def _encode_time_triggers(self):
        if not self.data or not self.data.get("triggers", None):
            return []

        triggers = []
        for t in self.data["triggers"]:
            if t["type"] == "interval":  # Convert into timedelta
                td: timedelta = t["time_data"]

                triggers.append(
                    {"type": t["type"], "time_data": {"days": td.days, "seconds": td.seconds}}
                )
                continue

            if t["type"] == "date":  # Convert into datetime
                dt: datetime = t["time_data"]
                triggers.append({"type": t["type"], "time_data": dt.isoformat()})
                # triggers.append(
                #     {
                #         "type": t["type"],
                #         "time_data": {
                #             "year": dt.year,
                #             "month": dt.month,
                #             "day": dt.day,
                #             "hour": dt.hour,
                #             "minute": dt.minute,
                #             "second": dt.second,
                #             "tzinfo": dt.tzinfo,
                #         },
                #     }
                # )
                continue

            if t["type"] == "cron":
                raise NotImplemented
            raise NotImplemented

        return triggers

    async def _decode_time_triggers(self):
        if not self.data or not self.data.get("triggers", None):
            return

        for n, t in enumerate(self.data["triggers"]):
            if t["type"] == "interval":  # Convert into timedelta
                self.data["triggers"][n]["time_data"] = timedelta(**t["time_data"])
                continue

            if t["type"] == "date":  # Convert into datetime
                # self.data["triggers"][n]["time_data"] = datetime(**t["time_data"])
                self.data["triggers"][n]["time_data"] = datetime.fromisoformat(t["time_data"])
                continue

            if t["type"] == "cron":
                raise NotImplemented
            raise NotImplemented

    # async def load_from_data(self, data: Dict):
    #     self.data = data.copy()

    async def load_from_config(self):
        data = await self.config.guild_from_id(self.guild_id).tasks.get_raw(
            self.name, default=None
        )

        if not data:
            return

        self.author_id = data["author_id"]
        self.guild_id = data["guild_id"]
        self.channel_id = data["channel_id"]

        self.data = data["data"]

        await self._decode_time_triggers()
        return self.data

    async def get_triggers(self) -> List[Union[IntervalTrigger, DateTrigger]]:
        if not self.data:
            await self.load_from_config()

        if self.data is None or "triggers" not in self.data:  # No triggers
            return []

        return [get_trigger(t) for t in self.data["triggers"]]

    async def get_combined_trigger(self) -> Union[BaseTrigger, None]:
        if not self.data:
            await self.load_from_config()

        return parse_triggers(self.data)

    # async def set_job_id(self, job_id):
    #     if self.data is None:
    #         await self.load_from_config()
    #
    #     self.data["job_id"] = job_id

    async def save_all(self):
        """To be used when creating an new task"""

        data_to_save = self.default_task_data.copy()
        if self.data:
            data_to_save["command_str"] = self.get_command_str()
            data_to_save["triggers"] = await self._encode_time_triggers()

        to_save = {
            "guild_id": self.guild_id,
            "author_id": self.author_id,
            "channel_id": self.channel_id,
            "data": data_to_save,
        }
        await self.config.guild_from_id(self.guild_id).tasks.set_raw(self.name, value=to_save)

    async def save_data(self):
        """To be used when updating triggers"""
        if not self.data:
            return

        data_to_save = self.data.copy()
        data_to_save["triggers"] = await self._encode_time_triggers()

        await self.config.guild_from_id(self.guild_id).tasks.set_raw(
            self.name, "data", value=data_to_save
        )

    async def execute(self):
        if not self.data or not self.get_command_str():
            log.warning(f"Could not execute task due to data problem: {self.data=}")
            return False

        guild: discord.Guild = self.bot.get_guild(self.guild_id)  # used for get_prefix
        if guild is None:
            log.warning(f"Could not execute task due to missing guild: {self.guild_id}")
            return False
        channel: discord.TextChannel = guild.get_channel(self.channel_id)
        if channel is None:
            log.warning(f"Could not execute task due to missing channel: {self.channel_id}")
            return False
        author: discord.User = guild.get_member(self.author_id)
        if author is None:
            log.warning(f"Could not execute task due to missing author: {self.author_id}")
            return False

        actual_message: discord.Message = channel.last_message
        if actual_message is None:
            log.warning("No message found in channel cache yet, skipping execution")
            return

        message = FakeMessage(actual_message)
        # message = FakeMessage2
        message.author = author
        message.id = None
        message.add_reaction = _do_nothing

        prefixes = await self.bot.get_prefix(message)
        if isinstance(prefixes, str):
            prefix = prefixes
        else:
            prefix = prefixes[0]

        message.content = f"{prefix}{self.get_command_str()}"

        if not message.guild or not message.author or not message.content:
            log.warning(f"Could not execute task due to message problem: {message}")
            return False

        new_ctx: commands.Context = await self.bot.get_context(message)
        new_ctx.assume_yes = True
        if not new_ctx.valid:
            log.warning(f"Could not execute task due invalid context: {new_ctx}")
            return False

        await self.bot.invoke(new_ctx)
        return True

    async def set_bot(self, bot: Red):
        self.bot = bot

    async def set_author(self, author: Union[discord.User, str]):
        self.author_id = getattr(author, "id", None) or author

    def get_command_str(self):
        return self.data.get("command_str", "")

    async def set_commmand_str(self, command_str):
        if not self.data:
            self.data = self.default_task_data.copy()
        self.data["command_str"] = command_str
        return True

    async def add_trigger(self, param, parsed_time: Union[timedelta, datetime]):
        trigger_data = {"type": param, "time_data": parsed_time}
        if not get_trigger(trigger_data):
            return False

        if not self.data:
            self.data = self.default_task_data.copy()

        self.data["triggers"].append(trigger_data)
        return True

    def __setstate__(self, task_state):
        self.name = task_state["name"]
        self.guild_id = task_state["guild_id"]
        self.config = task_state["config"]
        self.bot = None
        self.author_id = None
        self.channel_id = None
        self.data = None

    def __getstate__(self):
        return {
            "name": self.name,
            "guild_id": self.guild_id,
            "config": self.config,
            "bot": self.bot,
        }


def _assemble_job_id(task_name, guild_id):
    return f"{task_name}_{guild_id}"


def _disassemble_job_id(job_id: str):
    return job_id.split("_")


class FIFO(commands.Cog):
    """
    Simple Scheduling Cog

    Named after the simplest scheduling algorithm: First In First Out
    """

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=70737079, force_registration=True)

        default_global = {"jobs_index": {}, "jobs": []}
        default_guild = {"tasks": {}}

        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

        from .redconfigjobstore import RedConfigJobStore

        jobstores = {"default": RedConfigJobStore(self.config, self.bot)}

        job_defaults = {"coalesce": False, "max_instances": 1}

        # executors = {"default": AsyncIOExecutor()}

        # Default executor is already AsyncIOExecutor
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores, job_defaults=job_defaults, logger=schedule_log
        )

        self.scheduler.start()

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    async def _check_parsable_command(self, ctx: commands.Context, command_to_parse: str):
        message: discord.Message = ctx.message

        message.content = ctx.prefix + command_to_parse
        message.author = ctx.author

        new_ctx: commands.Context = await self.bot.get_context(message)

        return new_ctx.valid

    async def _process_task(self, task: Task):
        job: Union[Job, None] = await self._get_job(task)
        if job is not None:
            job.reschedule(await task.get_combined_trigger())
            return job
        return await self._add_job(task)

    async def _get_job(self, task: Task) -> Job:
        return self.scheduler.get_job(_assemble_job_id(task.name, task.guild_id))

    async def _add_job(self, task: Task):
        return self.scheduler.add_job(
            _execute_task,
            args=[task.__getstate__()],
            id=_assemble_job_id(task.name, task.guild_id),
            trigger=await task.get_combined_trigger(),
        )

    async def _pause_job(self, task: Task):
        return self.scheduler.pause_job(job_id=_assemble_job_id(task.name, task.guild_id))

    async def _remove_job(self, task: Task):
        return self.scheduler.remove_job(job_id=_assemble_job_id(task.name, task.guild_id))

    @checks.is_owner()
    @commands.command()
    async def fifoclear(self, ctx: commands.Context):
        """Debug command to clear all current fifo data"""
        self.scheduler.remove_all_jobs()
        await self.config.guild(ctx.guild).tasks.clear()
        await self.config.jobs.clear()
        await self.config.jobs_index.clear()
        await ctx.tick()

    @checks.is_owner()  # Will be reduced when I figure out permissions later
    @commands.group()
    async def fifo(self, ctx: commands.Context):
        """
        Base command for handling scheduling of tasks
        """
        if ctx.invoked_subcommand is None:
            pass

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

        embed = discord.Embed(title=task_name)

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
            embed.add_field(name="Server", value="Server not found")

        trigger_str = "\n".join(str(t) for t in await task.get_triggers())
        if trigger_str:
            embed.add_field(name="Triggers", value=trigger_str, inline=False)

        await ctx.send(embed=embed)

    @fifo.command(name="list")
    async def fifo_list(self, ctx: commands.Context, all_guilds: bool = False):
        """
        Lists all current tasks and their triggers.

        Do `[p]fifo list True` to see tasks from all guilds
        """
        if all_guilds:
            pass
        else:
            out = ""
            all_tasks = await self.config.guild(ctx.guild).tasks()
            for task_name, task_data in all_tasks.items():
                out += f"{task_name}: {task_data}\n"

            if out:
                await ctx.maybe_send_embed(out)
            else:
                await ctx.maybe_send_embed("No tasks to list")

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
        pass

    @fifo.group(name="trigger")
    async def fifo_trigger(self, ctx: commands.Context):
        """
        Add a new trigger for a task from the current guild.
        """
        if ctx.invoked_subcommand is None:
            pass

    @fifo_trigger.command(name="interval")
    async def fifo_trigger_interval(
        self, ctx: commands.Context, task_name: str, *, interval_str: TimedeltaConverter
    ):
        """
        Add an interval trigger to the specified task
        """

        task = Task(task_name, ctx.guild.id, self.config, bot=self.bot)
        await task.load_from_config()

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
            f"Task `{task_name}` added interval of {interval_str} to its scheduled runtimes\n"
            f"Next run time: {job.next_run_time} ({delta_from_now.total_seconds()} seconds)"
        )

    @fifo_trigger.command(name="date")
    async def fifo_trigger_date(
        self, ctx: commands.Context, task_name: str, *, datetime_str: DatetimeConverter
    ):
        """
        Add a "run once" datetime trigger to the specified task
        """

        task = Task(task_name, ctx.guild.id, self.config)
        await task.load_from_config()

        if task.data is None:
            await ctx.maybe_send_embed(
                f"Task by the name of {task_name} is not found in this guild"
            )
            return

        result = await task.add_trigger("date", datetime_str)
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
        self, ctx: commands.Context, task_name: str, cron_settings: DictConverter
    ):
        """
        Add a "time of day" trigger to the specified task
        """
        await ctx.maybe_send_embed("Not yet implemented")

    # async def load_tasks(self):
    #     """
    #     Run once on cog load.
    #     """
    #     all_guilds = await self.config.all_guilds()
    #     async for guild_id, guild_data in AsyncIter(all_guilds["tasks"].items(), steps=100):
    #         for task_name, task_data in guild_data["tasks"].items():
    #             task = Task(task_name, guild_id, self.config)
    #             await task.load_from_data(task_data)
    #
    #             job = self.scheduler.add_job(
    #                 task.execute, id=task_name + "_" + guild_id, trigger=await task.get_combined_trigger(),
    #             )
    #
    #     self.scheduler.start()

    # async def parent_loop(self):
    #     await asyncio.sleep(60)
    #     asyncio.create_task(self.process_tasks(datetime.datetime.utcnow()))
    #
    # async def process_tasks(self, now: datetime.datetime):
    #     for task in self.tasks:
    #         pass
