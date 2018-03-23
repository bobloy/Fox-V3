import discord
import asyncio 

from discord.ext import commands

from redbot.core import Config

from .utils import checks
from .utils.chat_formatting import pagify, box
import os
import re


class CCRole:
    """
    Custom commands
    Creates commands used to display text and adjust roles
    """

    def __init__(self, bot):
        self.bot = bot
        self.file_path = "data/ccrole/commands.json"
        self.c_commands = dataIO.load_json(self.file_path)

    @commands.group(pass_context=True, no_pm=True)
    async def ccrole(self, ctx):
        """Custom commands management"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @ccrole.command(name="add", pass_context=True)
    @checks.mod_or_permissions(administrator=True)
    async def ccrole_add(self, ctx, command : str):
        """Adds a custom command with roles"""
        command = command.lower()
        if command in self.bot.commands:
            await self.bot.say("That command is already a standard command.")
            return

        server = ctx.message.server
        author = ctx.message.author
        
        if server.id not in self.c_commands:
            self.c_commands[server.id] = {}
        cmdlist = self.c_commands[server.id]
        if command in cmdlist:
            await self.bot.say("This command already exists. Delete"
                               "`it with {}ccrole delete` first."
                               "".format(ctx.prefix))
            return

        # Roles to add
        await self.bot.say('What roles should it add? (Must be comma separated)\nSay `None` to skip adding roles')
        
        answer = await self.bot.wait_for_message(timeout=120, author=author)
        if not answer:
            await self.bot.say("Timed out, canceling")
            return
        arole_list = []
        if answer.content.upper()!="NONE":
            arole_list = answer.content.split(",")

            try:
                arole_list = [discord.utils.get(server.roles, name=role.strip(' ')).id for role in arole_list]
            except:
                await self.bot.say("Invalid answer, canceling")
                return
        
        # Roles to remove
        await self.bot.say('What roles should it remove? (Must be comma separated)\nSay `None` to skip removing roles')
        
        answer = await self.bot.wait_for_message(timeout=120, author=author)
        if not answer:
            await self.bot.say("Timed out, canceling")
            return
        
        rrole_list = []
        if answer.content.upper()!="NONE":
            rrole_list = answer.content.split(",")

            try:
                rrole_list = [discord.utils.get(server.roles, name=role.strip(' ')).id for role in rrole_list]
            except:
                await self.bot.say("Invalid answer, canceling")
                return
                
        # Roles to use
        await self.bot.say('What roles are allowed to use this command? (Must be comma separated)\nSay `None` to allow all roles')
        
        answer = await self.bot.wait_for_message(timeout=120, author=author)
        if not answer:
            await self.bot.say("Timed out, canceling")
            return
        
        prole_list = []
        if answer.content.upper()!="NONE":
            prole_list = answer.content.split(",")

            try:
                prole_list = [discord.utils.get(server.roles, name=role.strip(' ')).id for role in prole_list]
            except:
                await self.bot.say("Invalid answer, canceling")
                return
                
        # Selfrole
        await self.bot.say('Is this a targeted command?(yes/no)\nNo will make this a selfrole command')
        
        answer = await self.bot.wait_for_message(timeout=120, author=author)
        if not answer:
            await self.bot.say("Timed out, canceling")
            return
        
        if answer.content.upper() in ["Y", "YES"]:
            targeted = True
            await self.bot.say("This command will be targeted")
        else:
            targeted = False
            await self.bot.say("This command will be selfrole")
        
        # Message to send
        await self.bot.say('What message should the bot send?\nSay `None` to send the default `Success!` message')
        
        answer = await self.bot.wait_for_message(timeout=120, author=author)
        if not answer:
            await self.bot.say("Timed out, canceling")
            return
        text = "Success!"
        if answer.content.upper()!="NONE":
            text = answer.content

        # Save the command
        
        cmdlist[command] = {'text': text, 'aroles': arole_list, 'rroles': rrole_list, "proles": prole_list, "targeted": targeted}
        
        self.c_commands[server.id] = cmdlist
        dataIO.save_json(self.file_path, self.c_commands)
        await self.bot.say("Custom command successfully added.")

    @ccrole.command(name="delete", pass_context=True)
    @checks.mod_or_permissions(administrator=True)
    async def ccrole_delete(self, ctx, command : str):
        """Deletes a custom command
        Example:
        [p]ccrole delete yourcommand"""
        server = ctx.message.server
        command = command.lower()
        if server.id in self.c_commands:
            cmdlist = self.c_commands[server.id]
            if command in cmdlist:
                cmdlist.pop(command, None)
                self.c_commands[server.id] = cmdlist
                dataIO.save_json(self.file_path, self.c_commands)
                await self.bot.say("Custom command successfully deleted.")
            else:
                await self.bot.say("That command doesn't exist.")
        else:
            await self.bot.say("There are no custom commands in this server."
                               " Use `{}ccrole add` to start adding some."
                               "".format(ctx.prefix))

    @ccrole.command(name="list", pass_context=True)
    async def ccrole_list(self, ctx):
        """Shows custom commands list"""
        server = ctx.message.server
        commands = self.c_commands.get(server.id, {})

        if not commands:
            await self.bot.say("There are no custom commands in this server."
                               " Use `{}ccrole add` to start adding some."
                               "".format(ctx.prefix))
            return

        commands = ", ".join([ctx.prefix + c for c in sorted(commands.keys())])
        commands = "Custom commands:\n\n" + commands

        if len(commands) < 1500:
            await self.bot.say(box(commands))
        else:
            for page in pagify(commands, delims=[" ", "\n"]):
                await self.bot.whisper(box(page))

    async def on_message(self, message):
        if len(message.content) < 2 or message.channel.is_private:
            return

        server = message.server
        prefix = self.get_prefix(message)

        if not prefix:
            return

        if server.id in self.c_commands and self.bot.user_allowed(message):
            cmdlist = self.c_commands[server.id]
            cmd = message.content[len(prefix):].split()[0]
            if cmd in cmdlist:
                cmd = cmdlist[cmd]
                await self.eval_cc(cmd, message)
            elif cmd.lower() in cmdlist:
                cmd = cmdlist[cmd.lower()]
                await self.eval_cc(cmd, message)

    def get_prefix(self, message):
        for p in self.bot.settings.get_prefixes(message.server):
            if message.content.startswith(p):
                return p
        return False
        
    async def eval_cc(self, cmd, message):
        if cmd['proles'] and not (set(role.id for role in message.author.roles) & set(cmd['proles'])):
            return  # Not authorized, do nothing
        
        if cmd['targeted']:
            try:
                target = discord.utils.get(message.server.members, mention=message.content.split()[1])
            except:
                target = None
            
            if not target:
                out_message = "This command is targeted! @mention a target\n`{} <target>`".format(message.content.split()[0])
                
                await self.bot.send_message(message.channel, out_message)
                
                return
        else:
            target = message.author
            
        if cmd['aroles']:
            arole_list = [discord.utils.get(message.server.roles, id=roleid) for roleid in cmd['aroles']]
            # await self.bot.send_message(message.channel, "Adding: "+str([str(arole) for arole in arole_list]))
            await self.bot.add_roles(target, *arole_list)
            
        await asyncio.sleep(1)
        
        if cmd['rroles']:
            rrole_list = [discord.utils.get(message.server.roles, id=roleid) for roleid in cmd['rroles']]
            # await self.bot.send_message(message.channel, "Removing: "+str([str(rrole) for rrole in rrole_list]))
            await self.bot.remove_roles(target, *rrole_list)
        
        await self.bot.send_message(message.channel, cmd['text'])
            
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


def check_folders():
    if not os.path.exists("data/ccrole"):
        print("Creating data/ccrole folder...")
        os.makedirs("data/ccrole")


def check_files():
    f = "data/ccrole/commands.json"
    if not dataIO.is_valid_json(f):
        print("Creating empty commands.json...")
        dataIO.save_json(f, {})


def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(CCRole(bot))