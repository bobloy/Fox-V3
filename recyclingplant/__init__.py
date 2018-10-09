from redbot.core import data_manager

from .recyclingplant import RecyclingPlant


def setup(bot):
    plant = RecyclingPlant(bot)
    data_manager.load_bundled_data(plant, __file__)
    bot.add_cog(plant)
