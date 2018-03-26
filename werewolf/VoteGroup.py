import asyncio

import discord


class VoteGroup:
    """
    Base VoteGroup class for werewolf game
    Handles secret channels and group decisions
    Default handles wolf kill vote
    """
    
    allignment = 2     # 1: Town, 2: Werewolf, 3: Neutral
    channel_id = "werewolves" 

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
            
    vote_emojis = 
            
    def __init__(self, game):
        self.game = game
        self.channel = None
        self.properties = {}  # Extra data for other options
        self.vote_message = None
        
    async def on_event(self, event, data):
        """
        See Game class for event guide
        """
            
        await action_list[event][0](data)

    
    async def _at_game_start(self, data=None):
        if self.channel_id:
            self.channel = await self.game.register_channel(self.channel_id)

    async def _at_day_start(self, data=None):
        
    async def _at_voted(self, data=None):
        pass
        
    async def _at_kill(self, data=None):
        pass
        
    async def _at_hang(self, data=None):
        pass
        
    async def _at_day_end(self, data=None):
        pass
        
    async def _at_night_start(self, data=None):
        if self.channel is None:
            return
        
        self.vote_message = await self.game.generate_targets(self.channel)
        
        
        
    async def _at_night_end(self, data=None):
        if self.channel is None:
            return