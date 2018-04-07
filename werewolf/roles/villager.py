import asyncio

from werewolf.role import Role

class Villager(Role):
     
    rand_choice = False  # Determines if it can be picked as a random role (False for unusually disruptive roles)
    category = [0]      # List of enrolled categories (listed above)
    allignment = 0      # 1: Town, 2: Werewolf, 3: Neutral
    channel_id = ""     # Empty for no private channel
    unique = False      # Only one of this role per game
    game_start_message="""
            Your role is **Villager**
            You win by lynching all evil in the town
            Lynch players during the day with `[p]ww lynch <ID>`
            """

    def __init__(self, game):
        self.game = game
        self.player = None
        self.blocked = False
        self.properties = {}  # Extra data for other roles (i.e. arsonist)
        
        self.action_list = [
            (self._at_game_start, 0),  # (Action, Priority)
            (self._at_day_start, 0),
            (self._at_voted, 0),
            (self._at_kill, 0),
            (self._at_hang, 0),
            (self._at_day_end, 0),
            (self._at_night_start, 0),
            (self._at_night_end, 0)
            ]
        
    # async def on_event(self, event, data):
        # """
        # See Game class for event guide
        # """
            
        # await self.action_list[event][0](data)
        
        
    # async def assign_player(self, player):
        # """
        # Give this role a player
        # Can be used after the game has started  (Cult, Mason, other role swap)
        # """

        # player.role = self
        # self.player = player
    
    async def _get_role(self, source=None):
        """
        Interaction for powerful access of role
        Unlikely to be able to deceive this
        """
        return "Villager"
    
    async def _see_role(self, source=None):
        """
        Interaction for investigative roles.
        More common to be able to deceive these roles
        """
        return "Villager"
    
    # async def _at_game_start(self, data=None):
        # pass
        
    # async def _at_day_start(self, data=None):
        # pass
        
    # async def _at_voted(self, target=None):
        # pass
        
    # async def _at_kill(self, target=None):
        # pass
        
    # async def _at_hang(self, target=None):
        # pass
        
    # async def _at_day_end(self):
        # pass
        
    # async def _at_night_start(self):
        # pass
        
    # async def _at_night_end(self):
        # pass
