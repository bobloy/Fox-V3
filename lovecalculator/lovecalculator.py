import logging

import aiohttp
import discord
from bs4 import BeautifulSoup
from redbot.core import commands
from redbot.core.commands import Cog

log = logging.getLogger("red.fox_v3.chatter")


class LoveCalculator(Cog):
    """Calculate the love percentage for two users!"""

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

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
        async with aiohttp.ClientSession(headers={"Connection": "keep-alive"}) as session:
            async with session.get(url, ssl=False) as response:
                assert response.status == 200
                resp = await response.text()

        log.debug(f"{resp=}")
        soup_object = BeautifulSoup(resp, "html.parser")

        description = soup_object.find("div", class_="result__score")

        if description is None:
            description = "Dr. Love is busy right now"
        else:
            description = description.get_text().strip()

        result_image = soup_object.find("img", class_="result__image").get("src")

        result_text = soup_object.find("div", class_="result-text")
        if result_text is None:
            result_text = f"{x} and {y} aren't compatible 😔"
        else:
            result_text = result_text.get_text()
        result_text = " ".join(result_text.split())

        try:
            z = description[:2]
            z = int(z)
            if z > 50:
                emoji = "❤"
            else:
                emoji = "💔"
            title = f"Dr. Love says that the love percentage for {x} and {y} is: {emoji} {description} {emoji}"
        except (TypeError, ValueError):
            title = "Dr. Love has left a note for you."

        em = discord.Embed(
            title=title, description=result_text, color=discord.Color.red(), url=url
        )
        em.set_image(url=f"https://www.lovecalculator.com/{result_image}")
        await ctx.send(embed=em)
