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
            "category_id": None,
            "channel_id": None,
            "humanchannel_id": None,
            "botchannel_id": None,
            "roleschannel_id": None,
            "channels_channel_id": None,
            "onlinechannel_id": None,
            "offlinechannel_id": None,
            "role_ids":{},
            "member_count": True,
            "human_count": False,
            "bot_count": False,
            "roles_count": False,
            "channels_count": False,
            "online_count": False,
            "offline_count": False,
            "channel_names":{
                "category_name": "Server Stats",
                "members_channel": "Total Members: {count}",
                "humans_channel": "Humans: {count}",
                "bots_channel": "Bots: {count}",
                "roles_channel": "Total Roles: {count}",
                "channels_channel": "Total Channels: {count}",
                "online_channel": "Online: {count}",
                "offline_channel": "Offline:{count}",
                "role_channel": "{role}: {count}"
            }
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
        category_id = await self.config.guild(guild).category_id()
        category = None

        if category_id is not None:
            category: Union[discord.CategoryChannel, None] = guild.get_channel(category_id)

        if category_id is not None and category is None:
            await ctx.send("Info category has been deleted, recreate it?")
        elif category_id is None:
            await ctx.send("Enable info channels on this server?")
        else:
            await ctx.send("Do you wish to delete current info channels?")

        msg = await self.bot.wait_for("message", check=check)

        if msg.content.upper() in ["N", "NO"]:
            await ctx.send("Cancelled")
            return

        if category is None:
            try:
                await self.make_infochannel(guild)
            except discord.Forbidden:
                await ctx.send("Failure: Missing permission to create neccessary channels")
                return
        else:
            await self.delete_all_infochannels(guild)

        if not await ctx.tick():
            await ctx.send("Done!")

    @commands.group(aliases=['icset'])
    @checks.admin()
    async def infochannelset(self, ctx: commands.Context):
        """
        Toggle different types of infochannels
        """
        if not ctx.invoked_subcommand:
            pass
    
    @infochannelset.command(name="membercount")
    async def _infochannelset_membercount(self, ctx: commands.Context, enabled: bool = None):
        """
        Toggle an infochannel that shows the amount of total members in the server
        """
        guild = ctx.guild
        if enabled is None:
            enabled = not await self.config.guild(guild).member_count()

        await self.config.guild(guild).member_count.set(enabled)
        await self.make_infochannel(ctx.guild)

        if enabled:
            await ctx.send("InfoChannel for member count has been enabled.")
        else:
            await ctx.send("InfoChannel for member count has been disabled.")

    @infochannelset.command(name="humancount")
    async def _infochannelset_humancount(self, ctx: commands.Context, enabled: bool = None):
        """
        Toggle an infochannel that shows the amount of human users in the server
        """
        guild = ctx.guild
        if enabled is None:
            enabled = not await self.config.guild(guild).human_count()

        await self.config.guild(guild).human_count.set(enabled)
        await self.make_infochannel(ctx.guild)

        if enabled:
            await ctx.send("InfoChannel for human user count has been enabled.")
        else:
            await ctx.send("InfoChannel for human user count has been disabled.")
    
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

    @infochannelset.command(name="rolescount")
    async def _infochannelset_rolescount(self, ctx: commands.Context, enabled: bool = None):
        """
        Toggle an infochannel that shows the amount of roles in the server
        """
        guild = ctx.guild
        if enabled is None:
            enabled = not await self.config.guild(guild).roles_count()

        await self.config.guild(guild).roles_count.set(enabled)
        await self.make_infochannel(ctx.guild)

        if enabled:
            await ctx.send("InfoChannel for roles count has been enabled.")
        else:
            await ctx.send("InfoChannel for roles count has been disabled.")

    @infochannelset.command(name="channelscount")
    async def _infochannelset_channelscount(self, ctx: commands.Context, enabled: bool = None):
        """
        Toggle an infochannel that shows the amount of channels in the server
        """
        guild = ctx.guild
        if enabled is None:
            enabled = not await self.config.guild(guild).channels_count()

        await self.config.guild(guild).channels_count.set(enabled)
        await self.make_infochannel(ctx.guild)

        if enabled:
            await ctx.send("InfoChannel for channels count has been enabled.")
        else:
            await ctx.send("InfoChannel for channels count has been disabled.")

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

    @infochannelset.command(name="offlinecount")
    async def _infochannelset_offlinecount(self, ctx: commands.Context, enabled: bool = None):
        """
        Toggle an infochannel that shows the amount of offline users in the server
        """
        guild = ctx.guild
        if enabled is None:
            enabled = not await self.config.guild(guild).offline_count()

        await self.config.guild(guild).offline_count.set(enabled)
        await self.make_infochannel(ctx.guild)

        if enabled:
            await ctx.send("InfoChannel for offline user count has been enabled.")
        else:
            await ctx.send("InfoChannel for offline user count has been disabled.")

    @infochannelset.command(name="rolecount")
    async def _infochannelset_rolecount(self, ctx: commands.Context, role: discord.Role, enabled: bool = None):
        """
        Toggle an infochannel that shows the amount of users in the server with the specified role
        """
        guild = ctx.guild
        role_data = await self.config.guild(guild).role_ids.all()

        if str(role.id) in role_data.keys():
            enabled = False
        else:
            enabled = True

        await self.make_infochannel(ctx.guild, role)

        if enabled:
            await ctx.send(f"InfoChannel for {role.name} count has been enabled.")
        else:
            await ctx.send(f"InfoChannel for {role.name} count has been disabled.")

    @infochannelset.group(name='name')
    async def channelname(self, ctx: commands.Context):
        """
        Change the name of the infochannels
        """
        if not ctx.invoked_subcommand:
            pass
    
    @channelname.command(name='category')
    async def _channelname_Category(self, ctx: commands.Context, *, text):
        """
        Change the name of the infochannel's category.
        """
        guild = ctx.message.guild
        category_id = await self.config.guild(guild).category_id()
        category: discord.CategoryChannel = guild.get_channel(category_id)
        await category.edit(name = text)
        await self.config.guild(guild).channel_names.category_name.set(text)
        if not await ctx.tick():
            await ctx.send("Done!")

    @channelname.command(name='members')
    async def _channelname_Members(self, ctx: commands.Context, *, text=None):
        """
        Change the name of the total members infochannel.

        {count} can be used to display number of total members in the server.
        Leave blank to set back to default
        Default is set to:
            Total Members: {count}

        Example Formats:
            Total Members: {count}
            {count} Members
        """
        guild = ctx.message.guild
        if text:
            await self.config.guild(guild).channel_names.members_channel.set(text)
        else:
            await self.config.guild(guild).channel_names.members_channel.clear()

        await self.update_infochannel(guild)
        if not await ctx.tick():
            await ctx.send("Done!")

    @channelname.command(name='humans')
    async def _channelname_Humans(self, ctx: commands.Context, *, text=None):
        """
        Change the name of the human users infochannel.

        {count} can be used to display number of users in the server.
        Leave blank to set back to default
        Default is set to:
            Humans: {count}

        Example Formats:
            Users: {count}
            {count} Users
        """
        guild = ctx.message.guild
        if text:
            await self.config.guild(guild).channel_names.humans_channel.set(text)
        else:
            await self.config.guild(guild).channel_names.humans_channel.clear()

        await self.update_infochannel(guild)
        if not await ctx.tick():
            await ctx.send("Done!")
    
    @channelname.command(name='bots')
    async def _channelname_Bots(self, ctx: commands.Context, *, text=None):
        """
        Change the name of the bots infochannel.

        {count} can be used to display number of bots in the server.
        Leave blank to set back to default
        Default is set to:
            Bots: {count}

        Example Formats:
            Total Bots: {count}
            {count} Robots
        """
        guild = ctx.message.guild
        if text:
            await self.config.guild(guild).channel_names.bots_channel.set(text)
        else:
            await self.config.guild(guild).channel_names.bots_channel.clear()

        await self.update_infochannel(guild)
        if not await ctx.tick():
            await ctx.send("Done!")

    @channelname.command(name='roles')
    async def _channelname_Roles(self, ctx: commands.Context, *, text=None):
        """
        Change the name of the roles infochannel.

        Do NOT confuse with the role command that counts number of members with a specified role

        {count} can be used to display number of roles in the server.
        Leave blank to set back to default
        Default is set to:
            Total Roles: {count}

        Example Formats:
            Total Roles: {count}
            {count} Roles
        """
        guild = ctx.message.guild
        if text:
            await self.config.guild(guild).channel_names.roles_channel.set(text)
        else:
            await self.config.guild(guild).channel_names.roles_channel.clear()

        await self.update_infochannel(guild)
        if not await ctx.tick():
            await ctx.send("Done!")
    
    @channelname.command(name='channels')
    async def _channelname_Channels(self, ctx: commands.Context, *, text=None):
        """
        Change the name of the channels infochannel.

        {count} can be used to display number of channels in the server.
        This does not count the infochannels
        Leave blank to set back to default
        Default is set to:
            Total Channels: {count}

        Example Formats:
            Total Channels: {count}
            {count} Channels
        """
        guild = ctx.message.guild
        if text:
            await self.config.guild(guild).channel_names.channels_channel.set(text)
        else:
            await self.config.guild(guild).channel_names.channels_channel.clear()

        await self.update_infochannel(guild)
        if not await ctx.tick():
            await ctx.send("Done!")

    @channelname.command(name='online')
    async def _channelname_Online(self, ctx: commands.Context, *, text=None):
        """
        Change the name of the online infochannel.

        {count} can be used to display number online members in the server.
        Leave blank to set back to default
        Default is set to:
            Online: {count}

        Example Formats:
            Total Online: {count}
            {count} Online Members
        """
        guild = ctx.message.guild
        if text:
            await self.config.guild(guild).channel_names.online_channel.set(text)
        else:
            await self.config.guild(guild).channel_names.online_channel.clear()

        await self.update_infochannel(guild)
        if not await ctx.tick():
            await ctx.send("Done!")

    @channelname.command(name='offline')
    async def _channelname_Offline(self, ctx: commands.Context, *, text=None):
        """
        Change the name of the offline infochannel.

        {count} can be used to display number offline members in the server.
        Leave blank to set back to default
        Default is set to:
            Offline: {count}

        Example Formats:
            Total Offline: {count}
            {count} Offline Members
        """
        guild = ctx.message.guild
        if text:
            await self.config.guild(guild).channel_names.offline_channel.set(text)
        else:
            await self.config.guild(guild).channel_names.offline_channel.clear()

        await self.update_infochannel(guild)
        if not await ctx.tick():
            await ctx.send("Done!")

    @channelname.command(name='role')
    async def _channelname_Role(self, ctx: commands.Context, *, text=None):
        """
        Change the name of the infochannel for specific roles.
        
        All role infochannels follow this format.
        Do NOT confuse with the roles command that counts number of roles in the server

        {count} can be used to display number members with the given role.
        {role} can be used for the roles name
        Leave blank to set back to default
        Default is set to:
            {role}: {count}

        Example Formats:
            {role}: {count}
            {count} with {role} role
        """
        guild = ctx.message.guild
        if text:
            await self.config.guild(guild).channel_names.role_channel.set(text)
        else:
            await self.config.guild(guild).channel_names.role_channel.clear()

        await self.update_infochannel(guild)
        if not await ctx.tick():
            await ctx.send("Done!")

    async def make_infochannel(self, guild: discord.Guild, role: discord.Role = None):
        membercount = await self.config.guild(guild).member_count()
        humancount = await self.config.guild(guild).human_count()
        botcount = await self.config.guild(guild).bot_count()
        rolescount = await self.config.guild(guild).roles_count()
        channelscount = await self.config.guild(guild).channels_count()
        onlinecount = await self.config.guild(guild).online_count()
        offlinecount = await self.config.guild(guild).offline_count()
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(connect=False),
            guild.me: discord.PermissionOverwrite(manage_channels=True, connect=True),
        }

        #   Check for and create the category
        category_id = await self.config.guild(guild).category_id()
        if category_id is not None:
            category: discord.CategoryChannel = guild.get_channel(category_id)
            if category is None:
                await self.config.guild(guild).category_id.set(None)
                category_id = None
        
        if category_id is None:
            category: discord.CategoryChannel = await guild.create_category(
                "Server Stats", reason="InfoChannel Category make"
            )
            await self.config.guild(guild).category_id.set(category.id)
            await category.edit(position = 0)
            category_id = category.id
        
        category: discord.CategoryChannel = guild.get_channel(category_id)
        
        #  Remove the old members channel first
        channel_id = await self.config.guild(guild).channel_id()
        if category_id is not None:
            channel: discord.VoiceChannel = guild.get_channel(channel_id)
            if channel:
                await channel.delete(reason="InfoChannel delete")
        if membercount:
            # Then create the new one
            channel = await category.create_voice_channel(
                "Total Members:", reason="InfoChannel make", overwrites=overwrites
            )
            await self.config.guild(guild).channel_id.set(channel.id)

        # Remove the old human channel first
        humanchannel_id = await self.config.guild(guild).humanchannel_id()
        if category_id is not None:
            humanchannel: discord.VoiceChannel = guild.get_channel(humanchannel_id)
            if humanchannel:
                await humanchannel.delete(reason="InfoChannel delete")
        if humancount:
            # Then create the new one
            humanchannel = await category.create_voice_channel(
                "Humans:", reason="InfoChannel humancount", overwrites=overwrites
            )
            await self.config.guild(guild).humanchannel_id.set(humanchannel.id)

        
        # Remove the old bot channel first
        botchannel_id = await self.config.guild(guild).botchannel_id()
        if category_id is not None:
            botchannel: discord.VoiceChannel = guild.get_channel(botchannel_id)
            if botchannel:
                await botchannel.delete(reason="InfoChannel delete")
        if botcount:
            # Then create the new one
            botchannel = await category.create_voice_channel(
                "Bots:", reason="InfoChannel botcount", overwrites=overwrites
            )
            await self.config.guild(guild).botchannel_id.set(botchannel.id)

        
        # Remove the old roles channel first
        roleschannel_id = await self.config.guild(guild).roleschannel_id()
        if category_id is not None:
            roleschannel: discord.VoiceChannel = guild.get_channel(roleschannel_id)
            if roleschannel:
                await roleschannel.delete(reason="InfoChannel delete")

        if rolescount:
            # Then create the new one
            roleschannel = await category.create_voice_channel(
                "Total Roles:", reason="InfoChannel rolescount", overwrites=overwrites
            )
            await self.config.guild(guild).roleschannel_id.set(roleschannel.id)

        
        # Remove the old channels channel first
        channels_channel_id = await self.config.guild(guild).channels_channel_id()
        if category_id is not None:
            channels_channel: discord.VoiceChannel = guild.get_channel(channels_channel_id)
            if channels_channel:
                await channels_channel.delete(reason="InfoChannel delete")
        if channelscount:
            # Then create the new one
            channels_channel = await category.create_voice_channel(
                "Total Channels:", reason="InfoChannel botcount", overwrites=overwrites
            )
            await self.config.guild(guild).channels_channel_id.set(channels_channel.id)
        
        # Remove the old online channel first
        onlinechannel_id = await self.config.guild(guild).onlinechannel_id()
        if channel_id is not None:
            onlinechannel: discord.VoiceChannel = guild.get_channel(onlinechannel_id)
            if onlinechannel:
                await onlinechannel.delete(reason="InfoChannel delete")
        if onlinecount:
            # Then create the new one
            onlinechannel = await category.create_voice_channel(
                "Online:", reason="InfoChannel onlinecount", overwrites=overwrites
            )
            await self.config.guild(guild).onlinechannel_id.set(onlinechannel.id)
        
        # Remove the old offline channel first
        offlinechannel_id = await self.config.guild(guild).offlinechannel_id()
        if channel_id is not None:
            offlinechannel: discord.VoiceChannel = guild.get_channel(offlinechannel_id)
            if offlinechannel:
                await offlinechannel.delete(reason="InfoChannel delete")
        if offlinecount:
            # Then create the new one
            offlinechannel = await category.create_voice_channel(
                "Offline:", reason="InfoChannel offlinecount", overwrites=overwrites
            )
            await self.config.guild(guild).offlinechannel_id.set(offlinechannel.id)

        async with self.config.guild(guild).role_ids() as role_data:
            #Remove the old role channels first
            for role_id in role_data.keys():
                role_channel_id = role_data[role_id]
                if role_channel_id is not None:
                    rolechannel: discord.VoiceChannel = guild.get_channel(role_channel_id)
                    if rolechannel:
                        await rolechannel.delete(reason="InfoChannel delete")

            #The actual toggle for a role counter
            if role:
                if str(role.id) in role_data.keys():
                    role_data.pop(str(role.id)) #if the role is there, then remove it
                else:
                    role_data[role.id] = None #No channel created yet but we want one to be made
            if role_data:
                # Then create the new ones
                for role_id in role_data.keys():
                    rolechannel = await category.create_voice_channel(
                        str(role_id)+":", reason="InfoChannel rolecount", overwrites=overwrites
                    )
                    role_data[role_id] = rolechannel.id

        await self.update_infochannel(guild)

    async def delete_all_infochannels(self, guild: discord.Guild):
        guild_data = await self.config.guild(guild).all()
        role_data = guild_data["role_ids"]
        category_id = guild_data["category_id"]
        humanchannel_id = guild_data["humanchannel_id"]
        botchannel_id = guild_data["botchannel_id"]
        roleschannel_id = guild_data["roleschannel_id"]
        channels_channel_id = guild_data["channels_channel_id"]
        onlinechannel_id = guild_data["onlinechannel_id"]
        offlinechannel_id = guild_data["offlinechannel_id"]
        category: discord.CategoryChannel = guild.get_channel(category_id)
        humanchannel: discord.VoiceChannel = guild.get_channel(humanchannel_id)
        botchannel: discord.VoiceChannel = guild.get_channel(botchannel_id)
        roleschannel: discord.VoiceChannel = guild.get_channel(roleschannel_id)
        channels_channel: discord.VoiceChannel = guild.get_channel(channels_channel_id)
        onlinechannel: discord.VoiceChannel = guild.get_channel(onlinechannel_id)
        offlinechannel: discord.VoiceChannel = guild.get_channel(offlinechannel_id)
        channel_id = guild_data["channel_id"]
        channel: discord.VoiceChannel = guild.get_channel(channel_id)
        await channel.delete(reason="InfoChannel delete")
        if humanchannel_id is not None:
            await humanchannel.delete(reason="InfoChannel delete")
        if botchannel_id is not None:
            await botchannel.delete(reason="InfoChannel delete")
        if roleschannel_id is not None:
            await roleschannel.delete(reason="InfoChannel delete")
        if channels_channel is not None:
            await channels_channel.delete(reason="InfoChannel delete")
        if onlinechannel_id is not None:
            await onlinechannel.delete(reason="InfoChannel delete")
        if offlinechannel_id is not None:
            await offlinechannel.delete(reason="InfoChannel delete")
        if category_id is not None:
            await category.delete(reason="InfoChannel delete")
        async with self.config.guild(guild).role_ids() as role_data:
            if role_data:
                for role_channel_id in role_data.values():
                    rolechannel: discord.VoiceChannel = guild.get_channel(role_channel_id)
                    if rolechannel:
                        await rolechannel.delete(reason="InfoChannel delete")
        
        await self.config.guild(guild).clear()

    async def update_infochannel(self, guild: discord.Guild):
        guild_data = await self.config.guild(guild).all()
        humancount = guild_data["human_count"]
        botcount = guild_data["bot_count"]
        rolescount = guild_data["roles_count"]
        channelscount = guild_data["channels_count"]
        onlinecount = guild_data["online_count"]
        offlinecount = guild_data["offline_count"]

        category = guild.get_channel(guild_data["category_id"])

        # Gets count of bots
        # bots = lambda x: x.bot
        # def bots(x): return x.bot

        bot_num = len([m for m in guild.members if m.bot])
        # bot_msg = f"Bots: {num}"

        #Gets count of roles in the server
        roles_num = len(guild.roles)-1
        # roles_msg = f"Total Roles: {num}"

        #Gets count of channels in the server
        #<number of total channels> - <number of channels in the stats category> - <categories>
        channels_num = len(guild.channels) - len(category.voice_channels) - len(guild.categories)
        # channels_msg = f"Total Channels: {num}"

        # Gets all counts of members
        members = guild.member_count
        # member_msg = f"Total Members: {num}"
        offline = len(list(filter(lambda m: m.status is discord.Status.offline, guild.members)))
        # offline_msg = f"Offline: {num}"
        online_num = members - offline
        # online_msg = f"Online: {num}"

        # Gets count of actual users
        total = lambda x: not x.bot
        human_num = len([m for m in guild.members if total(m)])
        # human_msg = f"Users: {num}"

        channel_id = guild_data["channel_id"]
        if channel_id is None:
            return False

        botchannel_id = guild_data["botchannel_id"]
        roleschannel_id = guild_data["roleschannel_id"]
        channels_channel_id = guild_data["channels_channel_id"]
        onlinechannel_id = guild_data["onlinechannel_id"]
        offlinechannel_id = guild_data["offlinechannel_id"]
        humanchannel_id = guild_data["humanchannel_id"]
        channel_id = guild_data["channel_id"]
        channel: discord.VoiceChannel = guild.get_channel(channel_id)
        humanchannel: discord.VoiceChannel = guild.get_channel(humanchannel_id)
        botchannel: discord.VoiceChannel = guild.get_channel(botchannel_id)
        roleschannel: discord.VoiceChannel = guild.get_channel(roleschannel_id)
        channels_channel: discord.VoiceChannel = guild.get_channel(channels_channel_id)
        onlinechannel: discord.VoiceChannel = guild.get_channel(onlinechannel_id)
        offlinechannel: discord.VoiceChannel = guild.get_channel(offlinechannel_id)

        channel_names = await self.config.guild(guild).channel_names.all()

        if guild_data["member_count"]:
            name = channel_names["members_channel"].format(count = members)
            await channel.edit(reason="InfoChannel update", name=name)

        if humancount:
            name = channel_names["humans_channel"].format(count = human_num)
            await humanchannel.edit(reason="InfoChannel update", name=name)

        if botcount:
            name = channel_names["bots_channel"].format(count = bot_num)
            await botchannel.edit(reason="InfoChannel update", name=name)
        
        if rolescount:
            name = channel_names["roles_channel"].format(count = roles_num)
            await roleschannel.edit(reason="InfoChannel update", name=name)
        
        if channelscount:
            name = channel_names["channels_channel"].format(count = channels_num)
            await channels_channel.edit(reason="InfoChannel update", name=name)

        if onlinecount:
            name = channel_names["online_channel"].format(count = online_num)
            await onlinechannel.edit(reason="InfoChannel update", name=name)
        
        if offlinecount:
            name = channel_names["offline_channel"].format(count = offline)
            await offlinechannel.edit(reason="InfoChannel update", name=name)

        async with self.config.guild(guild).role_ids() as role_data:
            if role_data:
                for role_id, role_channel_id in role_data.items():
                    rolechannel: discord.VoiceChannel = guild.get_channel(role_channel_id)
                    role: discord.Role = guild.get_role(int(role_id))

                    role_num = len(role.members)

                    name = channel_names["role_channel"].format(count = role_num, role = role.name)
                    await rolechannel.edit(reason="InfoChannel update", name=name)


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
        role_data = await self.config.guild(after.guild).role_ids.all()
        if role_data:
            b = set(before.roles)
            a = set(after.roles)
            if b != a:
                await self.update_infochannel_with_cooldown(after.guild)

    @Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        if await self.bot.cog_disabled_in_guild(self, channel.guild):
            return
        channelscount = await self.config.guild(channel.guild).channels_count()
        if channelscount:
            await self.update_infochannel_with_cooldown(channel.guild)

    @Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        if await self.bot.cog_disabled_in_guild(self, channel.guild):
            return
        channelscount = await self.config.guild(channel.guild).channels_count()
        if channelscount:
            await self.update_infochannel_with_cooldown(channel.guild)
    
    @Cog.listener() 
    async def on_guild_role_create(self, role):
        if await self.bot.cog_disabled_in_guild(self, role.guild):
            return
        
        rolescount = await self.config.guild(role.guild).roles_count()
        if rolescount:
            await self.update_infochannel_with_cooldown(role.guild)

    @Cog.listener() 
    async def on_guild_role_delete(self, role):
        if await self.bot.cog_disabled_in_guild(self, role.guild):
            return
        
        rolescount = await self.config.guild(role.guild).roles_count()
        if rolescount:
            await self.update_infochannel_with_cooldown(role.guild)
        
        #delete specific role counter if the role is deleted
        async with self.config.guild(role.guild).role_ids() as role_data:
            if str(role.id) in role_data.keys():
                role_channel_id = role_data[str(role.id)]
                rolechannel: discord.VoiceChannel = role.guild.get_channel(role_channel_id)
                await rolechannel.delete(reason="InfoChannel delete")
                del role_data[str(role.id)]
