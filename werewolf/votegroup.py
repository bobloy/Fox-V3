import logging

from werewolf.listener import WolfListener, wolflistener

log = logging.getLogger("red.fox_v3.werewolf.votegroup")


class VoteGroup(WolfListener):
    """
    Base VoteGroup class for werewolf game
    Handles secret channels and group decisions
    """

    alignment = 0  # 1: Town, 2: Werewolf, 3: Neutral
    channel_id = ""

    def __init__(self, game, channel):
        super().__init__(game)
        self.game = game
        self.channel = channel
        self.players = []
        self.vote_results = {}
        self.properties = {}  # Extra data for other options

    def __repr__(self):
        return f"{self.__class__.__name__}({self.channel},{self.players})"

    @wolflistener("at_game_start", priority=1)
    async def _at_game_start(self):
        await self.channel.send(" ".join(player.mention for player in self.players))

    @wolflistener("at_kill", priority=1)
    async def _at_kill(self, player):
        if player in self.players:
            self.players.remove(player)

    @wolflistener("at_hang", priority=1)
    async def _at_hang(self, player):
        if player in self.players:
            self.players.remove(player)

    @wolflistener("at_night_start", priority=2)
    async def _at_night_start(self):
        if self.channel is None:
            return

        self.vote_results = {}

        await self.game.generate_targets(self.channel)

    @wolflistener("at_night_end", priority=5)
    async def _at_night_end(self):
        if self.channel is None:
            return

        target = None
        vote_list = list(self.vote_results.values())

        if vote_list:
            target = max(set(vote_list), key=vote_list.count)

        if target:
            # Do what the votegroup votes on
            raise NotImplementedError

    async def register_players(self, *players):
        """
        Extend players by passed list
        """
        self.players.extend(players)

    async def remove_player(self, player):
        """
        Remove a player from player list
        """
        if player.id in self.players:
            self.players.remove(player)

        if not self.players:
            # TODO: Confirm deletion
            pass

    async def vote(self, target, author, target_id):
        """
        Receive vote from game
        """

        self.vote_results[author.id] = target_id
