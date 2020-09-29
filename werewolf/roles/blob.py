import logging
import random

from werewolf.constants import ALIGNMENT_NEUTRAL, CATEGORY_NEUTRAL_EVIL
from werewolf.listener import wolflistener
from werewolf.player import Player
from werewolf.role import Role

log = logging.getLogger("red.fox_v3.werewolf.role.blob")


class TheBlob(Role):
    rand_choice = True
    category = [CATEGORY_NEUTRAL_EVIL]  # List of enrolled categories
    alignment = ALIGNMENT_NEUTRAL  # 1: Town, 2: Werewolf, 3: Neutral
    channel_id = ""  # Empty for no private channel
    unique = True  # Only one of this role per game
    game_start_message = (
        "Your role is **The Blob**\n"
        "You win by absorbing everyone town\n"
        "Lynch players during the day with `[p]ww vote <ID>`\n"
        "Each night you will absorb an adjacent player"
    )
    description = (
        "A mysterious green blob of jelly, slowly growing in size.\n"
        "The Blob fears no evil, must be dealt with in town"
    )

    def __init__(self, game):
        super().__init__(game)

        self.blob_target = None

    async def see_alignment(self, source=None):
        """
        Interaction for investigative roles attempting
        to see team (Village, Werewolf, Other)
        """
        return ALIGNMENT_NEUTRAL

    async def get_role(self, source=None):
        """
        Interaction for powerful access of role
        Unlikely to be able to deceive this
        """
        return "The Blob"

    async def see_role(self, source=None):
        """
        Interaction for investigative roles.
        More common to be able to deceive these roles
        """
        return "The Blob"

    async def kill(self, source):
        """
        Called when someone is trying to kill you!
        Can you do anything about it?
        self.player.alive is now set to False, set to True to stay alive
        """

        # Blob cannot simply be killed
        self.player.alive = True

    @wolflistener("at_night_start", priority=2)
    async def _at_night_start(self):
        if not self.player.alive:
            return

        self.blob_target = None
        idx = self.player.id
        left_or_right = random.choice((-1, 1))
        while self.blob_target is None:
            idx += left_or_right
            if idx >= len(self.game.players):
                idx = 0

            player = self.game.players[idx]

            # you went full circle, everyone is a blob or something else is wrong
            if player == self.player:
                break

            if player.role.properties.get("been_blobbed", False):
                self.blob_target = player

        if self.blob_target is not None:
            await self.player.send_dm(f"**You will attempt to absorb {self.blob_target} tonight**")
        else:
            await self.player.send_dm(f"**No player will be absorbed tonight**")

    @wolflistener("at_night_end", priority=4)
    async def _at_night_end(self):
        if self.blob_target is None or not self.player.alive:
            return

        target: "Player" = await self.game.visit(self.blob_target, self.player)

        if target is not None:
            target.role.properties["been_blobbed"] = True
            self.game.night_results.append("The Blob grows...")
