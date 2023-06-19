from .sayurl import SayUrl


async def setup(bot):
    cog = SayUrl(bot)
    r = bot.add_cog(cog)
    if r is not None:
        await r
