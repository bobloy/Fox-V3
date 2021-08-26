import asyncio
import json
import logging
import pathlib
import shutil
from io import BytesIO
from typing import List, Union

from PIL import Image, ImageChops, ImageColor, ImageDraw, ImageFont, ImageOps
from PIL.ImageDraw import _color_diff

log = logging.getLogger("red.fox_v3.conquest.regioner")


async def composite_regions(im, regions, color, masks_path) -> Union[Image.Image, None]:
    im2 = Image.new("RGB", im.size, color)

    loop = asyncio.get_running_loop()

    combined_mask = None
    for region in regions:
        mask = Image.open(masks_path / f"{region}.png").convert("1")
        if combined_mask is None:
            combined_mask = mask
        else:
            # combined_mask = ImageChops.logical_or(combined_mask, mask)
            combined_mask = await loop.run_in_executor(
                None, ImageChops.logical_and, combined_mask, mask
            )

    if combined_mask is None:  # No regions usually
        return None

    out = await loop.run_in_executor(None, Image.composite, im, im2, combined_mask)

    return out


def get_center(points):
    """
    Taken from https://stackoverflow.com/questions/4355894/how-to-get-center-of-set-of-points-using-python
    """
    x = [p[0] for p in points]
    y = [p[1] for p in points]
    return sum(x) / len(points), sum(y) / len(points)


def recommended_combinations(mask_centers):
    pass  # TODO: Create recommendation algo and test it


def floodfill(image, xy, value, border=None, thresh=0) -> set:
    """
    Taken and modified from PIL.ImageDraw.floodfill

    (experimental) Fills a bounded region with a given color.

    :param image: Target image.
    :param xy: Seed position (a 2-item coordinate tuple). See
        :ref:`coordinate-system`.
    :param value: Fill color.
    :param border: Optional border value.  If given, the region consists of
        pixels with a color different from the border color.  If not given,
        the region consists of pixels having the same color as the seed
        pixel.
    :param thresh: Optional threshold value which specifies a maximum
        tolerable difference of a pixel value from the 'background' in
        order for it to be replaced. Useful for filling regions of
        non-homogeneous, but similar, colors.
    """
    # based on an implementation by Eric S. Raymond
    # amended by yo1995 @20180806
    pixel = image.load()
    x, y = xy
    try:
        background = pixel[x, y]
        if _color_diff(value, background) <= thresh:
            return set()  # seed point already has fill color
        pixel[x, y] = value
    except (ValueError, IndexError):
        return set()  # seed point outside image
    edge = {(x, y)}
    # use a set to keep record of current and previous edge pixels
    # to reduce memory consumption
    filled_pixels = set()
    full_edge = set()
    while edge:
        filled_pixels.update(edge)
        new_edge = set()
        for (x, y) in edge:  # 4 adjacent method
            for (s, t) in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                # If already processed, or if a coordinate is negative, skip
                if (s, t) in full_edge or s < 0 or t < 0:
                    continue
                try:
                    p = pixel[s, t]
                except (ValueError, IndexError):
                    pass
                else:
                    full_edge.add((s, t))
                    if border is None:
                        fill = _color_diff(p, background) <= thresh
                    else:
                        fill = p not in [value, border]
                    if fill:
                        pixel[s, t] = value
                        new_edge.add((s, t))
        full_edge = edge  # discard pixels processed
        edge = new_edge
    return filled_pixels  # Modified to returned the filled pixels


def create_number_mask(regions, filepath, filename):
    base_img_path = filepath / filename
    if not base_img_path.exists():
        return False

    base_img: Image.Image = Image.open(base_img_path).convert("L")

    number_img = Image.new("L", base_img.size, 255)
    fnt = ImageFont.load_default()
    d = ImageDraw.Draw(number_img)
    for region_num, region in regions.items():
        text = getattr(region, "name", str(region_num))

        w1, h1 = region.center
        w2, h2 = fnt.getsize(text)

        d.text((w1 - (w2 / 2), h1 - (h2 / 2)), text, font=fnt, fill=0)
    number_img.save(filepath / f"numbers.png", "PNG")
    return True


