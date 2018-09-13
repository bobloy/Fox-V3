from redbot.cogs.trivia import LOG
from redbot.cogs.trivia.trivia import InvalidListError, Trivia
from redbot.core import Config, checks
from redbot.core import commands
from redbot.core.bot import Red
from .audiosession import AudioSession


class AudioTrivia(Trivia):
    """
    Custom commands
    Creates commands used to display text and adjust roles
    """

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot

    @commands.group()
    @commands.guild_only()
    async def audiotrivia(self, ctx: commands.Context, *categories: str):
        """Start trivia session on the specified category.

                You may list multiple categories, in which case the trivia will involve
                questions from all of them.
                """
        if not categories:
            await ctx.send_help()
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
                dict_ = self.get_trivia_list(category)
            except FileNotFoundError:
                await ctx.send(
                    "Invalid category `{0}`. See `{1}trivia list`"
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
        session = AudioSession.start(ctx, trivia_dict, settings)
        self.trivia_sessions.append(session)
        LOG.debug("New audio trivia session; #%s in %d", ctx.channel, ctx.guild.id)