import pathlib

import aiohttp
import discord
from MyQR import myqr
from PIL import Image
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path
from typing import Any

Cog: Any = getattr(commands, "Cog", object)


class QRInvite(Cog):
    """
    Create custom QR codes for server invites
    """

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9811198108111121, force_registration=True)
        default_global = {}
        default_guild = {}

        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

    @commands.command()
    async def qrinvite(
        self,
        ctx: commands.Context,
        invite: str = None,
        colorized: bool = False,
        image_url: str = None,
    ):
        """
        Create a custom QR code invite for this server
        """
        if invite is None:
            try:
                invite = await ctx.channel.create_invite()
            except discord.Forbidden:
                try:
                    invite = await ctx.channel.invites()
                    invite = invite[0]
                except discord.Forbidden:
                    await ctx.send("No permission to get an invite, please provide one")
                    return
            invite = invite.code

        if image_url is None:
            image_url = ctx.guild.icon_url

        if image_url == "":  # Still
            await ctx.send(
                "Could not get an image, please provide one. *(`{}help qrinvite` for details)*".format(
                    ctx.prefix
                )
            )
            return

        eextention = pathlib.Path(image_url).parts[-1].replace(".", "?").split("?")[1]

        path: pathlib.Path = cog_data_path(self)
        image_path = path / (ctx.guild.icon + "." + extension)
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                image = await response.read()

        with image_path.open("wb") as file:
            file.write(image)

        if extension == "webp":
            new_path = convert_png(str(image_path))
        else:
            new_path = str(image_path)

        myqr.run(
            invite,
            picture=new_path,
            save_name=ctx.guild.icon + "_qrcode.png",
            save_dir=str(cog_data_path(self)),
            colorized=colorized,
        )

        png_path: pathlib.Path = path / (ctx.guild.icon + "_qrcode.png")
        with png_path.open("rb") as png_fp:
            await ctx.send(file=discord.File(png_fp.read(), "qrcode.png"))


def convert_png(path):
    im = Image.open(path)
    im.load()
    alpha = im.split()[-1]
    im = im.convert("RGB").convert("P", palette=Image.ADAPTIVE, colors=255)
    mask = Image.eval(alpha, lambda a: 255 if a <= 128 else 0)
    im.paste(255, mask)
    new_path = path.replace(".webp", ".png")
    im.save(new_path, transparency=255)
    return new_path
