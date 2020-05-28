from redbot.core import data_manager

from .recyclingplant import RecyclingPlant


def setup(bot):
    plant = RecyclingPlant(bot)
    data_manager.bundled_data_path(plant)
    bot.add_cog(plant)
