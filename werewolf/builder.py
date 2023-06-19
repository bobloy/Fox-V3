import bisect
import logging
from collections import defaultdict
from operator import attrgetter
from random import choice

import discord


# Import all roles here
from redbot.core import commands

# from .roles.seer import Seer
# from .roles.vanillawerewolf import VanillaWerewolf
# from .roles.villager import Villager

from werewolf import roles
from redbot.core.utils.menus import menu, prev_page, next_page, close_menu

from werewolf.constants import ROLE_CATEGORY_DESCRIPTIONS
from werewolf.role import Role

log = logging.getLogger("red.fox_v3.werewolf.builder")

# All roles in this list for iterating

ROLE_DICT = {name: cls for name, cls in roles.__dict__.items() if isinstance(cls, type)}
ROLE_LIST = sorted(
    [cls for cls in ROLE_DICT.values()],
    key=attrgetter("alignment"),
)

log.debug(f"{ROLE_DICT=}")

# Town, Werewolf, Neutral
ALIGNMENT_COLORS = [0x008000, 0xFF0000, 0xC0C0C0]

ROLE_PAGES = []


def role_embed(idx, role: Role, color):
    embed = discord.Embed(
        title=f"**{idx}** - {role.__name__}",
        description=role.game_start_message,
        color=color,
    )
    if role.icon_url is not None:
        embed.set_thumbnail(url=role.icon_url)

    embed.add_field(
        name="Alignment",
        value=["Town", "Werewolf", "Neutral"][role.alignment - 1],
        inline=False,
    )
    embed.add_field(name="Multiples Allowed", value=str(not role.unique), inline=False)
    embed.add_field(
        name="Role Types",
        value=", ".join(ROLE_CATEGORY_DESCRIPTIONS[x] for x in role.category),
        inline=False,
    )
    embed.add_field(name="Random Option", value=str(role.rand_choice), inline=False)

    return embed


