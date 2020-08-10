import json
import os
import pathlib
from shutil import copyfile
from typing import Optional

import discord
from PIL import Image, ImageColor
from discord.ext.commands import Greedy
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.data_manager import bundled_data_path, cog_data_path


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
        self.asset_path = bundled_data_path(self) / "assets"
        print(self.asset_path)

    @commands.group()
    async def conquest(self, ctx: commands.Context):
        """
        Base command for conquest cog. Start with `[p]conquest set map` to select a map.
        """
        if ctx.invoked_subcommand is None:
            pass  # TODO: Print current map probably

    @conquest.command(name="list")
    async def _conquest_list(self, ctx: commands.Context):
        """
        List currently available maps
        """
        maps_json = self.asset_path / "maps.json"

        with maps_json.open() as maps:
            maps_json = json.load(maps)
            map_list = "\n".join(map_name for map_name in maps_json["maps"])
            await ctx.maybe_send_embed(f"Current maps:\n{map_list}")

    @conquest.group(name="set")
    async def conquest_set(self, ctx: commands.Context):
        """Base command for admin actions like selecting a map"""
        if ctx.invoked_subcommand is None:
            pass

    @conquest_set.command(name="save")
    async def _conquest_set_save(self, ctx: commands.Context, *, save_name):
        """Save the current map to be loaded later"""
        if self.current_map is None:
            await ctx.maybe_send_embed("No map is currently set. See `[p]conquest set map`")
            return

        current_map_folder = self.data_path / self.current_map
        current_map = current_map_folder / "current.jpg"

        if not current_map_folder.exists() or not current_map.exists():
            await ctx.maybe_send_embed("Current map doesn't exist! Try settin a new one")
            return

        copyfile(current_map, current_map_folder / f"{save_name}.jpg")
        await ctx.tick()

    @conquest_set.command(name="load")
    async def _conquest_set_load(self, ctx: commands.Context, *, save_name):
        """Load a saved map to be the current map"""
        if self.current_map is None:
            await ctx.maybe_send_embed("No map is currently set. See `[p]conquest set map`")
            return

        current_map_folder = self.data_path / self.current_map
        current_map = current_map_folder / "current.jpg"
        saved_map = current_map_folder / f"{save_name}.jpg"

        if not current_map_folder.exists() or not saved_map.exists():
            await ctx.maybe_send_embed(f"Saved map not found in the {self.current_map} folder")
            return

        copyfile(saved_map, current_map)
        await ctx.tick()

    @conquest_set.command(name="map")
    async def _conquest_set_map(self, ctx: commands.Context, mapname: str, reset: bool = False):
        """
        Select a map from current available maps

        To add more maps, see the guide (WIP)
        """
        map_dir = self.asset_path / mapname
        if not map_dir.exists() or not map_dir.is_dir():
            await ctx.maybe_send_embed(
                f"Map `{mapname}` was not found in the {self.asset_path} directory"
            )
            return

        self.current_map = mapname
        map_data_path = self.asset_path / mapname / "data.json"
        with map_data_path.open() as mapdata:
            self.map_data = json.load(mapdata)

        current_map_folder = self.data_path / self.current_map
        current_map = current_map_folder / "current.jpg"

        if not reset and current_map.exists():
            await ctx.maybe_send_embed(
                "This map is already in progress, resuming from last game\n"
                "Use `[p]conquest set map [mapname] True` to start a new game"
            )
        else:
            if not current_map_folder.exists():
                os.makedirs(current_map_folder)
            copyfile(self.asset_path / mapname / "blank.jpg", current_map)

        await ctx.tick()

    @conquest.command(name="current")
    async def _conquest_current(self, ctx: commands.Context):
        """
        Send the current map.
        """
        if self.current_map is None:
            await ctx.maybe_send_embed("No map is currently set. See `[p]conquest set map`")
            return

        current_jpg = self.data_path / self.current_map / "current.jpg"
        await ctx.send(file=discord.File(fp=current_jpg, filename="current_map.jpg"))

    @conquest.command("blank")
    async def _conquest_blank(self, ctx: commands.Context):
        """
        Print the blank version of the current map, for reference.
        """
        if self.current_map is None:
            await ctx.maybe_send_embed("No map is currently set. See `[p]conquest set map`")
            return

        current_blank_jpg = self.asset_path / self.current_map / "blank.jpg"
        await ctx.send(file=discord.File(fp=current_blank_jpg, filename="blank_map.jpg"))

    @conquest.command("numbered")
    async def _conquest_numbered(self, ctx: commands.Context):
        """
        Print the numbered version of the current map, for reference.
        """
        if self.current_map is None:
            await ctx.maybe_send_embed("No map is currently set. See `[p]conquest set map`")
            return

        current_numbered_jpg = self.asset_path / self.current_map / "numbered.jpg"
        await ctx.send(file=discord.File(fp=current_numbered_jpg, filename="numbered_map.jpg"))

    @conquest.command(name="take")
    async def _conquest_take(self, ctx: commands.Context, regions: Greedy[int], *, color: str):
        """
        Claim a territory or list of territories for a specified color

        :param regions: List of integer regions
        :param color: Color to claim regions
        """
        if not regions:
            await ctx.send_help()
            return

        if self.current_map is None:
            await ctx.maybe_send_embed("No map is currently set. See `[p]conquest set map`")
            return

        try:
            color = ImageColor.getrgb(color)
        except ValueError:
            await ctx.maybe_send_embed(f"Invalid color {color}")
            return

        for region in regions:
            if region > self.map_data["region_max"] or region < 1:
                await ctx.maybe_send_embed(
                    f"Max region number is {self.map_data['region_max']}, minimum is 1"
                )

        current_jpg_path = self.data_path / self.current_map / "current.jpg"
        im = Image.open(current_jpg_path)
        out: Image.Image = await self._composite_image(im, regions, color)

        out.save(current_jpg_path, "jpeg")

        await ctx.send(file=discord.File(fp=current_jpg_path, filename="map.jpg"))

    async def _composite_image(self, im, regions, color) -> Image.Image:

        im2 = Image.new("RGB", im.size, color)

        out = None
        for region in regions:
            mask = Image.open(
                self.asset_path / self.current_map / "masks" / f"{region}.jpg"
            ).convert("L")
            if out is None:
                out = Image.composite(im, im2, mask)
            else:
                out = Image.composite(out, im2, mask)
        return out
