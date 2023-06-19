from redbot.core import data_manager

from .conquest import Conquest
from .mapmaker import MapMaker


async def setup(bot):
    cog = Conquest(bot)
    data_manager.bundled_data_path(cog)
    await cog.load_data()

    r = bot.add_cog(cog)
    if r is not None:
        await r

        cog2 = MapMaker(bot)
        r2 = bot.add_cog(cog2)
        if r2 is not None:
            await r2
