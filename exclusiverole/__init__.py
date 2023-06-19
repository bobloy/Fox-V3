from .exclusiverole import ExclusiveRole


async def setup(bot):
    cog = ExclusiveRole(bot)
    r = bot.add_cog(cog)
    if r is not None:
        await r
