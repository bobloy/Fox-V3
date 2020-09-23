import pathlib

import aiohttp
import discord
from MyQR import myqr
from PIL import Image
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.commands import Cog
from redbot.core.data_manager import cog_data_path


class QRInvite(Cog):
    """
    Create custom QR codes for server invites
    """

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9811198108111121, force_registration=True)
        default_global = {}
        default_guild = {}

        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

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
                    await ctx.maybe_send_embed(
                        "No permission to get an invite, please provide one"
                    )
                    return
            invite = invite.code

        if image_url is None:
            image_url = str(ctx.guild.icon_url)

        if image_url == "":  # Still
            await ctx.maybe_send_embed(
                "Could not get an image, please provide one. *(`{}help qrinvite` for details)*".format(
                    ctx.prefix
                )
            )
            return

        extension = pathlib.Path(image_url).parts[-1].replace(".", "?").split("?")[1]

        path: pathlib.Path = cog_data_path(self)
        image_path = path / (ctx.guild.icon + "." + extension)
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                image = await response.read()

        with image_path.open("wb") as file:
            file.write(image)

        if extension == "webp":
            new_path = convert_webp_to_png(str(image_path))
        elif extension == "gif":
            await ctx.maybe_send_embed("gif is not supported yet, stay tuned")
            return
        elif extension == "png":
            new_path = str(image_path)
        else:
            await ctx.maybe_send_embed(f"{extension} is not supported yet, stay tuned")
            return

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


def convert_webp_to_png(path):
    im = Image.open(path)
    im.load()
    alpha = im.split()[-1]
    im = im.convert("RGB").convert("P", palette=Image.ADAPTIVE, colors=255)
    mask = Image.eval(alpha, lambda a: 255 if a <= 128 else 0)
    im.paste(255, mask)
    new_path = path.replace(".webp", ".png")
    im.save(new_path, transparency=255)
    return new_path
