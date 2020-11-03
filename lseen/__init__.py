from .lseen import LastSeen


async def setup(bot):
    seen = LastSeen(bot)
    bot.add_cog(seen)
    await seen.initialize()
