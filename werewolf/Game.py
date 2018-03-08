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
        self.game_over = False
        
        self.village_channel = None
        self.secret_channels = {}
        
        
        

    async def setup(self, ctx):
        """
        Runs the initial setup
        
        1. Assign Roles
        2. Create Channels
        2a.  Channel Permissions :eyes:
        3. Check Initial role setup (including alerts)
        4. Start game
        """
        
        
    async def _cycle(self):
        """
        Each event calls the next event
        
        _at_start()
        
        _at_day_start()
            _at_vote()
                _at_kill()
        _at_day_end()
        _at_night_begin()
        _at_night_end()
        
        and repeat with _at_morning_start() again
        """
        await self._at_start():
    
    async def _at_start(self):
    
    async def _at_day_start(self):
    
    async def _at_vote(self):
    
    async def _at_kill(self):
    
    async def _at_day_end(self):
    
    async def _at_night_start(self):
    
    async def _at_night_end(self):
            
 
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