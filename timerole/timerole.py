import asyncio
import logging
from datetime import datetime, timedelta

import discord
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.commands import Cog, parse_timedelta
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import pagify

log = logging.getLogger("red.fox_v3.timerole")


async def sleep_till_next_hour():
    now = datetime.utcnow()
    next_hour = datetime(year=now.year, month=now.month, day=now.day, hour=now.hour + 1)
    log.debug("Sleeping for {} seconds".format((next_hour - datetime.utcnow()).seconds))
    await asyncio.sleep((next_hour - datetime.utcnow()).seconds)


class Timerole(Cog):
    """Add roles to users based on time on server"""

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9811198108111121, force_registration=True)
        default_global = {}
        default_guild = {"announce": None, "roles": {}}

        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)
        self.updating = asyncio.create_task(self.check_hour())

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    def cog_unload(self):
        self.updating.cancel()

    @commands.command()
    @checks.guildowner()
    @commands.guild_only()
    async def runtimerole(self, ctx: commands.Context):
        """
        Trigger the hourly timerole

        Useful for troubleshooting the initial setup
        """

        async with ctx.typing():
            await self.timerole_update()
            await ctx.tick()

    @commands.group()
    @checks.mod_or_permissions(administrator=True)
    @commands.guild_only()
    async def timerole(self, ctx):
        """Adjust timerole settings"""
        if ctx.invoked_subcommand is None:
            pass

    @timerole.command()
    async def addrole(
        self, ctx: commands.Context, role: discord.Role, time: str, *requiredroles: discord.Role
    ):
        """Add a role to be added after specified time on server"""
        guild = ctx.guild

        try:
            parsed_time = parse_timedelta(time, allowed_units=["weeks", "days", "hours"])
        except commands.BadArgument:
            await ctx.maybe_send_embed("Error: Invalid time string.")
            return

        days = parsed_time.days
        hours = parsed_time.seconds // 60 // 60

        to_set = {"days": days, "hours": hours, "remove": False}
        if requiredroles:
            to_set["required"] = [r.id for r in requiredroles]

        await self.config.guild(guild).roles.set_raw(role.id, value=to_set)
        await ctx.maybe_send_embed(
            "Time Role for {0} set to {1} days  and {2} hours until added".format(
                role.name, days, hours
            )
        )

    @timerole.command()
    async def removerole(
        self, ctx: commands.Context, role: discord.Role, time: str, *requiredroles: discord.Role
    ):
        """
        Add a role to be removed after specified time on server

        Useful with an autorole cog
        """
        guild = ctx.guild
        try:
            parsed_time = parse_timedelta(time, allowed_units=["weeks", "days", "hours"])
        except commands.BadArgument:
            await ctx.maybe_send_embed("Error: Invalid time string.")
            return

        days = parsed_time.days
        hours = parsed_time.seconds // 60 // 60

        to_set = {"days": days, "hours": hours, "remove": True}
        if requiredroles:
            to_set["required"] = [r.id for r in requiredroles]

        await self.config.guild(guild).roles.set_raw(role.id, value=to_set)
        await ctx.maybe_send_embed(
            "Time Role for {0} set to {1} days and {2} hours until removed".format(
                role.name, days, hours
            )
        )

    @timerole.command()
    async def channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Sets the announce channel for role adds"""
        guild = ctx.guild

        await self.config.guild(guild).announce.set(channel.id)
        await ctx.send("Announce channel set to {0}".format(channel.mention))

    @timerole.command()
    async def delrole(self, ctx: commands.Context, role: discord.Role):
        """Deletes a role from being added/removed after specified time"""
        guild = ctx.guild

        await self.config.guild(guild).roles.set_raw(role.id, value=None)
        await ctx.send("{0} will no longer be applied".format(role.name))

    @timerole.command()
    async def list(self, ctx: commands.Context):
        """Lists all currently setup timeroles"""
        guild = ctx.guild

        role_dict = await self.config.guild(guild).roles()
        out = "Current Timeroles:\n"
        for r_id, r_data in role_dict.items():
            if r_data is not None:
                role = discord.utils.get(guild.roles, id=int(r_id))
                r_roles = []
                if role is None:
                    role = r_id
                if "required" in r_data:
                    r_roles = [
                        str(discord.utils.get(guild.roles, id=int(new_id)))
                        for new_id in r_data["required"]
                    ]
                out += "{} | {} days | requires: {}\n".format(str(role), r_data["days"], r_roles)
        await ctx.maybe_send_embed(out)

    async def timerole_update(self):
        for guild in self.bot.guilds:
            addlist = []
            removelist = []

            role_dict = await self.config.guild(guild).roles()
            if not any(role_data for role_data in role_dict.values()):  # No roles
                continue

            async for member in AsyncIter(guild.members):
                has_roles = [r.id for r in member.roles]

                add_roles = [
                    int(rID)
                    for rID, r_data in role_dict.items()
                    if r_data is not None and not r_data["remove"]
                ]
                remove_roles = [
                    int(rID)
                    for rID, r_data in role_dict.items()
                    if r_data is not None and r_data["remove"]
                ]

                check_add_roles = set(add_roles) - set(has_roles)
                check_remove_roles = set(remove_roles) & set(has_roles)

                await self.check_required_and_date(
                    addlist, check_add_roles, has_roles, member, role_dict
                )
                await self.check_required_and_date(
                    removelist, check_remove_roles, has_roles, member, role_dict
                )

            channel = await self.config.guild(guild).announce()
            if channel is not None:
                channel = guild.get_channel(channel)

            title = "**These members have received the following roles**\n"
            await self.announce_roles(title, addlist, channel, guild, to_add=True)
            title = "**These members have lost the following roles**\n"
            await self.announce_roles(title, removelist, channel, guild, to_add=False)

    async def announce_roles(self, title, role_list, channel, guild, to_add: True):
        results = ""
        for member, role_id in role_list:
            role = discord.utils.get(guild.roles, id=role_id)
            try:
                if to_add:
                    await member.add_roles(role, reason="Timerole")
                else:
                    await member.remove_roles(role, reason="Timerole")
            except (discord.Forbidden, discord.NotFound) as e:
                results += "{} : {} **(Failed)**\n".format(member.display_name, role.name)
            else:
                results += "{} : {}\n".format(member.display_name, role.name)
        if channel is not None and results:
            await channel.send(title)
            for page in pagify(results, shorten_by=50):
                await channel.send(page)
        elif results:  # Channel is None, log the results
            log.info(results)

    async def check_required_and_date(self, role_list, check_roles, has_roles, member, role_dict):
        for role_id in check_roles:
            # Check for required role
            if "required" in role_dict[str(role_id)]:
                if not set(role_dict[str(role_id)]["required"]) & set(has_roles):
                    # Doesn't have required role
                    continue

            if (
                member.joined_at
                + timedelta(
                    days=role_dict[str(role_id)]["days"],
                    hours=role_dict[str(role_id)].get("hours", 0),
                )
                <= datetime.today()
            ):
                # Qualifies
                role_list.append((member, role_id))

    async def check_hour(self):
        await sleep_till_next_hour()
        while self is self.bot.get_cog("Timerole"):
            await self.timerole_update()
            await sleep_till_next_hour()

from moviepy.editor import VideoFileClip