"""
Example code:
0 = Villager
1 = VanillaWerewolf
T1 - T6 = Random Town (1: Random, 2: Investigative, 3: Protective, 4: Government,
                       5: Killing, 6: Power (Special night action))
W1, W2, W5, W6 = Random Werewolf
N1 = Benign Neutral

0001-1112T11W112N2
which translates to
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

        if built in ["T", "W", "N"]:
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
            if not options:
                raise IndexError("No Match Found")

            decode.append(choice(options)(game))

        built = ""

    return decode


async def encode(role_list, rand_roles):
    """Convert role list to code"""
    digit_sort = sorted(role for role in role_list if role < 10)
    out_code = "".join(str(role) for role in digit_sort)

    digit_sort = sorted(role for role in role_list if 10 <= role < 100)
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


def role_from_alignment(alignment):
    return [
        role_embed(idx, role, ALIGNMENT_COLORS[role.alignment - 1])
        for idx, role in enumerate(ROLE_LIST)
        if alignment == role.alignment
    ]


def role_from_category(category):
    return [
        role_embed(idx, role, ALIGNMENT_COLORS[role.alignment - 1])
        for idx, role in enumerate(ROLE_LIST)
        if category in role.category
    ]


def role_from_id(idx):
    try:
        role = ROLE_LIST[idx]
    except IndexError:
        return None

    return role_embed(idx, role, ALIGNMENT_COLORS[role.alignment - 1])


def role_from_name(name: str):
    return [
        role_embed(idx, role, ALIGNMENT_COLORS[role.alignment - 1])
        for idx, role in enumerate(ROLE_LIST)
        if name in role.__name__
    ]


def say_role_list(code_list, rand_roles):
    roles = [ROLE_LIST[idx] for idx in code_list]
    embed = discord.Embed(title="Currently selected roles")
    role_dict = defaultdict(int)
    for role in roles:
        role_dict[str(role.__name__)] += 1

    for role in rand_roles:
        if 0 < role <= 6:
            role_dict[f"Town {ROLE_CATEGORY_DESCRIPTIONS[role]}"] += 1
        if 10 < role <= 16:
            role_dict[f"Werewolf {ROLE_CATEGORY_DESCRIPTIONS[role]}"] += 1
        if 20 < role <= 26:
            role_dict[f"Neutral {ROLE_CATEGORY_DESCRIPTIONS[role]}"] += 1

    for k, v in role_dict.items():
        embed.add_field(name=k, value=f"Count: {v}", inline=True)

    return embed


class GameBuilder:
    def __init__(self):
        self.code = []
        self.rand_roles = []
        self.page_groups = [0]
        self.category_count = []

        self.setup()

    def setup(self):
        # Roles
        last_alignment = ROLE_LIST[0].alignment
        for idx, role in enumerate(ROLE_LIST):
            if role.alignment != last_alignment and len(ROLE_PAGES) - 1 not in self.page_groups:
                self.page_groups.append(len(ROLE_PAGES) - 1)
                last_alignment = role.alignment

            ROLE_PAGES.append(role_embed(idx, role, ALIGNMENT_COLORS[role.alignment - 1]))

        # Random Town Roles
        if len(ROLE_PAGES) - 1 not in self.page_groups:
            self.page_groups.append(len(ROLE_PAGES) - 1)
        for k, v in ROLE_CATEGORY_DESCRIPTIONS.items():
            if 0 < k <= 9:
                ROLE_PAGES.append(
                    discord.Embed(
                        title="RANDOM:Town Role",
                        description=f"Town {v}",
                        color=ALIGNMENT_COLORS[0],
                    )
                )
                self.category_count.append(k)

        # Random WW Roles
        if len(ROLE_PAGES) - 1 not in self.page_groups:
            self.page_groups.append(len(ROLE_PAGES) - 1)
        for k, v in ROLE_CATEGORY_DESCRIPTIONS.items():
            if 10 < k <= 19:
                ROLE_PAGES.append(
                    discord.Embed(
                        title="RANDOM:Werewolf Role",
                        description=f"Werewolf {v}",
                        color=ALIGNMENT_COLORS[1],
                    )
                )
                self.category_count.append(k)
        # Random Neutral Roles
        if len(ROLE_PAGES) - 1 not in self.page_groups:
            self.page_groups.append(len(ROLE_PAGES) - 1)
        for k, v in ROLE_CATEGORY_DESCRIPTIONS.items():
            if 20 < k <= 29:
                ROLE_PAGES.append(
                    discord.Embed(
                        title=f"RANDOM:Neutral Role",
                        description=f"Neutral {v}",
                        color=ALIGNMENT_COLORS[2],
                    )
                )
                self.category_count.append(k)

    async def build_game(self, ctx: commands.Context):
        new_controls = {
            "⏪": self.prev_group,
            "⬅": prev_page,
            "☑": self.select_page,
            "➡": next_page,
            "⏩": self.next_group,
            "📇": self.list_roles,
            "❌": close_menu,
        }

        await ctx.send("Browse through roles and add the ones you want using the check mark")

        await menu(ctx, ROLE_PAGES, new_controls, timeout=60)

        out = await encode(self.code, self.rand_roles)
        return out

    async def list_roles(
        self,
        ctx: commands.Context,
        pages: list,
        controls: dict,
        message: discord.Message,
        page: int,
        timeout: float,
        emoji: str,
    ):
        perms = message.channel.permissions_for(ctx.me)
        if perms.manage_messages:  # Can manage messages, so remove react
            try:
                await message.remove_reaction(emoji, ctx.author)
            except discord.NotFound:
                pass

        await ctx.send(embed=say_role_list(self.code, self.rand_roles))

        return await menu(ctx, pages, controls, message=message, page=page, timeout=timeout)

    async def select_page(
        self,
        ctx: commands.Context,
        pages: list,
        controls: dict,
        message: discord.Message,
        page: int,
        timeout: float,
        emoji: str,
    ):
        perms = message.channel.permissions_for(ctx.me)
        if perms.manage_messages:  # Can manage messages, so remove react
            try:
                await message.remove_reaction(emoji, ctx.author)
            except discord.NotFound:
                pass

        if page >= len(ROLE_LIST):
            self.rand_roles.append(self.category_count[page - len(ROLE_LIST)])
        else:
            self.code.append(page)

        return await menu(ctx, pages, controls, message=message, page=page, timeout=timeout)

    async def next_group(
        self,
        ctx: commands.Context,
        pages: list,
        controls: dict,
        message: discord.Message,
        page: int,
        timeout: float,
        emoji: str,
    ):
        perms = message.channel.permissions_for(ctx.me)
        if perms.manage_messages:  # Can manage messages, so remove react
            try:
                await message.remove_reaction(emoji, ctx.author)
            except discord.NotFound:
                pass
        page = bisect.bisect_right(self.page_groups, page)

        if page == len(self.page_groups):
            page = self.page_groups[0]
        else:
            page = self.page_groups[page]

        return await menu(ctx, pages, controls, message=message, page=page, timeout=timeout)

    async def prev_group(
        self,
        ctx: commands.Context,
        pages: list,
        controls: dict,
        message: discord.Message,
        page: int,
        timeout: float,
        emoji: str,
    ):
        perms = message.channel.permissions_for(ctx.me)
        if perms.manage_messages:  # Can manage messages, so remove react
            try:
                await message.remove_reaction(emoji, ctx.author)
            except discord.NotFound:
                pass
        page = self.page_groups[bisect.bisect_left(self.page_groups, page) - 1]

        return await menu(ctx, pages, controls, message=message, page=page, timeout=timeout)
