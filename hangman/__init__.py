from .hangman import Hangman


def setup(bot):
    n = Hangman(bot)
    bot.add_cog(n)
    bot.add_listener(n._on_react, "on_reaction_add")
