import logging
import pathlib
import re
import string
from typing import Optional, Union

import discord
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.commands import Cog, PrivilegeLevel
from redbot.core.data_manager import cog_data_path

log = logging.getLogger("red.fox-v3.cogguide")

EXCLUDED_LIST = ['reinstallreqs']

def get_parent_tree(command: commands.Command):
    out = f"{command.name}"
    if command.parent:
        # out = f"{get_parent_tree(command.parent)}-" + out
        out = f"{'-'.join(command.full_parent_name.split())}-" + out
    return out


def markdown_link_replace(match, starts_with_text=None):
    """Converts a markdown match to restructuredtext match"""
    text = match.group(1)
    url = match.group(2)
    if starts_with_text and url.startswith(starts_with_text):
        i = len(starts_with_text)
        url = url[i:]
        i = url.find(".")
        url = url[:i]
        return f":ref:`{text} <{url}>`"

    return f"`{text} <{url}>`_"


def prepare_description(comm_or_cog: Union[commands.Command, Cog]):
    description = comm_or_cog.description or comm_or_cog.help
    description = description.replace("`", "``")
    pattern = re.compile(r"\[(.+)]\s?\((https?:\/\/[\w\d.\/?=#-@]+)\)")
    description = pattern.sub(markdown_link_replace, description)
    return description


def produce_aliases(command: commands.Command):
    return ", ".join(
        f"``{command.full_parent_name + ' ' if command.full_parent_name else ''}{alias}``"
        for alias in command.aliases
    )


class CogGuide(commands.Cog):
    """
    Cog to create cog guides

    Dunno if this is a good idea but I did it. Sue me.
    """

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=6711110371117105100101, force_registration=True
        )

        default_global = {"starts_with": None}
        self.config.register_global(**default_global)

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    @checks.is_owner()
    @commands.group()
    async def cogguideset(self, ctx: commands.Context):
        """Base command for configuring cogguide"""
        pass

    @cogguideset.command(name="url")
    async def cogguideset_url(self, ctx: commands.Context, url: str):
        """Sets the url of your ReadTheDocs for creating references

        For example: 'https://docs.discord.red/en/stable/' for Red docs
        """
        if not url:
            await self.config.starts_with.clear()
        else:
            await self.config.starts_with.set(url)

        await ctx.tick()

    @checks.is_owner()
    @commands.command()
    async def allcogguides(self, ctx: commands.Context):
        """
        Create a ReStructuredText file for all loaded cogs.

        Results can be found in the cog data folder.

        Returns: tick()

        """
        for cog_name, cog in self.bot.cogs.items():
            await self.create_cog_guide(cog_name, cog)
        await ctx.tick()

    @checks.is_owner()
    @commands.command()
    async def cogguide(self, ctx: commands.Context, camel_cog_name: str):
        """
        Create a ReStructuredText file for a given loaded cog.

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

{prepare_description(cog)}

"""
        cog_commands_intro = f"""
.. {reference}-commands:

--------
Commands
--------
"""

        def get_command_rst(command: commands.Command):
            description = prepare_description(command)

            cog_command = f"""
.. {reference}-command-{get_parent_tree(command)}:

{'^' * len(command.qualified_name) if not command.parent else '"' * len(command.qualified_name)}
{command.qualified_name}
{'^' * len(command.qualified_name) if not command.parent else '"' * len(command.qualified_name)}
"""
            if command.requires.privilege_level in privilege_levels:
                cog_command += f"""
.. note:: {privilege_levels[command.requires.privilege_level]}
"""
            cog_command += f"""
**Syntax**

.. code-block:: none

    [p]{command.qualified_name} {command.signature}
"""
            if command.aliases:
                cog_command += f"""
.. tip:: Alias{'es' if len(command.aliases) > 1 else ''}: {produce_aliases(command)}
"""
            cog_command += f"""
**Description**

{description}
"""
            return cog_command

        cog_commands_list = []
        com_list = [com for com in cog.walk_commands()]
        com_list.sort(key=lambda x: x.qualified_name)
        for com in com_list:
            com: commands.Command
            if com.name in EXCLUDED_LIST:
                continue
            if not com.hidden and com.enabled:
                cog_commands_list.append(get_command_rst(com))
        # for com in cog.walk_commands():
        #     cog_commands_list.append(get_command_rst(com))
        with filepath.open("w", encoding="utf-8") as f:
            f.write(intro)
            f.write(cog_commands_intro)
            f.writelines(cog_commands_list)
