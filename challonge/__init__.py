from .challonge import Challonge

def setup(bot):
    n = Challonge(bot)
    bot.add_cog(n)