from typing import Any

import discord
from redbot.core import Config, commands, checks
from redbot.core.bot import Red

Cog: Any = getattr(commands, "Cog", object)


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
            "category_id": None,
            "member_count": True,
            "channel_count": False,
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
            await ctx.send("Info channel is {}. Delete it?".format(channel.mention))

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

    async def make_infochannel(self, guild: discord.Guild):
        category: discord.CategoryChannel = await guild.create_category("────Server Stats────")

        overwrites = {guild.default_role: discord.PermissionOverwrite(connect=False)}

        channel = await guild.create_voice_channel(
            "Placeholder", category=category, reason="InfoChannel make", overwrites=overwrites
        )

        await self.config.guild(guild).channel_id.set(channel.id)
        await self.config.guild(guild).category_id.set(category.id)

        await self.update_infochannel(guild)

    async def delete_infochannel(self, guild: discord.Guild, channel: discord.VoiceChannel):
        await channel.category.delete(reason="InfoChannel delete")
        await channel.delete(reason="InfoChannel delete")
        await self.config.guild(guild).clear()

    async def update_infochannel(self, guild: discord.Guild):
        guild_data = await self.config.guild(guild).all()

        channel_id = guild_data["channel_id"]
        if channel_id is None:
            return

        channel: discord.VoiceChannel = guild.get_channel(channel_id)

        if channel is None:
            return

        name = ""
        if guild_data["member_count"]:
            name += "Members: {} ".format(guild.member_count)

        if guild_data["channel_count"]:
            name += "─ Channels: {}".format(len(guild.channels))

        if name == "":
            name = "Stats not enabled"

        await channel.edit(reason="InfoChannel update", name=name)

    async def on_member_join(self, member: discord.Member):
        await self.update_infochannel(member.guild)

    async def on_member_remove(self, member: discord.Member):
        await self.update_infochannel(member.guild)
