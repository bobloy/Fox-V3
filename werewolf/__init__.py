from .werewolf import Werewolf


def setup(bot):
    bot.add_cog(Werewolf(bot))
