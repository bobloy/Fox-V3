import asyncio
import random
from datetime import datetime, timedelta

import discord
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.commands import Cog
from redbot.core.data_manager import cog_data_path
from redbot.core.utils.chat_formatting import box, pagify

DEFAULT_MESSAGES = [
    # "Example message. Uncomment and overwrite to use",
    # "Example message 2. Each message is in quotes and separated by a comma"
]


class AnnounceDaily(Cog):
    """
    Send daily announcements
    """

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.path = str(cog_data_path(self)).replace("\\", "/")

        self.image_path = self.path + "/"

        self.config = Config.get_conf(self, identifier=9811198108111121, force_registration=True)
        default_global = {
            "messages": [],
            "images": [],
            "time": {"hour": 0, "minute": 0, "second": 0},
        }
        default_guild = {"channelid": None}

        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    async def _get_msgs(self):
        return DEFAULT_MESSAGES + await self.config.messages()

    @commands.group(name="announcedaily", aliases=["annd"])
    @checks.mod_or_permissions(administrator=True)
    @commands.guild_only()
    async def _ad(self, ctx: commands.Context):
        """
        Base command for managing AnnounceDaily settings

        Do `[p]help annd <subcommand>` for more details
        """
        pass

    @commands.command()
    @checks.guildowner()
    @commands.guild_only()
    async def runannounce(self, ctx: commands.Context):
        """Manually run the daily announcement"""

        await self.send_announcements()
        await ctx.send("Success")

    @_ad.command()
    async def setchannel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """
        Set the announcement channel for this server

        Don't pass a channel to clear this server of receiving announcements
        """
        if channel is not None:
            await self.config.guild(ctx.guild).channelid.set(channel.id)
            await ctx.send("Announcement channel has been set to {}".format(channel.mention))
        else:
            await self.config.guild(ctx.guild).channelid.set(None)
            await ctx.send("Announcement channel has been cleared")

    @_ad.command()
    async def addmsg(self, ctx: commands.Context, *, msg):
        """
        Add a message to the pool of announcement messages
        """
        async with self.config.messages() as msgs:
            msgs.append(msg)

        await ctx.send("Message successfully added!")

    @_ad.command()
    async def addimg(self, ctx: commands.Context, filename=None):
        """
        Add an image to the pool of announcement images

        You must attach an image while executing this command
        """
        if ctx.message.attachments:
            att_ = ctx.message.attachments[0]
            try:
                att_.height
            except AttributeError:
                await ctx.send("You must attach an image, no other file will be accepted")
                return

            if filename is None:
                filename = att_.filename

            try:
                # with open(self.image_path + filename, 'w') as f:
                #     await att_.save(f)
                await att_.save(self.image_path + filename)
            except discord.NotFound:
                await ctx.send(
                    "Did you delete the message? Cause I couldn't download the attachment"
                )
            except discord.HTTPException:
                await ctx.send("Failed to download the attachment, please try again")
            else:
                async with self.config.images() as images:
                    if filename in images:
                        await ctx.send("Image {} has been overwritten!".format(filename))
                    else:
                        images.append(filename)
                        await ctx.send("Image {} has been added!".format(filename))
        else:
            await ctx.send("You must attach an image when sending this command")

    @_ad.command()
    async def listmsg(self, ctx: commands.Context):
        """
        List all registered announcement messages
        """
        messages = await self.config.messages()
        for page in pagify(
            "\n".join("{} - {}".format(key, image) for key, image in enumerate(messages))
        ):
            await ctx.send(box(page))
        await ctx.send("Done!")

    @_ad.command()
    async def listimg(self, ctx: commands.Context):
        """
        List all registered announcement images
        """
        images = await self.config.images()
        for page in pagify("\n".join(images)):
            await ctx.send(box(page))
        await ctx.send("Done!")

    @_ad.command()
    async def delmsg(self, ctx: commands.Context, index: int):
        """
        Remove a message from the announcement pool

        Must provide the index of the message, which can be found by using `[p]annd listmsg`
        """
        async with self.config.messages() as messages:
            try:
                out = messages.pop(index)
            except IndexError:
                await ctx.send("Invalid index, check valid indexes with `listmsg` command")
                return

        await ctx.send("The following message was removed:\n```{}```".format(out))

    @_ad.command()
    async def delimg(self, ctx: commands.Context, filename: str):
        """
        Remove an image from the announcement pool

        Does not delete the file from the disk, so you may have to clean it up occasionally
        """
        async with self.config.images() as images:
            if filename not in images:
                await ctx.send("This file doesn't exist")
            else:
                images.remove(filename)
            await ctx.send("Successfully removed {}".format(filename))

    @_ad.command()
    async def settime(self, ctx: commands.Context, minutes_from_now: int):
        """
        Set the daily announcement time

        It will first announce at the time you provided, then it will repeat every 24 hours
        """
        ann_time = datetime.now() + timedelta(minutes=minutes_from_now)

        h = ann_time.hour
        m = ann_time.minute
        s = ann_time.second
        await self.config.time.set({"hour": h, "minute": m, "second": s})

        await ctx.send(
            "Announcement time has been set to {}::{}::{} every day\n"
            "**Changes will apply after next scheduled announcement or reload**".format(h, m, s)
        )

    async def send_announcements(self):
        messages = await self._get_msgs()
        images = await self.config.images()

        total = len(messages) + len(images)
        if total < 1:
            return

        x = random.randint(0, total - 1)

        if x >= len(messages):
            x -= len(messages)
            choice = images[x]
            choice = open(self.image_path + choice, "rb")
            is_image = True
        else:
            choice = messages[x]
            is_image = False

        for guild in self.bot.guilds:
            channel = await self.config.guild(guild).channelid()
            if channel is None:
                continue
            channel = guild.get_channel(channel)
            if channel is None:
                continue

            if is_image:
                await channel.send(file=discord.File(choice))
            else:
                await channel.send(choice)

    async def check_day(self):
        while True:
            tomorrow = datetime.now() + timedelta(days=1)
            time = await self.config.time()
            h, m, s = time["hour"], time["minute"], time["second"]
            midnight = datetime(
                year=tomorrow.year,
                month=tomorrow.month,
                day=tomorrow.day,
                hour=h,
                minute=m,
                second=s,
            )

            print("Sleeping for {} seconds".format((midnight - datetime.now()).seconds))
            await asyncio.sleep((midnight - datetime.now()).seconds)

            if self is not self.bot.get_cog("AnnounceDaily"):
                print("Announce canceled, cog has been lost")
                return

            await self.send_announcements()

            await asyncio.sleep(3)


# [p]setchannel #channelname - Set the announcement channel per server
# [p]addmsg <message goes here> - Adds a msg to the pool
# [p]addimg http://imgurl.com/image.jpg - Adds an image to the pool
# [p]listmsg - Lists all messages in the pool
# [p]listimg - Unsure about this one, but would probably just post all the images
# [p]delmsg - Remove msg from pool
# [p]delimg - Remove image from pool
# [p]settime <x> - S
