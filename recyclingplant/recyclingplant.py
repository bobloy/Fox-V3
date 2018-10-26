import asyncio
import json
import random
from typing import Any

from redbot.core import bank, commands
from redbot.core.data_manager import bundled_data_path

Cog: Any = getattr(commands, "Cog", object)


class RecyclingPlant(Cog):
    """
    Says a random line from Skyrim.
    """

    @commands.command()
    async def guard(self, ctx):
        """
        Says a random guard line from Skyrim.
        """
        filepath = bundled_data_path(self) / "lines.txt"
        with filepath.open() as file:
            line = next(file)
            for num, readline in enumerate(file):
                if random.randrange(num + 2):
                    continue
                line = readline
        await ctx.maybe_send_embed(line)

    @commands.command()
    async def nazeem(self, ctx):
        """
        Do you get to the Cloud District very often?

        Oh, what am I saying, of course you don't.
        """
        await ctx.maybe_send_embed(
            "Do you get to the Cloud District very often? Oh, what am I saying, of course you don't."
        )

    # """Apply for a job at the recycling plant!"""
    #
    # def __init__(self, bot):
    #     self.bot = bot
    #     self.junk = None
    #
    # def load_junk(self):
    #     junk_path = bundled_data_path(self) / "junk.json"
    #     with junk_path.open() as json_data:
    #         self.junk = json.load(json_data)
    #
    # @commands.command(aliases=["recycle"])
    # async def recyclingplant(self, ctx: commands.Context):
    #     """Apply for a job at the recycling plant!"""
    #     if self.junk is None:
    #         self.load_junk()
    #
    #     x = 0
    #     reward = 0
    #     await ctx.send(
    #         "{0} has signed up for a shift at the Recycling Plant! Type ``exit`` to terminate it early.".format(
    #             ctx.author.display_name
    #         )
    #     )
    #     while x in range(0, 10):
    #         used = random.choice(self.junk["can"])
    #         if used["action"] == "trash":
    #             opp = "recycle"
    #         else:
    #             opp = "trash"
    #         await ctx.send(
    #             "``{}``! Will {} ``trash`` it or ``recycle`` it?".format(
    #                 used["object"], ctx.author.display_name
    #             )
    #         )
    #
    #         def check(m):
    #             return m.author == ctx.author and m.channel == ctx.channel
    #
    #         try:
    #             answer = await self.bot.wait_for("message", timeout=120, check=check)
    #         except asyncio.TimeoutError:
    #             answer = None
    #
    #         if answer is None:
    #             await ctx.send(
    #                 "``{}`` fell down the conveyor belt to be sorted again!".format(used["object"])
    #             )
    #         elif answer.content.lower().strip() == used["action"]:
    #             await ctx.send(
    #                 "Congratulations! You put ``{}`` down the correct chute! (**+50**)".format(
    #                     used["object"]
    #                 )
    #             )
    #             reward = reward + 50
    #             x += 1
    #         elif answer.content.lower().strip() == opp:
    #             await ctx.send(
    #                 "{}, you little brute, you put it down the wrong chute! (**-50**)".format(
    #                     ctx.author.display_name
    #                 )
    #             )
    #             reward = reward - 50
    #         elif answer.content.lower().strip() == "exit":
    #             await ctx.send(
    #                 "{} has been relived of their duty.".format(ctx.author.display_name)
    #             )
    #             break
    #         else:
    #             await ctx.send(
    #                 "``{}`` fell down the conveyor belt to be sorted again!".format(used["object"])
    #             )
    #     else:
    #         if reward > 0:
    #             await bank.deposit_credits(ctx.author, reward)
    #         await ctx.send(
    #             "{} been given **{} {}s** for your services.".format(
    #                 ctx.author.display_name, reward, bank.get_currency_name(ctx.guild)
    #             )
    #         )
