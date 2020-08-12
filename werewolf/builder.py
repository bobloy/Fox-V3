import bisect
from collections import defaultdict
from random import choice

import discord


# Import all roles here
from redbot.core import commands

from .roles.seer import Seer
from .roles.vanillawerewolf import VanillaWerewolf
from .roles.villager import Villager
from redbot.core.utils.menus import menu, prev_page, next_page, close_menu

# All roles in this list for iterating

ROLE_LIST = sorted([Villager, Seer, VanillaWerewolf], key=lambda x: x.alignment)

ALIGNMENT_COLORS = [0x008000, 0xff0000, 0xc0c0c0]
TOWN_ROLES = [(idx, role) for idx, role in enumerate(ROLE_LIST) if role.alignment == 1]
WW_ROLES = [(idx, role) for idx, role in enumerate(ROLE_LIST) if role.alignment == 2]
OTHER_ROLES = [(idx, role) for idx, role in enumerate(ROLE_LIST) if role.alignment not in [0, 1]]

ROLE_PAGES = []
PAGE_GROUPS = [0]

ROLE_CATEGORIES = {
    1: "Random", 2: "Investigative", 3: "Protective", 4: "Government",
    5: "Killing", 6: "Power (Special night action)",
    11: "Random", 12: "Deception", 15: "Killing", 16: "Support",
    21: "Benign", 22: "Evil", 23: "Killing"}

CATEGORY_COUNT = []


def role_embed(idx, role, color):
    embed = discord.Embed(title="**{}** - {}".format(idx, str(role.__name__)), description=role.game_start_message,
                          color=color)
    embed.add_field(name='Alignment', value=['Town', 'Werewolf', 'Neutral'][role.alignment - 1], inline=True)
    embed.add_field(name='Multiples Allowed', value=str(not role.unique), inline=True)
    embed.add_field(name='Role Type', value=", ".join(ROLE_CATEGORIES[x] for x in role.category), inline=True)
    embed.add_field(name='Random Option', value=str(role.rand_choice), inline=True)

    return embed


def setup():
    # Roles
    last_alignment = ROLE_LIST[0].alignment
    for idx, role in enumerate(ROLE_LIST):
        if role.alignment != last_alignment and len(ROLE_PAGES) - 1 not in PAGE_GROUPS:
            PAGE_GROUPS.append(len(ROLE_PAGES) - 1)
            last_alignment = role.alignment

        ROLE_PAGES.append(role_embed(idx, role, ALIGNMENT_COLORS[role.alignment - 1]))

    # Random Town Roles
    if len(ROLE_PAGES) - 1 not in PAGE_GROUPS:
        PAGE_GROUPS.append(len(ROLE_PAGES) - 1)
    for k, v in ROLE_CATEGORIES.items():
        if 0 < k <= 6:
            ROLE_PAGES.append(discord.Embed(title="RANDOM:Town Role", description="Town {}".format(v), color=0x008000))
            CATEGORY_COUNT.append(k)

    # Random WW Roles
    if len(ROLE_PAGES) - 1 not in PAGE_GROUPS:
        PAGE_GROUPS.append(len(ROLE_PAGES) - 1)
    for k, v in ROLE_CATEGORIES.items():
        if 10 < k <= 16:
            ROLE_PAGES.append(
                discord.Embed(title="RANDOM:Werewolf Role", description="Werewolf {}".format(v), color=0xff0000))
            CATEGORY_COUNT.append(k)
    # Random Neutral Roles
    if len(ROLE_PAGES) - 1 not in PAGE_GROUPS:
        PAGE_GROUPS.append(len(ROLE_PAGES) - 1)
    for k, v in ROLE_CATEGORIES.items():
        if 20 < k <= 26:
            ROLE_PAGES.append(
                discord.Embed(title="RANDOM:Neutral Role", description="Neutral {}".format(v), color=0xc0c0c0))
            CATEGORY_COUNT.append(k)


"""
Example code:
0 = Villager
1 = VanillaWerewolf
T1 - T6 = Random Town (1: Random, 2: Investigative, 3: Protective, 4: Government,
                       5: Killing, 6: Power (Special night action))
W1, W2, W5, W6 = Random Werewolf
N1 = Benign Neutral

0001-1112T11W112N2
0,0,0,1,11,12,E1,R1,R1,R1,R2,P2

pre-letter = exact role position
double digit position preempted by `-`
"""


async def parse_code(code, game):
    """Do the magic described above"""
    decode = []

    digits = 1
    built = ""
    category = ""
    for c in code:
        if len(built) < digits:
            built += c

        if built == "T" or built == "W" or built == "N":
            # Random Towns
            category = built
            built = ""
            digits = 1
            continue
        elif built == "-":
            built = ""
            digits += 1
            continue

        try:
            idx = int(built)
        except ValueError:
            raise ValueError("Invalid code")

        if category == "":  # no randomness yet
            decode.append(ROLE_LIST[idx](game))
        else:
            options = []
            if category == "T":
                options = [role for role in ROLE_LIST if idx in role.category]
            elif category == "W":
                options = [role for role in ROLE_LIST if 10 + idx in role.category]
            elif category == "N":
                options = [role for role in ROLE_LIST if 20 + idx in role.category]
                pass

            if not options:
                raise IndexError("No Match Found")

            decode.append(choice(options)(game))

        built = ""

    return decode


