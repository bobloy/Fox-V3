from typing import Any
import discord

from redbot.core import Config, commands, checks
from redbot.core.bot import Red

Cog: Any = getattr(commands, "Cog", object)
listener = getattr(commands.Cog, "listener", None)  # Trusty + Sinbad
if listener is None:

    def listener(name=None):
        return lambda x: x


class InfoChannel(Cog):
    """
    Create a channel with updating server info

    Less important information about the cog
    """

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=731101021116710497110110101108, force_registration=True
        )

        default_guild = {
            "channel_id": None,
            "botchannel_id": None,
            "onlinechannel_id": None,
            "member_count": True,
            "bot_count": False,
            "online_count": False,
        }

        self.config.register_guild(**default_guild)

    @commands.command()
    @checks.admin()
    async def infochannel(self, ctx: commands.Context):
        """
        Toggle info channel for this server
        """

        def check(m):
            return (
                m.content.upper() in ["Y", "YES", "N", "NO"]
                and m.channel == ctx.channel
                and m.author == ctx.author
            )

        guild: discord.Guild = ctx.guild
        channel_id = await self.config.guild(guild).channel_id()
        if channel_id is not None:
            channel: discord.VoiceChannel = guild.get_channel(channel_id)
        else:
            channel: discord.VoiceChannel = None

        if channel_id is not None and channel is None:
            await ctx.send("Info channel has been deleted, recreate it?")
        elif channel_id is None:
            await ctx.send("Enable info channel on this server?")
        else:
            await ctx.send("Do you wish to delete current info channels?")

        msg = await self.bot.wait_for("message", check=check)

        if msg.content.upper() in ["N", "NO"]:
            await ctx.send("Cancelled")
            return

        if channel is None:
            await self.make_infochannel(guild)
        else:
            await self.delete_infochannel(guild, channel)

        if not await ctx.tick():
            await ctx.send("Done!")

    @commands.group()
    @checks.admin()
    async def infochannelset(self, ctx: commands.Context):
        """
        Toggle different types of infochannels
        """

    @infochannelset.command(name="botcount")
    async def _infochannelset_botcount(self, ctx: commands.Context, enabled: bool = None):
        """
        Toggle an infochannel that shows the amount of bots in the server
        """
        guild = ctx.guild
        if enabled is None:
            enabled = not await self.config.guild(guild).bot_count()
        await self.config.guild(guild).bot_count.set(enabled)
        if enabled:
            await ctx.send("InfoChannel for bot count has been enabled.")
        else:
            await ctx.send("InfoChannel for bot count has been disabled.")

    @infochannelset.command(name="onlinecount")
    async def _infochannelset_onlinecount(self, ctx: commands.Context, enabled: bool = None):
        """
        Toggle an infochannel that shows the amount of online users in the server
        """
        guild = ctx.guild
        if enabled is None:
            enabled = not await self.config.guild(guild).online_count()
        await self.config.guild(guild).online_count.set(enabled)
        if enabled:
            await ctx.send("InfoChannel for online user count has been enabled.")
        else:
            await ctx.send("InfoChannel for online user count has been disabled.")

    async def make_infochannel(self, guild: discord.Guild):
        botcount = await self.config.guild(guild).bot_count()
        onlinecount = await self.config.guild(guild).online_count()
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(connect=False),
            guild.me: discord.PermissionOverwrite(manage_channels=True, connect=True),
        }

        channel = await guild.create_voice_channel(
            "Placeholder", reason="InfoChannel make", overwrites=overwrites
        )
        await self.config.guild(guild).channel_id.set(channel.id)

        if botcount:
            botchannel = await guild.create_voice_channel(
                "Placeholder", reason="InfoChannel botcount", overwrites=overwrites
            )
            await self.config.guild(guild).botchannel_id.set(botchannel.id)
        if onlinecount:
            onlinechannel = await guild.create_voice_channel(
                "Placeholder", reason="InfoChannel onlinecount", overwrites=overwrites
            )
            await self.config.guild(guild).onlinechannel_id.set(onlinechannel.id)

        await self.update_infochannel(guild)

    async def delete_infochannel(self, guild: discord.Guild, channel: discord.VoiceChannel):
        guild_data = await self.config.guild(guild).all()
        botchannel_id = guild_data["botchannel_id"]
        onlinechannel_id = guild_data["onlinechannel_id"]
        botchannel: discord.VoiceChannel = guild.get_channel(botchannel_id)
        onlinechannel: discord.VoiceChannel = guild.get_channel(onlinechannel_id)
        channel_id = guild_data["channel_id"]
        channel: discord.VoiceChannel = guild.get_channel(channel_id)
        await channel.delete(reason="InfoChannel delete")
        if botchannel_id is not None:
            await botchannel.delete(reason="InfoChannel delete")
        if onlinechannel_id is not None:
            await onlinechannel.delete(reason="InfoChannel delete")
        await self.config.guild(guild).clear()

    async def update_infochannel(self, guild: discord.Guild):
        guild_data = await self.config.guild(guild).all()
        botcount = guild_data["bot_count"]
        onlinecount = guild_data["online_count"]

        # Gets count of bots
        bots = lambda x: x.bot
        num = len([m for m in guild.members if bots(m)])
        bot_msg = f"Bots: {num}"

        # Gets count of online users
        members = guild.member_count
        offline = len(list(filter(lambda m: m.status is discord.Status.offline, guild.members)))
        num = members - offline
        online_msg = f"Online: {num}"

        # Gets count of actual users
        total = lambda x: not x.bot
        num = len([m for m in guild.members if total(m)])
        human_msg = f"Total Humans: {num}"

        channel_id = guild_data["channel_id"]
        if channel_id is None:
            return

        botchannel_id = guild_data["botchannel_id"]
        onlinechannel_id = guild_data["onlinechannel_id"]
        channel_id = guild_data["channel_id"]
        channel: discord.VoiceChannel = guild.get_channel(channel_id)
        botchannel: discord.VoiceChannel = guild.get_channel(botchannel_id)
        onlinechannel: discord.VoiceChannel = guild.get_channel(onlinechannel_id)

        if guild_data["member_count"]:
            name = "{} ".format(human_msg)

        await channel.edit(reason="InfoChannel update", name=name)

        if botcount:
            name = "{} ".format(bot_msg)
            await botchannel.edit(reason="InfoChannel update", name=name)

        if onlinecount:
            name = "{} ".format(online_msg)
            await onlinechannel.edit(reason="InfoChannel update", name=name)

    @listener()
    async def on_member_join(self, member: discord.Member):
        await self.update_infochannel(member.guild)

    @listener()
    async def on_member_remove(self, member: discord.Member):
        await self.update_infochannel(member.guild)

    @listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        onlinecount = await self.config.guild(after.guild).online_count()
        if onlinecount:
            if before.status != after.status:
                await self.update_infochannel(after.guild)
