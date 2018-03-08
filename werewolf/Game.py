import asyncio

import discord

from datetime import datetime,timedelta

from .builder import parse_code

class Game:
    """
    Base to host a game of werewolf
    """

    def __init__(self, role_code=None):
        self.roles = []
        self.role_code = role_code
        
        if self.role_code:
            self.get_roles()
        
        self.players = []
        self.start_vote = 0
        
        self.started = False

    async def setup(self, ctx):
        """
        Runs the initial setup
        """
        if self.role_code:
            if not await self.get_roles():
        
        if not self.roles:
            ctx.send("No game code set, cannot start until this is set")
            
    async def join(self, member: discord.Member):
        """
        Joins a game
        """
        if self.started:
            return "**Game has already started!**"
        
        if member in self.players:
            return "{} is already in the game!".format(member.mention)
        
        self.started.append(member)
        
        return "{} has been added to the game, total players is **{}**".format(member.mention, len(self.players))
    
    async def get_roles(self, role_code=None):
        if role_code:
            self.role_code=role_code
        
        if not self.role_code:
            return False
        
        self.roles = await parse_code(self.role_code)
        
        if not self.roles:
            return False