from .leaver import Leaver


async def setup(bot):
    cog = Leaver(bot)
    r = bot.add_cog(cog)
    if r is not None:
        await r
