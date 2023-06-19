from .lseen import LastSeen


async def setup(bot):
    cog = LastSeen(bot)
    r = bot.add_cog(cog)
    if r is not None:
        await r
