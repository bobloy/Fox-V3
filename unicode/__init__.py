from .unicode import Unicode


async def setup(bot):
    cog = Unicode(bot)
    r = bot.add_cog(cog)
    if r is not None:
        await r
