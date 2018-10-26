import asyncio
import re
from typing import Any

import discord
from redbot.core import Config, checks
from redbot.core import commands
from redbot.core.utils.chat_formatting import pagify, box

Cog: Any = getattr(commands, "Cog", object)


class CCRole(Cog):
    """
    Custom commands
    Creates commands used to display text and adjust roles
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9999114111108101)
        default_guild = {"cmdlist": {}, "settings": {}}

        self.config.register_guild(**default_guild)

    @commands.guild_only()
    @commands.group()
    async def ccrole(self, ctx):
        """Custom commands management with roles

        Highly customizable custom commands with role management."""
        if not ctx.invoked_subcommand:
            pass

    @ccrole.command(name="add")
    @checks.mod_or_permissions(administrator=True)
    async def ccrole_add(self, ctx, command: str):
        """Adds a custom command with roles

        When adding text, put arguments in `{}` to eval them
        Options: `{author}`, `{target}`, `{server}`, `{channel}`, `{message}`"""
        command = command.lower()
        if command in self.bot.all_commands:
            await ctx.send("That command is already a standard command.")
            return

        guild = ctx.guild
        author = ctx.author
        channel = ctx.channel

        cmd_list = self.config.guild(guild).cmdlist

        if await cmd_list.get_raw(command, default=None):
            await ctx.send(
                "This command already exists. Delete it with `{}ccrole delete` first.".format(
                    ctx.prefix
                )
            )
            return

        # Roles to add
        await ctx.send(
            "What roles should it add? (Must be **comma separated**)\nSay `None` to skip adding roles"
        )

        def check(m):
            return m.author == author and m.channel == channel

        try:
            answer = await self.bot.wait_for("message", timeout=120, check=check)
        except asyncio.TimeoutError:
            await ctx.send("Timed out, canceling")
            return

        arole_list = []
        if answer.content.upper() != "NONE":
            arole_list = await self._get_roles_from_content(ctx, answer.content)
            if arole_list is None:
                await ctx.send("Invalid answer, canceling")
                return

        # Roles to remove
        await ctx.send(
            "What roles should it remove? (Must be comma separated)\nSay `None` to skip removing roles"
        )
        try:
            answer = await self.bot.wait_for("message", timeout=120, check=check)
        except asyncio.TimeoutError:
            await ctx.send("Timed out, canceling")
            return

        rrole_list = []
        if answer.content.upper() != "NONE":
            rrole_list = await self._get_roles_from_content(ctx, answer.content)
            if rrole_list is None:
                await ctx.send("Invalid answer, canceling")
                return

        # Roles to use
        await ctx.send(
            "What roles are allowed to use this command? (Must be comma separated)\nSay `None` to allow all roles"
        )

        try:
            answer = await self.bot.wait_for("message", timeout=120, check=check)
        except asyncio.TimeoutError:
            await ctx.send("Timed out, canceling")
            return

        prole_list = []
        if answer.content.upper() != "NONE":
            prole_list = await self._get_roles_from_content(ctx, answer.content)
            if prole_list is None:
                await ctx.send("Invalid answer, canceling")
                return

        # Selfrole
        await ctx.send(
            "Is this a targeted command?(yes/no)\nNo will make this a selfrole command"
        )

        try:
            answer = await self.bot.wait_for("message", timeout=120, check=check)
        except asyncio.TimeoutError:
            await ctx.send("Timed out, canceling")
            return

        if answer.content.upper() in ["Y", "YES"]:
            targeted = True
            await ctx.send("This command will be **`targeted`**")
        else:
            targeted = False
            await ctx.send("This command will be **`selfrole`**")

        # Message to send
        await ctx.send(
            "What message should the bot say when using this command?\n"
            "Say `None` to send the default `Success!` message\n"
            "Eval Options: `{author}`, `{target}`, `{server}`, `{channel}`, `{message}`\n"
            "For example: `Welcome {target.mention} to {server.name}!`"
        )

        try:
            answer = await self.bot.wait_for("message", timeout=120, check=check)
        except asyncio.TimeoutError:
            await ctx.send("Timed out, canceling")
            return

        text = "Success!"
        if answer.content.upper() != "NONE":
            text = answer.content

        # Save the command

        out = {
            "text": text,
            "aroles": arole_list,
            "rroles": rrole_list,
            "proles": prole_list,
            "targeted": targeted,
        }

        await cmd_list.set_raw(command, value=out)

        await ctx.send("Custom Command **`{}`** successfully added".format(command))

    @ccrole.command(name="delete")
    @checks.mod_or_permissions(administrator=True)
    async def ccrole_delete(self, ctx, command: str):
        """Deletes a custom command

        Example:
        `[p]ccrole delete yourcommand`"""
        guild = ctx.guild
        command = command.lower()
        if not await self.config.guild(guild).cmdlist.get_raw(command, default=None):
            await ctx.send("That command doesn't exist")
        else:
            await self.config.guild(guild).cmdlist.set_raw(command, value=None)
            await ctx.send("Custom command successfully deleted.")

    @ccrole.command(name="details")
    async def ccrole_details(self, ctx, command: str):
        """Provide details about passed custom command"""
        guild = ctx.guild
        command = command.lower()
        cmd = await self.config.guild(guild).cmdlist.get_raw(command, default=None)
        if cmd is None:
            await ctx.send("That command doesn't exist")
            return

        embed = discord.Embed(
            title=command,
            description="{} custom command".format(
                "Targeted" if cmd["targeted"] else "Non-Targeted"
            ),
        )

        def process_roles(role_list):
            if not role_list:
                return "None"
            return ", ".join(
                [discord.utils.get(ctx.guild.roles, id=roleid).name for roleid in role_list]
            )

        embed.add_field(name="Text", value="```{}```".format(cmd["text"]))
        embed.add_field(name="Adds Roles", value=process_roles(cmd["aroles"]), inline=True)
        embed.add_field(name="Removes Roles", value=process_roles(cmd["rroles"]), inline=True)
        embed.add_field(name="Role Restrictions", value=process_roles(cmd["proles"]), inline=True)

        await ctx.send(embed=embed)

    @ccrole.command(name="list")
    async def ccrole_list(self, ctx):
        """Shows custom commands list"""
        guild = ctx.guild
        cmd_list = await self.config.guild(guild).cmdlist()
        cmd_list = {k: v for k, v in cmd_list.items() if v}
        if not cmd_list:
            await ctx.send(
                "There are no custom commands in this server. Use `{}ccrole add` to start adding some.".format(
                    ctx.prefix
                )
            )
            return

        cmd_list = ", ".join([ctx.prefix + c for c in sorted(cmd_list.keys())])
        cmd_list = "Custom commands:\n\n" + cmd_list

        if (
            len(cmd_list) < 1500
        ):  # I'm allowed to have arbitrary numbers for when it's too much to dm dammit
            await ctx.send(box(cmd_list))
        else:
            for page in pagify(cmd_list, delims=[" ", "\n"]):
                await ctx.author.send(box(page))
            await ctx.send("Command list DM'd")

    async def on_message(self, message):
        if len(message.content) < 2 or message.guild is None:
            return

        guild = message.guild
        try:
            prefix = await self.get_prefix(message)
        except ValueError:
            return

        cmdlist = self.config.guild(guild).cmdlist
        cmd = message.content[len(prefix) :].split()[0].lower()
        cmd = await cmdlist.get_raw(cmd, default=None)

        if cmd is not None:
            await self.eval_cc(cmd, message)

    async def _get_roles_from_content(self, ctx, content):
        content_list = content.split(",")
        try:
            role_list = [
                discord.utils.get(ctx.guild.roles, name=role.strip(" ")).id
                for role in content_list
            ]
        except (discord.HTTPException, AttributeError):  # None.id is attribute error
            return None
        else:
            return role_list

    async def get_prefix(self, message: discord.Message) -> str:
        """
        Borrowed from alias cog
        Tries to determine what prefix is used in a message object.
            Looks to identify from longest prefix to smallest.

            Will raise ValueError if no prefix is found.
        :param message: Message object
        :return:
        """
        content = message.content
        prefix_list = await self.bot.command_prefix(self.bot, message)
        prefixes = sorted(prefix_list, key=lambda pfx: len(pfx), reverse=True)
        for p in prefixes:
            if content.startswith(p):
                return p
        raise ValueError

    async def eval_cc(self, cmd, message):
        """Does all the work"""
        if cmd["proles"] and not (
            set(role.id for role in message.author.roles) & set(cmd["proles"])
        ):
            return  # Not authorized, do nothing

        if cmd["targeted"]:
            try:
                target = discord.utils.get(
                    message.guild.members, mention=message.content.split()[1]
                )
            except IndexError:  # .split() return list of len<2
                target = None

            if not target:
                out_message = "This custom command is targeted! @mention a target\n`{} <target>`".format(
                    message.content.split()[0]
                )
                await message.channel.send(out_message)
                return
        else:
            target = message.author

        if cmd["aroles"]:
            arole_list = [
                discord.utils.get(message.guild.roles, id=roleid) for roleid in cmd["aroles"]
            ]
            # await self.bot.send_message(message.channel, "Adding: "+str([str(arole) for arole in arole_list]))
            try:
                await target.add_roles(*arole_list)
            except discord.Forbidden:
                await message.channel.send("Permission error: Unable to add roles")
        await asyncio.sleep(1)

        if cmd["rroles"]:
            rrole_list = [
                discord.utils.get(message.guild.roles, id=roleid) for roleid in cmd["rroles"]
            ]
            # await self.bot.send_message(message.channel, "Removing: "+str([str(rrole) for rrole in rrole_list]))
            try:
                await target.remove_roles(*rrole_list)
            except discord.Forbidden:
                await message.channel.send("Permission error: Unable to remove roles")

        out_message = self.format_cc(cmd, message, target)
        await message.channel.send(out_message)

    def format_cc(self, cmd, message, target):
        out = cmd["text"]
        results = re.findall("{([^}]+)\}", out)
        for result in results:
            param = self.transform_parameter(result, message, target)
            out = out.replace("{" + result + "}", param)
        return out

    def transform_parameter(self, result, message, target):
        """
        For security reasons only specific objects are allowed
        Internals are ignored
        """
        raw_result = "{" + result + "}"
        objects = {
            "message": message,
            "author": message.author,
            "channel": message.channel,
            "server": message.guild,
            "guild": message.guild,
            "target": target,
        }
        if result in objects:
            return str(objects[result])
        try:
            first, second = result.split(".")
        except ValueError:
            return raw_result
        if first in objects and not second.startswith("_"):
            first = objects[first]
        else:
            return raw_result
        return str(getattr(first, second, raw_result))
