from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

import aiohttp
import discord
from redbot.core import Config, checks
from redbot.core import commands
from redbot.core.bot import Red

Cog: Any = getattr(commands, "Cog", object)


async def fetch_url(session, url):
    async with session.get(url) as response:
        assert response.status == 200
        return await response.json()


class Dad(Cog):
    """
    Dad jokes

    Nicknaming user idea comes from https://github.com/Vexs/DadBot
    """

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=6897100, force_registration=True)

        default_guild = {"enabled": True, "nickname": False, "cooldown": 240}

        self.config.register_guild(**default_guild)

        self.cooldown = defaultdict(datetime.now)

    @commands.command()
    async def dadjoke(self, ctx: commands.Context):
        headers = {
            "User-Agent": "FoxV3 (https://github.com/bobloy/Fox-V3)",
            "Accept": "application/json",
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            joke = await fetch_url(session, "https://icanhazdadjoke.com/")

        em = discord.Embed()
        em.set_image(url="https://icanhazdadjoke.com/j/{}.png".format(joke["id"]))

        await ctx.send(embed=em)

    @commands.group()
    @checks.admin()
    async def dad(self, ctx: commands.Context):
        """Dad joke superhub"""
        pass

    @dad.command(name="toggle")
    async def dad_toggle(self, ctx: commands.Context):
        """Toggle automatic dad jokes on or off"""
        is_on = await self.config.guild(ctx.guild).enabled()
        await self.config.guild(ctx.guild).enabled.set(not is_on)
        await ctx.send("Auto dad jokes are now set to {}".format(not is_on))

    @dad.command(name="nickname")
    async def dad_nickname(self, ctx: commands.Context):
        """Toggle nicknaming"""
        is_on = await self.config.guild(ctx.guild).nickname()
        await self.config.guild(ctx.guild).nickname.set(not is_on)
        await ctx.send("Nicknaming is now set to {}".format(not is_on))

    @dad.command(name="cooldown")
    async def dad_cooldown(self, ctx: commands.Context, cooldown: int):
        """Set the auto-joke cooldown"""

        await self.config.guild(ctx.guild).cooldown.set(cooldown)
        await ctx.send("Dad joke cooldown is now set to {}".format(cooldown))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        guild: discord.Guild = message.guild
        if guild is None:
            return

        guild_config = self.config.guild(guild)
        is_on = await guild_config.enabled()
        if not is_on:
            return

        if self.cooldown[guild.id] > datetime.now():
            return

        lower = message.clean_content.lower()
        lower_split = lower.split()
        if len(lower_split) == 0:
            return

        if lower_split[0] == "i'm" and len(lower_split) >= 2:
            if await guild_config.nickname():
                try:
                    await message.author.edit(nick=lower[4:])
                except discord.Forbidden:
                    out = lower[4:]
                else:
                    out = message.author.mention
            else:
                out = lower[4:]
            try:
                await message.channel.send("Hi {}, I'm {}!".format(out, guild.me.display_name))
            except discord.HTTPException:
                return

            self.cooldown[guild.id] = datetime.now() + timedelta(
                seconds=(await guild_config.cooldown())
            )
