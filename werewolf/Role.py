import asyncio

import discord

from datetime import datetime,timedelta

class Role:
    """
    Base Role class for werewolf game
    
    Category enrollment guide as follows:
    
    Town:
    1: Random, 2: Investigative, 3: Protective, 4: Government,
    5: Killing, 6: Power (Special night action)
    
    Werewolf:
    11: Random, 12: Deception, 15: Killing, 16: Support
    
    Neutral:
    21: Benign, 22: Evil, 23: Killing
    
    
    Example category:
    category = [1, 5, 6] Could be Veteran
    category = [1, 5] Could be Bodyguard
    """
    
    random_choice = True  # Determines if it can be picked as a random
    category = [0]  # List of enrolled categories
    priority = 0  # 0 is "No Action"
    allignment = 0  # 1: Town, 2: Werewolf, 3: Neutral
    private_channel_id = ""  # No private channel
    unique = False  # Only one of this role per game
    
    def __init__(self):
        self.player = None
        self.blocked = False
        
    async def on_event(self, event, data):
        """
        Action guide as follows:
        
        _at_night_start
        1. Detain actions (Jailer/Kidnapper)
        2. Group discussions and Pick targets
        
        _at_night_end
        1. Self actions (Veteran)
        2. Target switching and role blocks (bus driver, witch, escort)
        3. Protection / Preempt actions (bodyguard/framer)
        4. Non-disruptive actions (seer/silencer)
        5. Disruptive actions (werewolf kill)
        6. Role altering actions (Cult / Mason)
        """
        
        """
        See Game class for event guide
        """
        action_list = [
            self._at_game_start(data),
            self._at_day_start(data),
            self._at_vote(data),
            self._at_kill(data),
            self._at_hang(data),
            self._at_day_end(data),
            self._at_night_start(data),
            self._at_night_end(data)
            ]
            
        await action_list[event]
        
        
    async def assign_player(self, player):
        """
        Give this role a player
        """
        self.player = player
    
    async def _at_game_start(self, data=None):
        pass
        
    async def _at_day_start(self, data=None):
        pass
        
    async def _at_vote(self, target=None):
        pass
        
    async def _at_kill(self, target=None):
        pass
        
    async def _at_hang(self, target=None):
        pass
        
    async def _at_day_end(self):
        pass
        
    async def _at_night_start(self):
        pass
        
    async def _at_night_end(self):
        pass