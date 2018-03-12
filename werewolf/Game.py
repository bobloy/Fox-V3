import asyncio

import discord

from datetime import datetime,timedelta

from .builder import parse_code

class Game:
    """
    Base class to run a single game of Werewolf
    """

    def __init__(self, role_code):
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
        
        self.loop = asyncio.get_event_loop()
        
        
        

    async def setup(self, ctx):
        """
        Runs the initial setup
        
        1. Assign Roles
        2. Create Channels
        2a.  Channel Permissions :eyes:
        3. Check Initial role setup (including alerts)
        4. Start game
        """
        if len(self.players) != self.roles:
            ctx.send("Players does not match roles, cannot start")
            return False
        
        
        
        
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
    
    async def _at_game_start(self):  # ID 0
        if self.game_over:
            return
        await self._notify(0)
        
        asyncio.sleep(60)
        await self._at_day_start()
        
    async def _at_day_start(self):  # ID 1
        if self.game_over:
            return
        await self._notify(1)
        
        asyncio.sleep(240)  # 4 minute days
        await self._at_day_end()
        
    async def _at_vote(self, target):  # ID 2
        if self.game_over:
            return
        await self._notify(2, target)
    
    async def _at_kill(self, target):  # ID 3
        if self.game_over:
            return
        await self._notify(3, target)
    
    async def _at_hang(self, target):  # ID 4
        if self.game_over:
            return
        await self._notify(4, target)
        
    async def _at_day_end(self):  # ID 5
        if self.game_over:
            return
        await self._notify(5)
        
        asyncio.sleep(60)
        await self._at_night_start()
        
    async def _at_night_start(self):  # ID 6
        if self.game_over:
            return
        await self._notify(6)
        
        asyncio.sleep(120) 
        # 2 minutes left
        asyncio.sleep(90) 
        # 30 seconds left
        asyncio.sleep(30)
        
        await self._at_night_end()
        
    async def _at_night_end(self):  # ID 7
        if self.game_over:
            return
        await self._notify(7)
        
        asyncio.sleep(15)
        await self._at_day_start()
            
    async def _notify(self, event):
        for i in range(10):
            tasks = []
            role_order = [role for role in self.roles if role.priority==i]
            for role in role_action:
                tasks.append(asyncio.ensure_future(role.on_event(event))
            # self.loop.create_task(role.on_event(event))
            self.loop.run_until_complete(asyncio.gather(*tasks))
        
    
    async def join(self, member: discord.Member):
        """
        Have a member join a game
        """
        if self.started:
            return "**Game has already started!**"
        
        if member in self.players:
            return "{} is already in the game!".format(member.mention)
        
        self.started.append(member)
        
        out = "{} has been added to the game, total players is **{}**".format(member.mention, len(self.players))
        
    async def quit(self, member: discord.Member):
        """
        Have a member quit a game
        """
        player = await self.get_player_by_member(member)
        
        if not player:
            return "You're not in a game!"

        if self.started:
            await self.kill()
        
        if member in self.players:
            return "{} is already in the game!".format(member.mention)
        
        self.started.append(member)
        
        out = "{} has been added to the game, total players is **{}**".format(member.mention, len(self.players))
        
        
    
    async def get_roles(self, role_code=None):
        if role_code:
            self.role_code=role_code
        
        if not self.role_code:
            return False
        
        self.roles = await parse_code(self.role_code)
        
        if not self.roles:
            return False