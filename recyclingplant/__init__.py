from redbot.core import data_manager

from .recyclingplant import RecyclingPlant


async def setup(bot):
    cog = RecyclingPlant(bot)
    data_manager.bundled_data_path(cog)
    r = bot.add_cog(cog)
    if r is not None:
        await r
