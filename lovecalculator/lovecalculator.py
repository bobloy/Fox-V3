import aiohttp
import discord
from bs4 import BeautifulSoup
from redbot.core import commands
from typing import Any

Cog: Any = getattr(commands, "Cog", object)


class LoveCalculator(Cog):
    """Calculate the love percentage for two users!"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["lovecalc"])
    async def lovecalculator(
        self, ctx: commands.Context, lover: discord.Member, loved: discord.Member
    ):
        """Calculate the love percentage!"""

        x = lover.display_name
        y = loved.display_name

        url = "https://www.lovecalculator.com/love.php?name1={}&name2={}".format(
            x.replace(" ", "+"), y.replace(" ", "+")
        )
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                soup_object = BeautifulSoup(await response.text(), "html.parser")
                try:
                    description = (
                        soup_object.find("div", attrs={"class": "result__score"}).get_text().strip()
                    )
                except:
                    description = "Dr. Love is busy right now"

        try:
            z = description[:2]
            z = int(z)
            if z > 50:
                emoji = "❤"
            else:
                emoji = "💔"
            title = "Dr. Love says that the love percentage for {} and {} is:".format(x, y)
        except:
            emoji = ""
            title = "Dr. Love has left a note for you."

        description = emoji + " " + description + " " + emoji
        em = discord.Embed(title=title, description=description, color=discord.Color.red())
        await ctx.send(embed=em)
