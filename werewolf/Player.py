import asyncio

import discord

from datetime import datetime,timedelta

class Player:
    """
    Base to host a game of werewolf
    """

    def __init__(self, member: discord.Member):
        self.user = member
        self.role = None
        self.alive = True
        self.muted = False
        

    async def assign_role(self, role):
        """
        Base command for this cog. Check help for the commands list.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help()
            
    async def join(self, ctx: commands.Context):
        """
        Joins a game
        """
        
        await self.config.guild(ctx.guild).days.set(days)
        await ctx.send("Success")
