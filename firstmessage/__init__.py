from .firstmessage import FirstMessage


async def setup(bot):
    cog = FirstMessage(bot)
    r = bot.add_cog(cog)
    if r is not None:
        await r
