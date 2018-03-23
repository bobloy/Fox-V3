import asyncio

import discord

from datetime import datetime,timedelta

from cogs.werewolf.Role import Role

from cogs.werewolf.VoteGroup import WolfVote

class DefaultWerewolf(Role):
     
    rand_choice = True  
    category = [11, 15]
    allignment = 2     # 1: Town, 2: Werewolf, 3: Neutral
    channel_id = "werewolf"
    unique = False
    action_list = [
            (self._at_game_start, 0),  # (Action, Priority)
            (self._at_day_start, 0),
            (self._at_voted, 0),
            (self._at_kill, 0),
            (self._at_hang, 0),
            (self._at_day_end, 0),
            (self._at_night_start, 2),
            (self._at_night_end, 5)
            ]
            
    def __init__(self, game):
        self.game = game
        self.player = None
        self.blocked = False
        self.properties = {}  # Extra data for other roles (i.e. arsonist)
        
    async def _get_role(self, source=None):
        """
        Interaction for powerful access of role
        Unlikely to be able to deceive this
        """
        return "Werewolf"
    
    async def _see_role(self, source=None):
        """
        Interaction for investigative roles.
        More common to be able to deceive these roles
        """
        return "Werewolf"
    
    async def _at_game_start(self, data=None):
        await self.game.register_vote_group(WolfVote(self.game), self.channel_id)
        
        super()._at_game_start(data)
        
    async def _at_day_start(self, data=None):
        super()._at_day_start(data)
        
    async def _at_voted(self, data=None):
        super()._at_voted(data)
        
    async def _at_kill(self, data=None):
        super()._at_kill(data)
        
    async def _at_hang(self, data=None):
        super()._at_hang(data)
        
    async def _at_day_end(self, data=None):
        super()._at_day_end(data)
        
    async def _at_night_start(self, data=None):
        channel = self.game.channel_lock(self.channel_id, False)
        # channel = await self.game.get_channel(self.channel_id)
        
        await self.game._generate_targets(channel)
        super()._at_night_start(data)
        
    async def _at_night_end(self, data=None):
        await self.game.channel_lock(self.channel_id, True)
        
        try:
            target = data["target"]
        except:
            # No target chosen, no kill
            target = None
        
        if target:
            await self.game.kill(target)
            
        super()._at_night_end(data)