async def encode(roles, rand_roles):
    """Convert role list to code"""
    out_code = ""

    digit_sort = sorted(role for role in roles if role < 10)
    for role in digit_sort:
        out_code += str(role)

    digit_sort = sorted(role for role in roles if 10 <= role < 100)
    if digit_sort:
        out_code += "-"
        for role in digit_sort:
            out_code += str(role)
    # That covers up to 99 roles, add another set here if we breach 100

    if rand_roles:
        # town sort
        digit_sort = sorted(role for role in rand_roles if role <= 6)
        if digit_sort:
            out_code += "T"
            for role in digit_sort:
                out_code += str(role)

        # werewolf sort
        digit_sort = sorted(role for role in rand_roles if 10 < role <= 20)
        if digit_sort:
            out_code += "W"
            for role in digit_sort:
                out_code += str(role)

        # neutral sort
        digit_sort = sorted(role for role in rand_roles if 20 < role <= 30)
        if digit_sort:
            out_code += "N"
            for role in digit_sort:
                out_code += str(role)

    return out_code


async def next_group(ctx: commands.Context, pages: list,
                     controls: dict, message: discord.Message, page: int,
                     timeout: float, emoji: str):
    perms = message.channel.permissions_for(ctx.guild.me)
    if perms.manage_messages:  # Can manage messages, so remove react
        try:
            await message.remove_reaction(emoji, ctx.author)
        except discord.NotFound:
            pass
    page = bisect.bisect_right(PAGE_GROUPS, page)

    if page == len(PAGE_GROUPS):
        page = PAGE_GROUPS[0]
    else:
        page = PAGE_GROUPS[page]

    return await menu(ctx, pages, controls, message=message,
                      page=page, timeout=timeout)


async def prev_group(ctx: commands.Context, pages: list,
                     controls: dict, message: discord.Message, page: int,
                     timeout: float, emoji: str):
    perms = message.channel.permissions_for(ctx.guild.me)
    if perms.manage_messages:  # Can manage messages, so remove react
        try:
            await message.remove_reaction(emoji, ctx.author)
        except discord.NotFound:
            pass
    page = PAGE_GROUPS[bisect.bisect_left(PAGE_GROUPS, page) - 1]

    return await menu(ctx, pages, controls, message=message,
                      page=page, timeout=timeout)


def role_from_alignment(alignment):
    return [role_embed(idx, role, ALIGNMENT_COLORS[role.alignment - 1])
            for idx, role in enumerate(ROLE_LIST) if alignment == role.alignment]


def role_from_category(category):
    return [role_embed(idx, role, ALIGNMENT_COLORS[role.alignment - 1])
            for idx, role in enumerate(ROLE_LIST) if category in role.category]


def role_from_id(idx):
    try:
        role = ROLE_LIST[idx]
    except IndexError:
        return None

    return role_embed(idx, role, ALIGNMENT_COLORS[role.alignment - 1])


def role_from_name(name: str):
    return [role_embed(idx, role, ALIGNMENT_COLORS[role.alignment - 1])
            for idx, role in enumerate(ROLE_LIST) if name in role.__name__]


def say_role_list(code_list, rand_roles):
    roles = [ROLE_LIST[idx] for idx in code_list]
    embed = discord.Embed(title="Currently selected roles")
    role_dict = defaultdict(int)
    for role in roles:
        role_dict[str(role.__name__)] += 1

    for role in rand_roles:
        if 0 < role <= 6:
            role_dict["Town {}".format(ROLE_CATEGORIES[role])] += 1
        if 10 < role <= 16:
            role_dict["Werewolf {}".format(ROLE_CATEGORIES[role])] += 1
        if 20 < role <= 26:
            role_dict["Neutral {}".format(ROLE_CATEGORIES[role])] += 1

    for k, v in role_dict.items():
        embed.add_field(name=k, value="Count: {}".format(v), inline=True)

    return embed


class GameBuilder:

    def __init__(self):
        self.code = []
        self.rand_roles = []
        setup()

    async def build_game(self, ctx: commands.Context):
        new_controls = {
            '⏪': prev_group,
            "⬅": prev_page,
            '☑': self.select_page,
            "➡": next_page,
            '⏩': next_group,
            '📇': self.list_roles,
            "❌": close_menu
        }

        await ctx.send("Browse through roles and add the ones you want using the check mark")

        await menu(ctx, ROLE_PAGES, new_controls, timeout=60)

        out = await encode(self.code, self.rand_roles)
        return out

    async def list_roles(self, ctx: commands.Context, pages: list,
                         controls: dict, message: discord.Message, page: int,
                         timeout: float, emoji: str):
        perms = message.channel.permissions_for(ctx.guild.me)
        if perms.manage_messages:  # Can manage messages, so remove react
            try:
                await message.remove_reaction(emoji, ctx.author)
            except discord.NotFound:
                pass

        await ctx.send(embed=say_role_list(self.code, self.rand_roles))

        return await menu(ctx, pages, controls, message=message,
                          page=page, timeout=timeout)

    async def select_page(self, ctx: commands.Context, pages: list,
                          controls: dict, message: discord.Message, page: int,
                          timeout: float, emoji: str):
        perms = message.channel.permissions_for(ctx.guild.me)
        if perms.manage_messages:  # Can manage messages, so remove react
            try:
                await message.remove_reaction(emoji, ctx.author)
            except discord.NotFound:
                pass

        if page >= len(ROLE_LIST):
            self.rand_roles.append(CATEGORY_COUNT[page - len(ROLE_LIST)])
        else:
            self.code.append(page)

        return await menu(ctx, pages, controls, message=message,
                          page=page, timeout=timeout)
