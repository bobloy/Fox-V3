from .fifo import FIFO


async def setup(bot):
    cog = FIFO(bot)
    await cog.load_tasks()
    bot.add_cog(cog)
