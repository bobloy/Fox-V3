import os
import pathlib
from PIL import Image, ImageColor, ImageFont, ImageOps, ImageDraw
from PIL.ImageDraw import _color_diff


def get_center(points):
    """
    Taken from https://stackoverflow.com/questions/4355894/how-to-get-center-of-set-of-points-using-python
    """
    x = [p[0] for p in points]
    y = [p[1] for p in points]
    return sum(x) / len(points), sum(y) / len(points)


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
    return filled_pixels


class Regioner:
    def __init__(
        self, filepath: pathlib.Path, filename: str, wall_color="black", region_color="white"
    ):
        self.filepath = filepath
        self.filename = filename
        self.wall_color = ImageColor.getcolor(wall_color, "L")
        self.region_color = ImageColor.getcolor(region_color, "L")

    def execute(self):
        base_img_path = self.filepath / self.filename
        if not base_img_path.exists():
            return None

        masks_path = self.filepath / "masks"

        if not masks_path.exists():
            os.makedirs(masks_path)

        black = ImageColor.getcolor("black", "L")
        white = ImageColor.getcolor("white", "L")

        base_img: Image.Image = Image.open(base_img_path).convert("L")
        already_processed = set()

        mask_count = 0
        mask_centers = {}

        for y1 in range(base_img.height):
            for x1 in range(base_img.width):
                if (x1, y1) in already_processed:
                    continue
                if base_img.getpixel((x1, y1)) == self.region_color:
                    filled = floodfill(base_img, (x1, y1), black, self.wall_color)
                    if filled:  # Pixels were updated, make them into a mask
                        mask = Image.new("L", base_img.size, 255)
                        for x2, y2 in filled:
                            mask.putpixel((x2, y2), 0)

                        mask_count += 1
                        mask = mask.convert("L")
                        mask.save(masks_path / f"{mask_count}.png", "PNG")

                        mask_centers[mask_count] = get_center(filled)

                        already_processed.update(filled)

        number_img = Image.new("L", base_img.size, 255)
        fnt = ImageFont.load_default()
        d = ImageDraw.Draw(number_img)
        for mask_num, center in mask_centers.items():
            d.text(center, str(mask_num), font=fnt, fill=0)

        number_img.save(self.filepath / f"numbers.png", "PNG")

        return mask_centers
