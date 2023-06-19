from .hangman import Hangman
from redbot.core import data_manager


async def setup(bot):
    cog = Hangman(bot)
    data_manager.bundled_data_path(cog)
    r = bot.add_cog(cog)
    if r is not None:
        await r
