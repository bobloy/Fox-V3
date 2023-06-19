from .scp import SCP


async def setup(bot):
    cog = SCP(bot)
    r = bot.add_cog(cog)
    if r is not None:
        await r
