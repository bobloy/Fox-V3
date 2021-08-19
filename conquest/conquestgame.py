import asyncio
import json
import pathlib
from shutil import copyfile
from types import SimpleNamespace
from typing import Optional, Union

import discord
from PIL import Image, ImageOps
from redbot.core import commands

from conquest.regioner import ConquestMap, composite_regions


class ConquestGame:
    ext = "PNG"
    ext_format = "PNG"

    default_zoom_json = {"enabled": False, "x": -1, "y": -1, "zoom": 1.0}

    def __init__(self, map_path: pathlib.Path, game_name: str, custom_map_path: pathlib.Path):
        self.source_map = ConquestMap(map_path)
        self.game_name = game_name
        self.current_map_folder = custom_map_path

        self.settings_json = self.current_map_folder / "settings.json"

        self.current_filename = f"current.{self.ext}"
        self.current_map = self.current_map_folder / self.current_filename

        self.zoomed_current_filename = f"current_zoomed.{self.ext}"
        self.zoomed_current_map = self.current_map_folder / self.zoomed_current_filename

        self.numbered_current_filename = f"current_numbered.{self.ext}"
        self.numbered_current_map = self.current_map_folder / self.numbered_current_filename

        self.zoomed_numbered_current_filename = f"current_zoomed_numbered.{self.ext}"
        self.zoomed_numbered_current_map = self.current_map_folder / self.zoomed_numbered_current_filename

        self.region_max = self.source_map.region_max

        # self.zoom_is_out_of_date = {'current': True, 'blank': True}

    async def save_region(self, region):
        if not self.custom:
            return False
        pass  # TODO: region data saving

    async def start_game(self):
        if not self.current_map_folder.exists():
            self.current_map_folder.mkdir()
        copyfile(self.source_map.blank_path(), self.current_map)

    async def resume_game(self, ctx: commands.Context, reset: bool):

        if not reset and self.current_map.exists():
            await ctx.maybe_send_embed(
                "This map is already in progress, resuming from last game\n"
                "Use `[p]conquest set map [mapname] True` to start a new game"
            )
        else:
            await self.start_game()

    async def _process_take_regions(self, color, regions):
        im = Image.open(self.current_map)

        out: Image.Image = await composite_regions(
            im,
            regions,
            color,
            self.source_map.masks_path(),
        )
        out.save(self.current_map, self.ext_format)  # Overwrite current map with new map
        # self.zoom_is_out_of_date.current = True

    async def create_numbered_map(self):
        if not self.source_map.numbers_path().exists():  # No numbers map, can't add numbers to current
            return self.source_map.numbered_path()

        current_map = Image.open(self.current_map)
        numbers = Image.open(self.source_map.numbers_path()).convert("L")

        inverted_map = ImageOps.invert(current_map)

        loop = asyncio.get_running_loop()
        current_numbered_img = await loop.run_in_executor(
            None, Image.composite, current_map, inverted_map, numbers
        )

        current_numbered_img.save(self.numbered_current_map, self.ext_format)

        return self.numbered_current_map

    async def create_zoomed_map(
        self, x, y, zoom, source_map: Union[Image.Image, pathlib.Path], target_path: pathlib.Path, **kwargs
    ):
        """Pass out_of_date when created a zoomed map based on something other than the settings json"""
        # if out_of_date:
        #     self.zoom_is_out_of_date.current = True

        # if current_map is None:
        #     current_map = Image.open(self.current_map_folder)
        #     target_map = self.zoomed_current_map

        if not isinstance(source_map, Image.Image):
            source_map = Image.open(source_map)

        w, h = source_map.size
        zoom2 = zoom * 2
        zoomed_map = source_map.crop((x - w / zoom2, y - h / zoom2, x + w / zoom2, y + h / zoom2))
        # zoomed_map = zoomed_map.resize((w, h), Image.LANCZOS)
        zoomed_map.save(target_path, self.ext_format)

        return True

    async def get_maybe_zoomed_map(self, version):
        zoom_data = {"enabled": False}

        if self.settings_json.exists():
            with self.settings_json.open() as zoom_json:
                zoom_data = json.load(zoom_json)

        if version == "numbered":
            map_path = self.create_numbered_map()
            zoomed_path = self.zoomed_numbered_current_map
        else:  # version == "current"
            map_path = self.current_map
            zoomed_path = self.zoomed_current_map

        if zoom_data["enabled"]:  # Send zoomed map instead of current map
            # if self.zoom_is_out_of_date:
            await self.create_zoomed_map(**zoom_data, source_map=map_path, target_map=zoomed_path)
            map_path = zoomed_path
            #   self.zoom_is_out_of_date = False

        return discord.File(fp=map_path)  # lol file names

    async def reset_zoom(self):
        if not self.settings_json.exists():
            return False

        with self.settings_json.open("w+") as zoom_json:
            json.dump({"enabled": False}, zoom_json, sort_keys=True, indent=4)

        # self.zoom_is_out_of_date = True

        return True

    async def set_zoom(self, x, y, zoom):

        zoom_data = self.default_zoom_json.copy()
        zoom_data["enabled"] = True
        zoom_data["x"] = x
        zoom_data["y"] = y
        zoom_data["zoom"] = zoom

        # self.zoom_is_out_of_date = True

        with self.settings_json.open("w+") as zoom_json:
            json.dump(zoom_data, zoom_json, sort_keys=True, indent=4)

    async def save_as(self, save_name):
        copyfile(self.current_map, self.current_map_folder / f"{save_name}.{self.ext}")

    async def load_from(self, save_name):
        saved_map = self.current_map_folder / f"{save_name}.{self.ext}"

        if not saved_map.exists():
            return False

        copyfile(saved_map, self.current_map)  # Overwrite current map with saved map
        return True
