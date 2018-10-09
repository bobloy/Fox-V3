from .scp import SCP


def setup(bot):
    bot.add_cog(SCP(bot))
