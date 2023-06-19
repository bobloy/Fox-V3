import asyncio
import logging
from datetime import datetime
from typing import Literal

import dateutil.parser
import discord
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.commands import Cog
from redbot.core.utils import AsyncIter

log = logging.getLogger("red.fox_v3.lseen")


class LastSeen(Cog):
    """
    Report when a user was last seen online
    """

    online_status = discord.Status.online

    offline_status = discord.Status.offline

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9811198108111121, force_registration=True)
        default_global = {"migrated_v2": False}
        default_guild = {"enabled": None}
        default_member = {"seen": None}

        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)
        # self.config.register_member(**default_member)
        self.config.init_custom("CustomMember", 2)
        self.config.register_custom("CustomMember", **default_member)

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ):

        all_members = await self.config.all_members()

        async for guild_id, guild_data in AsyncIter(all_members.items(), steps=100):
            if user_id in guild_data:
                await self.config.custom("CustomMember", guild_id, str(user_id)).clear()

    async def _initalize_tracking(self, guild: discord.Guild):
        now = datetime.utcnow().isoformat()
        online_members = {
            member.id: {"seen": now}
            for member in guild.members
            if member.status != self.offline_status
        }
        async with self.config.custom("CustomMember", guild.id).all() as cm:
            cm.update(online_members)
        # for member in guild.members:
        #     if member.status != self.offline_status:
        #         await self.config.custom("CustomMember", guild.id, member.id).seen.set(now)

    @staticmethod
    def get_date_time(s):
        return dateutil.parser.parse(s)

    @commands.group(aliases=["setlseen"], name="lseenset")
    async def lset(self, ctx: commands.Context):
        """Change settings for lseen"""
        pass

    @lset.command(name="toggle")
    async def lset_toggle(self, ctx: commands.Context):
        """Toggles tracking seen for this server"""
        enabled = await self.config.guild(ctx.guild).enabled()
        if enabled is None:
            needs_init = True
            enabled = True
        else:
            needs_init = False
            enabled = not enabled

        await self.config.guild(ctx.guild).enabled.set(enabled)

        if needs_init:
            asyncio.create_task(self._initalize_tracking(ctx.guild))

        await ctx.maybe_send_embed(
            "Seen for this server is now {}".format("Enabled" if enabled else "Disabled")
        )

    @commands.command(aliases=["lastseen"])
    async def lseen(self, ctx: commands.Context, member: discord.Member):
        """
        Just says the time the user was last seen
        """

        if member.status != self.offline_status:
            last_seen = datetime.utcnow()
            if await self.config.guild(ctx.guild).enabled():
                await self.config.custom("CustomMember", member.guild.id, member.id).seen.set(
                    last_seen.isoformat()
                )
        else:
            last_seen = await self.config.custom("CustomMember", member.guild.id, member.id).seen()
            if last_seen is None:
                await ctx.maybe_send_embed("I've never seen this user")
                return
            last_seen = self.get_date_time(last_seen)

        embed = discord.Embed(
            description="{} was last seen at this date and time".format(member.display_name),
            timestamp=last_seen,
            color=await self.bot.get_embed_color(ctx),
        )

        # embed = discord.Embed(timestamp=last_seen, color=await self.bot.get_embed_color(ctx))
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.status != self.offline_status and after.status == self.offline_status:
            if await self.bot.cog_disabled_in_guild(self, after.guild):
                return
            if not await self.config.guild(after.guild).enabled():
                return
            await self.config.custom("CustomMember", before.guild.id, before.id).seen.set(
                datetime.utcnow().isoformat()
            )

    async def initialize(self):
        if not await self.config.migrated_v2():
            all_members = await self.config.all_members()
            async for guild_id, guild_data in AsyncIter(all_members.items(), steps=100):
                async with self.config.custom("CustomMember").all() as cm:
                    cm.update(
                        {
                            str(guild_id): {str(member_id): {"seen": member_data["seen"]}}
                            for member_id, member_data in guild_data.items()
                        }
                    )
            log.info("LastSeen migrated to V2")
            await self.config.migrated_v2.set(True)
