"""
Role Constants

    Role Alignment guide as follows:
        Town: 1
        Werewolf: 2
        Neutral: 3

        Additional alignments may be added when warring factions are added
        (Rival werewolves, cultists, vampires)

    Role Category enrollment guide as follows (See Role.category):
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
"""


ALIGNMENT_TOWN = 1
ALIGNMENT_WEREWOLF = 2
ALIGNMENT_NEUTRAL = 3
ALIGNMENT_MAP = {"Town": 1, "Werewolf": 2, "Neutral": 3}

# 0-9: Town Role Categories
# 10-19: Werewolf Role Categories
# 20-29: Neutral Role Categories
CATEGORY_TOWN_RANDOM = 1
CATEGORY_TOWN_INVESTIGATIVE = 2
CATEGORY_TOWN_PROTECTIVE = 3
CATEGORY_TOWN_GOVERNMENT = 4
CATEGORY_TOWN_KILLING = 5
CATEGORY_TOWN_POWER = 6

CATEGORY_WW_RANDOM = 11
CATEGORY_WW_DECEPTION = 12
CATEGORY_WW_KILLING = 15
CATEGORY_WW_SUPPORT = 16

CATEGORY_NEUTRAL_BENIGN = 21
CATEGORY_NEUTRAL_EVIL = 22
CATEGORY_NEUTRAL_KILLING = 23

ROLE_CATEGORY_DESCRIPTIONS = {
    CATEGORY_TOWN_RANDOM: "Random",
    CATEGORY_TOWN_INVESTIGATIVE: "Investigative",
    CATEGORY_TOWN_PROTECTIVE: "Protective",
    CATEGORY_TOWN_GOVERNMENT: "Government",
    CATEGORY_TOWN_KILLING: "Killing",
    CATEGORY_TOWN_POWER: "Power (Special night action)",
    CATEGORY_WW_RANDOM: "Random",
    CATEGORY_WW_DECEPTION: "Deception",
    CATEGORY_WW_KILLING: "Killing",
    CATEGORY_WW_SUPPORT: "Support",
    CATEGORY_NEUTRAL_BENIGN: "Benign",
    CATEGORY_NEUTRAL_EVIL: "Evil",
    CATEGORY_NEUTRAL_KILLING: "Killing",
}


"""
Listener Actions Priority Guide

    Action priority guide as follows (see listeners.py for wolflistener):
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
