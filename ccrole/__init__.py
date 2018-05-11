from .ccrole import CCRole


def setup(bot):
    bot.add_cog(CCRole(bot))
