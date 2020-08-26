from .fifo import FIFO


async def setup(bot):
    cog = FIFO(bot)
    bot.add_cog(cog)
