from typing import Dict, Union

from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.triggers.base import BaseTrigger
from apscheduler.triggers.combining import AndTrigger, OrTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from dateutil import parser
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import discord
import asyncio
import datetime

from redbot.core.commands import DictConverter, TimedeltaConverter, parse_timedelta
from redbot.core.utils import AsyncIter


def get_trigger(data):
    if data["type"] == "interval":
        parsed_time = parse_timedelta(data["timedelta_str"])
        return IntervalTrigger(days=parsed_time.days, seconds=parsed_time.seconds)

    if data["type"] == "date":
        return DateTrigger(parser.parse(data["strtime"]))

    if data["type"] == "cron":
        return None  # TODO: Cron parsing


def parse_triggers(data: Union[Dict, None]):
    if data is None or not data.get("triggers", False):  # No triggers
        return None

    if len(data["triggers"]) > 1:  # Multiple triggers
        return OrTrigger(get_trigger(t_data) for t_data in data["triggers"])

    return get_trigger(data[0])


class Task:

    default_task_data = {"triggers": [], "command_str": ""}

    default_trigger = {
        "type": "",
        "timedelta_str": "",
    }

    def __init__(self, name: str, guild_id, config: Config):
        self.name = name
        self.guild_id = guild_id
        self.config = config

        self.data = None

    async def load_from_data(self, data: Dict):
        self.data = data.copy()

    async def load_from_config(self):
        self.data = await self.config.guild_from_id(self.guild_id).tasks.get_raw(
            self.name, default=None
        )
        return self.data

    async def get_trigger(self) -> Union[BaseTrigger, None]:
        if self.data is None:
            await self.load_from_config()

        return parse_triggers(self.data)

    # async def set_job_id(self, job_id):
    #     if self.data is None:
    #         await self.load_from_config()
    #
    #     self.data["job_id"] = job_id

    async def save_data(self):
        await self.config.guild_from_id(self.guild_id).tasks.set_raw(self.name, value=self.data)

    async def execute(self):
        pass  # TODO: something something invoke command

    async def add_trigger(self, param, parsed_time):
        pass


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

        jobstores = {"default": MemoryJobStore()}

        job_defaults = {"coalesce": False, "max_instances": 1}

        # executors = {"default": AsyncIOExecutor()}

        # Default executor is already AsyncIOExecutor
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores, job_defaults=job_defaults
        )

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    async def _parse_command(self, command_to_parse: str):
        return False  # TODO: parse commands somehow

    @checks.is_owner()  # Will be reduced when I figure out permissions later
    @commands.group()
    async def fifo(self, ctx: commands.Context):
        """
        Base command for handling scheduling of tasks
        """
        if ctx.invoked_subcommand is None:
            pass

    @fifo.command(name="list")
    async def fifo_list(self, ctx: commands.Context, all_guilds: bool = False):
        """
        Lists all current tasks and their triggers.

        Do `[p]fifo list True` to see tasks from all guilds
        """
        if all_guilds:
            pass
        else:
            pass  # TODO: parse and display tasks

    @fifo.command(name="add")
    async def fifo_add(self, ctx: commands.Context, task_name: str, *, command_to_execute: str):
        """
        Add a new task to this guild's task list
        """
        pass

    @fifo.command(name="delete")
    async def fifo_delete(self, ctx: commands.Context, task_name: str, *, command_to_execute: str):
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
        self, ctx: commands.Context, task_name: str, interval_str: TimedeltaConverter
    ):
        """
        Add an interval trigger to the specified task
        """

        task = Task(task_name, ctx.guild.id, self.config)
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
        await ctx.tick()

    @fifo_trigger.command(name="date")
    async def fifo_trigger_date(
        self, ctx: commands.Context, task_name: str, datetime_str: TimedeltaConverter
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
        await ctx.tick()

    @fifo_trigger.command(name="cron")
    async def fifo_trigger_cron(
        self, ctx: commands.Context, task_name: str, cron_settings: DictConverter
    ):
        """
        Add a "time of day" trigger to the specified task
        """
        await ctx.maybe_send_embed("Not yet implemented")

    async def load_tasks(self):
        """
        Run once on cog load.
        """
        all_guilds = await self.config.all_guilds()
        async for guild_id, guild_data in AsyncIter(all_guilds["tasks"].items(), steps=100):
            for task_name, task_data in guild_data["tasks"].items():
                task = Task(task_name, guild_id, self.config)
                await task.load_from_data(task_data)

                job = self.scheduler.add_job(
                    task.execute, id=task_name + "_" + guild_id, trigger=await task.get_trigger(),
                )

        self.scheduler.start()

    # async def parent_loop(self):
    #     await asyncio.sleep(60)
    #     asyncio.create_task(self.process_tasks(datetime.datetime.utcnow()))
    #
    # async def process_tasks(self, now: datetime.datetime):
    #     for task in self.tasks:
    #         pass
