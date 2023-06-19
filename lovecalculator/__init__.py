from .lovecalculator import LoveCalculator


async def setup(bot):
    cog = LoveCalculator(bot)
    r = bot.add_cog(cog)
    if r is not None:
        await r
