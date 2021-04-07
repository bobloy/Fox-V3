import asyncio
import random

import discord
from redbot.core import commands
from redbot.core.commands import Cog


class RPSLS(Cog):
    """Play Rock Paper Scissors Lizard Spock."""

    weaknesses = {
        "rock": ["paper", "spock"],
        "paper": ["scissors", "lizard"],
        "scissors": ["spock", "rock"],
        "lizard": ["scissors", "rock"],
        "spock": ["paper", "lizard"],
    }

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    @commands.command()
    async def rpsls(self, ctx: commands.Context, choice: str):
        """
        Play Rock Paper Scissors Lizard Spock by Sam Kass in Discord!

        Rules:
        Scissors cuts Paper
        Paper covers Rock
        Rock crushes Lizard
        Lizard poisons Spock
        Spock smashes Scissors
        Scissors decapitates Lizard
        Lizard eats Paper
        Paper disproves Spock
        Spock vaporizes Rock
        And as it has always Rock crushes Scissors
        """

        player_choice = choice.lower()
        player_emote = self.get_emote(player_choice)
        if player_emote is None:
            await ctx.maybe_send_embed("Invalid Choice")
            return

        bot_choice = random.choice(list(self.weaknesses.keys()))
        bot_emote = self.get_emote(bot_choice)
        message = "{} vs. {}, who will win?".format(player_emote, bot_emote)
        em = discord.Embed(description=message, color=discord.Color.blue())
        await ctx.send(embed=em)
        await asyncio.sleep(2)
        if player_choice in self.weaknesses[bot_choice]:
            message = "You win! :sob:"
            em_color = discord.Color.green()
        elif bot_choice in self.weaknesses[player_choice]:
            message = "I win! :smile:"
            em_color = discord.Color.red()
        else:
            message = "It's a draw! :neutral_face:"
            em_color = discord.Color.blue()
        em = discord.Embed(description=message, color=em_color)
        await ctx.send(embed=em)

    def get_emote(self, choice):
        if choice == "rock":
            return ":moyai:"
        elif choice == "spock":
            return ":vulcan:"
        elif choice == "paper":
            return ":page_facing_up:"
        elif choice in ["scissors", "lizard"]:
            return ":{}:".format(choice)
        else:
            return None
