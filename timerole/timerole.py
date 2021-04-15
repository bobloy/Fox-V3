import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

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


async def announce_to_channel(channel, results, title):
    if channel is not None and results:
        await channel.send(title)
        for page in pagify(results, shorten_by=50):
            await channel.send(page)
    elif results:  # Channel is None, log the results
        log.info(results)


class Timerole(Cog):
    """Add roles to users based on time on server"""

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9811198108111121, force_registration=True)
        default_global = {}
        default_guild = {"announce": None, "reapply": True, "roles": {}}
        default_rolemember = {"had_role": False, "check_again_time": None}

        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

        self.config.init_custom("RoleMember", 2)
        self.config.register_custom("RoleMember", **default_rolemember)

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
            pre_run = datetime.utcnow()
            await self.timerole_update()
            after_run = datetime.utcnow()
            await ctx.tick()

        await ctx.maybe_send_embed(f"Took {after_run-pre_run} seconds")

    @commands.group()
    @checks.mod_or_permissions(administrator=True)
    @commands.guild_only()
    async def timerole(self, ctx):
        """Adjust timerole settings"""
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
            f"Time Role for {role.name} set to {days} days  and {hours} hours until added"
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
            f"Time Role for {role.name} set to {days} days  and {hours} hours until removed"
        )

    @timerole.command()
    async def channel(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        """Sets the announce channel for role adds"""
        guild = ctx.guild
        if channel is None:
            await self.config.guild(guild).announce.clear()
            await ctx.maybe_send_embed(f"Announce channel has been cleared")
        else:
            await self.config.guild(guild).announce.set(channel.id)
            await ctx.send(f"Announce channel set to {channel.mention}")

    @timerole.command()
    async def reapply(self, ctx: commands.Context):
        """Toggle reapplying roles if the member loses it somehow. Defaults to True"""
        guild = ctx.guild
        current_setting = await self.config.guild(guild).reapply()
        await self.config.guild(guild).reapply.set(not current_setting)
        await ctx.maybe_send_embed(f"Reapplying roles is now set to: {not current_setting}")

    @timerole.command()
    async def delrole(self, ctx: commands.Context, role: discord.Role):
        """Deletes a role from being added/removed after specified time"""
        guild = ctx.guild

        await self.config.guild(guild).roles.set_raw(role.id, value=None)
        await self.config.custom("RoleMember", role.id).clear()
        await ctx.maybe_send_embed(f"{role.name} will no longer be applied")

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
                out += f"{role} | {r_data['days']} days | requires: {r_roles}\n"
        await ctx.maybe_send_embed(out)

    async def timerole_update(self):
        utcnow = datetime.utcnow()
        all_guilds = await self.config.all_guilds()

        # all_mrs = await self.config.custom("RoleMember").all()

        # log.debug(f"Begin timerole update")

        for guild in self.bot.guilds:
            guild_id = guild.id
            if guild_id not in all_guilds:
                log.debug(f"Guild has no configured settings: {guild}")
                continue

            add_results = ""
            remove_results = ""
            reapply = all_guilds[guild_id]["reapply"]
            role_dict = all_guilds[guild_id]["roles"]

            if not any(role_dict.values()):  # No roles
                log.debug(f"No roles are configured for guild: {guild}")
                continue

            # all_mr = await self.config.all_custom("RoleMember")
            # log.debug(f"{all_mr=}")

            async for member in AsyncIter(guild.members, steps=10):
                addlist = []
                removelist = []

                for role_id, role_data in role_dict.items():
                    # Skip non-configured roles
                    if not role_data:
                        continue

                    mr_dict = await self.config.custom("RoleMember", role_id, member.id).all()

                    # Stop if they've had the role and reapplying is disabled
                    if not reapply and mr_dict["had_role"]:
                        log.debug(f"{member.display_name} - Not reapplying")
                        continue

                    # Stop if the check_again_time hasn't passed yet
                    if (
                        mr_dict["check_again_time"] is not None
                        and datetime.fromisoformat(mr_dict["check_again_time"]) >= utcnow
                    ):
                        log.debug(f"{member.display_name} - Not time to check again yet")
                        continue
                    member: discord.Member
                    has_roles = {r.id for r in member.roles}

                    # Stop if they currently have or don't have the role, and mark had_role
                    if (int(role_id) in has_roles and not role_data["remove"]) or (
                        int(role_id) not in has_roles and role_data["remove"]
                    ):
                        if not mr_dict["had_role"]:
                            await self.config.custom(
                                "RoleMember", role_id, member.id
                            ).had_role.set(True)
                        log.debug(f"{member.display_name} - applying had_role")
                        continue

                    # Stop if they don't have all the required roles
                    if role_data is None or (
                        "required" in role_data and not set(role_data["required"]) & has_roles
                    ):
                        continue

                    check_time = member.joined_at + timedelta(
                        days=role_data["days"],
                        hours=role_data.get("hours", 0),
                    )

                    # Check if enough time has passed to get the role and save the check_again_time
                    if check_time >= utcnow:
                        await self.config.custom(
                            "RoleMember", role_id, member.id
                        ).check_again_time.set(check_time.isoformat())
                        log.debug(
                            f"{member.display_name} - Not enough time has passed to qualify for the role\n"
                            f"Waiting until {check_time}"
                        )
                        continue

                    if role_data["remove"]:
                        removelist.append(role_id)
                    else:
                        addlist.append(role_id)

                # Done iterating through roles, now add or remove the roles
                if not addlist and not removelist:
                    continue

                # log.debug(f"{addlist=}\n{removelist=}")
                add_roles = [
                    discord.utils.get(guild.roles, id=int(role_id)) for role_id in addlist
                ]
                remove_roles = [
                    discord.utils.get(guild.roles, id=int(role_id)) for role_id in removelist
                ]

                if None in add_roles or None in remove_roles:
                    log.info(
                        f"Timerole ran into an error with the roles in: {add_roles + remove_roles}"
                    )

                if addlist:
                    try:
                        await member.add_roles(*add_roles, reason="Timerole", atomic=False)
                    except (discord.Forbidden, discord.NotFound) as e:
                        log.exception("Failed Adding Roles")
                        add_results += f"{member.display_name} : **(Failed Adding Roles)**\n"
                    else:
                        add_results += " \n".join(
                            f"{member.display_name} : {role.name}" for role in add_roles
                        )
                        for role_id in addlist:
                            await self.config.custom(
                                "RoleMember", role_id, member.id
                            ).had_role.set(True)

                if removelist:
                    try:
                        await member.remove_roles(*remove_roles, reason="Timerole", atomic=False)
                    except (discord.Forbidden, discord.NotFound) as e:
                        log.exception("Failed Removing Roles")
                        remove_results += f"{member.display_name} : **(Failed Removing Roles)**\n"
                    else:
                        remove_results += " \n".join(
                            f"{member.display_name} : {role.name}" for role in remove_roles
                        )
                        for role_id in removelist:
                            await self.config.custom(
                                "RoleMember", role_id, member.id
                            ).had_role.set(True)

            # Done iterating through members, now maybe announce to the guild
            channel = await self.config.guild(guild).announce()
            if channel is not None:
                channel = guild.get_channel(channel)

            if add_results:
                title = "**These members have received the following roles**\n"
                await announce_to_channel(channel, add_results, title)
            if remove_results:
                title = "**These members have lost the following roles**\n"
                await announce_to_channel(channel, remove_results, title)
        # End

    # async def announce_roles(self, title, role_list, channel, guild, to_add: True):
    #     results = ""
    #     async for member, role_id in AsyncIter(role_list):
    #         role = discord.utils.get(guild.roles, id=role_id)
    #         try:
    #             if to_add:
    #                 await member.add_roles(role, reason="Timerole")
    #             else:
    #                 await member.remove_roles(role, reason="Timerole")
    #         except (discord.Forbidden, discord.NotFound) as e:
    #             results += f"{member.display_name} : {role.name} **(Failed)**\n"
    #         else:
    #             results += f"{member.display_name} : {role.name}\n"
    #     if channel is not None and results:
    #         await channel.send(title)
    #         for page in pagify(results, shorten_by=50):
    #             await channel.send(page)
    #     elif results:  # Channel is None, log the results
    #         log.info(results)

    # async def check_required_and_date(self, role_list, check_roles, has_roles, member, role_dict):
    #     async for role_id in AsyncIter(check_roles):
    #         # Check for required role
    #         if "required" in role_dict[str(role_id)]:
    #             if not set(role_dict[str(role_id)]["required"]) & set(has_roles):
    #                 # Doesn't have required role
    #                 continue
    #
    #         if (
    #             member.joined_at
    #             + timedelta(
    #                 days=role_dict[str(role_id)]["days"],
    #                 hours=role_dict[str(role_id)].get("hours", 0),
    #             )
    #             <= datetime.utcnow()
    #         ):
    #             # Qualifies
    #             role_list.append((member, role_id))

    async def check_hour(self):
        await sleep_till_next_hour()
        while self is self.bot.get_cog("Timerole"):
            await self.timerole_update()
            await sleep_till_next_hour()
