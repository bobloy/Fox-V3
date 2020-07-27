from .sherlock import Sherlock


def setup(bot):
    bot.add_cog(Sherlock(bot))