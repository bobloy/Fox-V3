import asyncio

import urllib
from urllib.parse import urlparse

import os

from typing import List, Union

import discord
from discord.ext import commands

from redbot.core import Config
from redbot.core.bot import Red


class StealEmoji:
    """
    This cog steals emojis and creates servers for them
    """

    def __init__(self, red: Red):
        self.bot = red
        self.config = Config.get_conf(self, identifier=11511610197108101109111106105)
        default_global = {  
                "stolemoji": {},
                "guildbanks": [],
                "on": False
                }
                
        default_stolemoji = {
                "guildbank": None,
                "name": None,
                "require_colons": False,
                "managed": False,
                "guild_id": None,
                "created_at": None,
                "url": None,
                "roles": [],
                "guild": None  # Will not save this one
                }
                
        self.config.register_global(**default_global)

    @commands.group()
    async def stealemoji(self, ctx: commands.Context):
        """
        Base command for this cog. Check help for the commands list.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @stealemoji.command(name="collect")
    async def se_collect(self, ctx):
        """Toggles whether emoji's are collected or not"""
        currSetting = await self.config.on()
        await self.config.on.set(not currSetting)
        await ctx.send("Collection is now "+str(not currSetting))
        
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        """Event handler for reaction watching"""
        if not reaction.custom_emoji():
            return
        
        if not (await self.config.on()):
            return
        
        emoji = reaction.emoji
        if emoji in self.bot.emojis:
            return
        
        # This is now a custom emoji that the bot doesn't have access to, time to steal it
        # First, do I have an available guildbank?
        
        
        guildbank = None
        banklist = await self.config.guildbanks()
        for guild in banklist:
            if len(guild.emojis)<50:
                guildbank = guild
                break
        
        if not guildbank:
            # Eventually make a new banklist
            return
            
        # Next, have I saved this emoji before (in self.bot.emojis should've done this)
        
        stolemojis = await self.config.stolemoji()
        
        if emoji.id in stolemojis:
            return
        
        # Alright, time to steal it for real
        path = urlparse(emoji.url).path
        ext = os.path.splitext(path)[1]
        urllib.urlretrieve(emoji.url, emoji.name+ext)
        
        try:
            await guildbank.create_custom_emoji(name=emoji.name,image=emoji.url,reason="Stole from "+str(user))
        except Forbidden as e:
            raise PermissionError("No permission to add emojis") from e
        except HTTPException:
            pass  # Unhandled error
            
        # If you get this far, YOU DID IT
        
        owner = await self.bot.application_info()
        owner = owner.owner
        await owner.send("Just added emoji "+str(emoji)+" to server "+str(guildbank))
        
        
        
        
    # async def 
    
    
    # async def on_raw_reaction_add(self, emoji: discord.PartialReactionEmoji,
                                  # message_id: int, channel_id: int, user_id: int):
        # """
        # Event handler for long term reaction watching.

        # :param discord.PartialReactionEmoji emoji:
        # :param int message_id:
        # :param int channel_id:
        # :param int user_id:
        # :return:
        # """
        # if emoji.is_custom_emoji():
            # emoji_id = emoji.id
        # else:
            # return
        
        # has_reactrestrict, combos = await self.has_reactrestrict_combo(message_id)

        # if not has_reactrestrict:
            # return

        # try:
            # member = self._get_member(channel_id, user_id)
        # except LookupError:
            # return

        # if member.bot:
            # return

        # try:
            # roles = [self._get_role(member.guild, c.role_id) for c in combos]
        # except LookupError:
            # return

        # for apprrole in roles:
            # if apprrole in member.roles:
                # return
                
        # message = await self._get_message_from_channel(channel_id, message_id)
        # await message.remove_reaction(emoji, member)
        
