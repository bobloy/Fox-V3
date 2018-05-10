from .lseen import LastSeen


def setup(bot):
    bot.add_cog(LastSeen(bot))
