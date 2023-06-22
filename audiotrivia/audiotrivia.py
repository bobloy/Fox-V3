import datetime
import logging
import pathlib
from typing import List, Optional

import discord
import lavalink
import yaml
from redbot.cogs.audio import Audio
from redbot.cogs.trivia.trivia import InvalidListError, Trivia, get_core_lists
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path
from redbot.core.utils.chat_formatting import bold, box

from .audiosession import AudioSession


log = logging.getLogger("red.fox_v3.audiotrivia")


class AudioTrivia(Trivia):
    """
    Upgrade to the Trivia cog that enables audio trivia
    Replaces the Trivia cog
    """

    def __init__(self, bot: Red):
        super().__init__(bot)
        self.bot = bot
        self.audioconf = Config.get_conf(
            self, identifier=651171001051118411410511810597, force_registration=True
        )

        self.audioconf.register_guild(audio_delay=30.0, repeat=True)

    @commands.group()
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def atriviaset(self, ctx: commands.Context):
        """Manage Audio Trivia settings."""
        audioset = self.audioconf.guild(ctx.guild)
        settings_dict = await audioset.all()
        msg = box(
            "**Audio settings**\n"
            "Answer time limit: {audio_delay} seconds\n"
            "Repeat Short Audio: {repeat}"
            "".format(**settings_dict),
            lang="py",
        )
        await ctx.send(msg)

    @atriviaset.command(name="timelimit")
    async def atriviaset_timelimit(self, ctx: commands.Context, seconds: float):
        """Set the maximum seconds permitted to answer a question."""
        if seconds < 4.0:
            await ctx.send("Must be at least 4 seconds.")
            return
        settings = self.audioconf.guild(ctx.guild)
        await settings.audo_delay.set(seconds)
        await ctx.maybe_send_embed(f"Done. Maximum seconds to answer set to {seconds}.")

    @atriviaset.command(name="repeat")
    async def atriviaset_repeat(self, ctx: commands.Context, true_or_false: bool):
        """Set whether or not short audio will be repeated"""
        settings = self.audioconf.guild(ctx.guild)
        await settings.repeat.set(true_or_false)
        await ctx.maybe_send_embed(f"Done. Repeating short audio is now set to {true_or_false}.")

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def audiotrivia(self, ctx: commands.Context, *categories: str):
        """Start trivia session on the specified category or categories.

        Includes Audio categories.
        You may list multiple categories, in which case the trivia will involve
        questions from all of them.
        """
        if not categories and ctx.invoked_subcommand is None:
            await ctx.send_help()
            return
        categories = [c.lower() for c in categories]
        session = self._get_trivia_session(ctx.channel)
        if session is not None:
            await ctx.maybe_send_embed(
                "There is already an ongoing trivia session in this channel."
            )
            return
        trivia_dict = {}
        authors = []
        any_audio = False
        for category in reversed(categories):
            # We reverse the categories so that the first list's config takes
            # priority over the others.
            try:
                dict_ = self.get_audio_list(category)
            except FileNotFoundError:
                await ctx.maybe_send_embed(
                    f"Invalid category `{category}`. See `{ctx.prefix}audiotrivia list`"
                    " for a list of trivia categories."
                )
            except InvalidListError:
                await ctx.maybe_send_embed(
                    "There was an error parsing the trivia list for"
                    f" the `{category}` category. It may be formatted"
                    " incorrectly."
                )
            else:
                is_audio = dict_.pop("AUDIO", False)
                authors.append(dict_.pop("AUTHOR", None))
                trivia_dict.update(
                    {_q: {"audio": is_audio, "answers": _a} for _q, _a in dict_.items()}
                )
                any_audio = any_audio or is_audio
                continue
            return
        if not trivia_dict:
            await ctx.maybe_send_embed(
                "The trivia list was parsed successfully, however it appears to be empty!"
            )
            return

        if not any_audio:
            audio = None
        else:
            audio: Optional["Audio"] = self.bot.get_cog("Audio")
            if audio is None:
                await ctx.send("Audio lists were parsed but Audio is not loaded!")
                return
            status = await audio.config.status()
            notify = await audio.config.guild(ctx.guild).notify()

            if status:
                await ctx.maybe_send_embed(
                    f"It is recommended to disable audio status with `{ctx.prefix}audioset status`"
                )

            if notify:
                await ctx.maybe_send_embed(
                    f"It is recommended to disable audio notify with `{ctx.prefix}audioset notify`"
                )

            failed = await ctx.invoke(audio.command_summon)
            if failed:
                return
            lavaplayer = lavalink.get_player(ctx.guild.id)
            lavaplayer.store("channel", ctx.channel.id)  # What's this for? I dunno

        settings = await self.config.guild(ctx.guild).all()
        audiosettings = await self.audioconf.guild(ctx.guild).all()
        config = trivia_dict.pop("CONFIG", {"answer": None})["answer"]
        if config and settings["allow_override"]:
            settings.update(config)
        settings["lists"] = dict(zip(categories, reversed(authors)))

        # Delay in audiosettings overwrites delay in settings
        combined_settings = {**settings, **audiosettings}
        session = AudioSession.start(
            ctx,
            trivia_dict,
            combined_settings,
            audio,
        )
        self.trivia_sessions.append(session)
        log.debug("New audio trivia session; #%s in %d", ctx.channel, ctx.guild.id)

    @audiotrivia.command(name="list")
    @commands.guild_only()
    async def audiotrivia_list(self, ctx: commands.Context):
        """List available trivia including audio categories."""
        lists = {p.stem for p in self._all_audio_lists()}
        if await ctx.embed_requested():
            await ctx.send(
                embed=discord.Embed(
                    title="Available trivia lists",
                    colour=await ctx.embed_colour(),
                    description=", ".join(sorted(lists)),
                )
            )
        else:
            msg = box(bold("Available trivia lists") + "\n\n" + ", ".join(sorted(lists)))
            if len(msg) > 1000:
                await ctx.author.send(msg)
            else:
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
            path = next(p for p in self._all_audio_lists() if p.stem == category)
        except StopIteration:
            raise FileNotFoundError("Could not find the `{}` category.".format(category))

        with path.open(encoding="utf-8") as file:
            try:
                dict_ = yaml.load(file, Loader=yaml.SafeLoader)
            except yaml.error.YAMLError as exc:
                raise InvalidListError("YAML parsing failed.") from exc
            else:
                return dict_

    def _all_audio_lists(self) -> List[pathlib.Path]:
        # Custom trivia lists uploaded with audiotrivia. Not necessarily audio lists
        personal_lists = [p.resolve() for p in cog_data_path(self).glob("*.yaml")]

        # Add to that custom lists uploaded with trivia and core lists
        return personal_lists + get_core_audio_lists() + self._all_lists()


def get_core_audio_lists() -> List[pathlib.Path]:
    """Return a list of paths for all trivia lists packaged with the bot."""
    core_lists_path = pathlib.Path(__file__).parent.resolve() / "data/lists"
    return list(core_lists_path.glob("*.yaml"))
