import asyncio
import logging
from typing import Union

import discord
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.commands import Cog

log = logging.getLogger("red.fox_v3.stealemoji")
# Replaced with discord.Asset.read()
# async def fetch_img(session: aiohttp.ClientSession, url: StrOrURL):
#     async with session.get(url) as response:
#         assert response.status == 200
#         return await response.read()


async def check_guild(guild, emoji):
    if len(guild.emojis) >= 2 * guild.emoji_limit:
        return False

    if len(guild.emojis) < guild.emoji_limit:
        return True

    if emoji.animated:
        return sum(e.animated for e in guild.emojis) < guild.emoji_limit
    else:
        return sum(not e.animated for e in guild.emojis) < guild.emoji_limit


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
        "saveid": None,
    }

    def __init__(self, red: Red):
        super().__init__()
        self.bot = red
        self.config = Config.get_conf(self, identifier=11511610197108101109111106105)
        default_global = {
            "stolemoji": {},
            "guildbanks": [],
            "autobanked_guilds": [],
            "on": False,
            "notify": 0,
            "autobank": False,
        }

        self.config.register_global(**default_global)

        self.is_on = None

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    @commands.group()
    async def stealemoji(self, ctx: commands.Context):
        """
        Base command for this cog. Check help for the commands list.
        """
        pass

    @checks.is_owner()
    @stealemoji.command(name="clearemojis")
    async def se_clearemojis(self, ctx: commands.Context, confirm: bool = False):
        """Removes the history of all stolen emojis. Will not delete emojis from server banks"""
        if not confirm:
            await ctx.maybe_send_embed(
                "This will reset all stolen emoji data.\n"
                "If you want to continue, run this command again as:\n"
                "`[p]stealemoji clearemojis True`"
            )
            return

        await self.config.stolemoji.clear()
        await ctx.tick()

    @checks.is_owner()
    @stealemoji.command(name="print")
    async def se_print(self, ctx: commands.Context):
        """Prints all the emojis that have been stolen so far"""
        stolen = await self.config.stolemoji()
        id_list = [v.get("saveid") for k, v in stolen.items()]

        emoj = " ".join(str(e) for e in self.bot.emojis if e.id in id_list)

        if emoj == " ":
            await ctx.maybe_send_embed("No stolen emojis yet")
            return

        await ctx.maybe_send_embed(emoj)

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
            await ctx.maybe_send_embed("Bot owner will now be notified when an emoji is stolen")
        elif curr_setting == 1:
            channel: discord.TextChannel = ctx.channel
            await self.config.notify.set(channel.id)
            await ctx.maybe_send_embed("This channel will now be notified when an emoji is stolen")
        else:
            await self.config.notify.set(0)
            await ctx.maybe_send_embed("Notifications are now off")

    @checks.is_owner()
    @stealemoji.command(name="collect")
    async def se_collect(self, ctx):
        """Toggles whether emoji's are collected or not"""
        curr_setting = await self.config.on()
        await self.config.on.set(not curr_setting)

        self.is_on = await self.config.on()

        await ctx.maybe_send_embed("Collection is now " + str(not curr_setting))

    @checks.is_owner()
    @stealemoji.command(name="autobank")
    async def se_autobank(self, ctx):
        """Toggles automatically creating new guilds as emoji banks"""
        curr_setting = await self.config.autobank()
        await self.config.autobank.set(not curr_setting)

        self.is_on = await self.config.autobank()

        await ctx.maybe_send_embed("AutoBanking is now " + str(not curr_setting))

    @checks.is_owner()
    @commands.guild_only()
    @stealemoji.command(name="deleteserver", aliases=["deleteguild"])
    async def se_deleteserver(self, ctx: commands.Context, guild_id=None):
        """Delete servers the bot is the owner of.

        Useful for auto-generated guildbanks."""
        if guild_id is None:
            guild = ctx.guild
        else:
            guild = await self.bot.get_guild(guild_id)

        if guild is None:
            await ctx.maybe_send_embed("Failed to get guild, cancelling")
            return
        guild: discord.Guild
        await ctx.maybe_send_embed(
            f"Will attempt to delete {guild.name} ({guild.id})\n" f"Okay to continue? (yes/no)"
        )

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            answer = await self.bot.wait_for("message", timeout=120, check=check)
        except asyncio.TimeoutError:
            await ctx.send("Timed out, canceling")
            return

        if answer.content.upper() not in ["Y", "YES"]:
            await ctx.maybe_send_embed("Cancelling")
            return
        try:
            await guild.delete()
        except discord.Forbidden:
            log.exception("No permission to delete. I'm probably not the guild owner")
            await ctx.maybe_send_embed("No permission to delete. I'm probably not the guild owner")
        except discord.HTTPException:
            log.exception("Unexpected error when deleting guild")
            await ctx.maybe_send_embed("Unexpected error when deleting guild")
        else:
            await self.bot.send_to_owners(f"Guild {guild.name} deleted")

    @checks.is_owner()
    @commands.guild_only()
    @stealemoji.command(name="bank")
    async def se_bank(self, ctx):
        """Add or remove current server as emoji bank"""

        def check(m):
            return (
                m.content.upper() in ["Y", "YES", "N", "NO"]
                and m.channel == ctx.channel
                and m.author == ctx.author
            )

        already_a_guildbank = ctx.guild.id in (await self.config.guildbanks())

        if already_a_guildbank:
            await ctx.maybe_send_embed(
                "This is already an emoji bank\n"
                "Are you sure you want to remove the current server from the emoji bank list? (y/n)"
            )
        else:
            await ctx.maybe_send_embed(
                "This will upload custom emojis to this server\n"
                "Are you sure you want to make the current server an emoji bank? (y/n)"
            )

        msg = await self.bot.wait_for("message", check=check)

        if msg.content.upper() in ["N", "NO"]:
            await ctx.maybe_send_embed("Cancelled")
            return

        async with self.config.guildbanks() as guildbanks:
            if already_a_guildbank:
                guildbanks.remove(ctx.guild.id)
            else:
                guildbanks.append(ctx.guild.id)

        if already_a_guildbank:
            await ctx.maybe_send_embed("This server has been removed from being an emoji bank")
        else:
            await ctx.maybe_send_embed("This server has been added to be an emoji bank")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        """Event handler for reaction watching"""
        if not reaction.custom_emoji:
            # print("Not a custom emoji")
            return

        if self.is_on is None:
            self.is_on = await self.config.on()

        if not self.is_on:
            # print("Collecting is off")
            return

        guild: discord.Guild = getattr(user, "guild", None)
        if await self.bot.cog_disabled_in_guild(self, guild):  # Handles None guild just fine
            return

        emoji: discord.Emoji = reaction.emoji
        if emoji in self.bot.emojis:
            # print("Emoji already in bot.emojis")
            return

        # This is now a custom emoji that the bot doesn't have access to, time to steal it
        # First, do I have an available guildbank?

        guildbank: Union[discord.Guild, None] = None
        banklist = await self.config.guildbanks()
        for guild_id in banklist:
            guild: discord.Guild = self.bot.get_guild(guild_id)
            # if len(guild.emojis) < 50:
            if await check_guild(guild, emoji):
                guildbank = guild
                break

        if guildbank is None:
            if not await self.config.autobank():
                return

            try:
                guildbank: discord.Guild = await self.bot.create_guild(
                    "StealEmoji Guildbank", code="S93bqTqKQ9rM"
                )
            except discord.HTTPException:
                await self.config.autobank.set(False)
                log.exception("Unable to create guilds, disabling autobank")
                return
            async with self.config.guildbanks() as guildbanks:
                guildbanks.append(guildbank.id)
            # Track generated guilds for easier deletion
            async with self.config.autobanked_guilds() as autobanked_guilds:
                autobanked_guilds.append(guildbank.id)

            await asyncio.sleep(2)

            if guildbank.text_channels:
                channel = guildbank.text_channels[0]
            else:
                # Always hits the else.
                # Maybe create_guild doesn't return guild object with
                #    the template channel?
                channel = await guildbank.create_text_channel("invite-channel")
            invite = await channel.create_invite()

            await self.bot.send_to_owners(invite)
            log.info(f"Guild created id {guildbank.id}. Invite: {invite}")
        # Next, have I saved this emoji before (because uploaded emoji != orignal emoji)

        if str(emoji.id) in await self.config.stolemoji():
            # print("Emoji has already been stolen")
            return

        img = await emoji.url.read()

        try:
            uploaded_emoji = await guildbank.create_custom_emoji(
                name=emoji.name, image=img, reason="Stole from " + str(user)
            )
        except discord.Forbidden as e:
            # print("PermissionError - no permission to add emojis")
            raise PermissionError("No permission to add emojis") from e
        except discord.HTTPException as e:
            # print("HTTPException exception")
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
        save_dict["saveid"] = uploaded_emoji.id

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

            await target.send(f"Just added emoji {uploaded_emoji} to server {guildbank}")
