from redbot.core import data_manager

from .planttycoon import PlantTycoon


async def setup(bot):
    cog = PlantTycoon(bot)
    data_manager.bundled_data_path(cog)
    await cog._load_plants_products()  # I can access protected members if I want, linter!!
    r = bot.add_cog(cog)
    if r is not None:
        await r
