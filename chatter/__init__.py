from .chat import Chatter


async def setup(bot):
    cog = Chatter(bot)
    await cog.initialize()
    r = bot.add_cog(cog)
    if r is not None:
        await r


# __all__ = (
#     'chatterbot'
# )
