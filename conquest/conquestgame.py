import json
import pathlib

import discord
from PIL import Image, ImageColor, ImageOps
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
        self.current_map = self.current_map_folder / f"current.{self.ext}"
        self.zoomed_map = self.current_map_folder / f"zoomed.{self.ext}"

        self.zoom_is_out_of_date = True

    async def save_region(self, region):
        if not self.custom:
            return False
        pass  # TODO: region data saving

    async def start_game(self):
        pass

    async def _process_take_regions(self, color, regions):
        im = Image.open(self.current_map)

        out: Image.Image = await composite_regions(
            im,
            regions,
            color,
            self.source_map.masks_path(),
        )
        out.save(self.current_map, self.ext_format)  # Overwrite current map with new map
        self.zoom_is_out_of_date = True

    async def create_zoomed_map(self, x, y, zoom, **kwargs):
        if not self.zoom_is_out_of_date:
            return self.zoomed_map

        current_map = Image.open(self.current_map_folder)

        w, h = current_map.size
        zoom2 = zoom * 2
        zoomed_map = current_map.crop((x - w / zoom2, y - h / zoom2, x + w / zoom2, y + h / zoom2))
        # zoomed_map = zoomed_map.resize((w, h), Image.LANCZOS)
        zoomed_map.save(self.zoomed_map, self.ext_format)
        self.zoom_is_out_of_date = False
        return self.zoomed_map

    async def get_maybe_zoomed_map(self, filename):
        zoom_data = {"enabled": False}

        if self.settings_json.exists():
            with self.settings_json.open() as zoom_json:
                zoom_data = json.load(zoom_json)

        map_path = self.current_map

        if zoom_data["enabled"]:
            map_path = await self.create_zoomed_map(**zoom_data)  # Send zoomed map instead of current map

        return discord.File(fp=map_path, filename=filename)

    async def reset_zoom(self):
        if not self.settings_json.exists():
            return False

        with self.settings_json.open("w+") as zoom_json:
            json.dump({"enabled": False}, zoom_json, sort_keys=True, indent=4)

        return True

    async def set_zoom(self, x, y, zoom):

        zoom_data = self.default_zoom_json.copy()
        zoom_data["enabled"] = True
        zoom_data["x"] = x
        zoom_data["y"] = y
        zoom_data["zoom"] = zoom

        with self.settings_json.open("w+") as zoom_json:
            json.dump(zoom_data, zoom_json, sort_keys=True, indent=4)

