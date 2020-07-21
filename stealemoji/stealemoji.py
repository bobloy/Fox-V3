from typing import Any

import aiohttp
import discord
from aiohttp.typedefs import StrOrURL
from redbot.core import Config, commands, checks
from redbot.core.bot import Red

from redbot.core.commands import Cog

# Replaced with discord.Asset.read()
# async def fetch_img(session: aiohttp.ClientSession, url: StrOrURL):
#     async with session.get(url) as response:
#         assert response.status == 200
#         return await response.read()


async def check_guild(guild, emoji):
    if len(guild.emojis) >= 100:
        return False

    if len(guild.emojis) < 50:
        return True

    if emoji.animated:
        return sum(e.animated for e in guild.emojis) < 50
    else:
        return sum(not e.animated for e in guild.emojis) < 50


class StealEmoji(Cog):
    """
    This cog steals emojis and creates servers for them
    """

    default_stolemoji = {
        "guildbank": None,
        "name": None,
        "require_colons": None,
        "managed": None,
        "guild_id": None,
        "animated": None,
    }

    def __init__(self, red: Red):
        self.bot = red
        self.config = Config.get_conf(self, identifier=11511610197108101109111106105)
        default_global = {"stolemoji": {}, "guildbanks": [], "on": False, "notify": 0}

        self.config.register_global(**default_global)

    @commands.group()
    async def stealemoji(self, ctx: commands.Context):
        """
        Base command for this cog. Check help for the commands list.
        """
        if ctx.invoked_subcommand is None:
            pass

    @checks.is_owner()
    @stealemoji.command(name="notify")
    async def se_notify(self, ctx: commands.Context):
        """Cycles between notification settings for when an emoji is stolen

        None (Default)
        DM Owner
        Msg in server channel
        """
        curr_setting = await self.config.notify()

        if not curr_setting:
            await self.config.notify.set(1)
            await ctx.send("Bot owner will now be notified when an emoji is stolen")
        elif curr_setting == 1:
            channel: discord.TextChannel = ctx.channel
            await self.config.notify.set(channel.id)
            await ctx.send("This channel will now be notified when an emoji is stolen")
        else:
            await self.config.notify.set(0)
            await ctx.send("Notifications are now off")

    @checks.is_owner()
    @stealemoji.command(name="collect")
    async def se_collect(self, ctx):
        """Toggles whether emoji's are collected or not"""
        curr_setting = await self.config.on()
        await self.config.on.set(not curr_setting)
        await ctx.send("Collection is now " + str(not curr_setting))

    @checks.is_owner()
    @commands.guild_only()
    @stealemoji.command(name="bank")
    async def se_bank(self, ctx):
        """Add current server as emoji bank"""

        def check(m):
            return (
                m.content.upper() in ["Y", "YES", "N", "NO"]
                and m.channel == ctx.channel
                and m.author == ctx.author
            )

        already_a_guildbank = ctx.guild.id in (await self.config.guildbanks())

        if already_a_guildbank:
            await ctx.send(
                "This is already an emoji bank\n"
                "Are you sure you want to remove the current server from the emoji bank list? (y/n)"
            )
        else:
            await ctx.send(
                "This will upload custom emojis to this server\n"
                "Are you sure you want to make the current server an emoji bank? (y/n)"
            )

        msg = await self.bot.wait_for("message", check=check)

        if msg.content.upper() in ["N", "NO"]:
            await ctx.send("Cancelled")
            return

        async with self.config.guildbanks() as guildbanks:
            if already_a_guildbank:
                guildbanks.remove(ctx.guild.id)
            else:
                guildbanks.append(ctx.guild.id)

        if already_a_guildbank:
            await ctx.send("This server has been removed from being an emoji bank")
        else:
            await ctx.send("This server has been added to be an emoji bank")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        """Event handler for reaction watching"""
        if not reaction.custom_emoji:
            # print("Not a custom emoji")
            return

        if not (await self.config.on()):  # TODO: Make this cached
            print("Collecting is off")
            return

        emoji: discord.Emoji = reaction.emoji
        if emoji in self.bot.emojis:
            print("Emoji already in bot.emojis")
            return

        # This is now a custom emoji that the bot doesn't have access to, time to steal it
        # First, do I have an available guildbank?

        guildbank = None
        banklist = await self.config.guildbanks()
        for guild_id in banklist:
            guild: discord.Guild = self.bot.get_guild(guild_id)
            # if len(guild.emojis) < 50:
            if await check_guild(guild, emoji):
                guildbank = guild
                break

        if guildbank is None:
            print("No guildbank to store emoji")
            # Eventually make a new banklist
            return

        # Next, have I saved this emoji before (because uploaded emoji != orignal emoji)

        stolemojis = await self.config.stolemoji()

        if emoji.id in stolemojis:  # TODO: This is not preventing duplicates
            print("Emoji has already been stolen")
            return

        # Alright, time to steal it for real
        # path = urlparse(emoji.url).path
        # ext = os.path.splitext(path)[1]

        # async with aiohttp.ClientSession() as session:
        #     img = await fetch_img(session, emoji.url)

        img = await emoji.url.read()

        # path = data_manager.cog_data_path(cog_instance=self) / (emoji.name+ext)

        # with path.open("wb") as f:
        # f.write(img)
        # urllib.urlretrieve(emoji.url, emoji.name+ext)

        try:
            await guildbank.create_custom_emoji(
                name=emoji.name, image=img, reason="Stole from " + str(user)
            )
        except discord.Forbidden as e:
            print("PermissionError - no permission to add emojis")
            raise PermissionError("No permission to add emojis") from e
        except discord.HTTPException as e:
            print("HTTPException exception")
            raise e  # Unhandled error

        # If you get this far, YOU DID IT

        save_dict = self.default_stolemoji.copy()
        # e_attr_list = [a for a in dir(emoji) if not a.startswith("__")]

        for k in save_dict.keys():
            save_dict[k] = getattr(emoji, k, None)

        # for k in e_attr_list:
        #     if k in save_dict:
        #         save_dict[k] = getattr(emoji, k, None)

        save_dict["guildbank"] = guildbank.id

        async with self.config.stolemoji() as stolemoji:
            stolemoji[emoji.id] = save_dict

        # Enable the below if you want to get notified when it works
        notify_settings = await self.config.notify()
        if notify_settings:
            if notify_settings == 1:
                owner = await self.bot.application_info()
                target = owner.owner
            else:
                target = self.bot.get_channel(notify_settings)

            await target.send(f"Just added emoji {emoji} to server {guildbank}")
