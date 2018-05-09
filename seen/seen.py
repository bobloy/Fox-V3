from datetime import datetime

import dateutil.parser
import discord
from discord.ext import commands
from redbot.core import Config, RedContext
from redbot.core.bot import Red


class Seen:
    """
    V3 Cog Template
    """

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

    @commands.command()
    async def seen(self, ctx: RedContext, member: discord.Member):

        last_seen = await self.config.member(member).seen()

        if last_seen is None:
            await ctx.send(embed=discord.Embed(description="I've never seen this user"))
        else:
            embed = discord.Embed(
                description="{} was last seen at this date and time".format(member.display_name),
                timestamp=self.get_date_time(last_seen))

            await ctx.send(embed=embed)

    # async def on_socket_raw_recieve(self, data):
    #     try:
    #         if type(data) == str:
    #             raw = json.loads(data)
    #             print(data)
    #     except:
    #         print(data)

    async def on_member_update(self, before, after):
        if before.status == 'online' and after.status == 'offline':
            if not await self.config.guild(before.guild).enabled():
                return
            await self.config.member(before).seen.set(datetime.now().isoformat())
