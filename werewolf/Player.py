import asyncio

import discord

from datetime import datetime,timedelta

class Player:
    """
    Base player class for Werewolf game
    """

    def __init__(self, member: discord.Member):
        self.user = member
        self.role = None
        
        self.alive = True
        self.muted = False
        self.protected = False
        
    async def assign_role(self, role):
        """
        Give this player a role
        """
        self.role = role
            
    async def join(self, ctx: commands.Context):
        """
        Joins a game
        """
        
        await self.config.guild(ctx.guild).days.set(days)
        await ctx.send("Success")
