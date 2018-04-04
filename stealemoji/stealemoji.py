import asyncio

from urllib.parse import urlparse

import os

from typing import List, Union

import discord
from discord.ext import commands

from redbot.core import Config
from redbot.core.bot import Red

async def fetch_img(session, url):
    with aiohttp.Timeout(10):
        async with session.get(url) as response:
            assert response.status == 200
            return await response.read()

      
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
        
    async def se_bank(self, ctx):
        """Add current server as emoji bank"""
        await ctx.send("This will upload custom emojis to this server\n"
                        "Are you sure you want to make the current server an emoji bank? (y/n)"
        
        def check(m):
            return upper(m.content) in ["Y","YES","N","NO"]  and m.channel == ctx.channel and m.author == ctx.author

        msg = await client.wait_for('message', check=check)
        
        if msg.content in ["N","NO"]
            await ctx.send("Cancelled")
            return
        
        async with self.config.guildbanks() as guildbanks:
            guildbanks.append(ctx.guild.id)
            
        await ctx.send("This server has been added as an emoji bank")
        
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        """Event handler for reaction watching"""
        if not reaction.custom_emoji:
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
        for guild_id in banklist:
            guild = self.bot.get_guild(guild_id)
            if len(guild.emojis)<50:
                guildbank = guild
                break
        
        if guildbank is None:
            # Eventually make a new banklist
            return
            
        # Next, have I saved this emoji before (in self.bot.emojis should've done this)
        
        stolemojis = await self.config.stolemoji()
        
        if emoji.id in stolemojis:
            return
        
        # Alright, time to steal it for real
        path = urlparse(emoji.url).path
        ext = os.path.splitext(path)[1]
        
        img = await fetch_img(emoji.url)
        
        with open("\\cogs\\stealemoji\\"+emoji.name+ext, "wb") as f:
            f.write(img)
        # urllib.urlretrieve(emoji.url, emoji.name+ext)
        
        
        try:
            await guildbank.create_custom_emoji(name=emoji.name,image="\\cogs\\stealemoji\\"+emoji.name+ext,reason="Stole from "+str(user))
        except Forbidden as e:
            print("PermissionError - no permission to add emojis")
            raise PermissionError("No permission to add emojis") from e
        except HTTPException:
            print("Unhandled exception")
            pass  # Unhandled error
            
        # If you get this far, YOU DID IT
        
        owner = await self.bot.application_info()
        owner = owner.owner
        await owner.send("Just added emoji "+str(emoji)+" to server "+str(guildbank))
        
        # add to config.stolemoji()?
