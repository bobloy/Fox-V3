import discord
import asyncio
import os
from datetime import datetime
from discord.ext import commands

from .utils.dataIO import dataIO
from .utils import checks


class Immortal:
    """Creates a goodbye message when people leave"""

    def __init__(self, bot):
        self.bot = bot
        self.path = "data/Fox-Cogs/immortal"
        self.file_path = "data/Fox-Cogs/immortal/immortal.json"
        self.the_data = dataIO.load_json(self.file_path)

    def save_data(self):
        """Saves the json"""
        dataIO.save_json(self.file_path, self.the_data)

    async def adj_roles(self, server, author, member: discord.Member=None, rrole_names=[], arole_names=[]):
        # Thank you SML for the addrole code
        # https://github.com/smlbiobot/SML-Cogs/tree/master/mm
        
        rroles = [r for r in server.roles if r.name in rrole_names]
        aroles = [r for r in server.roles if r.name in arole_names]
        try:
            await self.bot.add_roles(member, *aroles)
            await asyncio.sleep(0.5)
            await self.bot.remove_roles(member, *rroles)
            await asyncio.sleep(0.5)

        except discord.Forbidden:
            await self.bot.say(
                "{} does not have permission to edit {}’s roles.".format(
                    author.display_name, member.display_name))

        except discord.HTTPException:
            await self.bot.say(
                "Failed to adjust roles.")
        except:
            await self.bot.say("Unknown Exception")

        


    @commands.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_roles=True)
    async def iresort(self, ctx, member: discord.Member=None):
        """Sends someone on vacation!"""

        if member is None:
            await self.bot.send_cmd_help(ctx)
        else:
            server = ctx.message.server
            author = ctx.message.author
            role_names = ["Member", "Immortal", "Eternal", "Phantom", "Ghost", "Undead", "Revenant", "Crypt", "Relocate", "Guest"]
            arole_names = ["Resort"]
            await self.adj_roles(server, author, member, role_names, arole_names)
            if "Resort" in [r.name for r in member.roles]:
                await self.bot.say("You are being sent on Vacation! :tada:" +
                                   "Please relocate to Immortal Resort (#889L92UQ) when you find the time.")
                await self.bot.send_message(member, "You are being sent on Vacation! :tada: Please relocate " +
                                                    "to Immortal Resort (#889L92UQ) when you find the time.\n" +
                                                    "You'll have limited access to the server until you rejoin a main clan")

    @commands.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_roles=True)
    async def icrypt(self, ctx, member: discord.Member=None):
        """Sends someone to Crypt!"""

        if member is None:
            await self.bot.send_cmd_help(ctx)
        else:
            server = ctx.message.server
            author = ctx.message.author
            role_names = ["Immortal", "Eternal", "Ghost", "Phantom", "Revenant", "Undead", "Relocate", "Guest", "Resort"]
            arole_names = ["Member", "Crypt"]
            await self.adj_roles(server, author, member, role_names, arole_names)
            if "Crypt" in [r.name for r in member.roles]:
                await self.bot.say("Success")
                await self.send_welcome(member)
                
    @commands.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_roles=True)
    async def irevenant(self, ctx, member: discord.Member=None):
        """Sends someone to Revenant!"""

        if member is None:
            await self.bot.send_cmd_help(ctx)
        else:
            server = ctx.message.server
            author = ctx.message.author
            role_names = ["Immortal", "Eternal", "Ghost", "Phantom", "Undead", "Crypt", "Relocate", "Guest", "Resort"]
            arole_names = ["Member", "Revenant"]
            await self.adj_roles(server, author, member, role_names, arole_names)
            if "Revenant" in [r.name for r in member.roles]:
                await self.bot.say("Success")
                await self.send_welcome(member)
                
    @commands.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_roles=True)
    async def iundead(self, ctx, member: discord.Member=None):
        """Sends someone to Undead!"""

        if member is None:
            await self.bot.send_cmd_help(ctx)
        else:
            server = ctx.message.server
            author = ctx.message.author
            role_names = ["Immortal", "Eternal", "Ghost", "Phantom", "Revenant", "Crypt", "Relocate", "Guest", "Resort"]
            arole_names = ["Member", "Undead"]
            await self.adj_roles(server, author, member, role_names, arole_names)
            if "Undead" in [r.name for r in member.roles]:
                await self.bot.say("Success")
                await self.send_welcome(member)
                
    @commands.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_roles=True)
    async def iphantom(self, ctx, member: discord.Member=None):
        """Sends someone to Phantom!"""

        if member is None:
            await self.bot.send_cmd_help(ctx)
        else:
            server = ctx.message.server
            author = ctx.message.author
            role_names = ["Immortal", "Eternal", "Ghost", "Undead", "Revenant", "Crypt", "Relocate", "Guest", "Resort"]
            arole_names = ["Member", "Phantom"]
            await self.adj_roles(server, author, member, role_names, arole_names)
            if "Phantom" in [r.name for r in member.roles]:
                await self.bot.say("Success")
                await self.send_welcome(member)

    @commands.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_roles=True)
    async def ieternal(self, ctx, member: discord.Member=None):
        """Sends someone to Eternal!"""

        if member is None:
            await self.bot.send_cmd_help(ctx)
        else:
            server = ctx.message.server
            author = ctx.message.author
            role_names = ["Immortal", "Phantom", "Ghost", "Undead", "Revenant", "Crypt", "Relocate", "Guest", "Resort"]
            arole_names = ["Member", "Eternal"]
            await self.adj_roles(server, author, member, role_names, arole_names)
            if "Eternal" in [r.name for r in member.roles]:
                await self.bot.say("Success")
                await self.send_welcome(member)

    @commands.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_roles=True)
    async def iimmortal(self, ctx, member: discord.Member=None):
        """Sends someone to Immortal!"""

        if member is None:
            await self.bot.send_cmd_help(ctx)
        else:
            server = ctx.message.server
            author = ctx.message.author
            role_names = ["Eternal", "Phantom", "Ghost", "Undead", "Revenant", "Crypt", "Relocate", "Guest", "Resort"]
            arole_names = ["Member", "Immortal"]
            await self.adj_roles(server, author, member, role_names, arole_names)
            if "Immortal" in [r.name for r in member.roles]:
                await self.bot.say("Success")
                await self.send_welcome(member)

    @commands.group(aliases=['setimmortal'], pass_context=True, no_pm=True)
    @checks.mod_or_permissions(administrator=True)
    async def immortalset(self, ctx):
        """Adjust immortal settings"""

        server = ctx.message.server
        if server.id not in self.the_data:
            self.the_data[server.id] = {}
            self.save_data()

        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @immortalset.command(pass_context=True, no_pm=True)
    async def welcomechannel(self, ctx):
        server = ctx.message.server
        if 'WELCOMECHANNEL' not in self.the_data[server.id]:
            self.the_data[server.id]['WELCOMECHANNEL'] = ''

        self.the_data[server.id]['WELCOMECHANNEL'] = ctx.message.channel.id
        self.save_data()
        await self.bot.say("Welcome Channel set to "+ctx.message.channel.name)

    async def send_welcome(self, member):
        server = member.server
        if server.id in self.the_data:
            await self.bot.send_message(server.get_channel(self.the_data[server.id]['WELCOMECHANNEL']),
                                        "You now have access to the server, " + member.mention + "\n" +
                                        "Check " + server.get_channel("257557008662790145").mention + " & " +
                                        server.get_channel("257560603093106688").mention+" for clan rules etc.\n" +
                                        "We recommend turning all message notifications on for " + server.get_channel("257560603093106688").mention +
                                        " if you want to know when tourneys are posted and other important info.\n" +
                                        "You can also type `!help` for a list of bot commands/features.")

#    @immortalset.command(pass_context=True)
#    async def channel(self, ctx):
#        server = ctx.message.server
#        if 'channel' not in self.the_data[server.id]:
#            self.the_data[server.id]['channel'] = ''

#        self.the_data[server.id]['channel'] = ctx.message.channel.id
#        self.save_data()

#    async def _when_leave(self, member):
#        server = member.server
#        if server.id not in self.the_data:
#            return

#        await self.bot.say("YOU LEFT ME "+member.mention)
#        self.the_data[server.id]


def check_folders():
    if not os.path.exists("data/Fox-Cogs"):
        print("Creating data/Fox-Cogs folder...")
        os.makedirs("data/Fox-Cogs")

    if not os.path.exists("data/Fox-Cogs/immortal"):
        print("Creating data/Fox-Cogs/immortal folder...")
        os.makedirs("data/Fox-Cogs/immortal")


def check_files():
    if not dataIO.is_valid_json("data/Fox-Cogs/immortal/immortal.json"):
        dataIO.save_json("data/Fox-Cogs/immortal/immortal.json", {})


def setup(bot):
    check_folders()
    check_files()
    q = Immortal(bot)
    bot.add_cog(q)
