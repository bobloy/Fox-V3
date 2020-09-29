import logging
import random

import discord

from werewolf.listener import wolflistener
from werewolf.votegroup import VoteGroup

log = logging.getLogger("red.fox_v3.werewolf.votegroup.wolfvote")


class WolfVote(VoteGroup):
    """
    Werewolf implementation of base VoteGroup class
    """

    alignment = 2  # 1: Town, 2: Werewolf, 3: Neutral
    channel_id = "werewolves"

    kill_messages = [
        "**{ID}** - {target} was mauled by wolves",
        "**{ID}** - {target} was found torn to shreds",
    ]

    def __init__(self, game, channel):
        super().__init__(game, channel)

        self.killer = None  # Added killer

    @wolflistener("at_night_start", priority=2)
    async def _at_night_start(self):
        await super()._at_night_start()

        mention_list = " ".join(player.mention for player in self.players)
        if mention_list != "":
            await self.channel.send(mention_list)
        self.killer = random.choice(self.players)

        await self.channel.send(
            f"{self.killer.member.display_name} has been selected as tonight's killer"
        )

    @wolflistener("at_night_end", priority=5)
    async def _at_night_end(self):
        if self.channel is None:
            return

        target_id = None
        vote_list = list(self.vote_results.values())

        if vote_list:
            target_id = max(set(vote_list), key=vote_list.count)

        log.debug(f"Target id: {target_id}\nKiller: {self.killer.member.display_name}")
        if target_id is not None and self.killer:
            await self.game.kill(target_id, self.killer, random.choice(self.kill_messages))
            await self.channel.send(
                "*{} has left to complete the kill...*".format(self.killer.member.display_name)
            )
        else:
            await self.channel.send("*No kill will be attempted tonight...*")

    async def vote(self, target, author, target_id):
        """
        Receive vote from game
        """

        await super().vote(target, author, target_id)

        await self.channel.send(
            "{} has voted to kill {}".format(author.mention, target.member.display_name),
            allowed_mentions=discord.AllowedMentions(everyone=False, users=[author]),
        )
