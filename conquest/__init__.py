from .conquest import Conquest


def setup(bot):
    bot.add_cog(Conquest(bot))
