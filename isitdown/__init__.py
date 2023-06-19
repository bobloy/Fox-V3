from .isitdown import IsItDown


async def setup(bot):
    cog = IsItDown(bot)
    r = bot.add_cog(cog)
    if r is not None:
        await r
