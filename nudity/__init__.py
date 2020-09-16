from .nudity import Nudity


def setup(bot):
    n = Nudity(bot)
    bot.add_cog(n)
