from .stealemoji import StealEmoji


def setup(bot):
    bot.add_cog(StealEmoji(bot))
