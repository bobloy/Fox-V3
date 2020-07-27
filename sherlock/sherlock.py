from redbot.core import Config, commands
from redbot.core.bot import Red


class Sherlock(commands.Cog):
    """
    Cog Description

    Less important information about the cog
    """

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=0, force_registration=True)  # TODO: Identifier

        default_guild = {}

        self.config.register_guild(**default_guild)

    @commands.command()
    async def sherlock(self, ctx: commands.Context):
        await ctx.send("Hello world")
