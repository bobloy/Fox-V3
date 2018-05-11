from .coglint import CogLint


def setup(bot):
    bot.add_cog(CogLint(bot))
