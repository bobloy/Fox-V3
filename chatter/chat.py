import asyncio
import pathlib
from datetime import datetime, timedelta

import discord
from chatterbot import ChatBot
from chatterbot.comparisons import JaccardSimilarity, LevenshteinDistance, SpacySimilarity
from chatterbot.response_selection import get_first_response
from chatterbot.trainers import ChatterBotCorpusTrainer, ListTrainer
from redbot.core import Config, commands
from redbot.core.commands import Cog
from redbot.core.data_manager import cog_data_path


class ENG_LG:  # TODO: Add option to use this large model
    ISO_639_1 = "en_core_web_lg"
    ISO_639 = "eng"
    ENGLISH_NAME = "English"


class ENG_MD:
    ISO_639_1 = "en_core_web_md"
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
        default_guild = {"whitelist": None, "days": 1, "convo_delta": 15}
        path: pathlib.Path = cog_data_path(self)
        self.data_path = path / "database.sqlite3"

        self.chatbot = self._create_chatbot(self.data_path, SpacySimilarity, 0.45, ENG_MD)
        # self.chatbot.set_trainer(ListTrainer)

        # self.trainer = ListTrainer(self.chatbot)

        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

        self.loop = asyncio.get_event_loop()

    def _create_chatbot(
        self, data_path, similarity_algorithm, similarity_threshold, tagger_language
    ):
        return ChatBot(
            "ChatterBot",
            storage_adapter="chatterbot.storage.SQLStorageAdapter",
            database_uri="sqlite:///" + str(data_path),
            statement_comparison_function=similarity_algorithm,
            response_selection_method=get_first_response,
            logic_adapters=["chatterbot.logic.BestMatch"],
            maximum_similarity_threshold=similarity_threshold,
            tagger_language=tagger_language,
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
            await ctx.send("Gathering {}".format(channel.mention))
            user = None
            i = 0
            send_time = after - timedelta(days=100)  # Makes the first message a new message

            try:

                async for message in channel.history(
                    limit=None, after=after
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

    def _train_english(self):
        trainer = ChatterBotCorpusTrainer(self.chatbot)
        try:
            trainer.train("chatterbot.corpus.english")
        except:
            return False
        return True

    def _train(self, data):
        trainer = ListTrainer(self.chatbot)
        try:
            for convo in data:
                if len(convo) > 1:
                    trainer.train(convo)

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

    @chatter.command(name="algorithm")
    async def chatter_algorithm(self, ctx: commands.Context, algo_number: int):
        """
        Switch the active logic algorithm to one of the three. Default after reload is Spacy

        0: Spacy
        1: Jaccard
        2: Levenshtein
        """

        algos = [(SpacySimilarity, 0.45), (JaccardSimilarity, 0.75), (LevenshteinDistance, 0.75)]

        if algo_number < 0 or algo_number > 2:
            await ctx.send_help()
            return

        self.chatbot = self._create_chatbot(
            self.data_path, algos[algo_number][0], algos[algo_number][1], ENG_MD
        )

        await ctx.tick()

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

    @chatter.command(name="backup")
    async def backup(self, ctx, backupname):
        """
        Backup your training data to a json for later use
        """

        await ctx.send("Backing up data, this may take a while")

        path: pathlib.Path = cog_data_path(self)

        trainer = ListTrainer(self.chatbot)

        future = await self.loop.run_in_executor(
            None, trainer.export_for_training, str(path / f"{backupname}.json")
        )

        if future:
            await ctx.send(f"Backup successful! Look in {path} for your backup")
        else:
            await ctx.send("Error occurred :(")

    @chatter.command(name="trainenglish")
    async def chatter_train_english(self, ctx: commands.Context):
        """
        Trains the bot in english
        """
        async with ctx.typing():
            future = await self.loop.run_in_executor(None, self._train_english)

        if future:
            await ctx.send("Training successful!")
        else:
            await ctx.send("Error occurred :(")

    @chatter.command()
    async def train(self, ctx: commands.Context, channel: discord.TextChannel):
        """
        Trains the bot based on language in this guild
        """

        await ctx.send(
            "Warning: The cog may use significant RAM or CPU if trained on large data sets.\n"
            "Additionally, large sets will use more disk space to save the trained data.\n\n"
            "If you experience issues, clear your trained data and train again on a smaller scope."
        )

        async with ctx.typing():
            conversation = await self._get_conversation(ctx, channel)

        if not conversation:
            await ctx.send("Failed to gather training data")
            return

        await ctx.send(
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
            await ctx.send("Training successful!")
        else:
            await ctx.send("Error occurred :(")

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        """
        Credit to https://github.com/Twentysix26/26-Cogs/blob/master/cleverbot/cleverbot.py
        for on_message recognition of @bot

        Credit to:
        https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/cogs/customcom/customcom.py#L508
        for the message filtering
        """
        ###########
        is_private = isinstance(message.channel, discord.abc.PrivateChannel)

        # user_allowed check, will be replaced with self.bot.user_allowed or
        # something similar once it's added
        user_allowed = True

        if len(message.content) < 2 or is_private or not user_allowed or message.author.bot:
            return

        ctx: commands.Context = await self.bot.get_context(message)

        # if ctx.prefix is None:
        #     return
        ###########
        # Thank you Cog-Creators

        def my_local_get_prefix(prefixes, content):
            for p in prefixes:
                if content.startswith(p):
                    return p

        when_mentionables = commands.when_mentioned(self.bot, message)

        prefix = my_local_get_prefix(when_mentionables, message.content)

        if prefix is None:
            # print("not mentioned")
            return

        author = message.author
        guild: discord.Guild = message.guild

        channel: discord.TextChannel = message.channel

        # if author.id != self.bot.user.id:
        #     if guild is None:
        #         to_strip = "@" + channel.me.display_name + " "
        #     else:
        #         to_strip = "@" + guild.me.display_name + " "
        #     text = message.clean_content
        #     if not text.startswith(to_strip):
        #         return
        #     text = text.replace(to_strip, "", 1)

        # A bit more aggressive, could remove two mentions
        # Or might not work at all, since mentionables are pre-cleaned_content
        text = message.clean_content
        text.replace(prefix, "", 1)

        async with channel.typing():
            future = await self.loop.run_in_executor(None, self.chatbot.get_response, text)

            if future and str(future):
                await channel.send(str(future))
            else:
                await channel.send(":thinking:")
