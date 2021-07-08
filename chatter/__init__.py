from .chat import Chatter


async def setup(bot):
    cog = Chatter(bot)
    await cog.initialize()
    bot.add_cog(cog)


# __all__ = (
#     'chatterbot'
# )
