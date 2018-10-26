from redbot.core import data_manager
from .skyrim import Skyrim


def setup(bot):
    cog = Skyrim()
    data_manager.load_bundled_data(cog, __file__)
    bot.add_cog(cog)
