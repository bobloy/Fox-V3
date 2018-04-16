import asyncio

from werewolf.role import Role

class Seer(Role):
     
    rand_choice = False  # Determines if it can be picked as a random role (False for unusually disruptive roles)
    category = [1,2]      # List of enrolled categories (listed above)
    alignment = 1      # 1: Town, 2: Werewolf, 3: Neutral
    channel_id = ""     # Empty for no private channel
    unique = False      # Only one of this role per game
    game_start_message=(
            "Your role is **Seer**\n"
            "You win by lynching all evil in the town\n"
            "Lynch players during the day with `[p]ww vote <ID>`\n"
            "Check for werewolves at night with `[p]ww choose <ID>`"
            )

    def __init__(self, game):
        super().__init__()
        # self.game = game
        # self.player = None
        # self.blocked = False
        # self.properties = {}  # Extra data for other roles (i.e. arsonist)
        self.see_target = None
        self.action_list = [
            (self._at_game_start, 1),  # (Action, Priority)
            (self._at_day_start, 0),
            (self._at_voted, 0),
            (self._at_kill, 0),
            (self._at_hang, 0),
            (self._at_day_end, 0),
            (self._at_night_start, 2),
            (self._at_night_end, 4)
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
        
    # async def get_alignment(self, source=None):
        # """
        # Interaction for power access of team (Village, Werewolf, Other)
        # Unlikely to be able to deceive this
        # """
        # return self.alignment
        
    async def see_alignment(self, source=None):
        """
        Interaction for investigative roles attempting
        to see team (Village, Werewolf Other)
        """
        return "Village"

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
        
    async def _at_night_start(self):
        await self.game.generate_targets(self.player.member)
        await self.player.send_dm("{}\n**Pick a target to see tonight**\n")
        
        
    async def _at_night_end(self):
        target = await self.game.visit(self.see_target)
        
        alignment = None
        if target:
            alignment = await target.see_alignment(self.player)
        
        if alignment == "Werewolf":
            out = "Your insight reveals this player to be a **Werewolf!**"
        else:
            out = "You fail to find anything suspicious about this player..."

        await self.player.send_dm(out)

    # async def _at_visit(self, data=None):
        # pass
        
    # async def kill(self, source):
        # """
        # Called when someone is trying to kill you!
        # Can you do anything about it?
        # self.alive is now set to False, set to True to stay alive
        # """
        # pass
        
    # async def visit(self, source):
        # """
        # Called whenever a night action targets you
        # Source is the player who visited you
        # """
        # pass
        
    async def choose(self, ctx, data):
        """Handle night actions"""
        id = int(data)
        try:
            target = self.game.players[id]
        except IndexError:
            target = None
        
        if target is None:
            await ctx.send("Not a valid ID")
            return
        
        self.see_target = id
        await ctx.send("**You will attempt to see the role of {} tonight...**".format(target.member.display_name))
