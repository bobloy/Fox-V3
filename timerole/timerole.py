import asyncio
from datetime import timedelta, datetime

import discord
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import pagify


class Timerole:
    """Add roles to users based on time on server"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9811198108111121, force_registration=True)
        default_global = {}
        default_guild = {
            'announce': None,
            'roles': {}
        }

        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

    @commands.command()
    @checks.guildowner()
    @commands.guild_only()
    async def runtimerole(self, ctx: commands.Context):
        """Trigger the daily timerole"""

        await self.timerole_update()
        await ctx.send("Success")

    @commands.group()
    @checks.mod_or_permissions(administrator=True)
    @commands.guild_only()
    async def timerole(self, ctx):
        """Adjust timerole settings"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @timerole.command()
    async def addrole(self, ctx: commands.Context, role: discord.Role, days: int, *requiredroles: discord.Role):
        """Add a role to be added after specified time on server"""
        guild = ctx.guild

        to_set = {'days': days}
        if requiredroles:
            to_set['required'] = [r.id for r in requiredroles]

        await self.config.guild(guild).roles.set_raw(role.id, value=to_set)
        await ctx.send("Time Role for {0} set to {1} days".format(role.name, days))

    @timerole.command()
    async def channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Sets the announce channel for role adds"""
        guild = ctx.guild

        await self.config.guild(guild).announce.set(channel.id)
        await ctx.send("Announce channel set to {0}".format(channel.mention))

    @timerole.command()
    async def removerole(self, ctx: commands.Context, role: discord.Role):
        """Removes a role from being added after specified time"""
        guild = ctx.guild

        await self.config.guild(guild).roles.set_raw(role.id, value=None)
        await ctx.send("{0} will no longer be applied".format(role.name))

    @timerole.command()
    async def list(self, ctx: commands.Context):
        """Lists all currently setup timeroles"""
        guild = ctx.guild

        role_dict = await self.config.guild(guild).roles()
        out = ""
        for r_id, r_data in role_dict.items():
            if r_data is not None:
                role = discord.utils.get(guild.roles, id=int(r_id))
                r_roles = []
                if role is None:
                    role = r_id
                if 'required' in r_data:
                    r_roles = [str(discord.utils.get(guild.roles, id=int(new_id))) for new_id in r_data['required']]
                out += "{} || {} days || requires: {}\n".format(str(role), r_data['days'], r_roles)
        await ctx.maybe_send_embed(out)

    async def timerole_update(self):
        for guild in self.bot.guilds:
            addlist = []

            role_dict = await self.config.guild(guild).roles()
            if not any(role_data for role_data in role_dict.values()):  # No roles
                continue

            for member in guild.members:
                has_roles = [r.id for r in member.roles]

                get_roles = [int(rID) for rID, r_data in role_dict.items() if r_data is not None]

                check_roles = set(get_roles) - set(has_roles)

                for role_id in check_roles:
                    # Check for required role
                    if 'required' in role_dict[str(role_id)]:
                        if not set(role_dict[str(role_id)]['required']) & set(has_roles):
                            # Doesn't have required role
                            continue

                    if member.joined_at + timedelta(
                            days=role_dict[str(role_id)]['days']) <= datetime.today():
                        # Qualifies
                        addlist.append((member, role_id))

            channel = await self.config.guild(guild).announce()
            if channel is not None:
                channel = guild.get_channel(channel)

            title = "**These members have received the following roles**\n"
            results = ""
            for member, role_id in addlist:
                role = discord.utils.get(guild.roles, id=role_id)
                await member.add_roles(role, reason="Timerole")
                results += "{} : {}\n".format(member.display_name, role.name)

            if channel is not None and results:
                await channel.send(title)
                for page in pagify(
                        results, shorten_by=50):
                    await channel.send(page)

    async def check_day(self):
        while self is self.bot.get_cog("Timerole"):
            tomorrow = datetime.now() + timedelta(days=1)
            midnight = datetime(year=tomorrow.year, month=tomorrow.month,
                                day=tomorrow.day, hour=0, minute=0, second=0)

            await asyncio.sleep((midnight - datetime.now()).seconds)

            await self.timerole_update()

            await asyncio.sleep(3)
            # then start loop over again
