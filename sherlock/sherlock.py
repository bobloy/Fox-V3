import discord
from redbot.core import Config, commands
from redbot.core.bot import Red
from socialscan.util import Platforms, execute_queries, sync_execute_queries


class Sherlock(commands.Cog):
    """
    Cog Description

    Less important information about the cog
    """

    platforms = [
        Platforms.GITHUB,
        Platforms.GITLAB,
        Platforms.INSTAGRAM,
        Platforms.REDDIT,
        Platforms.SNAPCHAT,
        Platforms.SPOTIFY,
        Platforms.PINTEREST,
        Platforms.TUMBLR,
        Platforms.TWITTER,
        Platforms.LASTFM,
    ]

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=0, force_registration=True
        )  # TODO: Identifier

        default_guild = {}

        self.config.register_guild(**default_guild)

    @commands.command()
    async def sherlock(self, ctx: commands.Context, member: discord.abc.User):
        queries = {member.display_name}
        if isinstance(member, discord.Member):
            queries.add(member.nick)
        queries = list(queries)

        async with ctx.typing():
            results = await execute_queries(queries=queries, platforms=self.platforms)

            for result in results:
                out = discord.Embed(
                    title=str(result.platform),
                    url=result.link,
                    description=f"Valid: {result.valid}\nAvailable: {result.available}",
                )
                # out.description =
                # out.add_field(name=result.platform, value=)

                # out = "\n".join(
                #     f"{result.query} on {result.platform}: {result.message} "
                #     f"(Success: {result.success}, Valid: {result.valid}, Available: {result.available})"
                #     for result in results
                # )

                await ctx.send(embed=out)
