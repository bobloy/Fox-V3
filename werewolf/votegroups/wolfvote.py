import random

from ..votegroup import VoteGroup


class WolfVote(VoteGroup):
    """
    Werewolf implementation of base VoteGroup class
    """

    alignment = 2  # 1: Town, 2: Werewolf, 3: Neutral
    channel_id = "werewolves"

    kill_messages = [
        "**{ID}** - {target} was mauled by wolves",
        "**{ID}** - {target} was found torn to shreds"]

    def __init__(self, game, channel):
        super().__init__(game, channel)
        # self.game = game
        # self.channel = channel
        # self.players = []
        # self.vote_results = {}
        # self.properties = {}  # Extra data for other options

        self.killer = None  # Added killer

        self.action_list = [
            (self._at_game_start, 1),  # (Action, Priority)
            (self._at_day_start, 0),
            (self._at_voted, 0),
            (self._at_kill, 1),
            (self._at_hang, 1),
            (self._at_day_end, 0),
            (self._at_night_start, 2),
            (self._at_night_end, 5),  # Kill priority
            (self._at_visit, 0)
        ]

        # async def on_event(self, event, data):

    #     """
    #     See Game class for event guide
    #     """
    #
    #     await action_list[event][0](data)
    #
    # async def _at_game_start(self, data=None):
    #     await self.channel.send(" ".join(player.mention for player in self.players))
    #
    # async def _at_day_start(self, data=None):
    #     pass
    #
    # async def _at_voted(self, data=None):
    #     pass
    #
    # async def _at_kill(self, data=None):
    #     if data["player"] in self.players:
    #         self.players.pop(data["player"])
    #
    # async def _at_hang(self, data=None):
    #     if data["player"] in self.players:
    #         self.players.pop(data["player"])
    #
    # async def _at_day_end(self, data=None):
    #     pass

    async def _at_night_start(self, data=None):
        if self.channel is None:
            return

        await self.game.generate_targets(self.channel)
        mention_list = " ".join(player.mention for player in self.players)
        if mention_list != "":
            await self.channel.send(mention_list)
        self.killer = random.choice(self.players)

        await self.channel.send("{} has been selected as tonight's killer".format(self.killer.member.display_name))

    async def _at_night_end(self, data=None):
        if self.channel is None:
            return

        target_id = None
        vote_list = list(self.vote_results.values())

        if vote_list:
            target_id = max(set(vote_list), key=vote_list.count)

        print("Target id: {}\nKiller: {}".format(target_id, self.killer.member.display_name))
        if target_id is not None and self.killer:
            await self.game.kill(target_id, self.killer, random.choice(self.kill_messages))
            await self.channel.send("**{} has left to complete the kill...**".format(self.killer.member.display_name))
        else:
            await self.channel.send("**No kill will be attempted tonight...**")

    # async def _at_visit(self, data=None):
    #     pass
    #
    # async def register_players(self, *players):
    #     """
    #     Extend players by passed list
    #     """
    #     self.players.extend(players)
    #
    # async def remove_player(self, player):
    #     """
    #     Remove a player from player list
    #     """
    #     if player.id in self.players:
    #         self.players.remove(player)

    async def vote(self, target, author, target_id):
        """
        Receive vote from game
        """

        self.vote_results[author.id] = target_id

        await self.channel.send("{} has voted to kill {}".format(author.mention, target.member.display_name))
