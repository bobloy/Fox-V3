import datetime
import pathlib
from typing import List

import lavalink
import yaml
from redbot.cogs.audio import Audio
from redbot.cogs.trivia import LOG
from redbot.cogs.trivia.trivia import InvalidListError, Trivia
from redbot.core import commands, Config, checks
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path
from redbot.core.utils.chat_formatting import box

from .audiosession import AudioSession


class AudioTrivia(Trivia):
    """
    Upgrade to the Trivia cog that enables audio trivia
    Replaces the Trivia cog
    """

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.audio = None
        self.audioconf = Config.get_conf(
            self, identifier=651171001051118411410511810597, force_registration=True
        )

        self.audioconf.register_guild(delay=30.0, repeat=True)

    @commands.group()
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def atriviaset(self, ctx: commands.Context):
        """Manage Audio Trivia settings."""
        audioset = self.audioconf.guild(ctx.guild)
        settings_dict = await audioset.all()
        msg = box(
            "**Audio settings**\n"
            "Answer time limit: {delay} seconds\n"
            "Repeat Short Audio: {repeat}"
            "".format(**settings_dict),
            lang="py",
        )
        await ctx.send(msg)

    @atriviaset.command(name="delay")
    async def atriviaset_delay(self, ctx: commands.Context, seconds: float):
        """Set the maximum seconds permitted to answer a question."""
        if seconds < 4.0:
            await ctx.send("Must be at least 4 seconds.")
            return
        settings = self.audioconf.guild(ctx.guild)
        await settings.delay.set(seconds)
        await ctx.send("Done. Maximum seconds to answer set to {}.".format(seconds))

    @atriviaset.command(name="repeat")
    async def atriviaset_repeat(self, ctx: commands.Context, true_or_false: bool):
        """Set whether or not short audio will be repeated"""
        settings = self.audioconf.guild(ctx.guild)
        await settings.repeat.set(true_or_false)
        await ctx.send("Done. Repeating short audio is now set to {}.".format(true_or_false))

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def audiotrivia(self, ctx: commands.Context, *categories: str):
        """Start trivia session on the specified category.

                You may list multiple categories, in which case the trivia will involve
                questions from all of them.
                """
        if not categories and ctx.invoked_subcommand is None:
            await ctx.send_help()
            return

        if self.audio is None:
            self.audio: Audio = self.bot.get_cog("Audio")

        if self.audio is None:
            await ctx.send("Audio is not loaded. Load it and try again")
            return

        categories = [c.lower() for c in categories]
        session = self._get_trivia_session(ctx.channel)
        if session is not None:
            await ctx.send("There is already an ongoing trivia session in this channel.")
            return
        status = await self.audio.config.status()
        notify = await self.audio.config.guild(ctx.guild).notify()

        if status:
            await ctx.send(
                "It is recommended to disable audio status with `{}audioset status`".format(ctx.prefix)
            )

        if notify:
            await ctx.send(
                "It is recommended to disable audio notify with `{}audioset notify`".format(ctx.prefix)
            )

        if not self.audio._player_check(ctx):
            try:
                if not ctx.author.voice.channel.permissions_for(
                    ctx.me
                ).connect or self.audio._userlimit(ctx.author.voice.channel):
                    return await ctx.send("I don't have permission to connect to your channel.")
                await lavalink.connect(ctx.author.voice.channel)
                lavaplayer = lavalink.get_player(ctx.guild.id)
                lavaplayer.store("connect", datetime.datetime.utcnow())
            except AttributeError:
                return await ctx.send("Connect to a voice channel first.")

        lavaplayer = lavalink.get_player(ctx.guild.id)
        lavaplayer.store("channel", ctx.channel.id)  # What's this for? I dunno

        await self.audio._data_check(ctx)

        if not ctx.author.voice or ctx.author.voice.channel != lavaplayer.channel:
            return await ctx.send(
                "You must be in the voice channel to use the audiotrivia command."
            )

        trivia_dict = {}
        authors = []
        for category in reversed(categories):
            # We reverse the categories so that the first list's config takes
            # priority over the others.
            try:
                dict_ = self.get_audio_list(category)
            except FileNotFoundError:
                await ctx.send(
                    "Invalid category `{0}`. See `{1}audiotrivia list`"
                    " for a list of trivia categories."
                    "".format(category, ctx.prefix)
                )
            except InvalidListError:
                await ctx.send(
                    "There was an error parsing the trivia list for"
                    " the `{}` category. It may be formatted"
                    " incorrectly.".format(category)
                )
            else:
                trivia_dict.update(dict_)
                authors.append(trivia_dict.pop("AUTHOR", None))
                continue
            return
        if not trivia_dict:
            await ctx.send(
                "The trivia list was parsed successfully, however it appears to be empty!"
            )
            return
        settings = await self.conf.guild(ctx.guild).all()
        audiosettings = await self.audioconf.guild(ctx.guild).all()
        config = trivia_dict.pop("CONFIG", None)
        if config and settings["allow_override"]:
            settings.update(config)
        settings["lists"] = dict(zip(categories, reversed(authors)))

        # Delay in audiosettings overwrites delay in settings
        combined_settings = {**settings, **audiosettings}
        session = AudioSession.start(
            ctx=ctx, question_list=trivia_dict, settings=combined_settings, player=lavaplayer
        )
        self.trivia_sessions.append(session)
        LOG.debug("New audio trivia session; #%s in %d", ctx.channel, ctx.guild.id)

    @audiotrivia.command(name="list")
    @commands.guild_only()
    async def audiotrivia_list(self, ctx: commands.Context):
        """List available trivia categories."""
        lists = set(p.stem for p in self._audio_lists())

        msg = box("**Available trivia lists**\n\n{}".format(", ".join(sorted(lists))))
        if len(msg) > 1000:
            await ctx.author.send(msg)
            return
        await ctx.send(msg)

    def get_audio_list(self, category: str) -> dict:
        """Get the audiotrivia list corresponding to the given category.

        Parameters
        ----------
        category : str
            The desired category. Case sensitive.

        Returns
        -------
        `dict`
            A dict mapping questions (`str`) to answers (`list` of `str`).

        """
        try:
            path = next(p for p in self._audio_lists() if p.stem == category)
        except StopIteration:
            raise FileNotFoundError("Could not find the `{}` category.".format(category))

        with path.open(encoding="utf-8") as file:
            try:
                dict_ = yaml.load(file)
            except yaml.error.YAMLError as exc:
                raise InvalidListError("YAML parsing failed.") from exc
            else:
                return dict_

    def _audio_lists(self) -> List[pathlib.Path]:
        personal_lists = [p.resolve() for p in cog_data_path(self).glob("*.yaml")]

        return personal_lists + get_core_lists()


def get_core_lists() -> List[pathlib.Path]:
    """Return a list of paths for all trivia lists packaged with the bot."""
    core_lists_path = pathlib.Path(__file__).parent.resolve() / "data/lists"
    return list(core_lists_path.glob("*.yaml"))
