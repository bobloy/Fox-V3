import pathlib

import discord
from nudenet import NudeDetector
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path

all_labels = [
    "FEMALE_GENITALIA_COVERED",
    "FACE_FEMALE",
    "BUTTOCKS_EXPOSED",
    "FEMALE_BREAST_EXPOSED",
    "FEMALE_GENITALIA_EXPOSED",
    "MALE_BREAST_EXPOSED",
    "ANUS_EXPOSED",
    "FEET_EXPOSED",
    "BELLY_COVERED",
    "FEET_COVERED",
    "ARMPITS_COVERED",
    "ARMPITS_EXPOSED",
    "FACE_MALE",
    "BELLY_EXPOSED",
    "MALE_GENITALIA_EXPOSED",
    "ANUS_COVERED",
    "FEMALE_BREAST_COVERED",
    "BUTTOCKS_COVERED",
]

nsfw_labels = all_labels
# nsfw_labels = [
#     "BUTTOCKS_EXPOSED",
#     "FEMALE_BREAST_EXPOSED",
#     "FEMALE_GENITALIA_EXPOSED",
#     "ANUS_EXPOSED",
#     "MALE_GENITALIA_EXPOSED",
# ]


class Nudity(commands.Cog):
    """Monitor images for NSFW content and moves them to a nsfw channel if possible"""

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9811198108111121, force_registration=True)

        default_guild = {"enabled": False, "channel_id": None}

        self.config.register_guild(**default_guild)

        self.detector = NudeDetector()
        # self.classifier = NudeClassifier()

        self.data_path: pathlib.Path = cog_data_path(self)

        self.current_processes = 0

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    @commands.guild_only()
    @commands.command(aliases=["togglenudity"], name="nudity")
    async def nudity(self, ctx: commands.Context):
        """Toggle nude-checking on or off"""
        is_on = await self.config.guild(ctx.guild).enabled()
        await self.config.guild(ctx.guild).enabled.set(not is_on)
        await ctx.send("Nude checking is now set to {}".format(not is_on))

    @commands.guild_only()
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
        channel_id = await self.config.guild(guild).channel_id()

        if channel_id is None:
            return None
        else:
            return guild.get_channel(channel_id)

    async def nsfw(self, message: discord.Message, results: list):
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
        embed.add_field(name="Original Message Text", value=content)
        embed.set_author(name=message.author.name, icon_url=message.author.display_avatar.url)
        await message.channel.send(embed=embed)

        nsfw_channel = await self.get_nsfw_channel(guild)

        if nsfw_channel is None:
            return
        else:
            for image, r in results:
                detections = []
                for detection in r:
                    if detection["score"] > 0.7 and detection["class"] in nsfw_labels:
                        detections.append(detection)

                if detections:
                    await nsfw_channel.send(
                        f"NSFW Image @ {message.channel.mention}\nDetected {', '.join(d['class'] for d in detections)}",
                        file=discord.File(
                            image,
                        ),
                    )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        is_private = isinstance(message.channel, discord.abc.PrivateChannel)

        if not message.attachments or is_private or message.author.bot:
            # print("did not qualify")
            return

        if await self.bot.cog_disabled_in_guild(self, message.guild):
            return

        try:
            is_on = await self.config.guild(message.guild).enabled()
        except AttributeError:
            return

        if not is_on:
            print("Not on")
            return

        channel: discord.TextChannel = message.channel

        if channel.is_nsfw():
            print("nsfw channel is okay")
            return

        check_list = []
        for attachment in message.attachments:
            # async with aiohttp.ClientSession() as session:
            #     img = await fetch_img(session, attachment.url)

            ext = attachment.filename

            temp_name = self.data_path / f"nudecheck{self.current_processes}_{ext}"

            self.current_processes += 1

            print("Pre attachment save")
            await attachment.save(temp_name)
            check_list.append(temp_name)

        print("Pre nude check")

        nude_results = []
        for img in check_list:
            nude_results.append([img, self.detector.detect(str(img))])
        # nude_results = self.classifier.classify([str(n) for n in check_list])
        # print(nude_results)

        if True in [
            detection["score"] > 0.7 and detection["class"] in nsfw_labels
            for img, r in nude_results
            for detection in r
        ]:
            # print("Is nude")
            await message.add_reaction("❌")
            await self.nsfw(message, nude_results)
        else:
            # print("Is not nude")
            await message.add_reaction("✅")


# async def fetch_img(session, url):
#     with aiohttp.Timeout(10):
#         async with session.get(url) as response:
#             assert response.status == 200
#             return await response.read()
