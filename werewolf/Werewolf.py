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
    async def new(self, ctx, game_code):
        """
        Create and join a new game of Werewolf
        """
        
        game = self._get_game(ctx.guild, game_code)
        
        if not game:
            ctx.send("
        
    @ww.command()
    async def join(self, ctx):
        """
        Joins a game of Werewolf
        """
        
        game = self._get_game(ctx.guild)
        
        if not game:
            ctx.send("No game to join!\nCreate a new one with `[p]ww new`")
            return

        await game.join(ctx.author, ctx.channel)

    @ww.command()
    async def quit(self, ctx):
        """
        Quit a game of Werewolf
        """
        
        game = self._get_game(ctx.guild)
        
        await game.quit(ctx.author, ctx.channel)

    @ww.command()
    async def vote(self, ctx, id):
        """
        Vote for a player by ID
        """
        game = self._get_game(guild)
        if not game:
            ctx.send("No game running, cannot vote")
        
        # Game handles response now
        channel = ctx.channel
        if channel is game.village_channel: 
            await game.vote(ctx.author, id, channel)
        
        if channel in (c for id,c in game.secret_channels.items()):
            await game.vote(ctx.author, id, channel)

    def _get_game(self, guild, game_code = None):
        if guild.id not in self.games:
            if not game_code:
                return None
            self.games[guild.id] = Game(game_code)

        return self.games[guild.id]


    async def _game_start(self, game):
        await game.start()
        
    
    async def on_message(self, message):
        if message.author.id == self.bot.user.id:
            return
        
        author = message.author
        channel = message.channel
        guild = message.guild
        
        
        if channel is game.village_channel:
            
