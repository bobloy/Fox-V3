import asyncio

import discord

import random

from cogs.werewolf.votegroup import VoteGroup

class WolfVote(VoteGroup):
    """
    Werewolf implementation of base VoteGroup class
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
            (self._at_night_end, 5)  # Kill priority
            ]
            
    
    kill_messages = [
        "{target} was attacked by wolves",
        "{target} was found torn to shreds"]
    
    def __init__(self, game, members):
        self.game = game
        self.members = members
        self.channel = None
        self.vote_results = {}
        self.properties = {}  # Extra data for other options
        self.killer = None  # Added killer
        
        
    # async def on_event(self, event, data):
        # """
        # See Game class for event guide
        # """
        
        # await action_list[event][0](data)

    # async def _at_game_start(self, data=None):
        # if self.channel_id:
            # self.channel = await self.game.register_channel(self.channel_id)

    # async def _at_day_start(self, data=None):
        # pass
        
    # async def _at_voted(self, data=None):
        # pass
        
    # async def _at_kill(self, data=None):
        # pass
        
    # async def _at_hang(self, data=None):
        # pass
        
    # async def _at_day_end(self, data=None):
        # pass
        
    async def _at_night_start(self, data=None):
        if self.channel is None:
            return
        
        await self.game.generate_targets(self.channel)
        
        self.killer = random.choice(self.members)
        
        await channel.send("{} has been selected as tonight's killer")
        
    async def _at_night_end(self, data=None):
        if self.channel is None:
            return
        
        target = None
        vote_list = list(self.vote_results.values())
        
        if vote_list:
            target = max(set(vote_list), key=vote_list.count)
        
        if target and self.killer:
            await self.game.kill(target, self.killer, random.choice(self.kill_messages))
        
    # async def vote(self, author, id):
        # """
        # Receive vote from game
        # """
        
        # self.vote_results[author.id] = id