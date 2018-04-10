import asyncio

import discord
from discord.ext import commands

from redbot.core import Config

from datetime import datetime, timedelta

from werewolf.game import Game


class Werewolf:
    """
    Base to host werewolf on a guild
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=87101114101119111108102, force_registration=True)
        default_global = {}
        default_guild = {
            }

        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)
        
        self.games = {}  # Active games stored here, id is per guild
    
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
            await ctx.send("Failed to start a new game")
        else:
            await ctx.send("New game has started")
        
        
        
    @ww.command()
    async def join(self, ctx):
        """
        Joins a game of Werewolf
        """
        
        game = self._get_game(ctx.guild)
        
        if not game:
            await ctx.send("No game to join!\nCreate a new one with `[p]ww new`")
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
    async def start(self, ctx):
        """
        Checks number of players and attempts to start the game
        """
        game = self._get_game(ctx.guild)
        if not game:
            await ctx.send("No game running, cannot start")
        
        await game.setup(ctx)
    
    @ww.command()
    async def stop(self, ctx):
        """
        Stops the current game
        """
        game = self._get_game(ctx.guild)
        if not game:
            await ctx.send("No game running, cannot stop")
        
        game.game_over = True
        
        
    @ww.command()
    async def vote(self, ctx, id: int):
        """
        Vote for a player by ID
        """
        try:
            id = int(id)
        except:
            id = None
        
        if id is None:
            await ctx.send("`id` must be an integer")
            return

        game = self._get_game(ctx.guild)
        if not game:
            await ctx.send("No game running, cannot vote")
        
        # Game handles response now
        channel = ctx.channel
        if channel == game.village_channel: 
            await game.vote(ctx.author, id, channel)
        elif channel in (c["channel"] for c in game.p_channels.values()):
            await game.vote(ctx.author, id, channel)
        else:
            await ctx.send("Nothing to vote for in this channel")

    def _get_game(self, guild, game_code=None):
        if guild.id not in self.games:
            if not game_code:
                return None
            self.games[guild.id] = Game(guild, game_code)

        return self.games[guild.id]

    async def _game_start(self, game):
        await game.start()
