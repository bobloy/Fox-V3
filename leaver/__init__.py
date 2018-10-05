from .leaver import Leaver


def setup(bot):
    bot.add_cog(Leaver(bot))
