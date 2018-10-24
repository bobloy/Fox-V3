import asyncio

import discord
from redbot.core import Config, checks, commands
from typing import Any

Cog: Any = getattr(commands, "Cog", object)


class BanGame(Cog):
    """
    Ban anyone playing the chosen games
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=66971107197109101)
        default_guild = {"banned_games": [], "do_ban": False}

        self.config.register_guild(**default_guild)

    @commands.guild_only()
    @commands.group(aliases=["exclusiverole"])
    async def bangame(self, ctx):
        """Base command for managing exclusive roles"""

        if not ctx.invoked_subcommand:
            pass

    @bangame.command(name="toggleban")
    @checks.mod_or_permissions(administrator=True)
    async def bangame_toggleban(self, ctx):
        """Toggles kicking and banning"""

        do_ban = not self.config.guild(ctx.guild).do_ban()
        await self.config.guild(ctx.guild).do_ban.set(do_ban)

        await ctx.send(
            "Members will now be {} for playing a banned game".format(
                "Banned" if do_ban else "Kicked"
            )
        )

    @bangame.command(name="add")
    @checks.mod_or_permissions(administrator=True)
    async def bangame_add(self, ctx, game):
        """Adds a banned game"""
        if game in (await self.config.guild(ctx.guild).banned_games()):
            await ctx.send("That game is already banned")
            return

        async with self.config.guild(ctx.guild).banned_games() as bg:
            bg.append(game)

        await self.check_guild(ctx.guild)

        await ctx.send("Banned game added: {}".format(game))

    @bangame.command(name="delete")
    @checks.mod_or_permissions(administrator=True)
    async def bangame_delete(self, ctx, game):
        """Deletes a banned game"""
        if game not in (await self.config.guild(ctx.guild).banned_games()):
            await ctx.send("That game is not banned")
            return

        async with self.config.guild(ctx.guild).banned_games() as bg:
            bg.remove(game)

        await ctx.send("{} is no longer banned".format(game))

    @bangame.command(name="list")
    @checks.mod_or_permissions(administrator=True)
    async def bangame_list(self, ctx):
        """List current banned games"""
        banned_games = await self.config.guild(ctx.guild).banned_games()

        out = "**Banned Games**\n\n"

        for game in banned_games:
            out += "{}\n".format(game)

        await ctx.send(out)

    async def check_guild(self, guild: discord.Guild):
        game_set = set(await self.config.guild(guild).banned_games())
        for member in guild.members:
            try:
                await self.ban_or_kick_banned_games(member, game_set=game_set)
            except discord.Forbidden:
                pass

    async def ban_or_kick_banned_games(self, member: discord.Member, game_set=None):
        if game_set is None:
            game_set = set(await self.config.guild(member.guild).banned_games())

        if member.activity is not None and member.activity.name in game_set:
            do_ban = await self.config.guild(member.guild).do_ban()

            if do_ban:
                await member.ban(reason="Plays {}".format(member.activity.name))
            else:
                await member.kick(reason="Plays {}".format(member.activity.name))

    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.activity == after.activity:
            return

        await asyncio.sleep(1)

        game_set = set(await self.config.guild(after.guild).banned_games())

        if after.activity is not None and after.activity.name in game_set:
            try:
                await self.ban_or_kick_banned_games(after, game_set=game_set)
            except discord.Forbidden:
                pass
