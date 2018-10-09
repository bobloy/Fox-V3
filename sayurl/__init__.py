from .sayurl import SayUrl


def setup(bot):
    bot.add_cog(SayUrl(bot))
