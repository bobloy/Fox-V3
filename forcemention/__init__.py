from .forcemention import ForceMention


async def setup(bot):
    cog = ForceMention(bot)
    r = bot.add_cog(cog)
    if r is not None:
        await r
