from ..role import Role


class Villager(Role):
    rand_choice = True  # Determines if it can be picked as a random role (False for unusually disruptive roles)
    category = [1]  # List of enrolled categories (listed above)
    alignment = 1  # 1: Town, 2: Werewolf, 3: Neutral
    channel_id = ""  # Empty for no private channel
    unique = False  # Only one of this role per game
    game_start_message = (
        "Your role is **Villager**\n"
        "You win by lynching all evil in the town\n"
        "Lynch players during the day with `[p]ww vote <ID>`"
    )

    def __init__(self, game):
        super().__init__(game)

    async def see_alignment(self, source=None):
        """
        Interaction for investigative roles attempting
        to see team (Village, Werewolf Other)
        """
        return "Village"

    async def get_role(self, source=None):
        """
        Interaction for powerful access of role
        Unlikely to be able to deceive this
        """
        return "Villager"

    async def see_role(self, source=None):
        """
        Interaction for investigative roles.
        More common to be able to deceive these roles
        """
        return "Villager"
