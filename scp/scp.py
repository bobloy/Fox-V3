import discord
from redbot.core import commands
from typing import Any

Cog: Any = getattr(commands, "Cog", object)


class SCP(Cog):
    """Look up SCP articles. Warning: Some of them may be too creepy or gruesome."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def scp(self, ctx: commands.Context, num: int):
        """Look up SCP articles.

        Warning: Some of them may be too creepy or gruesome.
        Reminder: You must specify a number between 1 and 4999.
        """

        # Thanks Shigbeard and Redjumpman for helping me!

        if 0 < num <= 4999:
            msg = "http://www.scp-wiki.net/scp-{:03}".format(num)
            c = discord.Color.green()
        else:
            msg = "You must specify a number between 1 and 4999."
            c = discord.Color.red()

        if await ctx.embed_requested():
            await ctx.send(embed=discord.Embed(description=msg, color=c))
        else:
            await ctx.maybe_send_embed(msg)

    @commands.command()
    async def scpj(self, ctx: commands.Context, joke: str):
        """Look up SCP-Js.

        Reminder: Enter the correct name or else the resultant page will be invalid.
        Use 001, etc. in case of numbers less than 100.
        """

        msg = "http://www.scp-wiki.net/scp-{}-j".format(joke)
        await ctx.maybe_send_embed(msg)

    @commands.command()
    async def scparc(self, ctx: commands.Context, num: int):
        """Look up SCP archives.

        Warning: Some of them may be too creepy or gruesome."""
        valid_archive = (
            13,
            48,
            51,
            89,
            91,
            112,
            132,
            138,
            157,
            186,
            232,
            234,
            244,
            252,
            257,
            338,
            356,
            361,
            400,
            406,
            503,
            515,
            517,
            578,
            728,
            744,
            776,
            784,
            837,
            922,
            987,
            1023,
        )
        if num in valid_archive:
            msg = "http://www.scp-wiki.net/scp-{:03}-arc".format(num)
            c = discord.Color.green()
            em = discord.Embed(description=msg, color=c)
        else:
            ttl = "You must specify a valid archive number."
            msg = "{}".format(valid_archive)
            c = discord.Color.red()

            em = discord.Embed(title=ttl, description=msg, color=c)

        if await ctx.embed_requested():
            await ctx.send(embed=em)
        else:
            await ctx.maybe_send_embed(msg)

    @commands.command()
    async def scpex(self, ctx: commands.Context, num: int):
        """Look up explained SCP articles.

        Warning: Some of them may be too creepy or gruesome.
        """

        valid_archive = (711, 920, 1841, 1851, 1974, 2600, 4023, 8900)
        if num in valid_archive:
            msg = "http://www.scp-wiki.net/scp-{:03}-ex".format(num)
            c = discord.Color.green()
            em = discord.Embed(description=msg, color=c)
        else:
            ttl = "You must specify a valid archive number."
            msg = "{}".format(valid_archive)
            c = discord.Color.red()

            em = discord.Embed(title=ttl, description=msg, color=c)

        if await ctx.embed_requested():
            await ctx.send(embed=em)
        else:
            await ctx.maybe_send_embed(msg)

    @commands.command()
    async def anomalousitems(self, ctx: commands.Context):
        """Look through the log of anomalous items."""

        msg = "http://www.scp-wiki.net/log-of-anomalous-items"
        await ctx.maybe_send_embed(msg)

    @commands.command()
    async def extranormalevents(self, ctx: commands.Context):
        """Look through the log of extranormal events."""

        msg = "http://www.scp-wiki.net/log-of-extranormal-events"
        await ctx.maybe_send_embed(msg)

    @commands.command()
    async def unexplainedlocations(self, ctx: commands.Context):
        """Look through the log of unexplained locations."""

        msg = "http://www.scp-wiki.net/log-of-unexplained-locations"
        await ctx.maybe_send_embed(msg)


def setup(bot):
    bot.add_cog(SCP(bot))
