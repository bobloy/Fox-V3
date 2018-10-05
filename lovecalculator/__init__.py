from .lovecalculator import LoveCalculator


def setup(bot):
    bot.add_cog(LoveCalculator(bot))
