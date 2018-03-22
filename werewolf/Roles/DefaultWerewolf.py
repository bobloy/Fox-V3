import asyncio

import discord

from datetime import datetime,timedelta

class Role:
    """
    Base Role class for werewolf game
    
    Category enrollment guide as follows (category property):
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
        category = [11, 16] Could be Werewolf Silencer
        
    
    Action guide as follows (on_event function):
        _at_night_start
        0. No Action
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
    
    rand_choice = False  # Determines if it can be picked as a random role (False for unusually disruptive roles)
    category = [0]      # List of enrolled categories (listed above)
    allignment = 0      # 1: Town, 2: Werewolf, 3: Neutral
    channel_id = ""     # Empty for no private channel
    unique = False      # Only one of this role per game
    action_list = [
            (self._at_game_start, 0),  # (Action, Priority)
            (self._at_day_start, 0),
            (self._at_voted, 0),
            (self._at_kill, 0),
            (self._at_hang, 0),
            (self._at_day_end, 0),
            (self._at_night_start, 0),
            (self._at_night_end, 0)
            ]
            
    def __init__(self, game):
        self.game = game
        self.player = None
        self.blocked = False
        self.properties = {}  # Extra data for other roles (i.e. arsonist)
        
    async def on_event(self, event, data):
        """
        See Game class for event guide
        """
            
        await action_list[event][0](data)
        
        
    async def assign_player(self, player):
        """
        Give this role a player
        Can be used after the game has started  (Cult, Mason, other role swap)
        """

        player.role = self
        self.player = player
    
    async def _get_role(self, source=None):
        """
        Interaction for powerful access of role
        Unlikely to be able to deceive this
        """
        return "Default"
    
    async def _see_role(self, source=None):
        """
        Interaction for investigative roles.
        More common to be able to deceive these roles
        """
        return "Role"
    
    async def _at_game_start(self, data=None):
        pass
        
    async def _at_day_start(self, data=None):
        pass
        
    async def _at_voted(self, target=None):
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