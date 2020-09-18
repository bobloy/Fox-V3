import codecs as c

import discord
from redbot.core import commands
from redbot.core.commands import Cog


class Unicode(Cog):
    """Encode/Decode Unicode characters!"""

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    @commands.group(name="unicode", pass_context=True)
    async def unicode(self, ctx):
        """Encode/Decode a Unicode character."""
        if ctx.invoked_subcommand is None:
            pass

    @unicode.command()
    async def decode(self, ctx: commands.Context, character):
        """Decode a Unicode character."""
        try:
            data = "U+{:04X}".format(ord(character[0]))
            color = discord.Color.green()
        except ValueError:
            data = "<unknown>"
            color = discord.Color.red()
        em = discord.Embed(title=character, description=data, color=color)
        await ctx.send(embed=em)

    @unicode.command()
    async def encode(self, ctx: commands.Context, character):
        """Encode an Unicode character."""
        try:
            if character[:2] == "\\u":
                data = repr(c.decode(character, "unicode-escape"))
                data = data.strip("'")
                color = discord.Color.green()
            elif character[:2] == "U+":
                data = chr(int(character.lstrip("U+"), 16))
                color = discord.Color.green()
            else:
                data = "<unknown>"
                color = discord.Color.red()
        except ValueError:
            data = "<unknown>"
            color = discord.Color.red()
        em = discord.Embed(title=character, description=data, color=color)
        await ctx.send(embed=em)
