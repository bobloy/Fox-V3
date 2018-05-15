import codecs as c

import discord
from discord.ext import commands


class Unicode:
    """Encode/Decode Unicode characters!"""

    def __init__(self, bot):
        self.bot = bot

    @commands.group(name='unicode', pass_context=True)
    async def unicode(self, context):
        """Encode/Decode a Unicode character."""
        if context.invoked_subcommand is None:
            await self.bot.send_cmd_help(context)

    @unicode.command()
    async def decode(self, character):
        """Decode a Unicode character."""
        try:
            data = 'U+{:04X}'.format(ord(character[0]))
            color = discord.Color.green()
        except ValueError:
            data = '<unknown>'
            color = discord.Color.red()
        em = discord.Embed(title=character, description=data, color=color)
        await self.bot.say(embed=em)

    @unicode.command()
    async def encode(self, character):
        """Encode an Unicode character."""
        try:
            if character[:2] == '\\u':
                data = repr(c.decode(character, 'unicode-escape'))
                data = data.strip("'")
                color = discord.Color.green()
            elif character[:2] == 'U+':
                data = chr(int(character.lstrip('U+'), 16))
                color = discord.Color.green()
            else:
                data = '<unknown>'
                color = discord.Color.red()
        except ValueError:
            data = '<unknown>'
            color = discord.Color.red()
        em = discord.Embed(title=character, description=data, color=color)
        await self.bot.say(embed=em)


def setup(bot):
    bot.add_cog(Unicode(bot))
