from ..role import Role

from ..votegroups.wolfvote import WolfVote


class VanillaWerewolf(Role):
    rand_choice = True
    category = [11, 15]
    alignment = 2  # 1: Town, 2: Werewolf, 3: Neutral
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
            (self._at_game_start, 1),  # (Action, Priority)
            (self._at_day_start, 0),
            (self._at_voted, 0),
            (self._at_kill, 0),
            (self._at_hang, 0),
            (self._at_day_end, 0),
            (self._at_night_start, 0),
            (self._at_night_end, 0),
            (self._at_visit, 0)
        ]

    async def see_alignment(self, source=None):
        """
        Interaction for investigative roles attempting
        to see team (Village, Werewolf Other)
        """
        return "Werewolf"

    async def get_role(self, source=None):
        """
        Interaction for powerful access of role
        Unlikely to be able to deceive this
        """
        return "Werewolf"

    async def see_role(self, source=None):
        """
        Interaction for investigative roles.
        More common to be able to deceive these roles
        """
        return "Werewolf"

    async def _at_game_start(self, data=None):
        if self.channel_id:
            print("Wolf has channel_id: " + self.channel_id)
            await self.game.register_channel(self.channel_id, self, WolfVote)  # Add VoteGroup WolfVote

        await self.player.send_dm(self.game_start_message)

    async def choose(self, ctx, data):
        """Handle night actions"""
        await self.player.member.send("Use `[p]ww vote` in your werewolf channel")
