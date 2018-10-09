from .secrethitler import SecretHitler


def setup(bot):
    hitler = SecretHitler(bot)
    bot.add_cog(hitler)