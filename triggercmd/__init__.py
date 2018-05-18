from .triggercmd import TriggerCmd


def setup(bot):
    bot.add_cog(TriggerCmd(bot))
