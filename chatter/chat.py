import asyncio
import logging
import os
import pathlib
from datetime import datetime, timedelta
from typing import Optional

import discord
from chatterbot import ChatBot
from chatterbot.comparisons import JaccardSimilarity, LevenshteinDistance, SpacySimilarity
from chatterbot.response_selection import get_random_response
from chatterbot.trainers import ChatterBotCorpusTrainer, ListTrainer, UbuntuCorpusTrainer
from redbot.core import Config, checks, commands
from redbot.core.commands import Cog
from redbot.core.data_manager import cog_data_path
from redbot.core.utils.predicates import MessagePredicate

log = logging.getLogger("red.fox_v3.chatter")


def my_local_get_prefix(prefixes, content):
    for p in prefixes:
        if content.startswith(p):
            return p
    return None


class ENG_LG:
    ISO_639_1 = "en_core_web_lg"
    ISO_639 = "eng"
    ENGLISH_NAME = "English"


class ENG_MD:
    ISO_639_1 = "en_core_web_md"
    ISO_639 = "eng"
    ENGLISH_NAME = "English"


class ENG_SM:
    ISO_639_1 = "en_core_web_sm"
    ISO_639 = "eng"
    ENGLISH_NAME = "English"


class Chatter(Cog):
    """
    This cog trains a chatbot that will talk like members of your Guild
    """

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=6710497116116101114)
        default_global = {}
        default_guild = {
            "whitelist": None,
            "days": 1,
            "convo_delta": 15,
            "chatchannel": None,
            "reply": True,
        }
        path: pathlib.Path = cog_data_path(self)
        self.data_path = path / "database.sqlite3"

        # TODO: Move training_model and similarity_algo to config
        # TODO: Add an option to see current settings

        self.tagger_language = ENG_MD
        self.similarity_algo = SpacySimilarity
        self.similarity_threshold = 0.90
        self.chatbot = self._create_chatbot()
        # self.chatbot.set_trainer(ListTrainer)

        # self.trainer = ListTrainer(self.chatbot)

        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

        self.loop = asyncio.get_event_loop()

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    def _create_chatbot(self):

        return ChatBot(
            "ChatterBot",
            storage_adapter="chatterbot.storage.SQLStorageAdapter",
            database_uri="sqlite:///" + str(self.data_path),
            statement_comparison_function=self.similarity_algo,
            response_selection_method=get_random_response,
            logic_adapters=["chatterbot.logic.BestMatch"],
            maximum_similarity_threshold=self.similarity_threshold,
            tagger_language=self.tagger_language,
            logger=log,
        )

    async def _get_conversation(self, ctx, in_channel: discord.TextChannel = None):
        """
        Compiles all conversation in the Guild this bot can get it's hands on
        Currently takes a stupid long time
        Returns a list of text
        """
        out = [[]]
        after = datetime.today() - timedelta(days=(await self.config.guild(ctx.guild).days()))
        convo_delta = timedelta(minutes=(await self.config.guild(ctx.guild).convo_delta()))

        def predicate(msg: discord.Message):
            return msg.clean_content

        def new_conversation(msg, sent, out_in, delta):
            # if sent is None:
            #     return False

            # Don't do "too short" processing here. Sometimes people don't respond.
            # if len(out_in) < 2:
            #     return False

            # print(msg.created_at - sent)

            return msg.created_at - sent >= delta

        for channel in ctx.guild.text_channels:
            if in_channel:
                channel = in_channel
            await ctx.maybe_send_embed("Gathering {}".format(channel.mention))
            user = None
            i = 0
            send_time = after - timedelta(days=100)  # Makes the first message a new message

            try:

                async for message in channel.history(
                    limit=None, after=after, oldest_first=True
                ).filter(
                    predicate=predicate
                ):  # type: discord.Message
                    # if message.author.bot:  # Skip bot messages
                    #     continue
                    if new_conversation(message, send_time, out[i], convo_delta):
                        out.append([])
                        i += 1
                        user = None

                    send_time = (
                        message.created_at
                    )  # + timedelta(seconds=1)  # Can't remember why I added 1 second

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

    def _train_ubuntu(self):
        trainer = UbuntuCorpusTrainer(
            self.chatbot, ubuntu_corpus_data_directory=cog_data_path(self) / "ubuntu_data"
        )
        trainer.train()
        return True

    def _train_english(self):
        trainer = ChatterBotCorpusTrainer(self.chatbot)
        # try:
        trainer.train("chatterbot.corpus.english")
        # except:
        #     return False
        return True

    def _train(self, data):
        trainer = ListTrainer(self.chatbot)
        total = len(data)
        # try:
        for c, convo in enumerate(data, 1):
            if len(convo) > 1:  # TODO: Toggleable skipping short conversations
                print(f"{c} / {total}")
                trainer.train(convo)
        # except:
        #     return False
        return True

    @commands.group(invoke_without_command=False)
    async def chatter(self, ctx: commands.Context):
        """
        Base command for this cog. Check help for the commands list.
        """
        if ctx.invoked_subcommand is None:
            pass

    @checks.admin()
    @chatter.command(name="channel")
    async def chatter_channel(
        self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None
    ):
        """
        Set a channel that the bot will respond in without mentioning it

        Pass with no channel object to clear this guild's channel
        """
        if channel is None:
            await self.config.guild(ctx.guild).chatchannel.set(None)
            await ctx.maybe_send_embed("Chat channel for guild is cleared")
        else:
            if channel.guild != ctx.guild:
                await ctx.maybe_send_embed("What are you trying to pull here? :eyes:")
                return
            await self.config.guild(ctx.guild).chatchannel.set(channel.id)
            await ctx.maybe_send_embed(f"Chat channel is now {channel.mention}")

    @checks.admin()
    @chatter.command(name="reply")
    async def chatter_reply(self, ctx: commands.Context, toggle: Optional[bool] = None):
        """
        Toggle bot reply to messages if conversation continuity is not present

        """
        reply = await self.config.guild(ctx.guild).reply()
        if toggle is None:
            toggle = not reply
        await self.config.guild(ctx.guild).reply.set(toggle)

        if toggle:
            await ctx.send("I will now respond to you if conversation continuity is not present")
        else:
            await ctx.send(
                "I will not reply to your message if conversation continuity is not present, anymore"
            )

    @checks.is_owner()
    @chatter.command(name="cleardata")
    async def chatter_cleardata(self, ctx: commands.Context, confirm: bool = False):
        """
        This command will erase all training data and reset your configuration settings

        Use `[p]chatter cleardata True`
        """

        if not confirm:
            await ctx.maybe_send_embed(
                "Warning, this command will erase all your training data and reset your configuration\n"
                "If you want to proceed, run the command again as `[p]chatter cleardata True`"
            )
            return
        async with ctx.typing():
            await self.config.clear_all()
            self.chatbot = None
            await asyncio.sleep(
                10
            )  # Pause to allow pending commands to complete before deleting sql data
            if os.path.isfile(self.data_path):
                try:
                    os.remove(self.data_path)
                except PermissionError:
                    await ctx.maybe_send_embed(
                        "Failed to clear training database. Please wait a bit and try again"
                    )

            self._create_chatbot()

        await ctx.tick()

    @checks.is_owner()
    @chatter.command(name="algorithm", aliases=["algo"])
    async def chatter_algorithm(
        self, ctx: commands.Context, algo_number: int, threshold: float = None
    ):
        """
        Switch the active logic algorithm to one of the three. Default after reload is Spacy

        0: Spacy
        1: Jaccard
        2: Levenshtein
        """

        algos = [SpacySimilarity, JaccardSimilarity, LevenshteinDistance]

        if algo_number < 0 or algo_number > 2:
            await ctx.send_help()
            return

        if threshold is not None:
            if threshold >= 1 or threshold <= 0:
                await ctx.maybe_send_embed(
                    "Threshold must be a number between 0 and 1 (exclusive)"
                )
                return
            else:
                self.similarity_threshold = threshold

        self.similarity_algo = algos[algo_number]
        async with ctx.typing():
            self.chatbot = self._create_chatbot()

            await ctx.tick()

    @checks.is_owner()
    @chatter.command(name="model")
    async def chatter_model(self, ctx: commands.Context, model_number: int):
        """
        Switch the active model to one of the three. Default after reload is Medium

        0: Small
        1: Medium
        2: Large (Requires additional setup)
        """

        models = [ENG_SM, ENG_MD, ENG_LG]

        if model_number < 0 or model_number > 2:
            await ctx.send_help()
            return

        if model_number == 2:
            await ctx.maybe_send_embed(
                "Additional requirements needed. See guide before continuing.\n" "Continue?"
            )
            pred = MessagePredicate.yes_or_no(ctx)
            try:
                await self.bot.wait_for("message", check=pred, timeout=30)
            except TimeoutError:
                await ctx.send("Response timed out, please try again later.")
                return
            if not pred.result:
                return

        self.tagger_language = models[model_number]
        async with ctx.typing():
            self.chatbot = self._create_chatbot()

            await ctx.maybe_send_embed(
                f"Model has been switched to {self.tagger_language.ISO_639_1}"
            )

    @checks.is_owner()
    @chatter.command(name="minutes")
    async def minutes(self, ctx: commands.Context, minutes: int):
        """
        Sets the number of minutes the bot will consider a break in a conversation during training
        Active servers should set a lower number, while less active servers should have a higher number
        """

        if minutes < 1:
            await ctx.send_help()
            return

        await self.config.guild(ctx.guild).convo_length.set(minutes)

        await ctx.tick()

    @checks.is_owner()
    @chatter.command(name="age")
    async def age(self, ctx: commands.Context, days: int):
        """
        Sets the number of days to look back
        Will train on 1 day otherwise
        """

        if days < 1:
            await ctx.send_help()
            return

        await self.config.guild(ctx.guild).days.set(days)
        await ctx.tick()

    @checks.is_owner()
    @chatter.command(name="backup")
    async def backup(self, ctx, backupname):
        """
        Backup your training data to a json for later use
        """

        await ctx.maybe_send_embed("Backing up data, this may take a while")

        path: pathlib.Path = cog_data_path(self)

        trainer = ListTrainer(self.chatbot)

        future = await self.loop.run_in_executor(
            None, trainer.export_for_training, str(path / f"{backupname}.json")
        )

        if future:
            await ctx.maybe_send_embed(f"Backup successful! Look in {path} for your backup")
        else:
            await ctx.maybe_send_embed("Error occurred :(")

    @checks.is_owner()
    @chatter.command(name="trainubuntu")
    async def chatter_train_ubuntu(self, ctx: commands.Context, confirmation: bool = False):
        """
        WARNING: Large Download! Trains the bot using Ubuntu Dialog Corpus data.
        """

        if not confirmation:
            await ctx.maybe_send_embed(
                "Warning: This command downloads ~500MB then eats your CPU for training\n"
                "If you're sure you want to continue, run `[p]chatter trainubuntu True`"
            )
            return

        async with ctx.typing():
            future = await self.loop.run_in_executor(None, self._train_ubuntu)

        if future:
            await ctx.send("Training successful!")
        else:
            await ctx.send("Error occurred :(")

    @checks.is_owner()
    @chatter.command(name="trainenglish")
    async def chatter_train_english(self, ctx: commands.Context):
        """
        Trains the bot in english
        """
        async with ctx.typing():
            future = await self.loop.run_in_executor(None, self._train_english)

        if future:
            await ctx.maybe_send_embed("Training successful!")
        else:
            await ctx.maybe_send_embed("Error occurred :(")

    @checks.is_owner()
    @chatter.command()
    async def train(self, ctx: commands.Context, channel: discord.TextChannel):
        """
        Trains the bot based on language in this guild
        """

        await ctx.maybe_send_embed(
            "Warning: The cog may use significant RAM or CPU if trained on large data sets.\n"
            "Additionally, large sets will use more disk space to save the trained data.\n\n"
            "If you experience issues, clear your trained data and train again on a smaller scope."
        )

        async with ctx.typing():
            conversation = await self._get_conversation(ctx, channel)

        if not conversation:
            await ctx.maybe_send_embed("Failed to gather training data")
            return

        await ctx.maybe_send_embed(
            "Gather successful! Training begins now\n"
            "(**This will take a long time, be patient. See console for progress**)"
        )
        embed = discord.Embed(title="Loading")
        embed.set_image(url="http://www.loop.universaleverything.com/animations/1295.gif")
        temp_message = await ctx.send(embed=embed)
        future = await self.loop.run_in_executor(None, self._train, conversation)

        try:
            await temp_message.delete()
        except discord.Forbidden:
            pass

        if future:
            await ctx.maybe_send_embed("Training successful!")
        else:
            await ctx.maybe_send_embed("Error occurred :(")

    @Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        """
        Credit to https://github.com/Twentysix26/26-Cogs/blob/master/cleverbot/cleverbot.py
        for on_message recognition of @bot

        Credit to:
        https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/cogs/customcom/customcom.py#L508
        for the message filtering
        """
        ###########

        if len(message.content) < 2 or message.author.bot:
            return

        guild: discord.Guild = getattr(message, "guild", None)

        if await self.bot.cog_disabled_in_guild(self, guild):
            return

        ctx: commands.Context = await self.bot.get_context(message)

        if ctx.prefix is not None:  # Probably unnecessary, we're in on_message_without_command
            return

        ###########
        # Thank you Cog-Creators
        channel: discord.TextChannel = message.channel

        # is_reply = False # this is only useful with in_response_to
        if (
            message.reference is not None
            and isinstance(message.reference.resolved, discord.Message)
            and message.reference.resolved.author.id == self.bot.user.id
        ):
            # is_reply = True # this is only useful with in_response_to
            pass  # this is a reply to the bot, good to go
        elif guild is not None and channel.id == await self.config.guild(guild).chatchannel():
            pass  # good to go
        else:
            when_mentionables = commands.when_mentioned(self.bot, message)

            prefix = my_local_get_prefix(when_mentionables, message.content)

            if prefix is None:
                # print("not mentioned")
                return

            message.content = message.content.replace(prefix, "", 1)

        text = message.clean_content

        async with channel.typing():
            future = await self.loop.run_in_executor(None, self.chatbot.get_response, text)

            replying = None
            if await self.config.guild(guild).reply():
                if message != ctx.channel.last_message:
                    replying = message

            if future and str(future):
                await channel.send(str(future), reference=replying)
            else:
                await channel.send(":thinking:")
