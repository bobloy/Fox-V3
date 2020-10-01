from collections import defaultdict
from datetime import datetime, timedelta

import aiohttp
import discord
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.commands import Cog


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
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=6897100, force_registration=True)

        default_guild = {"enabled": True, "nickname": False, "cooldown": 240}

        self.config.register_guild(**default_guild)

        self.cooldown = defaultdict(datetime.now)

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    @commands.command()
    async def dadjoke(self, ctx: commands.Context):
        headers = {
            "User-Agent": "FoxV3 (https://github.com/bobloy/Fox-V3)",
            "Accept": "application/json",
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            joke = await fetch_url(session, "https://icanhazdadjoke.com/")

        await ctx.maybe_send_embed(joke["joke"])

        # print(joke)
        #
        # em = discord.Embed()
        # em.set_image(url="https://icanhazdadjoke.com/j/{}.png".format(joke["id"]))
        #
        # await ctx.send(embed=em)

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
        """Set the auto-joke cooldown in seconds"""

        await self.config.guild(ctx.guild).cooldown.set(cooldown)
        self.cooldown[ctx.guild.id] = datetime.now()
        await ctx.send("Dad joke cooldown is now set to {} seconds".format(cooldown))

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        if message.author.bot:
            return
        guild: discord.Guild = getattr(message, "guild", None)
        if guild is None:
            return

        if await self.bot.cog_disabled_in_guild(self, guild):
            return

        guild_config = self.config.guild(guild)
        is_on = await guild_config.enabled()
        if not is_on:
            return

        if self.cooldown[guild.id] > datetime.now():
            return

        cleaned_content = message.clean_content
        content_split = cleaned_content.split()
        if len(content_split) == 0:
            return

        if content_split[0].lower() == "i'm" and len(content_split) >= 2:
            if await guild_config.nickname():
                try:
                    await message.author.edit(nick=cleaned_content[4:])
                except discord.Forbidden:
                    out = cleaned_content[4:]
                else:
                    out = message.author.mention
            else:
                out = cleaned_content[4:]
            try:
                await message.channel.send(
                    f"Hi {out}, I'm {guild.me.display_name}!",
                    allowed_mentions=discord.AllowedMentions(),
                )
            except discord.HTTPException:
                return

            self.cooldown[guild.id] = datetime.now() + timedelta(
                seconds=(await guild_config.cooldown())
            )
