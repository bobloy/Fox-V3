import logging
import pathlib
from typing import Optional

import discord
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.commands import Cog, PrivilegeLevel
from redbot.core.data_manager import cog_data_path

log = logging.getLogger("red.fox-v3.cogguide")


class CogGuide(commands.Cog):
    """
    Cog to create cog guides

    Dunno if this is a good idea but I did it. Sue me.
    """

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=0, force_registration=True)

        default_guild = {}

        self.config.register_guild(**default_guild)

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    @commands.command()
    async def allcogguides(self, ctx: commands.Context):
        """
        Create a template ReStructuredText file for all loaded cogs.

        Results can be found in the cog data folder.

        Returns: tick()

        """
        for cog_name, cog in self.bot.cogs.items():
            await self.create_cog_guide(cog_name, cog)
        await ctx.tick()

    @commands.command()
    async def cogguide(self, ctx: commands.Context, camel_cog_name: str):
        """
        Create a template ReStructuredText file for a given loaded cog.

        Result can be found in the cog data folder.

        Args:
            camel_cog_name:

        Returns: tick

        """
        cog: Optional[Cog] = self.bot.get_cog(camel_cog_name)
        if cog is None:
            await ctx.send("No cog found with that name")
            return
        await self.create_cog_guide(camel_cog_name, cog)

        await ctx.tick()

    async def create_cog_guide(self, camel_cog_name, cog):
        path: pathlib.Path = cog_data_path(self)
        lower_cog_name = f"{camel_cog_name.lower()}"
        reference = f"_{camel_cog_name.lower()}"
        filename = f"{lower_cog_name}.rst"
        filepath = path / filename
        privilege_levels = {
            PrivilegeLevel.MOD: "|mod-lock|",
            PrivilegeLevel.ADMIN: "|admin-lock|",
            PrivilegeLevel.GUILD_OWNER: "|guildowner-lock|",
            PrivilegeLevel.BOT_OWNER: "|owner-lock|",
        }
        intro = f""".. {reference}:

{'=' * len(camel_cog_name)}
{camel_cog_name}
{'=' * len(camel_cog_name)}

This is the cog guide for the {lower_cog_name} cog. You will
find detailed docs about usage and commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

        [p]load {'customcom' if lower_cog_name == 'customcommands' else lower_cog_name}

.. _{lower_cog_name}-usage:

-----
Usage
-----

{cog.description if cog.description else "This is a general description of what the cog does. This should be a very basic explanation, addressing the core purpose of the cog. This is some additional information about what this cog can do. Try to answer *the* most frequently asked question."}

"""
        cog_commands_intro = f"""
.. {reference}-commands:

--------
Commands
--------
"""

        def get_parent_tree(command: commands.Command):
            out = f"{command.name}"
            if command.parent:
                # out = f"{get_parent_tree(command.parent)}-" + out
                out = f"{'-'.join(command.full_parent_name.split())}-" + out
            return out

        def get_command_rst(command: commands.Command):
            cog_command = f"""
.. {reference}-command-{get_parent_tree(command)}:

{'^' * len(command.name) if not command.parent else '"' * len(command.name)}
{command.name}
{'^' * len(command.name) if not command.parent else '"' * len(command.name)}
"""
            if command.requires.privilege_level in privilege_levels:
                cog_command += f"""
.. note:: {privilege_levels[command.requires.privilege_level]}
"""
            cog_command += f"""
**Syntax**

.. code-block:: none

    [p]{command.qualified_name} {command.signature}

**Description**

{command.description or command.help}
"""
            return cog_command

        cog_commands_list = []
        for com in cog.walk_commands():
            cog_commands_list.append(get_command_rst(com))
        with filepath.open("w", encoding="utf-8") as f:
            f.write(intro)
            f.write(cog_commands_intro)
            f.writelines(cog_commands_list)
