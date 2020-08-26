from datetime import datetime, timedelta
from typing import Dict, Union

import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.base import BaseTrigger
from apscheduler.triggers.combining import OrTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from dateutil import parser
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.commands import DictConverter, TimedeltaConverter, parse_timedelta

from .datetimeconverter import DatetimeConverter
from .redconfigjobstore import RedConfigJobStore


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

    return get_trigger(data[0])


class FakeMessage:
    _state = None


# class FakeMessage(discord.Message):
#     def __init__(self):
#         super().__init__(state=None, channel=None, data=None)


class Task:
    default_task_data = {"triggers": [], "command_str": ""}

    default_trigger = {
        "type": "",
        "time_data": None,  # Used for Interval and Date Triggers
    }

    def __init__(self, name: str, guild_id, config: Config, author_id=None, bot: Red = None):
        self.name = name
        self.guild_id = guild_id
        self.config = config
        self.bot = bot
        self.author_id = author_id
        self.data = None

    async def _encode_time_data(self):
        if not self.data or not self.data.get("triggers", None):
            return None

        triggers = []
        for t in self.data["triggers"]:
            if t["type"] == "interval":  # Convert into timedelta
                td: timedelta = t["time_data"]

                triggers.append({"type": t["type"], "time_data":  {"days": td.days, "seconds": td.seconds} })

            if t["type"] == "date":  # Convert into datetime
                dt: datetime = t["time_data"]
                triggers.append({"type": t["type"], "time_data":  {
                    "year": dt.year,
                    "month": dt.month,
                    "day": dt.day,
                    "hour": dt.hour,
                    "minute": dt.minute,
                    "second": dt.second,
                }})

            if t["type"] == "cron":
                raise NotImplemented
            raise NotImplemented

        return triggers

    async def _decode_time_data(self):
        if not self.data or not self.data.get("triggers", None):
            return

        for t in self.data["triggers"]:
            if t["type"] == "interval":  # Convert into timedelta
                t["time_data"] = timedelta(**t["time_data"])

            if t["type"] == "date":  # Convert into datetime
                t["time_data"] = datetime(**t["time_data"])

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

        self.data = data["data"]

        await self._decode_time_data()
        return self.data

    async def get_trigger(self) -> Union[BaseTrigger, None]:
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
            data_to_save["command_str"] = self.data.get("command_str", "")
            data_to_save["triggers"] = await self._encode_time_data()

        to_save = {
            "guild_id": self.guild_id,
            "author_id": self.author_id,
            "data": data_to_save,
        }
        await self.config.guild_from_id(self.guild_id).tasks.set_raw(self.name, value=to_save)

    async def save_data(self):
        """To be used when updating triggers"""
        if not self.data:
            return
        await self.config.guild_from_id(self.guild_id).tasks.set_raw(
            self.name, "data", value=await self._encode_time_data()
        )

    async def execute(self):
        if not self.data or self.data["command_str"]:
            return False
        message = FakeMessage()
        message.guild = self.bot.get_guild(self.guild_id)  # used for get_prefix
        message.author = message.guild.get_member(self.author_id)
        message.content = await self.bot.get_prefix(message) + self.data["command_str"]

        if not message.guild or not message.author or not message.content:
            return False

        new_ctx: commands.Context = await self.bot.get_context(message)
        if not new_ctx.valid:
            return False

        await self.bot.invoke(new_ctx)
        return True

    async def set_bot(self, bot: Red):
        self.bot = bot

    async def set_author(self, author: Union[discord.User, str]):
        self.author_id = getattr(author, "id", None) or author

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

        jobstores = {"default": RedConfigJobStore(self.config, self.bot)}

        job_defaults = {"coalesce": False, "max_instances": 1}

        # executors = {"default": AsyncIOExecutor()}

        # Default executor is already AsyncIOExecutor
        self.scheduler = AsyncIOScheduler(jobstores=jobstores, job_defaults=job_defaults)

        self.scheduler.start()

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    def _assemble_job_id(self, task_name, guild_id):
        return task_name + "_" + guild_id

    async def _check_parsable_command(self, ctx: commands.Context, command_to_parse: str):
        message = FakeMessage()
        message.content = ctx.prefix + command_to_parse
        message.author = ctx.author
        message.guild = ctx.guild

        new_ctx: commands.Context = await self.bot.get_context(message)

        return new_ctx.valid

    async def _get_job(self, task_name, guild_id):
        return self.scheduler.get_job(self._assemble_job_id(task_name, guild_id))

    async def _add_job(self, task):
        return self.scheduler.add_job(
            task.execute,
            id=self._assemble_job_id(task.name, task.guild_id),
            trigger=await task.get_trigger(),
        )

    @checks.is_owner()
    @commands.command()
    async def fifoclear(self, ctx: commands.Context):
        """Debug command to clear fifo config"""
        await self.config.guild(ctx.guild).tasks.clear()
        await ctx.tick()

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
        if (await self.config.guild(ctx.guild).tasks.get_raw(task_name, default=None)) is not None:
            await ctx.maybe_send_embed(f"Task already exists with {task_name=}")
            return

        if not await self._check_parsable_command(ctx, command_to_execute):
            await ctx.maybe_send_embed("Failed to parse command. Make sure to include the prefix")
            return

        task = Task(task_name, ctx.guild.id, self.config, ctx.author.id)
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
        await task.save_data()
        await ctx.tick()

    @fifo_trigger.command(name="date")
    async def fifo_trigger_date(
        self, ctx: commands.Context, task_name: str, datetime_str: DatetimeConverter
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
        await ctx.tick()

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
    #                 task.execute, id=task_name + "_" + guild_id, trigger=await task.get_trigger(),
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
