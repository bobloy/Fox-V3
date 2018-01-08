import os

import challonge

import discord
from discord.ext import commands

from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.chat_formatting import box
from redbot.core import Config
from redbot.core import checks




class Challonge:
    """Cog for organizing Challonge tourneys"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=6710497108108111110103101)
        default_global = {  
                "username": None,
                "apikey": None
                }
        default_guild = {
                "reportchannel": None,
                "announcechannel": None
                }

        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)
        
        await self._set_credentials()
        
# ************************Challonge command group start************************

    @commands.group()
    @commands.guild_only()
    async def challonge(self, ctx):
        """Challonge command base"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()
            # await ctx.send("I can do stuff!")
            
            
    @challonge.command(name="apikey")
    async def c_apikey(self, ctx, username, apikey):
        """Sets challonge username and apikey"""
        await self.config.username.set(username)
        await self.config.apikey.set(apikey)
        await self._set_credentials()
        await ctx.send("Success!")
        
    @challonge.command(name="report")
    async def c_report(self, ctx, channel: discord.TextChannel=None):
        """Set the channel for self-reporting matches"""
        if channel is None:
            channel = ctx.channel

        await self.config.guild(ctx.guild).reportchnnl.set(channel.id)
        
        channel = (await self._get_reportchnnl(ctx.guild))
        await ctx.send("Self-Reporting Channel is now set to: " + channel.mention)
        
    @challonge.command(name="announce")
    async def c_announce(self, ctx, channel: discord.TextChannel=None):
        """Set the channel for tournament announcements"""
        if channel is None:
            channel = ctx.channel

        await self.config.guild(ctx.guild).announcechnnl.set(channel.id)
        
        channel = (await self._get_announcechnnl(ctx.guild))
        await ctx.send("Announcement Channel is now set to: " + channel.mention)

# ************************Private command group start************************
    async def _print_tourney(self, guild: discord.Guild, tID: int):
        channel = (await self._get_announcechnnl(ctx.guild))
        
        await channel.send()
    
    async def _set_credentials(self):
        username = await self.config.username
        apikey = await self.config.apikey
        if username and apikey:
            challonge.set_credentials(username, apikey)
            return True
        return False
        
    async def _get_message_from_id(self, guild: discord.Guild, message_id: int):
        """
        Tries to find a message by ID in the current guild context.
        :param ctx:
        :param message_id:
        :return:
        """
        for channel in guild.text_channels:
            try:
                return await channel.get_message(message_id)
            except discord.NotFound:
                pass
            except AttributeError: # VoiceChannel object has no attribute 'get_message'
                pass

        return None

    async def _get_announcechnnl(self, guild: discord.Guild):
        channelid = await self.config.guild(guild).announcechnnl()
        channel = self._get_channel_from_id(channelid)
        return channel

    async def _get_reportchnnl(self, guild: discord.Guild):
        channelid = await self.config.guild(guild).reportchnnl()
        channel = self._get_channel_from_id(channelid)
        return channel
    
    def _get_channel_from_id(self, channelid):
        return self.bot.get_channel(channelid)
    
    def _get_user_from_id(self, userid):
        # guild = self._get_guild_from_id(guildID)
        # return discord.utils.get(guild.members, id=userid)
        return self.bot.get_user(userid)
        
    def _get_guild_from_id(self, guildID):
        return self.bot.get_guild(guildID)
    
    
    
    
    
    
        