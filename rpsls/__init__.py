from .rpsls import RPSLS


async def setup(bot):
    cog = RPSLS(bot)
    r = bot.add_cog(cog)
    if r is not None:
        await r