class ConquestMap:
    def __init__(self, path: pathlib.Path):
        self.path = path

        self.name = None
        self.custom = None
        self.region_max = None
        self.regions = {}

    def masks_path(self):
        return self.path / "masks"

    def data_path(self):
        return self.path / "data.json"

    def blank_path(self):
        return self.path / "blank.png"  # Everything is png now

    def numbers_path(self):
        return self.path / "numbers.png"

    def numbered_path(self):
        return self.path / "numbered.png"

    def load_data(self):
        with self.data_path().open() as dp:
            data = json.load(dp)

        self.name = data.get("name")
        self.custom = data.get("custom")
        self.region_max = data.get("region_max")
        if "regions" in data:
            self.regions = {int(key): Region(**data) for key, data in data["regions"].items()}
        else:
            self.regions = {}

    async def create_number_mask(self):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, create_number_mask, self.regions, self.path, "blank.png"
        )

    def _img_combine_masks(self, mask_list: List[int]):
        if not mask_list or len(mask_list) < 2:
            return False, None, None

        if not self.blank_path().exists():
            return False, None, None

        if not self.masks_path().exists():
            return False, None, None

        base_img: Image.Image = Image.open(self.blank_path())
        mask = Image.new("1", base_img.size, 1)

        lowest_num = None
        eliminated_masks = []

        for mask_num in mask_list:
            if lowest_num is None:
                lowest_num = mask_num
            elif mask_num < lowest_num:
                eliminated_masks.append(lowest_num)
                lowest_num = mask_num
            else:
                eliminated_masks.append(mask_num)

            mask2 = Image.open(self.masks_path() / f"{mask_num}.png").convert("1")
            mask = ImageChops.logical_and(mask, mask2)

        return lowest_num, eliminated_masks, mask

    async def get_sample(self, region=None):
        files = [self.blank_path()]

        masks_dir = self.masks_path()
        if masks_dir.exists() and masks_dir.is_dir():
            loop = asyncio.get_running_loop()
            current_map = Image.open(self.blank_path())

            if region is not None:
                if region in self.regions:
                    current_map = await composite_regions(
                        current_map, [region], ImageColor.getrgb("red"), self.masks_path()
                    )
            else:
                regions = list(self.regions.keys())

                fourth = len(regions) // 4

                current_map = await composite_regions(
                    current_map, regions[:fourth], ImageColor.getrgb("red"), self.masks_path()
                )
                current_map = await composite_regions(
                    current_map,
                    regions[fourth : fourth * 2],
                    ImageColor.getrgb("green"),
                    self.masks_path(),
                )
                current_map = await composite_regions(
                    current_map,
                    regions[fourth * 2 : fourth * 3],
                    ImageColor.getrgb("blue"),
                    self.masks_path(),
                )
                current_map = await composite_regions(
                    current_map, regions[fourth * 3 :], ImageColor.getrgb("yellow"), self.masks_path()
                )

            current_numbered_img = await self.get_numbered(current_map)

            buffer1 = BytesIO()
            buffer2 = BytesIO()

            current_map.save(buffer1, "png")
            buffer1.seek(0)
            current_numbered_img.save(buffer2, "png")
            buffer2.seek(0)

            files.append(buffer1)
            files.append(buffer2)

        return files

    async def get_blank_numbered_file(self):
        im = await self.get_numbered(Image.open(self.blank_path()))
        buffer1 = BytesIO()

        im.save(buffer1, "png")
        buffer1.seek(0)
        return buffer1

    async def get_numbered(self, current_map):
        loop = asyncio.get_running_loop()
        numbers = Image.open(self.numbers_path()).convert("L")
        inverted_map = ImageOps.invert(current_map)
        current_numbered_img = await loop.run_in_executor(
            None, Image.composite, current_map, inverted_map, numbers
        )
        return current_numbered_img


