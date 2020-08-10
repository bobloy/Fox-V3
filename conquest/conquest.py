import json
import os
import pathlib
from shutil import copyfile
from typing import Optional

import discord
from PIL import Image, ImageColor, ImageOps
from discord.ext.commands import Greedy
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.data_manager import bundled_data_path, cog_data_path


class Conquest(commands.Cog):
    """
    Cog Description

    Less important information about the cog
    """

    default_zoom_json = {"enabled": False, "x": -1, "y": -1, "zoom": 1.0}

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=67111110113117101115116, force_registration=True
        )

        default_guild = {}
        default_global = {"current_map": None}
        self.config.register_guild(**default_guild)
        self.config.register_global(**default_global)

        self.data_path: pathlib.Path = cog_data_path(self)
        self.asset_path: Optional[pathlib.Path] = None

        self.current_map = None
        self.map_data = None

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    async def load_data(self):
        self.asset_path = bundled_data_path(self) / "assets"
        self.current_map = await self.config.current_map()

        map_data_path = self.asset_path / self.current_map / "data.json"
        with map_data_path.open() as mapdata:
            self.map_data = json.load(mapdata)

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

    @conquest_set.command(name="resetzoom")
    async def _conquest_set_resetzoom(self, ctx: commands.Context):
        """Resets the zoom level of the current map"""
        if self.current_map is None:
            await ctx.maybe_send_embed("No map is currently set. See `[p]conquest set map`")
            return

        zoom_json_path = self.data_path / self.current_map / "settings.json"
        if not zoom_json_path.exists():
            await ctx.maybe_send_embed(
                f"No zoom data found for {self.current_map}, reset not needed"
            )
            return

        with zoom_json_path.open("w+") as zoom_json:
            json.dump({"enabled": False}, zoom_json)

        await ctx.tick()

    @conquest_set.command(name="zoom")
    async def _conquest_set_zoom(self, ctx: commands.Context, x: int, y: int, zoom: float):
        """
        Set the zoom level and position of the current map

        x: positive integer
        y: positive integer
        zoom: float greater than or equal to 1
        """
        if self.current_map is None:
            await ctx.maybe_send_embed("No map is currently set. See `[p]conquest set map`")
            return

        if x < 0 or y < 0 or zoom < 1:
            await ctx.send_help()
            return

        zoom_json_path = self.data_path / self.current_map / "settings.json"

        zoom_data = self.default_zoom_json.copy()
        zoom_data["enabled"] = True
        zoom_data["x"] = x
        zoom_data["y"] = y
        zoom_data["zoom"] = zoom

        with zoom_json_path.open("w+") as zoom_json:
            json.dump(zoom_data, zoom_json)

        await ctx.tick()

    @conquest_set.command(name="zoomtest")
    async def _conquest_set_zoomtest(self, ctx: commands.Context, x: int, y: int, zoom: float):
        """
        Test the zoom level and position of the current map

        x: positive integer
        y: positive integer
        zoom: float greater than or equal to 1
        """
        if self.current_map is None:
            await ctx.maybe_send_embed("No map is currently set. See `[p]conquest set map`")
            return

        if x < 0 or y < 0 or zoom < 1:
            await ctx.send_help()
            return

        zoomed_path = await self._create_zoomed_map(
            self.data_path / self.current_map / "current.jpg", x, y, zoom
        )

        await ctx.send(file=discord.File(fp=zoomed_path, filename="current_zoomed.jpg",))

    async def _create_zoomed_map(self, map_path, x, y, zoom, **kwargs):
        current_map = Image.open(map_path)

        w, h = current_map.size
        zoom2 = zoom * 2
        zoomed_map = current_map.crop((x - w / zoom2, y - h / zoom2, x + w / zoom2, y + h / zoom2))
        # zoomed_map = zoomed_map.resize((w, h), Image.LANCZOS)
        zoomed_map.save(self.data_path / self.current_map / "zoomed.jpg", "jpeg")
        return self.data_path / self.current_map / "zoomed.jpg"

    @conquest_set.command(name="save")
    async def _conquest_set_save(self, ctx: commands.Context, *, save_name):
        """Save the current map to be loaded later"""
        if self.current_map is None:
            await ctx.maybe_send_embed("No map is currently set. See `[p]conquest set map`")
            return

        current_map_folder = self.data_path / self.current_map
        current_map = current_map_folder / "current.jpg"

        if not current_map_folder.exists() or not current_map.exists():
            await ctx.maybe_send_embed("Current map doesn't exist! Try setting a new one")
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
        await self.config.current_map.set(self.current_map)  # Save to config too

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

        await self._send_maybe_zoomed_map(ctx, current_jpg, "current_map.jpg")

    async def _send_maybe_zoomed_map(self, ctx, map_path, filename):
        zoom_data = {"enabled": False}

        zoom_json_path = self.data_path / self.current_map / "settings.json"

        if zoom_json_path.exists():
            with zoom_json_path.open() as zoom_json:
                zoom_data = json.load(zoom_json)

        if zoom_data["enabled"]:
            map_path = await self._create_zoomed_map(map_path, **zoom_data)

        await ctx.send(file=discord.File(fp=map_path, filename=filename))

    @conquest.command("blank")
    async def _conquest_blank(self, ctx: commands.Context):
        """
        Print the blank version of the current map, for reference.
        """
        if self.current_map is None:
            await ctx.maybe_send_embed("No map is currently set. See `[p]conquest set map`")
            return

        current_blank_jpg = self.asset_path / self.current_map / "blank.jpg"

        await self._send_maybe_zoomed_map(ctx, current_blank_jpg, "blank_map.jpg")
        # await ctx.send(file=discord.File(fp=current_blank_jpg, filename="blank_map.jpg"))

    @conquest.command("numbered")
    async def _conquest_numbered(self, ctx: commands.Context):
        """
        Print the numbered version of the current map, for reference.
        """
        if self.current_map is None:
            await ctx.maybe_send_embed("No map is currently set. See `[p]conquest set map`")
            return

        numbers_path = self.asset_path / self.current_map / "numbers.jpg"
        if not numbers_path.exists():
            await ctx.send(
                file=discord.File(
                    fp=self.asset_path / self.current_map / "numbered.jpg",
                    filename="numbered.jpg",
                )
            )
            return

        current_map = Image.open(self.data_path / self.current_map / "current.jpg")
        numbers = Image.open(numbers_path).convert("L")

        inverted_map = ImageOps.invert(current_map)

        current_numbered_jpg: Image.Image = Image.composite(current_map, inverted_map, numbers)
        current_numbered_jpg.save(
            self.data_path / self.current_map / "current_numbered.jpg", "jpeg"
        )

        await self._send_maybe_zoomed_map(
            ctx, self.data_path / self.current_map / "current_numbered.jpg", "current_numbered.jpg"
        )
        # await ctx.send(
        #     file=discord.File(
        #         fp=self.data_path / self.current_map / "current_numbered.jpg",
        #         filename="current_numbered.jpg",
        #     )
        # )

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
        out: Image.Image = await self._composite_regions(im, regions, color)

        out.save(current_jpg_path, "jpeg")

        await self._send_maybe_zoomed_map(ctx, current_jpg_path, "map.jpg")
        # await ctx.send(file=discord.File(fp=current_jpg_path, filename="map.jpg"))

    async def _composite_regions(self, im, regions, color) -> Image.Image:

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
