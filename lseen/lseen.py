from datetime import datetime

import dateutil.parser
import discord

from redbot.core import Config
from redbot.core.bot import Red
from redbot.core import commands


class LastSeen:
    """
    V3 Cog Template
    """

    online_status = discord.Status.online

    offline_status = discord.Status.offline

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9811198108111121, force_registration=True)
        default_global = {}
        default_guild = {
            "enabled": True
        }
        default_member = {
            "seen": None
        }

        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member)

    @staticmethod
    def get_date_time(s):
        d = dateutil.parser.parse(s)
        return d

    @commands.group(aliases=['setlseen'], name='lseenset')
    async def lset(self, ctx: commands.Context):
        """Change settings for lseen"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @lset.command(name="toggle")
    async def lset_toggle(self, ctx: commands.Context):
        """Toggles tracking seen for this server"""
        enabled = not await self.config.guild(ctx.guild).enabled()
        await self.config.guild(ctx.guild).enabled.set(
            enabled)

        await ctx.send(
            "Seen for this server is now {}".format(
                "Enabled" if enabled else "Disabled"))

    @commands.command(aliases=['lastseen'])
    async def lseen(self, ctx: commands.Context, member: discord.Member):
        """
        Just says the time the user was last seen
        """

        if member.status != self.offline_status:
            last_seen = datetime.utcnow()
        else:
            last_seen = await self.config.member(member).seen()
            if last_seen is None:
                await ctx.send(embed=discord.Embed(description="I've never seen this user"))
                return
            last_seen = self.get_date_time(last_seen)

        # embed = discord.Embed(
        #     description="{} was last seen at this date and time".format(member.display_name),
        #     timestamp=self.get_date_time(last_seen))

        embed = discord.Embed(timestamp=last_seen)
        await ctx.send(embed=embed)

    # async def on_socket_raw_receive(self, data):
    #     try:
    #         if type(data) == str:
    #             raw = json.loads(data)
    #             print(data)
    #     except:
    #         print(data)

    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.status != self.offline_status and after.status == self.offline_status:
            if not await self.config.guild(before.guild).enabled():
                return
            await self.config.member(before).seen.set(datetime.utcnow().isoformat())
