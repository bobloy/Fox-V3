from .ccrole import CCRole


async def setup(bot):
    cog = CCRole(bot)
    r = bot.add_cog(cog)
    if r is not None:
        await r
