from .chat import Chatter


def setup(bot):
    bot.add_cog(Chatter(bot))


# __all__ = (
#     'chatterbot'
# )
