import os

import challonge

import discord
from discord.ext import commands

from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.chat_formatting import box
from redbot.core import Config
from redbot.core import checks




class Challonge:
    """Cog for organizing Challonge tourneys"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=6710497108108111110103101)
        default_global = {  
                "srtracker": {}
                }
        default_guild = {
                "current": None,
                }

        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)
        
      

# ************************Fight command group start************************


    @commands.group()
    @commands.guild_only()
    async def challonge(self, ctx):
        """Challonge command base"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()
            # await ctx.send("I can do stuff!")

