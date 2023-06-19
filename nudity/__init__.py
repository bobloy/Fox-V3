from .nudity import Nudity


async def setup(bot):
    cog = Nudity(bot)
    r = bot.add_cog(cog)
    if r is not None:
        await r