class MapMaker(ConquestMap):
    async def change_name(self, new_name: str, new_path: pathlib.Path):
        if new_path.exists() and new_path.is_dir():
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
            return False, "Overwrite currently not supported"

        # This is a new name
        new_path.mkdir()

        shutil.copytree(self.path, new_path)

        self.custom = True  # If this wasn't a custom map, it is now

        self.name = new_name
        self.path = new_path

        await self.save_data()

        return True

    async def generate_masks(self):
        regioner = Regioner(filename="blank.png", filepath=self.path)
        loop = asyncio.get_running_loop()
        regions = await loop.run_in_executor(None, regioner.execute)

        if not regions:
            return regions

        self.regions = regions
        self.region_max = len(regions) + 1

        await self.save_data()
        return regions

    async def combine_masks(self, mask_list: List[int]):
        loop = asyncio.get_running_loop()
        lowest, eliminated, mask = await loop.run_in_executor(
            None, self._img_combine_masks, mask_list
        )

        if not lowest:
            return lowest

        try:
            elim_regions = [self.regions[n] for n in eliminated]
            lowest_region = self.regions[lowest]
        except KeyError:
            return False

        mask.save(self.masks_path() / f"{lowest}.png", "PNG")

        # points = [self.mm["regions"][f"{n}"]["center"] for n in mask_list]
        #
        # points = [(r.center, r.weight) for r in elim_regions]

        weighted_points = [r.center for r in elim_regions for _ in range(r.weight)] + [
            lowest_region.center for _ in range(lowest_region.weight)
        ]

        lowest_region.center = get_center(weighted_points)

        for key in eliminated:
            self.regions.pop(key)
            # self.mm["regions"].pop(f"{key}")

        if self.region_max in eliminated:  # Max region has changed
            self.region_max = max(self.regions.keys())

        await self.create_number_mask()

        await self.save_data()

        return lowest

    async def delete_masks(self, mask_list):
        try:
            for key in mask_list:
                self.regions.pop(key)
                # self.mm["regions"].pop(f"{key}")
        except KeyError:
            return False

        if self.region_max in mask_list:  # Max region has changed
            self.region_max = max(self.regions.keys())

        await self.create_number_mask()

        await self.save_data()

        return mask_list

    async def save_data(self):
        to_save = {
            "name": self.name,
            "custom": self.custom,
            "region_max": self.region_max,
            "regions": {num: r.get_json() for num, r in self.regions.items()},
        }
        with self.data_path().open("w+") as dp:
            json.dump(to_save, dp, sort_keys=True, indent=4)

    async def init_directory(self, name: str, path: pathlib.Path, image: Image.Image):
        if not path.exists() or not path.is_dir():
            path.mkdir()

        self.name = name
        self.path = path

        await self.save_data()

        image.save(self.blank_path(), "PNG")

        return True


class Region:
    def __init__(self, center, weight, **kwargs):
        self.center = center
        self.weight = weight
        self.data = kwargs

    def get_json(self):
        return {"center": self.center, "weight": self.weight, "data": self.data.copy()}


class Regioner:
    def __init__(
        self, filepath: pathlib.Path, filename: str, region_color=None, wall_color="black"
    ):
        self.filepath = filepath
        self.filename = filename
        self.wall_color = ImageColor.getcolor(wall_color, "L")
        if region_color is None:
            self.region_color = None
        else:
            self.region_color = ImageColor.getcolor(region_color, "L")

    def execute(self):
        """
        Create the regions of the map

        TODO: Using proper multithreading best practices.
        TODO: This is iterating over a 2d array with some overlap, you went to school for this Bozo

        TODO: Fails on some maps where borders aren't just black (i.e. water borders vs region borders)
        """

        base_img_path = self.filepath / self.filename
        if not base_img_path.exists():
            return False

        masks_path = self.filepath / "masks"

        if not masks_path.exists():
            masks_path.mkdir()

        black = ImageColor.getcolor("black", "L")
        white = ImageColor.getcolor("white", "L")

        base_img: Image.Image = Image.open(base_img_path).convert("L")
        already_processed = set()

        mask_count = 0
        regions = {}

        for y1 in range(base_img.height):
            for x1 in range(base_img.width):
                if (x1, y1) in already_processed:
                    continue
                if (
                    self.region_color is None and base_img.getpixel((x1, y1)) != self.wall_color
                ) or base_img.getpixel((x1, y1)) == self.region_color:
                    filled = floodfill(base_img, (x1, y1), self.wall_color, self.wall_color)
                    if filled:  # Pixels were updated, make them into a mask
                        mask = Image.new("L", base_img.size, 255)
                        for x2, y2 in filled:
                            mask.putpixel((x2, y2), 0)  # TODO: Switch to ImageDraw

                        mask_count += 1
                        mask = mask.convert("L")
                        mask.save(masks_path / f"{mask_count}.png", "PNG")

                        regions[mask_count] = Region(center=get_center(filled), weight=len(filled))

                        already_processed.update(filled)

        # TODO: save mask_centers

        create_number_mask(regions, self.filepath, self.filename)
        return regions
