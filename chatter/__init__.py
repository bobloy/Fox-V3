from .chat import Chatter
from . import chatterbot

def setup(bot):
    bot.add_cog(Chatter(bot))

__all__ = (
    'chatterbot'
)
