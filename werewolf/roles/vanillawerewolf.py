import asyncio

from werewolf.role import Role

from werewolf.votegroups.wolfvote import WolfVote


class VanillaWerewolf(Role):
     
    rand_choice = True
    category = [11, 15]
    allignment = 2     # 1: Town, 2: Werewolf, 3: Neutral
    channel_id = "werewolves"
    unique = False
    game_start_message = (
        "Your role is **Werewolf**\n"
        "You win by killing everyone else in the village\n"
        "Lynch players during the day with `[p]ww vote <ID>`\n"
        "Vote to kill players at night with `[p]ww vote <ID>`"
        )
            
    
 
    def __init__(self, game):
        super().__init__(game)
        
        self.action_list = [
            (self._at_game_start, 0),  # (Action, Priority)
            (self._at_day_start, 0),
            (self._at_voted, 0),
            (self._at_kill, 0),
            (self._at_hang, 0),
            (self._at_day_end, 0),
            (self._at_night_start, 2),  # Get vote priority
            (self._at_night_end, 0),
            (self._at_visit, 0)
            ]
        self.killer = None  # Added killer
    
    # async def on_event(self, event, data):
        # """
        # See Game class for event guide
        # """
            
        # await self.action_list[event][0](data)
        
    # async def assign_player(self, player):
        # """
        # Give this role a player
        # Can be used after the game has started  (Cult, Mason, role swap)
        # """

        # player.role = self
        # self.player = player
        
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
        if self.channel_id:
            await self.game.register_channel(self.channel_id, self, WolfVote)  # Add VoteGroup WolfVote
        
        await self.player.send_dm(self.game_start_message)
        

    # async def _at_day_start(self, data=None):
        # super()._at_day_start(data)
        
    # async def _at_voted(self, data=None):
        # super()._at_voted(data)
        
    # async def _at_kill(self, data=None):
        # super()._at_kill(data)
        
    # async def _at_hang(self, data=None):
        # super()._at_hang(data)
        
    # async def _at_day_end(self, data=None):
        # super()._at_day_end(data)
        
    # async def _at_night_start(self, data=None):
        # super()._at_night_start(data)
        
    # async def _at_night_end(self, data=None):
        # super()._at_night_end(data)
    
    # async def _at_visit(self, data=None):
        # pass
    
    # async def visit(self, source):
        # """
        # Called whenever a night action targets you
        # Source is the player who visited you
        # """
        # pass

    async def choose(self, ctx, data):
        """Handle night actions"""
        await self.player.member.send("Use `[p]ww vote` in your werewolf channel")
