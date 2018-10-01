import asyncio
import json
import random

from redbot.core import bank
from redbot.core import commands
from redbot.core.data_manager import cog_data_path
from typing import Any

Cog: Any = getattr(commands, "Cog", object)


class RecyclingPlant(Cog):
    """Apply for a job at the recycling plant!"""

    def __init__(self, bot):
        self.bot = bot
        self.path = str(cog_data_path(self)).replace('\\', '/')
        self.junk_path = self.path + "/bundled_data/junk.json"

        with open(self.junk_path) as json_data:
            self.junk = json.load(json_data)

    @commands.command(aliases=["recycle"])
    async def recyclingplant(self, ctx: commands.Context):
        """Apply for a job at the recycling plant!"""
        x = 0
        reward = 0
        await ctx.send(
            '{0} has signed up for a shift at the Recycling Plant! Type ``exit`` to terminate it early.'.format(
                ctx.author.display_name))
        while x in range(0, 10):
            used = random.choice(self.junk['can'])
            if used['action'] == 'trash':
                opp = 'recycle'
            else:
                opp = 'trash'
            await ctx.send('``{}``! Will {} ``trash`` it or ``recycle`` it?'.format(used['object'],
                                                                                    ctx.author.display_name))

            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel

            try:
                answer = await self.bot.wait_for('message', timeout=120, check=check)
            except asyncio.TimeoutError:
                answer = None

            if answer is None:
                await ctx.send('``{}`` fell down the conveyor belt to be sorted again!'.format(used['object']))
            elif answer.content.lower().strip() == used['action']:
                await ctx.send(
                    'Congratulations! You put ``{}`` down the correct chute! (**+50**)'.format(used['object']))
                reward = reward + 50
                x += 1
            elif answer.content.lower().strip() == opp:
                await ctx.send('{}, you little brute, you put it down the wrong chute! (**-50**)'.format(
                    ctx.author.display_name))
                reward = reward - 50
            elif answer.content.lower().strip() == 'exit':
                await ctx.send('{} has been relived of their duty.'.format(ctx.author.display_name))
                break
            else:
                await ctx.send('``{}`` fell down the conveyor belt to be sorted again!'.format(used['object']))
        else:
            if reward > 0:
                bank.deposit_credits(ctx.author, reward)
            await ctx.send(
                '{} been given **{} {}s** for your services.'.format(ctx.author.display_name, reward,
                                                                     bank.get_currency_name(ctx.guild)))
