from datetime import date, timedelta
from typing import Literal

import discord
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.commands import Cog
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import pagify


class Flag(Cog):
    """
    Set expiring flags on members
    """

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9811198108111121, force_registration=True)
        default_global = {}
        default_guild = {"days": 31, "dm": True, "flags": {}}

        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ):
        if requester not in ["discord_deleted_user", "owner"]:
            return

        all_guilds = await self.config.all_guilds()

        async for guild_id, guild_data in AsyncIter(all_guilds.items(), steps=100):
            if user_id in guild_data["flags"]:
                await self.config.guild_from_id(guild_id).flags.clear_raw(user_id)

    @checks.is_owner()
    @commands.guild_only()
    @commands.command()
    async def clearallflag(self, ctx: commands.Context):
        """Clears all flags for all members in this server"""

        await self.config.guild(ctx.guild).flags.clear()
        await ctx.maybe_send_embed("Done")

    @checks.mod_or_permissions(manage_roles=True)
    @commands.guild_only()
    @commands.group()
    async def flagset(self, ctx: commands.Context):
        """
        Commands for managing Flag settings
        """
        pass

    @flagset.command(name="expire")
    async def flagset_expire(self, ctx: commands.Context, days: int):
        """
        Set the number of days for flags to expire after for server
        """
        await self.config.guild(ctx.guild).days.set(days)
        await ctx.maybe_send_embed(
            "Number of days for new flags to expire is now {} days".format(days)
        )

    @flagset.command(name="dm")
    async def flagset_dm(self, ctx: commands.Context):
        """Toggles DM-ing the flags"""

        dm = await self.config.guild(ctx.guild).dm()
        await self.config.guild(ctx.guild).dm.set(not dm)

        await ctx.maybe_send_embed(
            "DM-ing members when they get a flag is now set to **{}**".format(not dm)
        )

    @staticmethod
    def _flag_template():
        return {"reason": "", "expireyear": 0, "expiremonth": 0, "expireday": 0}

    @commands.guild_only()
    @checks.mod_or_permissions(manage_roles=True)
    @commands.command()
    async def flag(self, ctx: commands.Context, member: discord.Member, *, reason):
        """Flag a member"""
        guild = ctx.guild
        await self._check_flags(guild)

        flag = self._flag_template()
        expire_date = date.today() + timedelta(days=await self.config.guild(guild).days())

        flag["reason"] = reason
        flag["expireyear"] = expire_date.year
        flag["expiremonth"] = expire_date.month
        flag["expireday"] = expire_date.day

        # flags = await self.config.guild(guild).flags.get_raw(str(member.id), default=[])
        # flags.append(flag)
        # await self.config.guild(guild).flags.set_raw(str(member.id), value=flags)

        async with self.config.guild(guild).flags() as flags:
            if str(member.id) not in flags:
                flags[str(member.id)] = []
            flags[str(member.id)].append(flag)

        outembed = await self._list_flags(member)

        if outembed:
            await ctx.send(embed=outembed)
            if await self.config.guild(guild).dm():
                try:
                    await member.send(embed=outembed)
                except discord.Forbidden:
                    await ctx.maybe_send_embed("DM-ing user failed")
        else:
            await ctx.maybe_send_embed("This member has no flags.. somehow..")

    @commands.guild_only()
    @checks.mod_or_permissions(manage_roles=True)
    @commands.command(aliases=["flagclear"])
    async def clearflag(self, ctx: commands.Context, member: discord.Member):
        """Clears flags for a member"""
        guild = ctx.guild
        await self._check_flags(guild)

        await self.config.guild(guild).flags.set_raw(str(member.id), value=[])

        await ctx.maybe_send_embed("Success!")

    @commands.guild_only()
    @commands.command(aliases=["flaglist"])
    async def listflag(self, ctx: commands.Context, member: discord.Member):
        """Lists flags for a member"""
        server = ctx.guild
        await self._check_flags(server)

        outembed = await self._list_flags(member)

        if outembed:
            await ctx.send(embed=outembed)
        else:
            await ctx.maybe_send_embed("This member has no flags!")

    @commands.guild_only()
    @commands.command(aliases=["flagall"])
    async def allflag(self, ctx: commands.Context):
        """Lists all flags for the server"""
        guild = ctx.guild
        await self._check_flags(guild)
        out = "All flags for {}\n".format(ctx.guild.name)

        flags = await self.config.guild(guild).flags()
        flag_d = {}
        for memberid, flag_data in flags.items():
            if len(flag_data) > 0:
                member = guild.get_member(int(memberid))
                flag_d[member.display_name + member.discriminator] = len(flag_data)

        for display_name, flag_count in sorted(flag_d.items()):
            out += "{} - **{}** flags".format(display_name, flag_count)

        for page in pagify(out):
            await ctx.send(page)

    async def _list_flags(self, member: discord.Member):
        """Returns a pretty embed of flags on a member"""
        flags = await self.config.guild(member.guild).flags.get_raw(str(member.id), default=[])

        embed = discord.Embed(
            title="Flags for " + member.display_name,
            description="User has {} active flags".format(len(flags)),
            color=0x804040,
        )
        for flag in flags:
            embed.add_field(
                name="Reason: " + flag["reason"],
                value="Expires on "
                + str(date(flag["expireyear"], flag["expiremonth"], flag["expireday"])),
                inline=True,
            )

        embed.set_thumbnail(url=member.avatar_url)

        return embed

    async def _check_flags(self, guild: discord.Guild):
        """Updates and removes expired flags"""
        flag_data = await self.config.guild(guild).flags()
        # flag_d = {}
        for memberid, flags in flag_data.items():
            # for member in guild.members:
            # flags = await self.config.guild(guild).flags.get_raw(str(member.id), default=[])
            x = 0
            while x < len(flags):
                flag = flags[x]
                if date.today() >= date(
                    flag["expireyear"], flag["expiremonth"], flag["expireday"]
                ):
                    del flags[x]
                else:
                    x += 1

            await self.config.guild(guild).flags.set_raw(memberid, value=flags)
