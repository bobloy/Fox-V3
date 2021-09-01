import asyncio
import json
import logging
import pathlib
from collections import defaultdict
from io import BytesIO
from shutil import copyfile
from typing import Optional, Union, Dict

import discord
from PIL import Image, ImageColor, ImageOps, ImageFont
from discord.ext.commands import Greedy
from redbot.core import Config, commands
from redbot.core.commands import Context
from redbot.core.bot import Red
from redbot.core.data_manager import bundled_data_path, cog_data_path
from redbot.core.utils.predicates import MessagePredicate

from conquest import regioner
from conquest.conquestgame import ConquestGame

ERROR_CONQUEST_SET_MAP = "No map is currently set. See `[p]conquest set map`"

log = logging.getLogger("red.fox_v3.conquest")


class Conquest(commands.Cog):
    """
    Create and modify maps for RPGs and War Games
    """

    default_maps_json = {"maps": []}

    # Usage: await self.config.games.get_raw("game_name", "is_custom")
    default_games = {"map_name": None, "is_custom": False}

    ext = "PNG"
    ext_format = "PNG"

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=67_111_110_113_117_101_115_116, force_registration=True
        )

        default_guild = {"current_game": None}
        default_global = {"games": {}}
        self.config.register_guild(**default_guild)
        self.config.register_global(**default_global)

        self.data_path: pathlib.Path = cog_data_path(self)

        self.custom_map_folder = self.data_path / "custom_maps"
        if not self.custom_map_folder.exists() or not self.custom_map_folder.is_dir():
            self.custom_map_folder.mkdir()
            with (self.custom_map_folder / "maps.json").open("w+") as dj:
                json.dump(self.default_maps_json.copy(), dj, sort_keys=True, indent=4)

        self.current_map_folder = self.data_path / "current_maps"
        if not self.current_map_folder.exists() or not self.current_map_folder.is_dir():
            self.current_map_folder.mkdir()

        self.asset_path: Optional[pathlib.Path] = None

        self.current_games: Dict[int, Optional[ConquestGame]] = defaultdict(
            lambda: None
        )  # key: guild_id
        self.map_data = {}  # key, value = guild.id, ConquestGame

        self.mm: Optional[regioner.MapMaker] = None

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    def _path_if_custom(self, custom_custom: bool = None) -> pathlib.Path:
        check_value = custom_custom  # if custom_custom is not None else self.is_custom
        if check_value:
            return self.custom_map_folder
        return self.asset_path

    async def load_data(self):
        """
        Initial loading of data from bundled_data_path and config
        """
        self.asset_path = bundled_data_path(self) / "assets"
        for guild in self.bot.guilds:
            game_data = await self.config.guild(guild).current_game()
            if game_data is not None:
                await self.load_guild_data(guild, **game_data)

        # regioner.MAP_FONT = ImageFont.truetype(
        #     str(bundled_data_path(self) / "fonts" / "smallest_pixel_7" / "smallest_pixel-7.ttf"), size=10
        # )

        # regioner.MAP_FONT = ImageFont.truetype(
        #     str(bundled_data_path(self) / "fonts" / "bit01" / "bit01.ttf"), size=4
        # )

        regioner.MAP_FONT = ImageFont.truetype(
            str(bundled_data_path(self) / "fonts" / "pixels" / "Pixels.ttf"), size=16
        )

        # for guild_id, game_name in self.current_maps.items():
        #     await self.current_map_load(guild_id, game_name)

    async def load_guild_data(self, guild: discord.Guild, map_name: str, is_custom: bool):
        # map_data = await self.config.games.get_raw(game_name)
        # if map_data is None:
        #     return False
        # map_name = map_data["map_name"]
        map_path = self._path_if_custom(is_custom) / map_name

        if (
            not (self.current_map_folder / str(guild.id)).exists()
            or not (self.current_map_folder / str(guild.id) / map_name).exists()
        ):
            return False

        self.current_games[guild.id] = ConquestGame(
            map_path, map_name, self.current_map_folder / str(guild.id) / map_name
        )

        return True

    # async def current_map_load(self):
    #     map_path = self._path_if_custom()
    #     self.map_data = ConquestMap(map_path / self.current_map)
    #     await self.map_data.load_data()
    #     # map_data_path = map_path / self.current_map / "data.json"
    #     # try:
    #     #     with map_data_path.open() as mapdata:
    #     #         self.map_data: dict = json.load(mapdata)
    #     # except FileNotFoundError as e:
    #     #     print(e)
    #     #     await self.config.current_map.set(None)
    #     #     return

    # async def _get_current_map_folder(self, guild):
    #     return self.current_map_folder / guild.id / self.current_map

    async def _mm_save_map(self, map_name, target_save):
        return await self.mm.change_name(map_name, target_save)

    @commands.is_owner()
    @commands.group()
    async def mapmaker(self, ctx: Context):
        """
        Base command for managing current maps or creating new ones
        """
        if ctx.invoked_subcommand is None:
            pass

    @mapmaker.command(name="numbers")
    async def _mapmaker_numbers(self, ctx: Context):
        """Regenerates the number mask and puts it in the channel"""
        if not self.mm:
            await ctx.maybe_send_embed("No map currently being worked on")
            return

        async with ctx.typing():
            await self.mm.create_number_mask()
            im = await self.mm.get_blank_numbered_file()

            await ctx.send(file=discord.File(im, filename="map.png"))

    @mapmaker.command(name="close")
    async def _mapmaker_close(self, ctx: Context):
        """Close the currently open map."""
        self.mm = None

        await ctx.tick()

    @mapmaker.group(name="debug")
    async def _mapmaker_debug(self, ctx: Context):
        """Debug commands for making maps. Don't use unless directed to."""
        pass

    @_mapmaker_debug.command(name="recalculatecenter")
    async def _mapmaker_debug_recalculatecenter(self, ctx: Context, region: int = None):
        """Recaculate the center point for the given region.

        Processes all regions if region isn't specified."""

        await self.mm.recalculate_center(region)

        await ctx.tick()

    @mapmaker.command(name="save")
    async def _mapmaker_save(self, ctx: Context, *, map_name: str):
        """Save the current map to a different map name"""
        if not self.mm:
            await ctx.maybe_send_embed("No map currently being worked on")
            return

        if self.mm.name == map_name:
            await ctx.maybe_send_embed("This map already has that name, no reason to save")
            return

        target_save = self.custom_map_folder / map_name

        result = await self._mm_save_map(map_name, target_save)
        if not result:
            await ctx.maybe_send_embed("Failed to save to that name")
        else:
            await ctx.maybe_send_embed(f"Map successfully saved to {target_save}")

    @mapmaker.command(name="upload")
    async def _mapmaker_upload(self, ctx: Context, map_name: str, path_to_image=""):
        """Load a map image to be modified. Upload one with this command or provide a path"""
        message: discord.Message = ctx.message
        if not message.attachments and not path_to_image:
            await ctx.maybe_send_embed(
                "Either upload an image with this command or provide a path to the image"
            )
            return

        target_save = self.custom_map_folder / map_name

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

        if self.mm:  # Only one map can be worked on at a time
            await ctx.maybe_send_embed(
                "An existing map is in progress, close it before opening a new one. (`[p]mapmaker close`)"
            )
            return

        async with ctx.typing():
            self.mm = regioner.MapMaker(target_save)
            self.mm.custom = True

            if path_to_image:
                path_to_image = pathlib.Path(path_to_image)

                if not path_to_image.exists():
                    await ctx.maybe_send_embed("Map not found at that path")
                    return

                mm_img = Image.open(path_to_image)

            elif message.attachments:
                attch: discord.Attachment = message.attachments[0]
                # attch_file = await attch.to_file()

                buffer = BytesIO()
                await attch.save(buffer)

                mm_img: Image.Image = Image.open(buffer)
            else:
                # Wait what?
                return

            if mm_img.mode == "P":
                # Maybe convert to L to prevent RGB?
                mm_img = mm_img.convert()  # No P mode, convert it

            result = await self.mm.init_directory(map_name, target_save, mm_img)

            if not result:
                self.mm = None
                await ctx.maybe_send_embed("Failed to upload to that name")
                return

            maps_json_path = self.custom_map_folder / "maps.json"
            with maps_json_path.open("r+") as maps:
                map_data = json.load(maps)
                map_data["maps"].append(map_name)
                maps.seek(0)
                json.dump(map_data, maps, sort_keys=True, indent=4)

            await ctx.maybe_send_embed(f"Map successfully uploaded to {target_save}")

    @mapmaker.command(name="sample")
    async def _mapmaker_sample(self, ctx: Context, region: int = None):
        """Print the currently being modified map as a sample"""
        if not self.mm:
            await ctx.maybe_send_embed("No map currently being worked on")
            return

        if region is not None and region not in self.mm.regions:
            await ctx.send("This region doesn't exist or was deleted")
            return

        async with ctx.typing():

            files = await self.mm.get_sample(region)

            for f in files:
                await ctx.send(file=discord.File(f, filename="map.png"))

            await ctx.tick()

    @mapmaker.command(name="region")
    async def _mapmaker_region(self, ctx: Context, region: int, print_number: bool = False):
        """Print the currently being modified map as a sample"""
        if not self.mm:
            await ctx.maybe_send_embed("No map currently being worked on")
            return

        if region not in self.mm.regions:
            await ctx.send("This region doesn't exist or was deleted")
            return

        async with ctx.typing():

            files = await self.mm.sample_region(region, print_number)

            for f in files:
                await ctx.send(file=discord.File(f, filename="map.png"))

            await ctx.tick()

    @mapmaker.command(name="load")
    async def _mapmaker_load(self, ctx: Context, map_name: str):
        """Load an existing map to be modified."""
        if self.mm:
            await ctx.maybe_send_embed(
                "There is a current map in progress. Close it first with `[p]mapmaker close`"
            )
            return

        map_path = self.custom_map_folder / map_name

        if not map_path.exists() or not map_path.is_dir():
            await ctx.maybe_send_embed(f"Map {map_name} not found in {self.custom_map_folder}")
            return

        self.mm = regioner.MapMaker(map_path)
        self.mm.load_data()

        await ctx.tick()

    @mapmaker.group(name="masks")
    async def _mapmaker_masks(self, ctx: Context):
        """Base command for managing map masks"""
        if ctx.invoked_subcommand is None:
            pass

    @_mapmaker_masks.command(name="generate")
    async def _mapmaker_masks_generate(self, ctx: Context):
        """
        Generate masks for the map

        Currently only works on maps with black borders and white regions.
        Non-white regions are ignored (i.e. blue water)
        """
        if not self.mm:
            await ctx.maybe_send_embed("No map currently being worked on")
            return

        masks_dir = self.mm.masks_path()
        if masks_dir.exists() and masks_dir.is_dir():
            await ctx.maybe_send_embed("Mask folder already exists, delete this before continuing")
            return

        with ctx.typing():
            regions = await self.mm.generate_masks()

        if not regions:
            await ctx.maybe_send_embed("Failed to generate masks")
            return

        await ctx.maybe_send_embed(f"{len(regions)} masks generated into {masks_dir}")

    @_mapmaker_masks.command(name="delete")
    async def _mapmaker_masks_delete(self, ctx: Context, mask_list: Greedy[int]):
        """
        Delete the listed masks from the map
        """
        if not mask_list:
            await ctx.send_help()
            return

        if not self.mm:
            await ctx.maybe_send_embed("No map currently being worked on")
            return

        masks_dir = self.mm.masks_path()
        if not masks_dir.exists() or not masks_dir.is_dir():
            await ctx.maybe_send_embed("There are no masks")
            return

        async with ctx.typing():
            result = await self.mm.delete_masks(mask_list)
        if result:
            await ctx.maybe_send_embed(f"Delete masks: {mask_list}")
        else:
            await ctx.maybe_send_embed(f"Failed to delete masks")

    @_mapmaker_masks.command(name="merge", aliases=["combine"])
    async def _mapmaker_masks_combine(
        self, ctx: Context, mask_list: Greedy[int], recommended=False
    ):
        """Merge masks into a single mask"""
        if not mask_list and not recommended:
            await ctx.send_help()
            return

        if not self.mm:
            await ctx.maybe_send_embed("No map currently being worked on")
            return

        if recommended and mask_list:
            await ctx.maybe_send_embed(
                "Can't combine recommend masks and a mask list at the same time, pick one"
            )
            return

        masks_dir = self.mm.masks_path()
        if not masks_dir.exists() or not masks_dir.is_dir():
            await ctx.maybe_send_embed("There are no masks")
            return

        if not recommended:
            for mask in mask_list:  # TODO: switch to self.mm.regions intersection of sets
                m = masks_dir / f"{mask}.png"
                if not m.exists():
                    await ctx.maybe_send_embed(f"Mask #{mask} does not exist")
                    return
        else:
            await ctx.send("Not Implemented")
            return

        async with ctx.typing():
            result = await self.mm.combine_masks(mask_list)
            if not result:
                await ctx.maybe_send_embed(
                    "Failed to combine masks, try the command again or check log for errors"
                )
                return
        await ctx.maybe_send_embed(f"Combined masks into mask # {result}")

    @commands.group()
    async def conquest(self, ctx: Context):
        """
        Base command for conquest cog. Start with `[p]conquest set map` to select a map.
        """
        # if ctx.invoked_subcommand is None:
        #     if self.current_maps[ctx.guild.id] is not None:
        #         await self._conquest_current(ctx)

    @conquest.command(name="list")
    async def _conquest_list(self, ctx: Context):
        """
        List maps available for starting a Conquest game.
        """
        maps_json = self.asset_path / "maps.json"
        with maps_json.open() as maps:
            maps_json = json.load(maps)
            map_list = maps_json["maps"]

        maps_json = self.custom_map_folder / "maps.json"
        if maps_json.exists():
            with maps_json.open() as maps:
                maps_json = json.load(maps)
                custom_map_list = maps_json["maps"]

        map_list = "\n".join(map_list)
        custom_map_list = "\n".join(custom_map_list)
        await ctx.maybe_send_embed(f"Current maps:\n{map_list}\n\nCustom maps:\n{custom_map_list}")

    @conquest.group(name="set")
    async def conquest_set(self, ctx: Context):
        """Base command for admin actions like selecting a map"""
        if ctx.invoked_subcommand is None:
            pass

    @conquest_set.command(name="resetzoom")
    async def _conquest_set_resetzoom(self, ctx: Context):
        """Resets the zoom level of the current map"""
        current_game = self.current_games[ctx.guild.id]
        if current_game is None:
            await ctx.maybe_send_embed(ERROR_CONQUEST_SET_MAP)
            return

        if not await current_game.reset_zoom():
            await ctx.maybe_send_embed(f"No zoom data found, reset not needed")
        await ctx.tick()

    @conquest_set.command(name="zoom")
    async def _conquest_set_zoom(self, ctx: Context, x: int, y: int, zoom: float):
        """
        Set the zoom level and position of the current map

        x: positive integer
        y: positive integer
        zoom: float greater than or equal to 1
        """
        current_game = self.current_games[ctx.guild.id]
        if current_game is None:
            await ctx.maybe_send_embed(ERROR_CONQUEST_SET_MAP)
            return

        if x < 0 or y < 0 or zoom < 1:
            await ctx.send_help()
            return

        await current_game.set_zoom(x, y, zoom)

        await ctx.tick()

    @conquest_set.command(name="zoomtest")
    async def _conquest_set_zoomtest(self, ctx: Context, x: int, y: int, zoom: float):
        """
        Test the zoom level and position of the current map

        x: positive integer
        y: positive integer
        zoom: float greater than or equal to 1
        """
        current_game = self.current_games[ctx.guild.id]
        if current_game is None:
            await ctx.maybe_send_embed(ERROR_CONQUEST_SET_MAP)
            return

        if x < 0 or y < 0 or zoom < 1:
            await ctx.send_help()
            return

        # UNUSED: out_of_date marks zoom as oudated, since this overwrite the temp
        zoomed_path = await current_game.create_zoomed_map(
            x, y, zoom, current_game.current_map, current_game.zoomed_current_map
        )

        await ctx.send(file=discord.File(fp=zoomed_path, filename=f"test_zoom.{self.ext}"))

    @conquest_set.command(name="save")
    async def _conquest_set_save(self, ctx: Context, *, save_name):
        """Save the current map to be loaded later"""
        current_game = self.current_games[ctx.guild.id]
        if current_game is None:
            await ctx.maybe_send_embed(ERROR_CONQUEST_SET_MAP)
            return

        await current_game.save_as(save_name)

        await ctx.tick()

    @conquest_set.command(name="load")
    async def _conquest_set_load(self, ctx: Context, *, save_name):
        """Load a saved map to be the current map"""
        current_game = self.current_games[ctx.guild.id]
        if current_game is None:
            await ctx.maybe_send_embed(ERROR_CONQUEST_SET_MAP)
            return

        if not await current_game.load_from(save_name):
            await ctx.maybe_send_embed(f"Saved map not found, check your spelling")
            return

        await ctx.tick()

    @conquest_set.command(name="map")
    async def _conquest_set_map(
        self, ctx: Context, mapname: str, reset: bool = False, is_custom: bool = False
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

        guild_folder = self.current_map_folder / str(ctx.guild.id)
        if not guild_folder.exists():
            guild_folder.mkdir()
        self.current_games[ctx.guild.id] = ConquestGame(map_dir, mapname, guild_folder / mapname)

        # self.current_map = mapname
        # self.is_custom = is_custom
        # await self.config.current_map.set(self.current_map)  # Save to config too
        # await self.config.is_custom.set(is_custom)
        #
        # await self.current_map_load()

        await self.current_games[ctx.guild.id].resume_game(ctx, reset)

        new_game = self.default_games.copy()
        new_game["map_name"] = mapname
        new_game["is_custom"] = is_custom

        await self.config.guild(ctx.guild).current_game.set(new_game)

        # current_map_folder = await self._get_current_map_folder()
        # current_map = current_map_folder / f"current.{self.ext}"
        #
        # if not reset and current_map.exists():
        #     await ctx.maybe_send_embed(
        #         "This map is already in progress, resuming from last game\n"
        #         "Use `[p]conquest set map [mapname] True` to start a new game"
        #     )
        # else:
        #     if not current_map_folder.exists():
        #         current_map_folder.mkdir()
        #     copyfile(check_path / mapname / f"blank.{self.ext}", current_map)

        await ctx.tick()

    @conquest.command(name="current")
    async def _conquest_current(self, ctx: Context):
        """
        Send the current map.
        """
        current_game = self.current_games[ctx.guild.id]
        if current_game is None:
            await ctx.maybe_send_embed(ERROR_CONQUEST_SET_MAP)
            return
        async with ctx.typing():
            map_file = await current_game.get_maybe_zoomed_map("current")
        await ctx.send(file=map_file)

    @conquest.command("blank")
    async def _conquest_blank(self, ctx: Context):
        """
        Print the blank version of the current map, for reference.
        """
        current_game = self.current_games[ctx.guild.id]
        if current_game is None:
            await ctx.maybe_send_embed(ERROR_CONQUEST_SET_MAP)
            return
        async with ctx.typing():
            map_file = await current_game.get_maybe_zoomed_map("blank")
        await ctx.send(file=map_file)

    @conquest.command("numbered")
    async def _conquest_numbered(self, ctx: Context):
        """
        Print the numbered version of the current map, for reference.
        """
        current_game = self.current_games[ctx.guild.id]
        if current_game is None:
            await ctx.maybe_send_embed(ERROR_CONQUEST_SET_MAP)
            return
        async with ctx.typing():
            map_file = await current_game.get_maybe_zoomed_map("numbered")
        await ctx.send(file=map_file)

    @conquest.command(name="multitake")
    async def _conquest_multitake(
        self, ctx: Context, start_region: int, end_region: int, color: str
    ):
        """
        Claim all the territories between the two provided region numbers (inclusive)

        :param start_region:
        """
        current_game = self.current_games[ctx.guild.id]
        if current_game is None:
            await ctx.maybe_send_embed(ERROR_CONQUEST_SET_MAP)
            return

        try:
            color = ImageColor.getrgb(color)
        except ValueError:
            await ctx.maybe_send_embed(f"Invalid color {color}")
            return

        if start_region > end_region:
            start_region, end_region = end_region, start_region

        if end_region > current_game.region_max or start_region < 1:
            await ctx.maybe_send_embed(
                f"Max region number is {current_game.region_max}, minimum is 1"
            )
            return

        regions = [r for r in range(start_region, end_region + 1)]

        async with ctx.typing():
            await current_game._process_take_regions(color, regions)
            map_file = await current_game.get_maybe_zoomed_map("current")

        await ctx.send(file=map_file)

    @conquest.command(name="take")
    async def _conquest_take(self, ctx: Context, regions: Greedy[int], *, color: str):
        """
        Claim a territory or list of territories for a specified color

        :param regions: List of integer regions
        :param color: Color to claim regions
        """
        if not regions:
            await ctx.send_help()
            return

        current_game = self.current_games[ctx.guild.id]
        if current_game is None:
            await ctx.maybe_send_embed(ERROR_CONQUEST_SET_MAP)
            return

        try:
            color = ImageColor.getrgb(color)
        except ValueError:
            await ctx.maybe_send_embed(f"Invalid color {color}")
            return

        for region in regions:
            if region > current_game.region_max or region < 1:
                await ctx.maybe_send_embed(
                    f"Max region number is {current_game.region_max}, minimum is 1"
                )
                return
        async with ctx.typing():
            await current_game._process_take_regions(color, regions)
            map_file = await current_game.get_maybe_zoomed_map("current")

        await ctx.send(file=map_file)
