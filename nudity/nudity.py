from datetime import datetime

import discord
import nude
from nude import Nude
from redbot.core import Config
from redbot.core import commands
from redbot.core.bot import Red


class Nudity:
    """
    V3 Cog Template
    """

    online_status = discord.Status.online

    offline_status = discord.Status.offline

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9811198108111121, force_registration=True)

        default_guild = {
            "enabled": False
        }

        self.config.register_guild(**default_guild)

    @commands.command(aliases=['togglenudity'], name='nudity')
    async def nudity(self, ctx: commands.Context):
        """Toggle nude-checking on or off"""
        is_on = await self.config.guild(ctx.guild).enabled()
        await self.config.guild(ctx.guild).enabled.set(not is_on)
        await ctx.send("Nude checking is now set to {}".format(not is_on))

    async def on_message(self, message: discord.Message):
        is_on = await self.config.guild(message.guild).enabled()
        if not is_on:
            return

        if not message.attachments:
            return


