import asyncio
import json
import pathlib
from io import BytesIO
from shutil import copyfile
from typing import Optional, Union

import discord
from PIL import Image, ImageChops, ImageColor, ImageOps
from discord.ext.commands import Greedy
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.data_manager import bundled_data_path, cog_data_path
from redbot.core.utils.predicates import MessagePredicate

from conquest.regioner import Regioner, get_center


class Conquest(commands.Cog):
    """
    Cog for creating and modifying maps for RPGs and War Games
    """

    default_zoom_json = {"enabled": False, "x": -1, "y": -1, "zoom": 1.0}

    default_custom_map = {
        "name": "",
        "regions": {},
        "region_max": 0,
        "extension": "png",
        "custom": True,
    }

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=67111110113117101115116, force_registration=True
        )

        default_guild = {}
        default_global = {"current_map": None, "is_custom": False}
        self.config.register_guild(**default_guild)
        self.config.register_global(**default_global)

        self.data_path: pathlib.Path = cog_data_path(self)

        self.custom_map_path = self.data_path / "custom_maps"
        if not self.custom_map_path.exists() or not self.custom_map_path.is_dir():
            self.custom_map_path.mkdir()

        self.current_map_folder = self.data_path / "current_maps"
        if not self.current_map_folder.exists() or not self.current_map_folder.is_dir():
            self.current_map_folder.mkdir()

        self.asset_path: Optional[pathlib.Path] = None

        self.is_custom = False
        self.current_map = None
        self.map_data = None
        self.ext = None
        self.ext_format = None

        self.mm = {}
        self.mm_img: Union[Image.Image, None] = None

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    def _path_if_custom(self, custom_custom: bool = None) -> pathlib.Path:
        check_value = custom_custom if custom_custom is not None else self.is_custom
        if check_value:
            return self.custom_map_path
        return self.asset_path

    async def load_data(self):
        """
        Initial loading of data from bundled_data_path and config
        """
        self.asset_path = bundled_data_path(self) / "assets"
        self.current_map = await self.config.current_map()
        self.is_custom = await self.config.is_custom()

        if self.current_map:
            await self.current_map_load()

    async def current_map_load(self):
        map_path = self._path_if_custom()
        map_data_path = map_path / self.current_map / "data.json"
        with map_data_path.open() as mapdata:
            self.map_data: dict = json.load(mapdata)
        self.ext = self.map_data["extension"]
        self.ext_format = "JPEG" if self.ext.upper() == "JPG" else self.ext.upper()

    async def _get_current_map_path(self):
        return self.current_map_folder / self.current_map

    async def _create_zoomed_map(self, map_path, x, y, zoom, **kwargs):
        current_map = Image.open(map_path)

        w, h = current_map.size
        zoom2 = zoom * 2
        zoomed_map = current_map.crop((x - w / zoom2, y - h / zoom2, x + w / zoom2, y + h / zoom2))
        # zoomed_map = zoomed_map.resize((w, h), Image.LANCZOS)
        current_map_path_ = await self._get_current_map_path()
        zoomed_map.save(current_map_path_ / f"zoomed.{self.ext}", self.ext_format)
        return current_map_path_ / f"zoomed.{self.ext}"

    async def _send_maybe_zoomed_map(self, ctx, map_path, filename):
        zoom_data = {"enabled": False}

        zoom_json_path = await self._get_current_map_path() / "settings.json"

        if zoom_json_path.exists():
            with zoom_json_path.open() as zoom_json:
                zoom_data = json.load(zoom_json)

        if zoom_data["enabled"]:
            map_path = await self._create_zoomed_map(map_path, **zoom_data)

        await ctx.send(file=discord.File(fp=map_path, filename=filename))

    async def _process_take_regions(self, color, ctx, regions):
        current_img_path = await self._get_current_map_path() / f"current.{self.ext}"
        im = Image.open(current_img_path)
        async with ctx.typing():
            out: Image.Image = await self._composite_regions(im, regions, color,
                                                             self._path_if_custom() / self.current_map)
            out.save(current_img_path, self.ext_format)
            await self._send_maybe_zoomed_map(ctx, current_img_path, f"map.{self.ext}")

    async def _composite_regions(self, im, regions, color, region_path) -> Image.Image:
        im2 = Image.new("RGB", im.size, color)

        loop = asyncio.get_running_loop()

        combined_mask = None
        for region in regions:
            mask = Image.open(
                region_path / "masks" / f"{region}.{self.ext}"
            ).convert("1")
            if combined_mask is None:
                combined_mask = mask
            else:
                # combined_mask = ImageChops.logical_or(combined_mask, mask)
                combined_mask = await loop.run_in_executor(
                    None, ImageChops.logical_and, combined_mask, mask
                )

        out = await loop.run_in_executor(None, Image.composite, im, im2, combined_mask.covert("L"))

        return out

    async def _mm_save_map(self, ctx, map_name, target_save):
        self.mm["name"] = map_name
        if target_save.exists() and target_save.is_dir():
            # This is an overwrite operation
            # await ctx.maybe_send_embed(f"{map_name} already exists, okay to overwrite?")
            #
            # pred = MessagePredicate.yes_or_no(ctx)
            # try:
            #     await self.bot.wait_for("message", check=pred, timeout=30)
            # except TimeoutError:
            #     await ctx.maybe_send_embed("Response timed out, cancelling save")
            #     return
            # if not pred.result:
            #     return
            await ctx.maybe_send_embed("Overwrite currently not supported")
            return False

        # This is a new name
        target_save.mkdir()
        ext = self.mm["extension"]
        ext_format = "JPEG" if ext.upper() == "JPG" else ext.upper()
        self.mm_img.save(target_save / f"blank.{ext}", ext_format)

        await self._save_mm_data(target_save)

        return True

    async def _save_mm_data(self, target_save):
        data_json = target_save / "data.json"
        with data_json.open("w+") as dj:
            json.dump(self.mm, dj)

    @commands.group()
    async def mapmaker(self, ctx: commands.context):
        """
        Base command for managing current maps or creating new ones
        """
        if ctx.invoked_subcommand is None:
            pass

    @mapmaker.command(name="close")
    async def _mapmaker_close(self, ctx: commands.Context):
        """Close the currently open map."""
        self.mm = {}
        self.mm_img = None

        await ctx.tick()

    @mapmaker.command(name="save")
    async def _mapmaker_save(self, ctx: commands.Context, *, map_name: str):
        """Save the current map to the specified map name"""
        if not self.mm:
            await ctx.maybe_send_embed("No map currently being worked on")
            return

        if not self.mm_img:
            await ctx.maybe_send_embed("No map image to save")
            return

        if self.mm["name"] == map_name:
            await ctx.maybe_send_embed("This map already has that name, no reason to save")
            return

        target_save = self.custom_map_path / map_name

        result = await self._mm_save_map(ctx, map_name, target_save)
        if not result:
            await ctx.maybe_send_embed("Failed to save to that name")
        else:
            await ctx.maybe_send_embed(f"Map successfully saved to {target_save}")

    @mapmaker.command(name="upload")
    async def _mapmaker_upload(self, ctx: commands.Context, map_name: str, map_path=""):
        """Load a map image to be modified. Upload one with this command or provide a path"""
        message: discord.Message = ctx.message
        if not message.attachments and not map_path:
            await ctx.maybe_send_embed(
                "Either upload an image with this command or provide a path to the image"
            )
            return

        target_save = self.custom_map_path / map_name

        if target_save.exists() and target_save.is_dir():
            await ctx.maybe_send_embed(f"{map_name} already exists, okay to overwrite?")

            pred = MessagePredicate.yes_or_no(ctx)
            try:
                await self.bot.wait_for("message", check=pred, timeout=30)
            except TimeoutError:
                await ctx.maybe_send_embed("Response timed out, cancelling save")
                return
            if not pred.result:
                return

        if not self.mm:
            self.mm = self.default_custom_map.copy()

        if map_path:
            map_path = pathlib.Path(map_path)

            if not map_path.exist():
                await ctx.maybe_send_embed("Map not found at that path")
                return

            self.mm_img = Image.open(map_path)
            self.mm["extension"] = map_path.suffix[1:]

        elif message.attachments:
            attch: discord.Attachment = message.attachments[0]
            # attch_file = await attch.to_file()

            buffer = BytesIO()
            await attch.save(buffer)

            self.mm_img: Image.Image = Image.open(buffer)

            self.mm["extension"] = pathlib.Path(attch.filename).suffix[1:]
        else:
            # Wait what?
            return

        result = await self._mm_save_map(ctx, map_name, target_save)

        if not result:
            self.mm = {}
            self.mm_img = None
            await ctx.maybe_send_embed("Failed to upload to that name")
        else:
            await ctx.maybe_send_embed(f"Map successfully uploaded to {target_save}")

    @mapmaker.command(name="sample")
    async def _mapmaker_sample(self, ctx: commands.Context):
        """Print the currently being modified map as a sample"""
        if not self.mm:
            await ctx.maybe_send_embed("No map currently being worked on")
            return

        if not self.mm_img:
            await ctx.maybe_send_embed("No map image has been loaded")
            return

        async with ctx.typing():
            map_dir = self.custom_map_path / self.mm["name"]

            files = []

            file1 = discord.File(map_dir / f"blank.{self.mm['extension']}")

            files.append(file1)

            masks_dir = map_dir / "masks"
            if masks_dir.exists() and masks_dir.is_dir():
                loop = asyncio.get_running_loop()
                current_map = Image.open(map_dir / f"blank.{self.mm['extension']}")

                regions = list(self.mm["regions"].keys())
                fourth = len(regions) // 4

                current_map = await self._composite_regions(
                    current_map, regions[:fourth], ImageColor.getrgb("red"), map_dir
                )
                current_map = await self._composite_regions(
                    current_map, regions[fourth: fourth * 2], ImageColor.getrgb("green"), map_dir
                )
                current_map = await self._composite_regions(
                    current_map, regions[fourth * 2: fourth * 3], ImageColor.getrgb("blue"), map_dir
                )
                current_map = await self._composite_regions(
                    current_map, regions[fourth * 3:], ImageColor.getrgb("yellow"), map_dir
                )

                numbers = Image.open(map_dir / "numbers.png").convert("L")
                inverted_map = ImageOps.invert(current_map)
                current_numbered_img = await loop.run_in_executor(
                    None, Image.composite, current_map, inverted_map, numbers
                )

                buffer1 = BytesIO()
                buffer2 = BytesIO()

                current_map.save(buffer1, "png")
                buffer1.seek(0)
                current_numbered_img.save(buffer2, "png")
                buffer2.seek(0)

                files.append(discord.File(fp=buffer1, filename="colored_map.png"))
                files.append(discord.File(fp=buffer2, filename="with_numbers.png"))

            for f in files:
                await ctx.send(file=f)

    @mapmaker.command(name="load")
    async def _mapmaker_load(self, ctx: commands.Context, map_name: str):
        """Load an existing map to be modified."""
        if self.mm or self.mm_img:
            await ctx.maybe_send_embed("There is a current map in progres. Close it first with `[p]mapmaker close`")
            return

        map_path = self.custom_map_path / map_name

        if not map_path.exists() or not map_path.is_dir():
            await ctx.maybe_send_embed(f"Map {map_name} not found in {self.custom_map_path}")
            return

        maps_json = map_path / "data.json"

        with maps_json.open() as maps:
            self.mm = json.load(maps)

        self.mm_img = Image.open(map_path / f"blank.{self.mm['extension']}")

        await ctx.tick()

    @mapmaker.group(name="masks")
    async def _mapmaker_masks(self, ctx: commands.Context):
        """Base command for managing map masks"""
        if ctx.invoked_subcommand is None:
            pass

    @_mapmaker_masks.command(name="generate")
    async def _mapmaker_masks_generate(self, ctx: commands.Context):
        """
        Generate masks for the map

        Currently only works on maps with black borders and white regions.
        Non-white regions are ignored (i.e. blue water)
        """
        if not self.mm:
            await ctx.maybe_send_embed("No map currently being worked on")
            return

        if not self.mm_img:
            await ctx.maybe_send_embed("No map image to save")
            return

        map_dir = self.custom_map_path / self.mm["name"]
        masks_dir = map_dir / "masks"
        if masks_dir.exists() and masks_dir.is_dir():
            await ctx.maybe_send_embed("Mask folder already exists, delete this before continuing")
            return

        # Done by Regioner
        # masks_dir.mkdir()

        regioner = Regioner(filename=f"blank.{self.mm['extension']}", filepath=map_dir)

        loop = asyncio.get_running_loop()
        with ctx.typing():
            regions = await loop.run_in_executor(None, regioner.execute)

        if not regions:
            await ctx.maybe_send_embed("Failed to generate masks")
            return

        self.mm["regions"] = regions
        self.mm["region_max"] = len(regions) + 1

        await self._save_mm_data(map_dir)

        await ctx.maybe_send_embed(f"{len(regions)} masks generated into {masks_dir}")

    @_mapmaker_masks.command(name="combine")
    async def _mapmaker_masks_combine(
            self, ctx: commands.Context, mask_list: Greedy[int], recommended=False
    ):
        """Generate masks for the map"""
        if not self.mm:
            await ctx.maybe_send_embed("No map currently being worked on")
            return

        if not self.mm_img:
            await ctx.maybe_send_embed("No map image to save")
            return

        if recommended and mask_list:
            await ctx.maybe_send_embed(
                "Can't combine recommend masks and a mask list at the same time, pick one"
            )
            return

        map_dir = self.custom_map_path / self.mm["name"]
        masks_dir = map_dir / "masks"
        if not masks_dir.exists() or not masks_dir.is_dir():
            await ctx.maybe_send_embed("There are no masks")
            return

        if not recommended:
            for mask in mask_list:
                m = masks_dir / f"{mask}.png"
                if not m.exists():
                    await ctx.maybe_send_embed(f"Mask #{mask} does not exist")
                    return
        else:
            await ctx.send("Not Implemented")
            return

        regioner = Regioner(filename=f"blank.{self.mm['extension']}", filepath=map_dir)

        loop = asyncio.get_running_loop()
        lowest, eliminated = await loop.run_in_executor(None, regioner.combine_masks, mask_list)

        if not lowest:
            await ctx.maybe_send_embed("Failed to combine masks")
            return

        points = [self.mm["regions"][f"{n}"] for n in mask_list]
        self.mm["regions"][f"{lowest}"] = get_center(points)

        for key in eliminated:
            self.mm["regions"].pop(f"{key}")

        future = await loop.run_in_executor(None, regioner.create_number_mask, self.mm["regions"])

        if not future:
            await ctx.maybe_send_embed(
                "Failed to generate number mask, try running this command again"
            )

        await self._save_mm_data(map_dir)

    @commands.group()
    async def conquest(self, ctx: commands.Context):
        """
        Base command for conquest cog. Start with `[p]conquest set map` to select a map.
        """
        if ctx.invoked_subcommand is None:
            if self.current_map is not None:
                await self._conquest_current(ctx)

    @conquest.command(name="list")
    async def _conquest_list(self, ctx: commands.Context):
        """
        List currently available maps
        """
        maps_json = self._path_if_custom() / "maps.json"

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

        zoom_json_path = await self._get_current_map_path() / "settings.json"
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

        zoom_json_path = await self._get_current_map_path() / "settings.json"

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
            await self._get_current_map_path() / f"current.{self.ext}", x, y, zoom
        )

        await ctx.send(file=discord.File(fp=zoomed_path, filename=f"current_zoomed.{self.ext}",))

    @conquest_set.command(name="save")
    async def _conquest_set_save(self, ctx: commands.Context, *, save_name):
        """Save the current map to be loaded later"""
        if self.current_map is None:
            await ctx.maybe_send_embed("No map is currently set. See `[p]conquest set map`")
            return

        current_map_folder = await self._get_current_map_path()
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

        current_map_folder = await self._get_current_map_path()
        current_map = current_map_folder / f"current.{self.ext}"
        saved_map = current_map_folder / f"{save_name}.{self.ext}"

        if not current_map_folder.exists() or not saved_map.exists():
            await ctx.maybe_send_embed(f"Saved map not found in the {self.current_map} folder")
            return

        copyfile(saved_map, current_map)
        await ctx.tick()

    @conquest_set.command(name="map")
    async def _conquest_set_map(
            self, ctx: commands.Context, mapname: str, is_custom: bool = False, reset: bool = False
    ):
        """
        Select a map from current available maps

        To add more maps, see the guide (WIP)
        """
        check_path = self._path_if_custom(is_custom)

        map_dir = check_path / mapname
        if not map_dir.exists() or not map_dir.is_dir():
            await ctx.maybe_send_embed(
                f"Map `{mapname}` was not found in the {check_path} directory"
            )
            return

        self.current_map = mapname
        self.is_custom = is_custom
        await self.config.current_map.set(self.current_map)  # Save to config too
        await self.config.is_custom.set(is_custom)

        await self.current_map_load()

        current_map_folder = await self._get_current_map_path()
        current_map = current_map_folder / f"current.{self.ext}"

        if not reset and current_map.exists():
            await ctx.maybe_send_embed(
                "This map is already in progress, resuming from last game\n"
                "Use `[p]conquest set map [mapname] True` to start a new game"
            )
        else:
            if not current_map_folder.exists():
                current_map_folder.mkdir()
            copyfile(check_path / mapname / f"blank.{self.ext}", current_map)

        await ctx.tick()

    @conquest.command(name="current")
    async def _conquest_current(self, ctx: commands.Context):
        """
        Send the current map.
        """
        if self.current_map is None:
            await ctx.maybe_send_embed("No map is currently set. See `[p]conquest set map`")
            return

        current_img = await self._get_current_map_path() / f"current.{self.ext}"

        await self._send_maybe_zoomed_map(ctx, current_img, f"current_map.{self.ext}")

    @conquest.command("blank")
    async def _conquest_blank(self, ctx: commands.Context):
        """
        Print the blank version of the current map, for reference.
        """
        if self.current_map is None:
            await ctx.maybe_send_embed("No map is currently set. See `[p]conquest set map`")
            return

        current_blank_img = self._path_if_custom() / self.current_map / f"blank.{self.ext}"

        await self._send_maybe_zoomed_map(ctx, current_blank_img, f"blank_map.{self.ext}")

    @conquest.command("numbered")
    async def _conquest_numbered(self, ctx: commands.Context):
        """
        Print the numbered version of the current map, for reference.
        """
        if self.current_map is None:
            await ctx.maybe_send_embed("No map is currently set. See `[p]conquest set map`")
            return

        numbers_path = self._path_if_custom() / self.current_map / f"numbers.{self.ext}"
        if not numbers_path.exists():
            await ctx.send(
                file=discord.File(
                    fp=self._path_if_custom() / self.current_map / f"numbered.{self.ext}",
                    filename=f"numbered.{self.ext}",
                )
            )
            return

        current_map_path = await self._get_current_map_path()
        current_map = Image.open(current_map_path / f"current.{self.ext}")
        numbers = Image.open(numbers_path).convert("L")

        inverted_map = ImageOps.invert(current_map)

        loop = asyncio.get_running_loop()
        current_numbered_img = await loop.run_in_executor(
            None, Image.composite, current_map, inverted_map, numbers
        )

        current_numbered_img.save(
            current_map_path / f"current_numbered.{self.ext}", self.ext_format
        )

        await self._send_maybe_zoomed_map(
            ctx, current_map_path / f"current_numbered.{self.ext}", f"current_numbered.{self.ext}",
        )

    @conquest.command(name="multitake")
    async def _conquest_multitake(
        self, ctx: commands.Context, start_region: int, end_region: int, color: str
    ):
        """
        Claim all the territories between the two provided region numbers (inclusive)

        :param start_region:
        """
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

        if start_region < end_region:
            start_region, end_region = end_region, start_region

        regions = [r for r in range(start_region, end_region + 1)]

        await self._process_take_regions(color, ctx, regions)

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
