import asyncio
import pathlib
from datetime import datetime, timedelta

import discord
from redbot.core import Config
from redbot.core import commands
from redbot.core.data_manager import cog_data_path

from .chatterbot import ChatBot
from .chatterbot.comparisons import levenshtein_distance
from .chatterbot.response_selection import get_first_response
from .chatterbot.trainers import ListTrainer
from typing import Any

Cog: Any = getattr(commands, "Cog", object)


class Chatter(Cog):
    """
    This cog trains a chatbot that will talk like members of your Guild
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=6710497116116101114)
        default_global = {}
        default_guild = {"whitelist": None, "days": 1}
        path: pathlib.Path = cog_data_path(self)
        data_path = path / "database.sqlite3"

        self.chatbot = ChatBot(
            "ChatterBot",
            storage_adapter="chatter.chatterbot.storage.SQLStorageAdapter",
            database=str(data_path),
            statement_comparison_function=levenshtein_distance,
            response_selection_method=get_first_response,
            logic_adapters=[
                "chatter.chatterbot.logic.BestMatch",
                {
                    "import_path": "chatter.chatterbot.logic.LowConfidenceAdapter",
                    "threshold": 0.65,
                    "default_response": ":thinking:",
                },
            ],
        )
        self.chatbot.set_trainer(ListTrainer)

        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

        self.loop = asyncio.get_event_loop()

    async def _get_conversation(self, ctx, in_channel: discord.TextChannel = None):
        """
        Compiles all conversation in the Guild this bot can get it's hands on
        Currently takes a stupid long time
        Returns a list of text
        """
        out = [[]]
        after = datetime.today() - timedelta(days=(await self.config.guild(ctx.guild).days()))

        def new_message(msg, sent, out_in):
            if sent is None:
                return False

            if len(out_in) < 2:
                return False

            return msg.created_at - sent >= timedelta(
                hours=3
            )  # This should be configurable perhaps

        for channel in ctx.guild.text_channels:
            if in_channel:
                channel = in_channel
            await ctx.send("Gathering {}".format(channel.mention))
            user = None
            i = 0
            send_time = None
            try:

                async for message in channel.history(limit=None, after=after):
                    # if message.author.bot:  # Skip bot messages
                    #     continue
                    if new_message(message, send_time, out[i]):
                        out.append([])
                        i += 1
                        user = None
                    else:
                        send_time = message.created_at + timedelta(seconds=1)
                    if user == message.author:
                        out[i][-1] += "\n" + message.clean_content
                    else:
                        user = message.author
                        out[i].append(message.clean_content)

            except discord.Forbidden:
                pass
            except discord.HTTPException:
                pass

            if in_channel:
                break

        return out

    def _train(self, data):
        try:
            for convo in data:
                self.chatbot.train(convo)
        except:
            return False
        return True

    @commands.group(invoke_without_command=False)
    async def chatter(self, ctx: commands.Context):
        """
        Base command for this cog. Check help for the commands list.
        """
        if ctx.invoked_subcommand is None:
            pass

    @chatter.command()
    async def age(self, ctx: commands.Context, days: int):
        """
        Sets the number of days to look back
        Will train on 1 day otherwise
        """

        await self.config.guild(ctx.guild).days.set(days)
        await ctx.send("Success")

    @chatter.command()
    async def backup(self, ctx, backupname):
        """
        Backup your training data to a json for later use
        """
        await ctx.send("Backing up data, this may take a while")
        future = await self.loop.run_in_executor(
            None, self.chatbot.trainer.export_for_training, "./{}.json".format(backupname)
        )

        if future:
            await ctx.send("Backup successful!")
        else:
            await ctx.send("Error occurred :(")

    @chatter.command()
    async def train(self, ctx: commands.Context, channel: discord.TextChannel):
        """
        Trains the bot based on language in this guild
        """

        await ctx.send("Warning: The cog may use significant RAM or CPU if trained on large data sets.\n"
                       "Additionally, large sets will use more disk space to save the trained data.\n\n"
                       "If you experience issues, clear your trained data and train again on a smaller scope.")

        conversation = await self._get_conversation(ctx, channel)

        if not conversation:
            await ctx.send("Failed to gather training data")
            return

        await ctx.send(
            "Gather successful! Training begins now\n(**This will take a long time, be patient**)"
        )
        embed = discord.Embed(title="Loading")
        embed.set_image(url="http://www.loop.universaleverything.com/animations/1295.gif")
        temp_message = await ctx.send(embed=embed)
        future = await self.loop.run_in_executor(None, self._train, conversation)

        try:
            await temp_message.delete()
        except:
            pass

        if future:
            await ctx.send("Training successful!")
        else:
            await ctx.send("Error occurred :(")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Credit to https://github.com/Twentysix26/26-Cogs/blob/master/cleverbot/cleverbot.py
        for on_message recognition of @bot
        """
        author = message.author
        guild: discord.Guild = message.guild

        channel: discord.TextChannel = message.channel

        if author.id != self.bot.user.id:
            if guild is None:
                to_strip = "@" + channel.me.display_name + " "
            else:
                to_strip = "@" + guild.me.display_name + " "
            text = message.clean_content
            if not text.startswith(to_strip):
                return
            text = text.replace(to_strip, "", 1)
            async with channel.typing():
                future = await self.loop.run_in_executor(None, self.chatbot.get_response, text)

                if future and str(future):
                    await channel.send(str(future))
                else:
                    await channel.send(":thinking:")
