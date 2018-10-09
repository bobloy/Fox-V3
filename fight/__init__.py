from .fight import Fight


def setup(bot):
    n = Fight(bot)
    bot.add_cog(n)
