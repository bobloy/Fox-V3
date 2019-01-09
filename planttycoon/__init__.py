from redbot.core import data_manager

from .planttycoon import PlantTycoon


async def setup(bot):
    tycoon = PlantTycoon(bot)
    data_manager.load_bundled_data(tycoon, __file__)
    await tycoon._load_plants_products()  # I can access protected members if I want, linter!!
    bot.add_cog(tycoon)
