from io import BytesIO

import discord
from PIL import Image
from nude import is_nude
from redbot.core import Config
from redbot.core import commands
from redbot.core.bot import Red


class Nudity:
    """
    V3 Cog Template
    """

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9811198108111121, force_registration=True)

        default_guild = {"enabled": False, "channel_id": None}

        self.config.register_guild(**default_guild)

    @commands.command(aliases=["togglenudity"], name="nudity")
    async def nudity(self, ctx: commands.Context):
        """Toggle nude-checking on or off"""
        is_on = await self.config.guild(ctx.guild).enabled()
        await self.config.guild(ctx.guild).enabled.set(not is_on)
        await ctx.send("Nude checking is now set to {}".format(not is_on))

    @commands.command()
    async def nsfwchannel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        if channel is None:
            await self.config.guild(ctx.guild).channel_id.set(None)
            await ctx.send("NSFW Channel cleared")
        else:
            if not channel.is_nsfw():
                await ctx.send("This channel isn't NSFW!")
                return
            else:
                await self.config.guild(ctx.guild).channel_id.set(channel.id)
                await ctx.send("NSFW channel has been set to {}".format(channel.mention))

    async def get_nsfw_channel(self, guild: discord.Guild):
        channel_id = self.config.guild(guild).channel_id()

        if channel_id is None:
            return None
        else:
            return await guild.get_channel(channel_id=channel_id)

    async def nsfw(self, message: discord.Message, image: BytesIO):
        content = message.content
        guild: discord.Guild = message.guild
        if not content:
            content = "*`None`*"
        try:
            await message.delete()
        except discord.Forbidden:
            await message.channel.send("NSFW Image detected!")
            return

        embed = discord.Embed(title="NSFW Image Detected")
        embed.add_field(name="Original Message", value=content)

        await message.channel.send(embed=embed)

        nsfw_channel = await self.get_nsfw_channel(guild)

        if nsfw_channel is None:
            return
        else:
            await nsfw_channel.send(
                "NSFW Image from {}".format(message.channel.mention), file=image
            )

    async def on_message(self, message: discord.Message):
        if not message.attachments:
            return

        if message.guild is None:
            return

        try:
            is_on = await self.config.guild(message.guild).enabled()
        except AttributeError:
            return

        if not is_on:
            return

        channel: discord.TextChannel = message.channel

        if channel.is_nsfw():
            return

        attachment = message.attachments[0]

        # async with aiohttp.ClientSession() as session:
        #     img = await fetch_img(session, attachment.url)

        temp = BytesIO()
        print("Pre attachment save")
        await attachment.save(temp)
        print("Pre Image open")
        temp = Image.open(temp)

        print("Pre nude check")
        if is_nude(temp):
            print("Is nude")
            await message.add_reaction("❌")
            await self.nsfw(message, temp)
        else:
            print("Is not nude")
            await message.add_reaction("✅")


# async def fetch_img(session, url):
#     with aiohttp.Timeout(10):
#         async with session.get(url) as response:
#             assert response.status == 200
#             return await response.read()
