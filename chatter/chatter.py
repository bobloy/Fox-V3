import asyncio
from typing import List, Union

import discord
from discord.ext import commands

from redbot.core import Config
from redbot.core.bot import Red

from chatterbot import ChatBot
from chatterbot.trainers import ListTrainer



class Chatter:
    """
    This cog trains a chatbot that will talk like members of your Guild
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=6710497116116101114)
        default_global = {}
        default_guild = {}
        
        self.chatbot = ChatBot("Chatter", trainer=ListTrainer)

        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)
    
    async def _get_conversation(guild: discord.Guild):
        """
        Compiles all conversation on the server this bot can get it's hands on
        Currently takes a stupid long time
        Returns a list of text
        """
        out = []
        
        for channel in guild.textchannels: 
            try:
                async for message in channel.history(limit=None, reverse=True):
                    out.append(message.content)
            except discord.Forbidden:
                pass
            except discord.HTTPException:
                pass

        
        return out
        
    async def _train(data):
        try:
            self.chatbot.train(data)
        except:
            return False
        return True
    @commands.group()
    async def chatter(self, ctx: commands.Context):
        """
        Base command for this cog. Check help for the commands list.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @reactrestrict.command()
    async def train(self, ctx: commands.Context):
        """
        Trains the bot based on language in this guild
        """
        
        conversation = await _get_conversation(ctx.guild)
        if not conversation:
            await ctx.send("Failed to gather training data")
            return

        if await _train(conversation):
            await ctx.send("Training successful")
        else:
            await ctx.send("Error occurred")

