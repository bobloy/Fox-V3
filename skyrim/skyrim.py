from random import randrange
import discord

from redbot.core import commands
from redbot.core.data_manager import bundled_data_path


Cog = getattr(commands, "Cog", object)


class Skyrim(Cog):
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
                if randrange(num + 2):
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
