from .rpsls import RPSLS


def setup(bot):
    bot.add_cog(RPSLS(bot))
