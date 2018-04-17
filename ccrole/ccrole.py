import discord
import asyncio 

from discord.ext import commands

from redbot.core import Config, checks

from redbot.core.utils.chat_formatting import pagify, box
import os
import re


class CCRole:
    """
    Custom commands
    Creates commands used to display text and adjust roles
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9999114111108101)
        default_guild = {
            "cmdlist" : {}, 
            "settings": {}
        }
        
        self.config.register_guild(**default_guild)


    @commands.group(no_pm=True)
    async def ccrole(self, ctx):
        """Custom commands management"""
        if not ctx.invoked_subcommand:
            await ctx.send_help()

    @ccrole.command(name="add")
    @checks.mod_or_permissions(administrator=True)
    async def ccrole_add(self, ctx, command : str):
        """Adds a custom command with roles"""
        command = command.lower()
        if command in self.bot.all_commands:
            await ctx.send("That command is already a standard command.")
            return

        guild = ctx.guild
        author = ctx.author
        channel = ctx.channel
        
        cmdlist = self.config.guild(ctx.guild).cmdlist
        
        if await cmdlist.get_raw(command, default=None):
            await ctx.send("This command already exists. Delete it with `{}ccrole delete` first.".format(ctx.prefix))
            return

        # Roles to add
        await ctx.send('What roles should it add? (Must be **comma separated**)\nSay `None` to skip adding roles')
        
        def check(m):
            return m.author == author and m.channel==channel
        
        try:
            answer = await self.bot.wait_for('message', timeout=120, check=check)
        except asyncio.TimeoutError:
            await ctx.send("Timed out, canceling")
            
        arole_list = []
        if answer.content.upper()!="NONE":
            arole_list = await self._get_roles_from_content(ctx, answer.content)
            if arole_list is None:
                await ctx.send("Invalid answer, canceling")
                return
        
        # Roles to remove
        await ctx.send('What roles should it remove? (Must be comma separated)\nSay `None` to skip removing roles')
        try:
            answer = await self.bot.wait_for('message', timeout=120, check=check)
        except asyncio.TimeoutError:
            await ctx.send("Timed out, canceling")
        
        rrole_list = []
        if answer.content.upper()!="NONE":
            rrole_list = await self._get_roles_from_content(ctx, answer.content)
            if rrole_list is None:
                await ctx.send("Invalid answer, canceling")
                return
                
        # Roles to use
        await ctx.send('What roles are allowed to use this command? (Must be comma separated)\nSay `None` to allow all roles')
        
        try:
            answer = await self.bot.wait_for('message', timeout=120, check=check)
        except asyncio.TimeoutError:
            await ctx.send("Timed out, canceling")
        
        prole_list = []
        if answer.content.upper()!="NONE":
            prole_list = await self._get_roles_from_content(ctx, answer.content)
            if prole_list is None:
                await ctx.send("Invalid answer, canceling")
                return
                
        # Selfrole
        await ctx.send('Is this a targeted command?(yes/no)\nNo will make this a selfrole command')
        
        try:
            answer = await self.bot.wait_for('message', timeout=120, check=check)
        except asyncio.TimeoutError:
            await ctx.send("Timed out, canceling")
        
        if answer.content.upper() in ["Y", "YES"]:
            targeted = True
            await ctx.send("This command will be **`targeted`**")
        else:
            targeted = False
            await ctx.send("This command will be **`selfrole`**")
        
        # Message to send
        await ctx.send('What message should the bot say when using this command?\nSay `None` to send the default `Success!` message')
        
        try:
            answer = await self.bot.wait_for('message', timeout=120, check=check)
        except asyncio.TimeoutError:
            await ctx.send("Timed out, canceling")
        text = "Success!"
        if answer.content.upper()!="NONE":
            text = answer.content

        # Save the command
        
        out = {'text': text, 'aroles': arole_list, 'rroles': rrole_list, "proles": prole_list, "targeted": targeted}
        
        await cmdlist.set_raw(command, value=out)

    @ccrole.command(name="delete")
    @checks.mod_or_permissions(administrator=True)
    async def ccrole_delete(self, ctx, command : str):
        """Deletes a custom command
        Example:
        [p]ccrole delete yourcommand"""
        guild = ctx.guild
        command = command.lower()
        if not await self.config.guild(ctx.guild).cmdlist.get_raw(command, default=None):
            await ctx.send("That command doesn't exist")
        else:
            await self.config.guild(ctx.guild).cmdlist.set_raw(command, value=None)
            await ctx.send("Custom command successfully deleted.")

    @ccrole.command(name="list")
    async def ccrole_list(self, ctx):
        """Shows custom commands list"""
        guild = ctx.guild
        commands = await self.config.guild(ctx.guild).cmdlist

        if not commands:
            await ctx.send("There are no custom commands in this server. Use `{}ccrole add` to start adding some.".format(ctx.prefix))
            return

        commands = ", ".join([ctx.prefix + c for c in sorted(commands.keys())])
        commands = "Custom commands:\n\n" + commands

        if len(commands) < 1500:
            await ctx.send(box(commands))
        else:
            for page in pagify(commands, delims=[" ", "\n"]):
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
        cmd = message.content[len(prefix):].split()[0]
        cmd = await cmdlist.get_raw(cmd.lower(), default=None)
        
        if cmd:
            await self.eval_cc(cmd, message)
    
    async def _get_roles_from_content(ctx, content):
        content_list = content.split(",")
        role_list = []
        try:
            role_list = [discord.utils.get(ctx.guild.roles, name=role.strip(' ')).id for role in content_list]
        except:
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
        prefixes = sorted(prefix_list,
                          key=lambda pfx: len(pfx),
                          reverse=True)
        for p in prefixes:
            if content.startswith(p):
                return p
        raise ValueError
        
    async def eval_cc(self, cmd, message):
        """Does all the work"""
        if cmd['proles'] and not (set(role.id for role in message.author.roles) & set(cmd['proles'])):
            return  # Not authorized, do nothing
        
        if cmd['targeted']:
            try:
                target = discord.utils.get(message.guild.members, mention=message.content.split()[1])
            except:
                target = None
            
            if not target:
                out_message = "This command is targeted! @mention a target\n`{} <target>`".format(message.content.split()[0])
                
                await message.channel.send(out_message)
                
                return
        else:
            target = message.author
            
        if cmd['aroles']:
            arole_list = [discord.utils.get(message.guild.roles, id=roleid) for roleid in cmd['aroles']]
            # await self.bot.send_message(message.channel, "Adding: "+str([str(arole) for arole in arole_list]))
            await target.add_roles(*arole_list)
            
        await asyncio.sleep(1)
        
        if cmd['rroles']:
            rrole_list = [discord.utils.get(message.guild.roles, id=roleid) for roleid in cmd['rroles']]
            # await self.bot.send_message(message.channel, "Removing: "+str([str(rrole) for rrole in rrole_list]))
            await target.remove_roles(*rrole_list)
        
        await message.channel.send(cmd['text'])
            
        # {'text': text, 'aroles': arole_list, 'rroles': rrole_list, "proles", prole_list, "targeted": targeted}

    # def format_cc(self, command, message):
        # results = re.findall("\{([^}]+)\}", command)
        # for result in results:
            # param = self.transform_parameter(result, message)
            # command = command.replace("{" + result + "}", param)
        # return command

    # def transform_parameter(self, result, message):
        # """
        # For security reasons only specific objects are allowed
        # Internals are ignored
        # """
        # raw_result = "{" + result + "}"
        # objects = {
            # "message" : message,
            # "author"  : message.author,
            # "channel" : message.channel,
            # "server"  : message.server
        # }
        # if result in objects:
            # return str(objects[result])
        # try:
            # first, second = result.split(".")
        # except ValueError:
            # return raw_result
        # if first in objects and not second.startswith("_"):
            # first = objects[first]
        # else:
            # return raw_result
        # return str(getattr(first, second, raw_result))