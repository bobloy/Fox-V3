from .bangame import BanGame


def setup(bot):
    bot.add_cog(BanGame(bot))
