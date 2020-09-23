import logging
from datetime import datetime, timedelta
from typing import Dict, List, Union

import discord
from apscheduler.triggers.base import BaseTrigger
from apscheduler.triggers.combining import OrTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from discord.utils import time_snowflake
from redbot.core import Config, commands
from redbot.core.bot import Red

log = logging.getLogger("red.fox_v3.fifo.task")


async def _do_nothing(*args, **kwargs):
    pass


def get_trigger(data):
    if data["type"] == "interval":
        parsed_time = data["time_data"]
        return IntervalTrigger(days=parsed_time.days, seconds=parsed_time.seconds)

    if data["type"] == "date":
        return DateTrigger(data["time_data"])

    if data["type"] == "cron":
        return CronTrigger.from_crontab(data["time_data"])

    return False


def parse_triggers(data: Union[Dict, None]):
    if data is None or not data.get("triggers", False):  # No triggers
        return None

    if len(data["triggers"]) > 1:  # Multiple triggers
        return OrTrigger(get_trigger(t_data) for t_data in data["triggers"])

    return get_trigger(data["triggers"][0])


class FakeMessage:
    def __init__(self, message: discord.Message):
        d = {k: getattr(message, k, None) for k in dir(message)}
        self.__dict__.update(**d)


def neuter_message(message: FakeMessage):
    message.delete = _do_nothing
    message.edit = _do_nothing
    message.publish = _do_nothing
    message.pin = _do_nothing
    message.unpin = _do_nothing
    message.add_reaction = _do_nothing
    message.remove_reaction = _do_nothing
    message.clear_reaction = _do_nothing
    message.clear_reactions = _do_nothing
    message.ack = _do_nothing

    return message


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
                triggers.append(t)  # already a string, nothing to do

                continue
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
                continue  # already a string
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
        # I'd like to present you my chain of increasingly desperate message fetching attempts
        if actual_message is None:
            # log.warning("No message found in channel cache yet, skipping execution")
            # return
            actual_message = await channel.fetch_message(channel.last_message_id)
            if actual_message is None:  # last_message_id was an invalid message I guess
                actual_message = await channel.history(limit=1).flatten()
                if not actual_message:  # Basically only happens if the channel has no messages
                    actual_message = await author.history(limit=1).flatten()
                    if not actual_message:  # Okay, the *author* has never sent a message?
                        log.warning("No message found in channel cache yet, skipping execution")
                        return
                actual_message = actual_message[0]

        message = FakeMessage(actual_message)
        # message = FakeMessage2
        message.author = author
        message.guild = guild  # Just in case we got desperate
        message.channel = channel
        message.id = time_snowflake(datetime.now())  # Pretend to be now
        message = neuter_message(message)

        # absolutely weird that this takes a message object instead of guild
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
            log.warning(
                f"Could not execute Task[{self.name}] due invalid context: {new_ctx.invoked_with}"
            )
            return False

        await self.bot.invoke(new_ctx)
        return True

    async def set_bot(self, bot: Red):
        self.bot = bot

    async def set_author(self, author: Union[discord.User, discord.Member, str]):
        self.author_id = getattr(author, "id", None) or author
        await self.config.guild_from_id(self.guild_id).tasks.set_raw(
            self.name, "author_id", value=self.author_id
        )

    async def set_channel(self, channel: Union[discord.TextChannel, str]):
        self.channel_id = getattr(channel, "id", None) or channel
        await self.config.guild_from_id(self.guild_id).tasks.set_raw(
            self.name, "channel_id", value=self.channel_id
        )

    def get_command_str(self):
        return self.data.get("command_str", "")

    async def set_commmand_str(self, command_str):
        if not self.data:
            self.data = self.default_task_data.copy()
        self.data["command_str"] = command_str
        return True

    async def add_trigger(self, param, parsed_time: Union[timedelta, datetime, str]):
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

    async def clear_triggers(self):
        self.data["triggers"] = []
        await self.save_data()

    async def delete_self(self):
        """Hopefully nothing uses the object after running this..."""
        await self.config.guild_from_id(self.guild_id).tasks.clear_raw(self.name)
