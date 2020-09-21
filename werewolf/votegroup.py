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

        # self.action_list = [
        #     (self._at_game_start, 1),  # (Action, Priority)
        #     (self._at_day_start, 0),
        #     (self._at_voted, 0),
        #     (self._at_kill, 1),
        #     (self._at_hang, 1),
        #     (self._at_day_end, 0),
        #     (self._at_night_start, 2),
        #     (self._at_night_end, 0),
        #     (self._at_visit, 0),
        # ]

    # async def on_event(self, event, data):
    #     """
    #     See Game class for event guide
    #     """
    #
    #     await self.action_list[event][0](data)

    @wolflistener("at_game_start")
    async def _at_game_start(self, data=None):
        await self.channel.send(" ".join(player.mention for player in self.players))

    @wolflistener("at_kill")
    async def _at_kill(self, data=None):
        if data["player"] in self.players:
            self.players.remove(data["player"])

    # Removed, only if they actually die
    # @wolflistener("at_hang")
    # async def _at_hang(self, data=None):
    #     if data["player"] in self.players:
    #         self.players.remove(data["player"])

    @wolflistener("at_night_start")
    async def _at_night_start(self, data=None):
        if self.channel is None:
            return

        await self.game.generate_targets(self.channel)

    @wolflistener("at_night_end")
    async def _at_night_end(self, data=None):
        if self.channel is None:
            return

        target = None
        vote_list = list(self.vote_results.values())

        if vote_list:
            target = max(set(vote_list), key=vote_list.count)

        if target:
            # Do what you voted on
            pass

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
            # ToDo: Trigger deletion of votegroup
            pass

    async def vote(self, target, author, target_id):
        """
        Receive vote from game
        """

        self.vote_results[author.id] = target_id
