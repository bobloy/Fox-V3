from .hangman import Hangman
from redbot.core import data_manager


def setup(bot):
    n = Hangman(bot)
    data_manager.load_bundled_data(n, __file__)
    bot.add_cog(n)
    bot.add_listener(n.on_react, "on_reaction_add")
