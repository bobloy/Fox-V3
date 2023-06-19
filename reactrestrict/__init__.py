from .reactrestrict import ReactRestrict


async def setup(bot):
    cog = ReactRestrict(bot)
    r = bot.add_cog(cog)
    if r is not None:
        await r
