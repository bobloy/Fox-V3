import asyncio
import json
import os
import pathlib
from abc import ABC
from shutil import copyfile
from typing import Optional

import discord
from PIL import Image, ImageChops, ImageColor, ImageOps
from discord.ext.commands import Greedy
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.data_manager import bundled_data_path, cog_data_path


class Conquest(commands.Cog):
    """
    Cog for
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
        self.ext = None
        self.ext_format = None

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    async def load_data(self):
        """
        Initial loading of data from bundled_data_path and config
        """
        self.asset_path = bundled_data_path(self) / "assets"
        self.current_map = await self.config.current_map()

        if self.current_map:
            await self.current_map_load()

    async def current_map_load(self):
        map_data_path = self.asset_path / self.current_map / "data.json"
        with map_data_path.open() as mapdata:
            self.map_data: dict = json.load(mapdata)
        self.ext = self.map_data["extension"]
        self.ext_format = "JPEG" if self.ext.upper() == "JPG" else self.ext.upper()

    @commands.group()
    async def conquest(self, ctx: commands.Context):
        """
        Base command for conquest cog. Start with `[p]conquest set map` to select a map.
        """
        if ctx.invoked_subcommand is None and self.current_map is not None:
            await self._conquest_current(ctx)

    @conquest.command(name="list")
    async def _conquest_list(self, ctx: commands.Context):
        """
        List currently available maps
        """
        maps_json = self.asset_path / "maps.json"

        with maps_json.open() as maps:
            maps_json = json.load(maps)
            map_list = "\n".join(maps_json["maps"])
            await ctx.maybe_send_embed(f"Current maps:\n{map_list}")

    @conquest.group(name="set")
    async def conquest_set(self, ctx: commands.Context):
        """Base command for admin actions like selecting a map"""
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
            self.data_path / self.current_map / f"current.{self.ext}", x, y, zoom
        )

        await ctx.send(
            file=discord.File(
                fp=zoomed_path,
                filename=f"current_zoomed.{self.ext}",
            )
        )

    async def _create_zoomed_map(self, map_path, x, y, zoom, **kwargs):
        current_map = Image.open(map_path)

        w, h = current_map.size
        zoom2 = zoom * 2
        zoomed_map = current_map.crop((x - w / zoom2, y - h / zoom2, x + w / zoom2, y + h / zoom2))
        # zoomed_map = zoomed_map.resize((w, h), Image.LANCZOS)
        zoomed_map.save(self.data_path / self.current_map / f"zoomed.{self.ext}", self.ext_format)
        return self.data_path / self.current_map / f"zoomed.{self.ext}"

    @conquest_set.command(name="save")
    async def _conquest_set_save(self, ctx: commands.Context, *, save_name):
        """Save the current map to be loaded later"""
        if self.current_map is None:
            await ctx.maybe_send_embed("No map is currently set. See `[p]conquest set map`")
            return

        current_map_folder = self.data_path / self.current_map
        current_map = current_map_folder / f"current.{self.ext}"

        if not current_map_folder.exists() or not current_map.exists():
            await ctx.maybe_send_embed("Current map doesn't exist! Try setting a new one")
            return

        copyfile(current_map, current_map_folder / f"{save_name}.{self.ext}")
        await ctx.tick()

    @conquest_set.command(name="load")
    async def _conquest_set_load(self, ctx: commands.Context, *, save_name):
        """Load a saved map to be the current map"""
        if self.current_map is None:
            await ctx.maybe_send_embed("No map is currently set. See `[p]conquest set map`")
            return

        current_map_folder = self.data_path / self.current_map
        current_map = current_map_folder / f"current.{self.ext}"
        saved_map = current_map_folder / f"{save_name}.{self.ext}"

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

        await self.current_map_load()

        # map_data_path = self.asset_path / mapname / "data.json"
        # with map_data_path.open() as mapdata:
        #     self.map_data = json.load(mapdata)
        #
        # self.ext = self.map_data["extension"]

        current_map_folder = self.data_path / self.current_map
        current_map = current_map_folder / f"current.{self.ext}"

        if not reset and current_map.exists():
            await ctx.maybe_send_embed(
                "This map is already in progress, resuming from last game\n"
                "Use `[p]conquest set map [mapname] True` to start a new game"
            )
        else:
            if not current_map_folder.exists():
                os.makedirs(current_map_folder)
            copyfile(self.asset_path / mapname / f"blank.{self.ext}", current_map)

        await ctx.tick()

    @conquest.command(name="current")
    async def _conquest_current(self, ctx: commands.Context):
        """
        Send the current map.
        """
        if self.current_map is None:
            await ctx.maybe_send_embed("No map is currently set. See `[p]conquest set map`")
            return

        current_img = self.data_path / self.current_map / f"current.{self.ext}"

        await self._send_maybe_zoomed_map(ctx, current_img, f"current_map.{self.ext}")

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

        current_blank_img = self.asset_path / self.current_map / f"blank.{self.ext}"

        await self._send_maybe_zoomed_map(ctx, current_blank_img, f"blank_map.{self.ext}")

    @conquest.command("numbered")
    async def _conquest_numbered(self, ctx: commands.Context):
        """
        Print the numbered version of the current map, for reference.
        """
        if self.current_map is None:
            await ctx.maybe_send_embed("No map is currently set. See `[p]conquest set map`")
            return

        numbers_path = self.asset_path / self.current_map / f"numbers.{self.ext}"
        if not numbers_path.exists():
            await ctx.send(
                file=discord.File(
                    fp=self.asset_path / self.current_map / f"numbered.{self.ext}",
                    filename=f"numbered.{self.ext}",
                )
            )
            return

        current_map = Image.open(self.data_path / self.current_map / f"current.{self.ext}")
        numbers = Image.open(numbers_path).convert("L")

        inverted_map = ImageOps.invert(current_map)

        loop = asyncio.get_running_loop()
        current_numbered_img = await loop.run_in_executor(
            None, Image.composite, current_map, inverted_map, numbers
        )

        current_numbered_img.save(
            self.data_path / self.current_map / f"current_numbered.{self.ext}", self.ext_format
        )

        await self._send_maybe_zoomed_map(
            ctx,
            self.data_path / self.current_map / f"current_numbered.{self.ext}",
            f"current_numbered.{self.ext}",
        )

    @conquest.command(name="multitake")
    async def _conquest_multitake(
        self, ctx: commands.Context, start_region: int, end_region: int, color: str
    ):
        if self.current_map is None:
            await ctx.maybe_send_embed("No map is currently set. See `[p]conquest set map`")
            return

        try:
            color = ImageColor.getrgb(color)
        except ValueError:
            await ctx.maybe_send_embed(f"Invalid color {color}")
            return

        if end_region > self.map_data["region_max"] or start_region < 1:
            await ctx.maybe_send_embed(
                f"Max region number is {self.map_data['region_max']}, minimum is 1"
            )
            return
        regions = [r for r in range(start_region, end_region + 1)]

        await self._process_take_regions(color, ctx, regions)

    async def _process_take_regions(self, color, ctx, regions):
        current_img_path = self.data_path / self.current_map / f"current.{self.ext}"
        im = Image.open(current_img_path)
        async with ctx.typing():
            out: Image.Image = await self._composite_regions(im, regions, color)
            out.save(current_img_path, self.ext_format)
            await self._send_maybe_zoomed_map(ctx, current_img_path, f"map.{self.ext}")

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
                return

        await self._process_take_regions(color, ctx, regions)

    async def _composite_regions(self, im, regions, color) -> Image.Image:
        im2 = Image.new("RGB", im.size, color)

        loop = asyncio.get_running_loop()

        combined_mask = None
        for region in regions:
            mask = Image.open(
                self.asset_path / self.current_map / "masks" / f"{region}.{self.ext}"
            ).convert("L")
            if combined_mask is None:
                combined_mask = mask
            else:
                # combined_mask = ImageChops.logical_or(combined_mask, mask)
                combined_mask = await loop.run_in_executor(
                    None, ImageChops.multiply, combined_mask, mask
                )

        out = await loop.run_in_executor(None, Image.composite, im, im2, combined_mask)

        return out
