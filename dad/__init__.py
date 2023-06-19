from .dad import Dad


async def setup(bot):
    cog = Dad(bot)
    r = bot.add_cog(cog)
    if r is not None:
        await r
