from .timerole import Timerole


async def setup(bot):
    cog = Timerole(bot)
    r = bot.add_cog(cog)
    if r is not None:
        await r
