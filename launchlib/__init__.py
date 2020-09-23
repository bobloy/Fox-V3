from .launchlib import LaunchLib


def setup(bot):
    bot.add_cog(LaunchLib(bot))
