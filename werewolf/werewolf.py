import discord
from discord.ext import commands
from redbot.core import Config
from redbot.core import RedContext
from redbot.core.bot import Red

from werewolf.builder import GameBuilder
from werewolf.game import Game


class Werewolf:
    """
    Base to host werewolf on a guild
    """

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=87101114101119111108102, force_registration=True)
        default_global = {}
        default_guild = {
            "role_id": None
        }

        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

        self.games = {}  # Active games stored here, id is per guild

    def __unload(self):
        print("Unload called")
        for game in self.games.values():
            del game

    @commands.command()
    async def buildgame(self, ctx):
        gb = GameBuilder()
        code = await gb.build_game(ctx)

        if code is not None:
            await ctx.send("Your game code is **{}**".format(code))
        else:
            await ctx.send("No code generated")

    @commands.group()
    async def wwset(self, ctx: RedContext):
        """
        Base command to adjust settings. Check help for command list.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @commands.guild_only()
    @wwset.command(name="role")
    async def wwset_role(self, ctx, role: discord.Role):
        """
        Assign the game role
        This role should not be manually assigned
        """
        await self.config.guild(ctx.guild).role_id.set(role.id)
        await ctx.send("Game role has been set to **{}**".format(role.name))

    @commands.group()
    async def ww(self, ctx: RedContext):
        """
        Base command for this cog. Check help for the commands list.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @commands.guild_only()
    @ww.command()
    async def new(self, ctx, game_code=None):
        """
        Create and join a new game of Werewolf
        """
        game = await self._get_game(ctx, game_code)
        if not game:
            await ctx.send("Failed to start a new game")
        else:
            await ctx.send("Game is ready to join! Use `[p]ww join`")

    @commands.guild_only()
    @ww.command()
    async def join(self, ctx):
        """
        Joins a game of Werewolf
        """

        game = await self._get_game(ctx)

        if not game:
            await ctx.send("No game to join!\nCreate a new one with `[p]ww new`")
            return

        await game.join(ctx.author, ctx.channel)

    @commands.guild_only()
    @ww.command()
    async def quit(self, ctx):
        """
        Quit a game of Werewolf
        """

        game = await self._get_game(ctx)

        await game.quit(ctx.author, ctx.channel)

    @commands.guild_only()
    @ww.command()
    async def start(self, ctx):
        """
        Checks number of players and attempts to start the game
        """
        game = await self._get_game(ctx)
        if not game:
            await ctx.send("No game running, cannot start")

        await game.setup(ctx)

    @commands.guild_only()
    @ww.command()
    async def stop(self, ctx):
        """
        Stops the current game
        """
        game = await self._get_game(ctx)
        if not game:
            await ctx.send("No game running, cannot stop")

        game.game_over = True

    @commands.guild_only()
    @ww.command()
    async def vote(self, ctx, target_id: int):
        """
        Vote for a player by ID
        """
        try:
            target_id = int(target_id)
        except ValueError:
            target_id = None

        if target_id is None:
            await ctx.send("`id` must be an integer")
            return

        # if ctx.guild is None:
        #     # DM nonsense, find their game
        #     # If multiple games, panic
        #     for game in self.games.values():
        #         if await game.get_player_by_member(ctx.author):
        #             break #game = game
        #     else:
        #         await ctx.send("You're not part of any werewolf game")
        #         return
        # else:

        game = await self._get_game(ctx)

        if game is None:
            await ctx.send("No game running, cannot vote")
            return

        # Game handles response now
        channel = ctx.channel
        if channel == game.village_channel:
            await game.vote(ctx.author, target_id, channel)
        elif channel in (c["channel"] for c in game.p_channels.values()):
            await game.vote(ctx.author, target_id, channel)
        else:
            await ctx.send("Nothing to vote for in this channel")

    @ww.command()
    async def choose(self, ctx, data):
        """
        Arbitrary decision making
        Handled by game+role
        Can be received by DM
        """

        if ctx.guild is not None:
            await ctx.send("This action is only available in DM's")
            return

        # DM nonsense, find their game
        # If multiple games, panic
        for game in self.games.values():
            if await game.get_player_by_member(ctx.author):
                break  # game = game
        else:
            await ctx.send("You're not part of any werewolf game")
            return

        await game.choose(ctx, data)

    async def _get_game(self, ctx: RedContext, game_code=None):
        if ctx.guild is None:
            # Private message, can't get guild
            ctx.send("Cannot start game from PM!")
            return None
        if ctx.guild.id not in self.games or self.games[ctx.guild.id].game_over:
            await ctx.send("Starting a new game...")
            role_id = await self.config.guild(ctx.guild).role_id()
            role = discord.utils.get(ctx.guild.roles, id=role_id)
            if role is None:
                ctx.send("Game role is invalid, cannot start new game")
                return None
            self.games[ctx.guild.id] = Game(ctx.guild, role, game_code)

        return self.games[ctx.guild.id]

    async def _game_start(self, game):
        await game.start()
