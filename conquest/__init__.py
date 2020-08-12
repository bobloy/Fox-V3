from redbot.core import data_manager

from .conquest import Conquest
from .mapmaker import MapMaker


async def setup(bot):
    cog = Conquest(bot)
    data_manager.bundled_data_path(cog)
    await cog.load_data()

    bot.add_cog(cog)

    cog2 = MapMaker(bot)
    bot.add_cog(cog2)
