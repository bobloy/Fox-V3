import asyncio
from typing import List, Union

import discord
from discord.ext import commands

from redbot.core import Config
from redbot.core.bot import Red

from .source import ChatBot
from .source.trainers import ListTrainer

from datetime import datetime,timedelta

class Chatter:
    """
    This cog trains a chatbot that will talk like members of your Guild
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=6710497116116101114)
        default_global = {}
        default_guild = {
            "whitelist": None,
            "days": 1
            }
        
        self.chatbot = ChatBot("ChatterBot")
        self.chatbot.set_trainer(ListTrainer)

        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)
        
        self.loop = asyncio.get_event_loop()
    
    async def _get_conversation(self, ctx, in_channel: discord.TextChannel=None):
        """
        Compiles all conversation in the Guild this bot can get it's hands on
        Currently takes a stupid long time
        Returns a list of text
        """
        out = []
        after = datetime.today() - timedelta(days=(await self.config.guild(ctx.guild).days()))
        

        for channel in ctx.guild.text_channels: 
            if in_channel:
                channel = in_channel
            await ctx.send("Gathering {}".format(channel.mention))
            user = None
            try:
                async for message in channel.history(limit=None, reverse=True, after=after):
                    if user == message.author:
                        out[-1] += "\n"+message.clean_content
                    else:
                        user = message.author
                        out.append(message.clean_content)
            except discord.Forbidden:
                pass
            except discord.HTTPException:
                pass
            
            if in_channel:
                break
        
        return out
        
    def _train(self, data):
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
    @chatter.command()
    async def age(self, ctx: commands.Context, days: int):
        """
        Sets the number of days to look back
        Will train on 1 day otherwise
        """
        
        await self.config.guild(ctx.guild).days.set(days)
        await ctx.send("Success")
        
    @chatter.command()
    async def train(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """
        Trains the bot based on language in this guild
        """
        
        conversation = await self._get_conversation(ctx, channel)
        
        if not conversation:
            await ctx.send("Failed to gather training data")
            return
            
        await ctx.send("Gather successful! Training begins now\n(**This will take a long time, be patient**)")
        embed=discord.Embed(title="Loading")
        embed.set_image(url="http://www.loop.universaleverything.com/animations/1295.gif")
        temp_message = await self.bot.say(embed=embed)
        future = await self.loop.run_in_executor(None, self._train, conversation)
        
        try:
            await temp_message.delete()
        except:
            pass
        
        if future:
            await ctx.send("Training successful!")
        else:
            await ctx.send("Error occurred :(")
            
    async def on_message(self, message): 
        """
        Credit to https://github.com/Twentysix26/26-Cogs/blob/master/cleverbot/cleverbot.py
        for on_message recognition of @bot
        """
        author = message.author
        channel = message.channel

        if message.author.id != self.bot.user.id:
            to_strip = "@" + author.guild.me.display_name + " "
            text = message.clean_content
            if not text.startswith(to_strip):
                return
            text = text.replace(to_strip, "", 1)
            async with channel.typing():
                response = self.chatbot.get_response(text)
                if not response:
                    response = ":thinking:"
                await channel.send(response)
                

