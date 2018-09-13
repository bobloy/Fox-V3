from .exclusiverole import ExclusiveRole


def setup(bot):
    bot.add_cog(ExclusiveRole(bot))
