from io import BytesIO

from PIL import Image
from redbot.core import Config, commands
from redbot.core.bot import Red

import discord
import numpy as np
from redbot.core.data_manager import bundled_data_path
from skimage.color import rgb2lab, rgb2gray, lab2rgb
from skimage.io import imread, imshow
import matplotlib.pyplot as plt


class Conquest(commands.Cog):
    """
    Cog Description

    Less important information about the cog
    """

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=0, force_registration=True)

        default_guild = {}

        self.config.register_guild(**default_guild)

        self.assets = None

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    async def load_data(self):
        self.assets = bundled_data_path(self) / "assets"

    @commands.command()
    async def conquest(self, ctx: commands.Context, region: int, color: str):

        im = Image.open(self.assets / "simple_blank_map/blank.jpg")
        im2 = Image.new("RGB", im.size, color)
        mask = Image.open(self.assets / f"simple_blank_map/masks/{region}.jpg").convert('L')

        out: Image.Image = Image.composite(im, im2, mask)

        output_buffer = BytesIO()
        out.save(output_buffer, "jpeg")
        output_buffer.seek(0)

        # TODO: Save the map in between

        await ctx.send(file=discord.File(fp=output_buffer, filename="map.jpg"))
