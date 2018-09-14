import pathlib
from typing import List

import yaml
from redbot.cogs.audio import Audio
from redbot.cogs.trivia import LOG
from redbot.cogs.trivia.trivia import InvalidListError, Trivia
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path
from redbot.core.utils import box

from .audiosession import AudioSession


class AudioTrivia(Trivia):
    """
    Custom commands
    Creates commands used to display text and adjust roles
    """

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.audio = None

    # @commands.command()
    # @commands.is_owner()
    # async def testit(self, ctx: commands.Context):
    #     self.audio: Audio = self.bot.get_cog("Audio")
    #     await ctx.invoke(self.audio.play, query="https://www.youtube.com/watch?v=FrceWR4XnVU")
    #     print("done")

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
            self.audio = self.bot.get_cog("Audio")

        if self.audio is None:
            await ctx.send("Audio is not loaded. Load it and try again")
            return

        categories = [c.lower() for c in categories]
        session = self._get_trivia_session(ctx.channel)
        if session is not None:
            await ctx.send("There is already an ongoing trivia session in this channel.")
            return
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
        config = trivia_dict.pop("CONFIG", None)
        if config and settings["allow_override"]:
            settings.update(config)
        settings["lists"] = dict(zip(categories, reversed(authors)))
        session = AudioSession.start(ctx, trivia_dict, settings, self.audio)
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
