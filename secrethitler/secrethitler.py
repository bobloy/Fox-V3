from redbot.core import commands


class SecretHitler:
    """
    Base to host Secret Hitler on a guild
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.group()
    async def secrethitler(self, ctx: commands.Context):
        """
        Base command for this cog. Check help for the commands list.
        """
        if ctx.invoked_subcommand is None:
            pass
