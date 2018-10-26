from redbot.core import data_manager

from .planttycoon import PlantTycoon


def setup(bot):
    tycoon = PlantTycoon(bot)
    data_manager.load_bundled_data(tycoon, __file__)
    bot.add_cog(tycoon)
