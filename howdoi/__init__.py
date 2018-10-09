from .howdoi import Howdoi


def setup(bot):
    bot.add_cog(Howdoi(bot))
