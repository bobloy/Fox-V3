import asyncio
from typing import Union

import discord
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.commands import Cog

# Cog: Any = getattr(commands, "Cog", object)
# listener = getattr(commands.Cog, "listener", None)  # Trusty + Sinbad
# if listener is None:
#     def listener(name=None):
#         return lambda x: x

RATE_LIMIT_DELAY = 60 * 10  # If you're willing to risk rate limiting, you can decrease the delay


class InfoChannel(Cog):
    """
    Create a channel with updating server info

    Less important information about the cog
    """

    def __init__(self, bot: Red):
        super().__init__()
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

        self._critical_section_wooah_ = 0

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

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
        channel = None
        if channel_id is not None:
            channel: Union[discord.VoiceChannel, None] = guild.get_channel(channel_id)

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
            try:
                await self.make_infochannel(guild)
            except discord.Forbidden:
                await ctx.send("Failure: Missing permission to create voice channel")
                return
        else:
            await self.delete_all_infochannels(guild)

        if not await ctx.tick():
            await ctx.send("Done!")

    @commands.group()
    @checks.admin()
    async def infochannelset(self, ctx: commands.Context):
        """
        Toggle different types of infochannels
        """
        if not ctx.invoked_subcommand:
            pass

    @infochannelset.command(name="botcount")
    async def _infochannelset_botcount(self, ctx: commands.Context, enabled: bool = None):
        """
        Toggle an infochannel that shows the amount of bots in the server
        """
        guild = ctx.guild
        if enabled is None:
            enabled = not await self.config.guild(guild).bot_count()

        await self.config.guild(guild).bot_count.set(enabled)
        await self.make_infochannel(ctx.guild)

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
        await self.make_infochannel(ctx.guild)

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

        #  Remove the old info channel first
        channel_id = await self.config.guild(guild).channel_id()
        if channel_id is not None:
            channel: discord.VoiceChannel = guild.get_channel(channel_id)
            if channel:
                await channel.delete(reason="InfoChannel delete")

        # Then create the new one
        channel = await guild.create_voice_channel(
            "Total Humans:", reason="InfoChannel make", overwrites=overwrites
        )
        await self.config.guild(guild).channel_id.set(channel.id)

        if botcount:
            # Remove the old bot channel first
            botchannel_id = await self.config.guild(guild).botchannel_id()
            if channel_id is not None:
                botchannel: discord.VoiceChannel = guild.get_channel(botchannel_id)
                if botchannel:
                    await botchannel.delete(reason="InfoChannel delete")

            # Then create the new one
            botchannel = await guild.create_voice_channel(
                "Bots:", reason="InfoChannel botcount", overwrites=overwrites
            )
            await self.config.guild(guild).botchannel_id.set(botchannel.id)
        if onlinecount:
            # Remove the old online channel first
            onlinechannel_id = await self.config.guild(guild).onlinechannel_id()
            if channel_id is not None:
                onlinechannel: discord.VoiceChannel = guild.get_channel(onlinechannel_id)
                if onlinechannel:
                    await onlinechannel.delete(reason="InfoChannel delete")

            # Then create the new one
            onlinechannel = await guild.create_voice_channel(
                "Online:", reason="InfoChannel onlinecount", overwrites=overwrites
            )
            await self.config.guild(guild).onlinechannel_id.set(onlinechannel.id)

        await self.update_infochannel(guild)

    async def delete_all_infochannels(self, guild: discord.Guild):
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
        # bots = lambda x: x.bot
        # def bots(x): return x.bot

        bot_num = len([m for m in guild.members if m.bot])
        # bot_msg = f"Bots: {num}"

        # Gets count of online users
        members = guild.member_count
        offline = len(list(filter(lambda m: m.status is discord.Status.offline, guild.members)))
        online_num = members - offline
        # online_msg = f"Online: {num}"

        # Gets count of actual users
        total = lambda x: not x.bot
        human_num = len([m for m in guild.members if total(m)])
        # human_msg = f"Total Humans: {num}"

        channel_id = guild_data["channel_id"]
        if channel_id is None:
            return False

        botchannel_id = guild_data["botchannel_id"]
        onlinechannel_id = guild_data["onlinechannel_id"]
        channel_id = guild_data["channel_id"]
        channel: discord.VoiceChannel = guild.get_channel(channel_id)
        botchannel: discord.VoiceChannel = guild.get_channel(botchannel_id)
        onlinechannel: discord.VoiceChannel = guild.get_channel(onlinechannel_id)

        if guild_data["member_count"]:
            name = f"{channel.name.split(':')[0]}: {human_num}"

            await channel.edit(reason="InfoChannel update", name=name)

        if botcount:
            name = f"{botchannel.name.split(':')[0]}: {bot_num}"
            await botchannel.edit(reason="InfoChannel update", name=name)

        if onlinecount:
            name = f"{onlinechannel.name.split(':')[0]}: {online_num}"
            await onlinechannel.edit(reason="InfoChannel update", name=name)

    async def update_infochannel_with_cooldown(self, guild):
        """My attempt at preventing rate limits, lets see how it goes"""
        if self._critical_section_wooah_:
            if self._critical_section_wooah_ == 2:
                # print("Already pending, skipping")
                return  # Another one is already pending, don't queue more than one
            # print("Queuing another update")
            self._critical_section_wooah_ = 2

            while self._critical_section_wooah_:
                await asyncio.sleep(
                    RATE_LIMIT_DELAY // 4
                )  # Max delay ends up as 1.25 * RATE_LIMIT_DELAY

            # print("Issuing queued update")
            return await self.update_infochannel_with_cooldown(guild)

        # print("Entering critical")
        self._critical_section_wooah_ = 1
        await self.update_infochannel(guild)
        await asyncio.sleep(RATE_LIMIT_DELAY)
        self._critical_section_wooah_ = 0
        # print("Exiting critical")

    @Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if await self.bot.cog_disabled_in_guild(self, member.guild):
            return
        await self.update_infochannel_with_cooldown(member.guild)

    @Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if await self.bot.cog_disabled_in_guild(self, member.guild):
            return
        await self.update_infochannel_with_cooldown(member.guild)

    @Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if await self.bot.cog_disabled_in_guild(self, after.guild):
            return
        onlinecount = await self.config.guild(after.guild).online_count()
        if onlinecount:
            if before.status != after.status:
                await self.update_infochannel_with_cooldown(after.guild)
