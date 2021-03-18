import asyncio
import logging
from collections import defaultdict
from typing import Dict, Optional, Union

import discord
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.commands import Cog

# 10 minutes. Rate limit is 2 per 10, so 1 per 6 is safe.
RATE_LIMIT_DELAY = 60 * 6  # If you're willing to risk rate limiting, you can decrease the delay

log = logging.getLogger("red.fox_v3.infochannel")


async def get_channel_counts(category, guild):
    # Gets count of bots
    bot_num = len([m for m in guild.members if m.bot])
    # Gets count of roles in the server
    roles_num = len(guild.roles) - 1
    # Gets count of channels in the server
    # <number of total channels> - <number of channels in the stats category> - <categories>
    channels_num = len(guild.channels) - len(category.voice_channels) - len(guild.categories)
    # Gets all counts of members
    members = guild.member_count
    offline_num = len(list(filter(lambda m: m.status is discord.Status.offline, guild.members)))
    online_num = members - offline_num
    # Gets count of actual users
    human_num = members - bot_num
    return {
        "members": members,
        "humans": human_num,
        "bots": bot_num,
        "roles": roles_num,
        "channels": channels_num,
        "online": online_num,
        "offline": offline_num,
    }


class InfoChannel(Cog):
    """
    Create a channel with updating server info

    This relies on editing channels, which is a strictly rate-limited activity.
    As such, updates will not be frequent. Currently capped at 1 per 5 minutes per server.
    """

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=731101021116710497110110101108, force_registration=True
        )

        # self. so I can get the keys from this later
        self.default_channel_names = {
            "members": "Members: {count}",
            "humans": "Humans: {count}",
            "bots": "Bots: {count}",
            "roles": "Roles: {count}",
            "channels": "Channels: {count}",
            "online": "Online: {count}",
            "offline": "Offline: {count}",
        }

        default_channel_ids = {k: None for k in self.default_channel_names}
        # Only members is enabled by default
        default_enabled_counts = {k: k == "members" for k in self.default_channel_names}

        default_guild = {
            "category_id": None,
            "channel_ids": default_channel_ids,
            "enabled_channels": default_enabled_counts,
            "channel_names": self.default_channel_names,
        }

        self.config.register_guild(**default_guild)

        self.default_role = {"enabled": False, "channel_id": None, "name": "{role}: {count}"}

        self.config.register_role(**self.default_role)

        self._critical_section_wooah_ = 0

        self.channel_data = defaultdict(dict)

        self.edit_queue = defaultdict(lambda: defaultdict(lambda: asyncio.Queue(maxsize=2)))

        self._rate_limited_edits: Dict[int, Dict[str, Optional[asyncio.Task]]] = defaultdict(
            lambda: defaultdict(lambda: None)
        )

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    async def initialize(self):
        for guild in self.bot.guilds:
            await self.update_infochannel(guild)

    def cog_unload(self):
        self.stop_all_queues()

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
        category_id = await self.config.guild(guild).category_id()
        category = None

        if category_id is not None:
            category: Union[discord.CategoryChannel, None] = guild.get_channel(category_id)

        if category_id is not None and category is None:
            await ctx.maybe_send_embed("Info category has been deleted, recreate it?")
        elif category_id is None:
            await ctx.maybe_send_embed("Enable info channels on this server?")
        else:
            await ctx.maybe_send_embed("Do you wish to delete current info channels?")

        msg = await self.bot.wait_for("message", check=check)

        if msg.content.upper() in ["N", "NO"]:
            await ctx.maybe_send_embed("Cancelled")
            return

        if category is None:
            try:
                await self.make_infochannel(guild)
            except discord.Forbidden:
                await ctx.maybe_send_embed(
                    "Failure: Missing permission to create necessary channels"
                )
                return
        else:
            await self.delete_all_infochannels(guild)

        ctx.message = msg

        if not await ctx.tick():
            await ctx.maybe_send_embed("Done!")

    @commands.group(aliases=["icset"])
    @checks.admin()
    async def infochannelset(self, ctx: commands.Context):
        """
        Toggle different types of infochannels
        """
        pass

    @infochannelset.command(name="togglechannel")
    async def _infochannelset_togglechannel(
        self, ctx: commands.Context, channel_type: str, enabled: Optional[bool] = None
    ):
        """Toggles the infochannel for the specified channel type.

        Valid Types are:
        - `members`: Total members on the server
        - `humans`: Total members that aren't bots
        - `bots`: Total bots
        - `roles`: Total number of roles
        - `channels`: Total number of channels excluding infochannels,
        - `online`: Total online members,
        - `offline`: Total offline members,
        """
        guild = ctx.guild
        if channel_type not in self.default_channel_names.keys():
            await ctx.maybe_send_embed("Invalid channel type provided.")
            return

        if enabled is None:
            enabled = not await self.config.guild(guild).enabled_channels.get_raw(channel_type)

        await self.config.guild(guild).enabled_channels.set_raw(channel_type, value=enabled)
        await self.make_infochannel(ctx.guild, channel_type=channel_type)

        if enabled:
            await ctx.maybe_send_embed(f"InfoChannel `{channel_type}` has been enabled.")
        else:
            await ctx.maybe_send_embed(f"InfoChannel `{channel_type}` has been disabled.")

    @infochannelset.command(name="togglerole")
    async def _infochannelset_rolecount(
        self, ctx: commands.Context, role: discord.Role, enabled: bool = None
    ):
        """Toggle an infochannel that shows the count of users with the specified role"""
        if enabled is None:
            enabled = not await self.config.role(role).enabled()

        await self.config.role(role).enabled.set(enabled)

        await self.make_infochannel(ctx.guild, channel_role=role)

        if enabled:
            await ctx.maybe_send_embed(f"InfoChannel for {role.name} count has been enabled.")
        else:
            await ctx.maybe_send_embed(f"InfoChannel for {role.name} count has been disabled.")

    @infochannelset.command(name="name")
    async def _infochannelset_name(self, ctx: commands.Context, channel_type: str, *, text=None):
        """
        Change the name of the infochannel for the specified channel type.

        {count} must be used to display number of total members in the server.
        Leave blank to set back to default.

        Examples:
        - `[p]infochannelset name members Cool Cats: {count}`
        - `[p]infochannelset name bots {count} Robot Overlords`

        Valid Types are:
        - `members`: Total members on the server
        - `humans`: Total members that aren't bots
        - `bots`: Total bots
        - `roles`: Total number of roles
        - `channels`: Total number of channels excluding infochannels
        - `online`: Total online members
        - `offline`: Total offline members

        Warning: This command counts against the channel update rate limit and may be queued.
        """
        guild = ctx.guild
        if channel_type not in self.default_channel_names.keys():
            await ctx.maybe_send_embed("Invalid channel type provided.")
            return

        if text is None:
            text = self.default_channel_names.get(channel_type)
        elif "{count}" not in text:
            await ctx.maybe_send_embed(
                "Improperly formatted. Make sure to use `{count}` in your channel name"
            )
            return
        elif len(text) > 93:
            await ctx.maybe_send_embed("Name is too long, max length is 93.")
            return

        await self.config.guild(guild).channel_names.set_raw(channel_type, value=text)
        await self.update_infochannel(guild, channel_type=channel_type)
        if not await ctx.tick():
            await ctx.maybe_send_embed("Done!")

    @infochannelset.command(name="rolename")
    async def _infochannelset_rolename(
        self, ctx: commands.Context, role: discord.Role, *, text=None
    ):
        """
        Change the name of the infochannel for specific roles.

        {count} must be used to display number members with the given role.
        {role} can be used for the roles name.
        Leave blank to set back to default.

        Default is set to: `{role}: {count}`

        Examples:
        - `[p]infochannelset rolename @Patrons {role}: {count}`
        - `[p]infochannelset rolename Elite {count} members with {role} role`
        - `[p]infochannelset rolename "Space Role" Total boosters: {count}`

        Warning: This command counts against the channel update rate limit and may be queued.
        """
        guild = ctx.message.guild
        if text is None:
            text = self.default_role["name"]
        elif "{count}" not in text:
            await ctx.maybe_send_embed(
                "Improperly formatted. Make sure to use `{count}` in your channel name"
            )
            return

        await self.config.role(role).name.set(text)
        await self.update_infochannel(guild, channel_role=role)
        if not await ctx.tick():
            await ctx.maybe_send_embed("Done!")

    async def create_individual_channel(
        self, guild, category: discord.CategoryChannel, overwrites, channel_type, count
    ):
        # Delete the channel if it exists
        channel_id = await self.config.guild(guild).channel_ids.get_raw(channel_type)
        if channel_id is not None:
            channel: discord.VoiceChannel = guild.get_channel(channel_id)
            if channel:
                self.stop_queue(guild.id, channel_type)
                await channel.delete(reason="InfoChannel delete")

        # Only make the channel if it's enabled
        if await self.config.guild(guild).enabled_channels.get_raw(channel_type):
            name = await self.config.guild(guild).channel_names.get_raw(channel_type)
            name = name.format(count=count)
            channel = await category.create_voice_channel(
                name, reason="InfoChannel make", overwrites=overwrites
            )
            await self.config.guild(guild).channel_ids.set_raw(channel_type, value=channel.id)
            return channel
        return None

    async def create_role_channel(
        self, guild, category: discord.CategoryChannel, overwrites, role: discord.Role
    ):
        # Delete the channel if it exists
        channel_id = await self.config.role(role).channel_id()
        if channel_id is not None:
            channel: discord.VoiceChannel = guild.get_channel(channel_id)
            if channel:
                self.stop_queue(guild.id, role.id)
                await channel.delete(reason="InfoChannel delete")

        # Only make the channel if it's enabled
        if await self.config.role(role).enabled():
            count = len(role.members)
            name = await self.config.role(role).name()
            name = name.format(role=role.name, count=count)
            channel = await category.create_voice_channel(
                name, reason="InfoChannel make", overwrites=overwrites
            )
            await self.config.role(role).channel_id.set(channel.id)
            return channel
        return None

    async def make_infochannel(self, guild: discord.Guild, channel_type=None, channel_role=None):
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(connect=False),
            guild.me: discord.PermissionOverwrite(manage_channels=True, connect=True),
        }

        # Check for and create the Infochannel category
        category_id = await self.config.guild(guild).category_id()
        if category_id is not None:
            category: discord.CategoryChannel = guild.get_channel(category_id)
            if category is None:  # Category id is invalid, probably deleted.
                category_id = None
        if category_id is None:
            category: discord.CategoryChannel = await guild.create_category(
                "Server Stats", reason="InfoChannel Category make"
            )
            await self.config.guild(guild).category_id.set(category.id)
            await category.edit(position=0)
            category_id = category.id

        category: discord.CategoryChannel = guild.get_channel(category_id)

        channel_data = await get_channel_counts(category, guild)

        # Only update a single channel
        if channel_type is not None:
            await self.create_individual_channel(
                guild, category, overwrites, channel_type, channel_data[channel_type]
            )
            return
        if channel_role is not None:
            await self.create_role_channel(guild, category, overwrites, channel_role)
            return

        # Update all channels
        for channel_type in self.default_channel_names.keys():
            await self.create_individual_channel(
                guild, category, overwrites, channel_type, channel_data[channel_type]
            )

        for role in guild.roles:
            await self.create_role_channel(guild, category, overwrites, role)

        # await self.update_infochannel(guild)

    async def delete_all_infochannels(self, guild: discord.Guild):
        self.stop_guild_queues(guild.id)  # Stop processing edits

        # Delete regular channels
        for channel_type in self.default_channel_names.keys():
            channel_id = await self.config.guild(guild).channel_ids.get_raw(channel_type)
            if channel_id is not None:
                channel = guild.get_channel(channel_id)
                if channel is not None:
                    await channel.delete(reason="InfoChannel delete")
                await self.config.guild(guild).channel_ids.clear_raw(channel_type)

        # Delete role channels
        for role in guild.roles:
            channel_id = await self.config.role(role).channel_id()
            if channel_id is not None:
                channel = guild.get_channel(channel_id)
                if channel is not None:
                    await channel.delete(reason="InfoChannel delete")
                await self.config.role(role).channel_id.clear()

        # Delete the category last
        category_id = await self.config.guild(guild).category_id()
        if category_id is not None:
            category = guild.get_channel(category_id)
            if category is not None:
                await category.delete(reason="InfoChannel delete")

    async def add_to_queue(self, guild, channel, identifier, count, formatted_name):
        self.channel_data[guild.id][identifier] = (count, formatted_name, channel.id)
        if not self.edit_queue[guild.id][identifier].full():
            try:
                self.edit_queue[guild.id][identifier].put_nowait(identifier)
            except asyncio.QueueFull:
                pass  # If queue is full, disregard

        if self._rate_limited_edits[guild.id][identifier] is None:
            await self.start_queue(guild.id, identifier)

    async def update_individual_channel(self, guild, channel_type, count, guild_data):
        name = guild_data["channel_names"][channel_type]
        name = name.format(count=count)
        channel = guild.get_channel(guild_data["channel_ids"][channel_type])
        if channel is None:
            return  # abort
        await self.add_to_queue(guild, channel, channel_type, count, name)

    async def update_role_channel(self, guild, role: discord.Role, role_data):
        if not role_data["enabled"]:
            return  # Not enabled
        count = len(role.members)
        name = role_data["name"]
        name = name.format(role=role.name, count=count)
        channel = guild.get_channel(role_data["channel_id"])
        if channel is None:
            return  # abort
        await self.add_to_queue(guild, channel, role.id, count, name)

    async def update_infochannel(self, guild: discord.Guild, channel_type=None, channel_role=None):
        if channel_type is None and channel_role is None:
            return await self.trigger_updates_for(
                guild,
                members=True,
                humans=True,
                bots=True,
                roles=True,
                channels=True,
                online=True,
                offline=True,
                extra_roles=set(guild.roles),
            )

        if channel_type is not None:
            return await self.trigger_updates_for(guild, **{channel_type: True})

        return await self.trigger_updates_for(guild, extra_roles={channel_role})

    async def start_queue(self, guild_id, identifier):
        self._rate_limited_edits[guild_id][identifier] = asyncio.create_task(
            self._process_queue(guild_id, identifier)
        )

    def stop_queue(self, guild_id, identifier):
        if self._rate_limited_edits[guild_id][identifier] is not None:
            self._rate_limited_edits[guild_id][identifier].cancel()

    def stop_guild_queues(self, guild_id):
        for identifier in self._rate_limited_edits[guild_id].keys():
            self.stop_queue(guild_id, identifier)

    def stop_all_queues(self):
        for guild_id in self._rate_limited_edits.keys():
            self.stop_guild_queues(guild_id)

    async def _process_queue(self, guild_id, identifier):
        while True:
            identifier = await self.edit_queue[guild_id][identifier].get()  # Waits forever

            count, formatted_name, channel_id = self.channel_data[guild_id][identifier]
            channel: discord.VoiceChannel = self.bot.get_channel(channel_id)

            if channel.name == formatted_name:
                continue  # Nothing to process

            log.debug(f"Processing guild_id: {guild_id} - identifier: {identifier}")

            try:
                await channel.edit(reason="InfoChannel update", name=formatted_name)
            except (discord.Forbidden, discord.HTTPException):
                pass  # Don't bother figuring it out
            except discord.InvalidArgument:
                log.exception(f"Invalid formatted infochannel: {formatted_name}")
            else:
                await asyncio.sleep(RATE_LIMIT_DELAY)  # Wait a reasonable amount of time

    async def trigger_updates_for(self, guild, **kwargs):
        extra_roles: Optional[set] = kwargs.pop("extra_roles", False)
        guild_data = await self.config.guild(guild).all()

        to_update = (
            kwargs.keys() & guild_data["enabled_channels"].keys()
        )  # Value in kwargs doesn't matter

        log.debug(f"{to_update=}")

        if to_update or extra_roles:
            category = guild.get_channel(guild_data["category_id"])
            if category is None:
                return  # Nothing to update, must be off

            channel_data = await get_channel_counts(category, guild)
            if to_update:
                for channel_type in to_update:
                    await self.update_individual_channel(
                        guild, channel_type, channel_data[channel_type], guild_data
                    )
            if extra_roles:
                role_data = await self.config.all_roles()
                for channel_role in extra_roles:
                    if channel_role.id in role_data:
                        await self.update_role_channel(
                            guild, channel_role, role_data[channel_role.id]
                        )

    @Cog.listener(name="on_member_join")
    @Cog.listener(name="on_member_remove")
    async def on_member_join_remove(self, member: discord.Member):
        if await self.bot.cog_disabled_in_guild(self, member.guild):
            return

        if member.bot:
            await self.trigger_updates_for(
                member.guild, members=True, bots=True, online=True, offline=True
            )
        else:
            await self.trigger_updates_for(
                member.guild, members=True, humans=True, online=True, offline=True
            )

    @Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if await self.bot.cog_disabled_in_guild(self, after.guild):
            return

        if before.status != after.status:
            return await self.trigger_updates_for(after.guild, online=True, offline=True)

        # XOR
        c = set(after.roles) ^ set(before.roles)

        if c:
            await self.trigger_updates_for(after.guild, extra_roles=c)

    @Cog.listener("on_guild_channel_create")
    @Cog.listener("on_guild_channel_delete")
    async def on_guild_channel_create_delete(self, channel: discord.TextChannel):
        if await self.bot.cog_disabled_in_guild(self, channel.guild):
            return
        await self.trigger_updates_for(channel.guild, channels=True)

    @Cog.listener()
    async def on_guild_role_create(self, role):
        if await self.bot.cog_disabled_in_guild(self, role.guild):
            return
        await self.trigger_updates_for(role.guild, roles=True)

    @Cog.listener()
    async def on_guild_role_delete(self, role):
        if await self.bot.cog_disabled_in_guild(self, role.guild):
            return
        await self.trigger_updates_for(role.guild, roles=True)

        role_channel_id = await self.config.role(role).channel_id()
        if role_channel_id is not None:
            rolechannel: discord.VoiceChannel = role.guild.get_channel(role_channel_id)
            if rolechannel:
                await rolechannel.delete(reason="InfoChannel delete")

        await self.config.role(role).clear()
