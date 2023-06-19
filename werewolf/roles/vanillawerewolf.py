import logging

from werewolf.constants import (
    ALIGNMENT_WEREWOLF,
    CATEGORY_WW_KILLING,
    CATEGORY_WW_RANDOM,
)
from werewolf.listener import wolflistener
from werewolf.role import Role
from werewolf.votegroups.wolfvote import WolfVote

log = logging.getLogger("red.fox_v3.werewolf.role.vanillawerewolf")


class VanillaWerewolf(Role):
    rand_choice = True
    town_balance = -6
    category = [CATEGORY_WW_RANDOM, CATEGORY_WW_KILLING]
    alignment = ALIGNMENT_WEREWOLF  # 1: Town, 2: Werewolf, 3: Neutral
    channel_name = "werewolves"
    unique = False
    game_start_message = (
        "Your role is **Werewolf**\n"
        "You win by killing everyone else in the village\n"
        "Lynch players during the day with `[p]ww vote <ID>`\n"
        "Vote to kill players at night with `[p]ww vote <ID>`"
    )

    async def see_alignment(self, source=None):
        """
        Interaction for investigative roles attempting
        to see team (Village, Werewolf Other)
        """
        return ALIGNMENT_WEREWOLF

    async def get_role(self, source=None):
        """
        Interaction for powerful access of role
        Unlikely to be able to deceive this
        """
        return "VanillaWerewolf"

    async def see_role(self, source=None):
        """
        Interaction for investigative roles.
        More common to be able to deceive these roles
        """
        return "Werewolf"

    @wolflistener("at_game_start", priority=2)
    async def _at_game_start(self):
        if self.channel_name:
            log.debug("Wolf has channel_name: " + self.channel_name)
            await self.game.register_channel(
                self.channel_name, self, WolfVote
            )  # Add VoteGroup WolfVote

        await self.player.send_dm(self.game_start_message)

    async def choose(self, ctx, data):
        """Handle night actions"""
        await self.player.member.send("Use `[p]ww vote` in your werewolf channel")
