from .villager import Villager
from .seer import Seer

from .vanillawerewolf import VanillaWerewolf

from .shifter import Shifter

# Don't sort these imports. They are unstably in order
# TODO: Replace with unique IDs for roles in the future

__all__ = ["Seer", "Shifter", "VanillaWerewolf", "Villager"]
