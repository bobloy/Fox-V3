from .coglint import CogLint


async def setup(bot):
    cog = CogLint(bot)
    r = bot.add_cog(cog)
    if r is not None:
        await r
