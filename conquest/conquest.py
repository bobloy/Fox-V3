import json
import pathlib
from io import BytesIO
from typing import Optional

import discord
from PIL import Image
from discord.ext.commands import Greedy
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.data_manager import bundled_data_path, cog_data_path
from shutil import copyfile


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
        self.data_path: pathlib.Path = cog_data_path(self)
        self.asset_path: Optional[pathlib.Path] = None

        self.current_map = None
        self.map_data = None

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    async def load_data(self):
        self.asset_path = bundled_data_path(self) / "asset_path"

    @commands.group(name="conquestset")
    async def conquest_set(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            pass

    @conquest_set.command(name="map")
    async def _conquest_set_map(self, ctx: commands.Context, mapname: str):
        map_dir = self.asset_path / mapname
        if not map_dir.exists() or not map_dir.is_dir():
            await ctx.maybe_send_embed(
                f"Map `{mapname}` was not found in the {self.asset_path} directory"
            )
            return

        self.current_map = mapname
        async with open(self.asset_path / mapname / "data.json") as mapdata:
            self.map_data = json.load(mapdata)

        current_map = self.data_path / self.current_map / "current.jpg"
        if current_map.exists():
            await ctx.maybe_send_embed(
                "This map is already in progress, resuming from last game"
            )
        else:
            copyfile(self.asset_path / mapname / "blank.jpg", current_map)

        await ctx.tick()

    @commands.group()
    async def conquest(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            pass  # TODO: Print current map probably

    @conquest.command("current")
    async def _conquest_current(self, ctx: commands.Context):
        if self.current_map:
            await ctx.maybe_send_embed(
                "No map is currently set. See `[p]conquestset map`"
            )
            return

        with open(self.data_path / self.current_map / "current.jpg") as map_file:
            await ctx.send(file=discord.File(fp=map_file, filename="current_map.jpg"))

    @conquest.command("blank")
    async def _conquest_blank(self, ctx: commands.Context):
        if self.current_map:
            await ctx.maybe_send_embed(
                "No map is currently set. See `[p]conquestset map`"
            )
            return

        with open(self.asset_path / self.current_map / "blank.jpg") as map_file:
            await ctx.send(file=discord.File(fp=map_file, filename="blank_map.jpg"))

    @conquest.command("numbered")
    async def _conquest_numbered(self, ctx: commands.Context):
        if self.current_map:
            await ctx.maybe_send_embed(
                "No map is currently set. See `[p]conquestset map`"
            )
            return

        with open(self.asset_path / self.current_map / "numbered.jpg") as map_file:
            await ctx.send(file=discord.File(fp=map_file, filename="numbered_map.jpg"))

    @conquest.command(name="take")
    async def _conquest_take(
        self, ctx: commands.Context, regions: Greedy[int], color: str
    ):
        if not regions:
            await ctx.send_help()
            return

        for region in regions:
            if region > self.map_data["region_max"] or region < 1:
                await ctx.maybe_send_embed(
                    f"Max region number is {self.map_data['region_max']}, minimum is 1"
                )

        im = Image.open(self.data_path / self.current_map / "current.jpg")
        im2 = Image.new("RGB", im.size, color)
        out = None
        for region in regions:
            mask = Image.open(
                self.asset_path / f"simple_blank_map/masks/{region}.jpg"
            ).convert("L")
            if out is None:
                out = Image.composite(im, im2, mask)
            else:
                out = Image.composite(out, im2, mask)

        output_buffer = BytesIO()
        out.save(output_buffer, "jpeg")
        output_buffer.seek(0)

        # TODO: Save the map in between

        await ctx.send(file=discord.File(fp=output_buffer, filename="map.jpg"))
