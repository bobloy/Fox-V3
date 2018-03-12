import asyncio

import discord
from discord.ext import commands

from redbot.core import Config

from datetime import datetime,timedelta

from .game import Game

class Werewolf:
    """
    Base to host werewolf on a server
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=87101114101119111108102, force_registration=True)
        default_global = {}
        default_guild = {
            }
        
       
        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)
        
        self.games = {}  # Active games stored here, id is per server
    
    @commands.group()
    async def ww(self, ctx: commands.Context):
        """
        Base command for this cog. Check help for the commands list.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help()
            
    @ww.command()
    async def join(self, ctx, role_code=None):
        """
        Joins a game of Werewolf or start a new one
        """
        
        game = self._get_game(ctx, setup_id)
        out = await game.join(ctx.author)
        
        ctx.send(out)
    
    @ww.command()
    async def quit(self, ctx):
        """
        Quit a game of Werewolf
        """
        
        game = self._get_game(ctx)
        
        out = await game.quit(ctx.author)
        
        ctx.send(out)

    def _get_game(self, ctx, role_code):
        if ctx.guild.id not in self.games:
            self.games[ctx.guild.id] = Game(role_code)

        return self.games[ctx.guild.id]


    async def _game_start(self, game):
        await game.start()
