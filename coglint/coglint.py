import discord
from discord.ext import commands
from redbot.core import Config, checks, RedContext

from redbot.core.bot import Red

import pylint


class CogLint:
    """
    V3 Cog Template
    """

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9811198108111121, force_registration=True)
        default_global = {}
        default_guild = {}

        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

    @commands.command()
    async def lint(self, ctx: RedContext):
        await ctx.send("Hello World")
