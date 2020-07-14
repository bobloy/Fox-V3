import discord

from redbot.core import Config, checks

from redbot.core.bot import Red
from redbot.core import commands

from .builder import GameBuilder, role_from_name, role_from_alignment, role_from_category, role_from_id
from .game import Game
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
from typing import Any

Cog: Any = getattr(commands, "Cog", object)


class Werewolf(Cog):
    """
    Base to host werewolf on a guild
    """

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=87101114101119111108102, force_registration=True)
        default_global = {}
        default_guild = {
            "role_id": None,
            "category_id": None,
            "channel_id": None,
            "log_channel_id": None
        }

        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

        self.games = {}  # Active games stored here, id is per guild

    def __unload(self):
        print("Unload called")
        for game in self.games.values():
            del game

    @commands.command()
    async def buildgame(self, ctx: commands.Context):
        """
        Create game codes to run custom games.

        Pick the roles or randomized roles you want to include in a game
        """
        gb = GameBuilder()
        code = await gb.build_game(ctx)

        if code != "":
            await ctx.send("Your game code is **{}**".format(code))
        else:
            await ctx.send("No code generated")

    @checks.guildowner()
    @commands.group()
    async def wwset(self, ctx: commands.Context):
        """
        Base command to adjust settings. Check help for command list.
        """
        if ctx.invoked_subcommand is None:
            pass

    @commands.guild_only()
    @wwset.command(name="list")
    async def wwset_list(self, ctx: commands.Context):
        """
        Lists current guild settings
        """
        success, role, category, channel, log_channel = await self._get_settings(ctx)
        if not success:
            await ctx.send("Failed to get settings")
            return None

        embed = discord.Embed(title="Current Guild Settings")
        embed.add_field(name="Role", value=str(role))
        embed.add_field(name="Category", value=str(category))
        embed.add_field(name="Channel", value=str(channel))
        embed.add_field(name="Log Channel", value=str(log_channel))
        await ctx.send(embed=embed)

    @commands.guild_only()
    @wwset.command(name="role")
    async def wwset_role(self, ctx: commands.Context, role: discord.Role=None):
        """
        Assign the game role
        This role should not be manually assigned
        """
        if role is None:
            await self.config.guild(ctx.guild).role_id.set(None)
            await ctx.send("Cleared Game Role")
        else:
            await self.config.guild(ctx.guild).role_id.set(role.id)
            await ctx.send("Game Role has been set to **{}**".format(role.name))

    @commands.guild_only()
    @wwset.command(name="category")
    async def wwset_category(self, ctx: commands.Context, category_id: int=None):
        """
        Assign the channel category
        """
        if category_id is None:
            await self.config.guild(ctx.guild).category_id.set(None)
            await ctx.send("Cleared Game Channel Category")
        else:
            category = discord.utils.get(ctx.guild.categories, id=int(category_id))
            if category is None:
                await ctx.send("Category not found")
                return
            await self.config.guild(ctx.guild).category_id.set(category.id)
            await ctx.send("Game Channel Category has been set to **{}**".format(category.name))

    @commands.guild_only()
    @wwset.command(name="channel")
    async def wwset_channel(self, ctx: commands.Context, channel: discord.TextChannel=None):
        """
        Assign the village channel
        """
        if channel is None:
            await self.config.guild(ctx.guild).channel_id.set(None)
            await ctx.send("Cleared Game Channel")
        else:
            await self.config.guild(ctx.guild).channel_id.set(channel.id)
            await ctx.send("Game Channel has been set to **{}**".format(channel.mention))

    @commands.guild_only()
    @wwset.command(name="logchannel")
    async def wwset_log_channel(self, ctx: commands.Context, channel: discord.TextChannel=None):
        """
        Assign the log channel
        """
        if channel is None:
            await self.config.guild(ctx.guild).log_channel_id.set(None)
            await ctx.send("Cleared Game Log Channel")
        else:
            await self.config.guild(ctx.guild).log_channel_id.set(channel.id)
            await ctx.send("Game Log Channel has been set to **{}**".format(channel.mention))

    @commands.group()
    async def ww(self, ctx: commands.Context):
        """
        Base command for this cog. Check help for the commands list.
        """
        if ctx.invoked_subcommand is None:
            pass

    @commands.guild_only()
    @ww.command(name="new")
    async def ww_new(self, ctx: commands.Context, game_code=None):
        """
        Create and join a new game of Werewolf
        """
        game = await self._get_game(ctx, game_code)
        if not game:
            await ctx.send("Failed to start a new game")
        else:
            await ctx.send("Game is ready to join! Use `[p]ww join`")

    @commands.guild_only()
    @ww.command(name="join")
    async def ww_join(self, ctx: commands.Context):
        """
        Joins a game of Werewolf
        """

        game = await self._get_game(ctx)

        if not game:
            await ctx.send("No game to join!\nCreate a new one with `[p]ww new`")
            return

        await game.join(ctx.author, ctx.channel)

    @commands.guild_only()
    @ww.command(name="code")
    async def ww_code(self, ctx: commands.Context, code):
        """
        Adjust game code
        """

        game = await self._get_game(ctx)

        if not game:
            await ctx.send("No game to join!\nCreate a new one with `[p]ww new`")
            return

        await game.set_code(ctx, code)

    @commands.guild_only()
    @ww.command(name="quit")
    async def ww_quit(self, ctx: commands.Context):
        """
        Quit a game of Werewolf
        """

        game = await self._get_game(ctx)

        await game.quit(ctx.author, ctx.channel)

    @commands.guild_only()
    @ww.command(name="start")
    async def ww_start(self, ctx: commands.Context):
        """
        Checks number of players and attempts to start the game
        """
        game = await self._get_game(ctx)
        if not game:
            await ctx.send("No game running, cannot start")

        if not await game.setup(ctx):
            pass  # Do something?

    @commands.guild_only()
    @ww.command(name="stop")
    async def ww_stop(self, ctx: commands.Context):
        """
        Stops the current game
        """
        if ctx.guild is None:
            # Private message, can't get guild
            await ctx.send("Cannot start game from PM!")
            return
        if ctx.guild.id not in self.games or self.games[ctx.guild.id].game_over:
            await ctx.send("No game to stop")
            return

        game = await self._get_game(ctx)
        game.game_over = True
        await ctx.send("Game has been stopped")

    @commands.guild_only()
    @ww.command(name="vote")
    async def ww_vote(self, ctx: commands.Context, target_id: int):
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

    @ww.command(name="choose")
    async def ww_choose(self, ctx: commands.Context, data):
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

    @ww.group(name="search")
    async def ww_search(self, ctx: commands.Context):
        """
        Find custom roles by name, alignment, category, or ID
        """
        if ctx.invoked_subcommand is None or ctx.invoked_subcommand == self.ww_search:
            pass

    @ww_search.command(name="name")
    async def ww_search_name(self, ctx: commands.Context, *, name):
        """Search for a role by name"""
        if name is not None:
            from_name = role_from_name(name)
            if from_name:
                await menu(ctx, from_name, DEFAULT_CONTROLS)
            else:
                await ctx.send("No roles containing that name were found")

    @ww_search.command(name="alignment")
    async def ww_search_alignment(self, ctx: commands.Context, alignment: int):
        """Search for a role by alignment"""
        if alignment is not None:
            from_alignment = role_from_alignment(alignment)
            if from_alignment:
                await menu(ctx, from_alignment, DEFAULT_CONTROLS)
            else:
                await ctx.send("No roles with that alignment were found")

    @ww_search.command(name="category")
    async def ww_search_category(self, ctx: commands.Context, category: int):
        """Search for a role by category"""
        if category is not None:
            pages = role_from_category(category)
            if pages:
                await menu(ctx, pages, DEFAULT_CONTROLS)
            else:
                await ctx.send("No roles in that category were found")

    @ww_search.command(name="index")
    async def ww_search_index(self, ctx: commands.Context, idx: int):
        """Search for a role by ID"""
        if idx is not None:
            idx_embed = role_from_id(idx)
            if idx_embed is not None:
                await ctx.send(embed=idx_embed)
            else:
                await ctx.send("Role ID not found")

    async def _get_game(self, ctx: commands.Context, game_code=None):
        guild: discord.Guild = ctx.guild

        if guild is None:
            # Private message, can't get guild
            await ctx.send("Cannot start game from PM!")
            return None
        if guild.id not in self.games or self.games[guild.id].game_over:
            await ctx.send("Starting a new game...")
            success, role, category, channel, log_channel = await self._get_settings(ctx)

            if not success:
                await ctx.send("Cannot start a new game")
                return None

            self.games[guild.id] = Game(guild, role, category, channel, log_channel, game_code)

        return self.games[guild.id]

    async def _game_start(self, game):
        await game.start()

    async def _get_settings(self, ctx):
        guild = ctx.guild
        role = None
        category = None
        channel = None
        log_channel = None

        role_id = await self.config.guild(guild).role_id()
        category_id = await self.config.guild(guild).category_id()
        channel_id = await self.config.guild(guild).channel_id()
        log_channel_id = await self.config.guild(guild).log_channel_id()

        if role_id is not None:
            role = discord.utils.get(guild.roles, id=role_id)
            if role is None:
                await ctx.send("Game Role is invalid")
                return False, None, None, None, None
        if category_id is not None:
            category = discord.utils.get(guild.categories, id=category_id)
            if category is None:
                await ctx.send("Game Category is invalid")
                return False, None, None, None, None
        if channel_id is not None:
            channel = discord.utils.get(guild.text_channels, id=channel_id)
            if channel is None:
                await ctx.send("Village Channel is invalid")
                return False, None, None, None, None
        if log_channel_id is not None:
            log_channel = discord.utils.get(guild.text_channels, id=log_channel_id)
            if log_channel is None:
                await ctx.send("Log Channel is invalid")
                return False, None, None, None, None

        return True, role, category, channel, log_channel
