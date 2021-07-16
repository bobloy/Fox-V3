import inspect
import logging

from werewolf.listener import WolfListener, wolflistener

log = logging.getLogger("red.fox_v3.werewolf.role")


class Role(WolfListener):
    """
    Base Role class for werewolf game

    Category enrollment guide as follows (category property):
        Town:
        1: Random, 2: Investigative, 3: Protective, 4: Government,
        5: Killing, 6: Power (Special night action)

        Werewolf:
        11: Random, 12: Deception, 15: Killing, 16: Support

        Neutral:
        21: Benign, 22: Evil, 23: Killing


        Example category:
        category = [1, 5, 6] Could be Veteran
        category = [1, 5] Could be Bodyguard
        category = [11, 16] Could be Werewolf Silencer
        category = [22] Could be Blob (non-killing)
        category = [22, 23] Could be Serial-Killer


    Action priority guide as follows (on_event function):
        _at_night_start
        0. No Action
        1. Detain actions (Jailer/Kidnapper)
        2. Group discussions and choose targets

        _at_night_end
        0. No Action
        1. Self actions (Veteran)
        2. Target switching and role blocks (bus driver, witch, escort)
        3. Protection / Preempt actions (bodyguard/framer)
        4. Non-disruptive actions (seer/silencer)
        5. Disruptive actions (Killing)
        6. Role altering actions (Cult / Mason / Shifter)
    """

    # Determines if it can be picked as a random role (False for unusually disruptive roles)
    rand_choice = False  # TODO: Rework random with categories
    town_balance = 0  # Guess at power level and it's balance on the town
    category = [0]  # List of enrolled categories (listed above)
    alignment = 0  # 1: Town, 2: Werewolf, 3: Neutral
    channel_name = ""  # Empty for no private channel
    unique = False  # Only one of this role per game
    game_start_message = (
        "Your role is **Default**\n"
        "You win by testing the game\n"
        "Lynch players during the day with `[p]ww vote <ID>`"
    )
    description = (
        "This is the basic role\n"
        "All roles are based on this Class\n"
        "Has no special significance"
    )
    icon_url = None  # Adding a URL here will enable a thumbnail of the role

    def __init__(self, game):
        super().__init__(game)
        self.game = game
        self.player = None
        self.blocked = False
        self.properties = {}  # Extra data for other roles (i.e. arsonist)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f"{self.__class__.__name__}({self.player.__repr__()})"

    async def assign_player(self, player):
        """
        Give this role a player
        Can be used after the game has started  (Cult, Mason, other role swap)
        """

        player.role = self
        self.player = player

        log.debug(f"Assigned {self} to {player}")

    async def get_alignment(self, source=None):  # TODO: Rework to be "strength" tiers
        """
        Interaction for powerful access of alignment
        (Village, Werewolf, Other)
        Unlikely to be able to deceive this
        """
        return self.alignment

    async def see_alignment(self, source=None):
        """
        Interaction for investigative roles attempting
        to see alignment (Village, Werewolf, Other)
        """
        return "Other"

    async def get_role(self, source=None):
        """
        Interaction for powerful access of role
        Unlikely to be able to deceive this
        """
        return "Role"

    async def see_role(self, source=None):
        """
        Interaction for investigative roles.
        More common to be able to deceive this action
        """
        return "Default"

    @wolflistener("at_game_start", priority=2)
    async def _at_game_start(self):
        if self.channel_name:
            await self.game.register_channel(self.channel_name, self)

        try:
            await self.player.send_dm(self.game_start_message)  # Maybe embeds eventually
        except AttributeError as e:
            log.exception(self.__repr__())
            raise e

    async def kill(self, source):
        """
        Called when someone is trying to kill you!
        Can you do anything about it?
        self.player.alive is now set to False, set to True to stay alive
        """
        pass

    async def visit(self, source):
        """
        Called whenever a night action targets you
        Source is the player who visited you
        """
        pass

    async def choose(self, ctx, data):
        """Handle night actions"""
        pass
