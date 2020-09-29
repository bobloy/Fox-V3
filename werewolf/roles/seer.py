import logging

from werewolf.constants import (
    ALIGNMENT_TOWN,
    ALIGNMENT_WEREWOLF,
    CATEGORY_TOWN_INVESTIGATIVE,
    CATEGORY_TOWN_RANDOM,
)
from werewolf.listener import wolflistener
from werewolf.night_powers import pick_target
from werewolf.role import Role

log = logging.getLogger("red.fox_v3.werewolf.role.seer")


class Seer(Role):
    rand_choice = True
    town_balance = 4
    category = [
        CATEGORY_TOWN_RANDOM,
        CATEGORY_TOWN_INVESTIGATIVE,
    ]  # List of enrolled categories (listed above)
    alignment = ALIGNMENT_TOWN  # 1: Town, 2: Werewolf, 3: Neutral
    channel_id = ""  # Empty for no private channel
    unique = False  # Only one of this role per game
    game_start_message = (
        "Your role is **Seer**\n"
        "You win by lynching all evil in the town\n"
        "Lynch players during the day with `[p]ww vote <ID>`\n"
        "Check for werewolves at night with `[p]ww choose <ID>`"
    )
    description = (
        "A mystic in search of answers in a chaotic town.\n"
        "Calls upon the cosmos to discern those of Lycan blood"
    )

    def __init__(self, game):
        super().__init__(game)
        # self.game = game
        # self.player = None
        # self.blocked = False
        # self.properties = {}  # Extra data for other roles (i.e. arsonist)
        self.see_target = None
        # self.action_list = [
        #     (self._at_game_start, 1),  # (Action, Priority)
        #     (self._at_day_start, 0),
        #     (self._at_voted, 0),
        #     (self._at_kill, 0),
        #     (self._at_hang, 0),
        #     (self._at_day_end, 0),
        #     (self._at_night_start, 2),
        #     (self._at_night_end, 4),
        #     (self._at_visit, 0),
        # ]

    async def see_alignment(self, source=None):
        """
        Interaction for investigative roles attempting
        to see team (Village, Werewolf, Other)
        """
        return ALIGNMENT_TOWN

    async def get_role(self, source=None):
        """
        Interaction for powerful access of role
        Unlikely to be able to deceive this
        """
        return "Seer"

    async def see_role(self, source=None):
        """
        Interaction for investigative roles.
        More common to be able to deceive these roles
        """
        return "Seer"

    @wolflistener("at_night_start", priority=2)
    async def _at_night_start(self):
        if not self.player.alive:
            return
        self.see_target = None
        await self.game.generate_targets(self.player.member)
        await self.player.send_dm("**Pick a target to see tonight**")

    @wolflistener("at_night_end", priority=4)
    async def _at_night_end(self):
        if self.see_target is None:
            if self.player.alive:
                await self.player.send_dm("You will not use your powers tonight...")
            return
        target = await self.game.visit(self.see_target, self.player)

        alignment = None
        if target:
            alignment = await target.role.see_alignment(self.player)

        if alignment == ALIGNMENT_WEREWOLF:
            out = "Your insight reveals this player to be a **Werewolf!**"
        else:  # Don't reveal neutrals
            out = "You fail to find anything suspicious about this player..."

        await self.player.send_dm(out)

    async def choose(self, ctx, data):
        """Handle night actions"""
        await super().choose(ctx, data)

        self.see_target, target = await pick_target(self, ctx, data)
        await ctx.send(
            f"**You will attempt to see the role of {target.member.display_name} tonight...**"
        )
