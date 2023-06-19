import asyncio
import logging
import random
from collections import deque
from typing import Dict, List, Union

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils import AsyncIter

from werewolf.builder import parse_code
from werewolf.constants import ALIGNMENT_NEUTRAL
from werewolf.player import Player
from werewolf.role import Role
from werewolf.votegroup import VoteGroup

log = logging.getLogger("red.fox_v3.werewolf.game")

HALF_DAY_LENGTH = 90  # FixMe: Make configurable
HALF_NIGHT_LENGTH = 60


async def anyone_has_role(
    member_list: List[discord.Member], role: discord.Role
) -> Union[None, discord.Member]:
    return await AsyncIter(member_list).find(
        lambda m: AsyncIter(m.roles).find(lambda r: r.id == role.id)
    )


class Game:
    """
    Base class to run a single game of Werewolf
    """

    vote_groups: Dict[str, VoteGroup]
    roles: List[Role]
    players: List[Player]

    default_secret_channel = {
        "channel": None,
        "players": [],
        "votegroup": None,  # uninitialized VoteGroup
    }

    day_start_messages = [
        "*The sun rises on day {} in the village..*",
        "*Morning has arrived on day {}..*",
    ]

    day_end_messages = ["*Dawn falls..*", "*The sun sets on the village*"]

    day_vote_count = 3

    def __init__(
        self,
        bot: Red,
        guild: discord.Guild,
        role: discord.Role = None,
        category: discord.CategoryChannel = None,
        village: discord.TextChannel = None,
        log_channel: discord.TextChannel = None,
        game_code=None,
    ):
        self.bot = bot
        self.guild = guild
        self.game_code = game_code

        self.roles = []  # List[Role]
        self.players = []  # List[Player]

        self.day_vote = {}  # author: target
        self.vote_totals = {}  # id: total_votes

        self.started = False
        self.game_over = False
        self.any_votes_remaining = False
        self.used_votes = 0

        self.day_time = False
        self.day_count = 0
        self.ongoing_vote = False

        self.game_role = role  # discord.Role
        self.channel_category = category  # discord.CategoryChannel
        self.village_channel = village  # discord.TextChannel
        self.log_channel = log_channel

        self.to_delete = set()
        self.save_perms = {}

        self.p_channels = {}  # uses default_secret_channel
        self.vote_groups = {}  # ID : VoteGroup()

        self.night_results = []

        self.loop = asyncio.get_event_loop()

        self.action_queue = deque()
        self.current_action = None
        self.listeners = {}

    # def __del__(self):
    #     """
    #     Cleanup channels as necessary
    #     :return:
    #     """
    #
    #     print("Delete is called")
    #
    #     self.game_over = True
    #     if self.village_channel:
    #         asyncio.ensure_future(self.village_channel.delete("Werewolf game-over"))
    #
    #     for c_data in self.p_channels.values():
    #         asyncio.ensure_future(c_data["channel"].delete("Werewolf game-over"))

    async def setup(self, ctx: commands.Context):
        """
        Runs the initial setup

        1. Assign Roles
        2. Create Channels
        2a.  Channel Permissions
        3. Check Initial role setup (including alerts)
        4. Start game
        """
        if self.game_code:
            await self.get_roles(ctx)

        if len(self.players) != len(self.roles):
            await ctx.maybe_send_embed(
                f"Player count does not match role count, cannot start\n"
                f"Currently **{len(self.players)} / {len(self.roles)}**\n"
                f"Use `{ctx.prefix}ww code` to pick a game setup\n"
                f"Use `{ctx.prefix}buildgame` to generate a new game"
            )
            self.roles = []
            return False

        # If there's no game role, make the role and delete it later in `self.to_delete`
        if self.game_role is None:
            try:
                self.game_role = await ctx.guild.create_role(
                    name="WW Players",
                    hoist=True,
                    mentionable=True,
                    reason="(BOT) Werewolf game role",
                )
                self.to_delete.add(self.game_role)
            except (discord.Forbidden, discord.HTTPException):
                await ctx.maybe_send_embed(
                    "Game role not configured and unable to generate one, cannot start"
                )
                self.roles = []
                return False

        anyone_with_role = await anyone_has_role(self.guild.members, self.game_role)
        if anyone_with_role is not None:
            await ctx.maybe_send_embed(
                f"{anyone_with_role.display_name} has the game role, "
                f"can't continue until no one has the role"
            )
            return False

        try:
            for player in self.players:
                await player.member.add_roles(*[self.game_role])
        except discord.Forbidden:
            log.exception(f"Unable to add role **{self.game_role.name}**")
            await ctx.maybe_send_embed(
                f"Unable to add role **{self.game_role.name}**\n"
                f"Bot is missing `manage_roles` permissions"
            )
            return False

        await self.assign_roles()

        # Create category and channel with individual overwrites
        overwrite = {
            self.guild.default_role: discord.PermissionOverwrite(
                read_messages=True, send_messages=False, add_reactions=False
            ),
            self.guild.me: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                add_reactions=True,
                manage_messages=True,
                manage_channels=True,
                manage_roles=True,
            ),
            self.game_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        if self.channel_category is None:
            self.channel_category = await self.guild.create_category(
                "Werewolf Game",
                overwrites=overwrite,
                reason="(BOT) New game of werewolf",
            )
        else:  # No need to modify categories
            pass
            # await self.channel_category.edit(name="🔴 Werewolf Game (ACTIVE)", reason="(BOT) New game of werewolf")
            # for target, ow in overwrite.items():
            #     await self.channel_category.set_permissions(target=target,
            #                                                 overwrite=ow,
            #                                                 reason="(BOT) New game of werewolf")
        if self.village_channel is None:
            try:
                self.village_channel = await self.guild.create_text_channel(
                    "🔵Werewolf",
                    overwrites=overwrite,
                    reason="(BOT) New game of werewolf",
                    category=self.channel_category,
                )
            except discord.Forbidden:
                await ctx.maybe_send_embed(
                    "Unable to create Game Channel and none was provided\n"
                    "Grant Bot appropriate permissions or assign a game_channel"
                )
                return False
        else:
            self.save_perms[self.village_channel] = self.village_channel.overwrites
            try:
                await self.village_channel.edit(
                    name="🔵werewolf",
                    reason="(BOT) New game of werewolf",
                )
            except discord.Forbidden as e:
                log.exception("Unable to rename Game Channel")
                await ctx.maybe_send_embed("Unable to rename Game Channel, ignoring")

            try:
                for target, ow in overwrite.items():
                    curr = self.village_channel.overwrites_for(target)
                    curr.update(**{perm: value for perm, value in ow})
                    await self.village_channel.set_permissions(
                        target=target,
                        overwrite=curr,
                        reason="(BOT) New game of werewolf",
                    )
            except discord.Forbidden:
                await ctx.maybe_send_embed(
                    "Unable to edit Game Channel permissions\n"
                    "Grant Bot appropriate permissions to manage permissions"
                )
                return
        self.started = True
        # Assuming everything worked so far
        log.debug("Pre at_game_start")
        await self._at_game_start()  # This will add votegroups to self.p_channels
        log.debug("Post at_game_start")
        log.debug(f"Private channels: {self.p_channels}")
        for channel_id in self.p_channels.keys():
            log.debug("Setup Channel id: " + channel_id)
            overwrite = {
                self.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                self.guild.me: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    add_reactions=True,
                    manage_messages=True,
                    manage_channels=True,
                    manage_roles=True,
                ),
            }

            for player in self.p_channels[channel_id]["players"]:
                overwrite[player.member] = discord.PermissionOverwrite(read_messages=True)

            channel = await self.guild.create_text_channel(
                channel_id,
                overwrites=overwrite,
                reason="(BOT) WW game secret channel",
                category=self.channel_category,
            )

            self.p_channels[channel_id]["channel"] = channel

            self.to_delete.add(channel)

            if self.p_channels[channel_id]["votegroup"] is not None:
                vote_group = self.p_channels[channel_id]["votegroup"](self, channel)

                await vote_group.register_players(*self.p_channels[channel_id]["players"])

                self.vote_groups[channel_id] = vote_group

        log.debug("Pre-cycle")
        await asyncio.sleep(0)

        asyncio.create_task(self._cycle())  # Start the loop
        return True

    # ###########START Notify structure############
    async def _cycle(self):
        """
        Each event enqueues the next event

        _at_day_start()
            _at_voted()
                _at_kill()
        _at_day_end()
        _at_night_start()
        _at_night_end()

        and repeat with _at_day_start() again
        """

        self.action_queue.append(self._at_day_start())

        while self.action_queue and not self.game_over:
            self.current_action = asyncio.create_task(self.action_queue.popleft())
            try:
                await self.current_action
            except asyncio.CancelledError:
                log.debug("Cancelled task")
        #
        # await self._at_day_start()
        # # Once cycle ends, this will trigger end_game
        await self._end_game()  # Handle open channels

    async def _at_game_start(self):  # ID 0
        if self.game_over:
            return

        await self.village_channel.send(
            embed=discord.Embed(title="Game is starting, please wait for setup to complete")
        )

        await self._notify("at_game_start")

    async def _at_day_start(self):  # ID 1
        if self.game_over:
            return

        # await self.village_channel.edit(reason="WW Night Start", name="werewolf-🌞")
        self.action_queue.append(self._at_day_end())  # Get this ready in case day is cancelled

        def check():
            return not self.any_votes_remaining or not self.day_time or self.game_over

        self.day_count += 1

        # Print the results of who died during the night
        embed = discord.Embed(title=random.choice(self.day_start_messages).format(self.day_count))
        for result in self.night_results:
            embed.add_field(name=result, value="________", inline=False)

        self.day_time = True  # True while day

        self.night_results = []  # Clear for next day

        await self.village_channel.send(embed=embed)
        await self.generate_targets(self.village_channel)  # Print remaining players for voting

        await self.day_perms(self.village_channel)
        await self._notify("at_day_start")  # Wait for day_start actions

        await self._check_game_over()
        if self.game_over:  # If game ended because of _notify
            return

        self.any_votes_remaining = True

        # Now we sleep and let the day happen. Print the remaining daylight half way through
        await asyncio.sleep(HALF_DAY_LENGTH)  # 4 minute days FixMe to 120 later
        if check():
            return
        await self.village_channel.send(
            embed=discord.Embed(title=f"*{HALF_DAY_LENGTH / 60} minutes of daylight remain...*")
        )
        await asyncio.sleep(HALF_DAY_LENGTH)  # 4 minute days FixMe to 120 later

        # Need a loop here to wait for trial to end
        while self.ongoing_vote:
            await asyncio.sleep(5)

        # Abruptly ends, assuming _day_end is next in queue

    async def _at_voted(self, target):  # ID 2
        if self.game_over:
            return

        # Notify that a target has been chosen
        await self._notify("at_voted", player=target)

        # TODO: Support pre-vote target modifying roles
        self.ongoing_vote = True

        self.used_votes += 1

        await self.speech_perms(self.village_channel, target.member)  # Only target can talk
        await self.village_channel.send(
            f"*{target.mention} will be put to trial and has 30 seconds to defend themselves**",
            allowed_mentions=discord.AllowedMentions(everyone=False, users=[target]),
        )

        await asyncio.sleep(30)

        await self.speech_perms(self.village_channel, target.member, undo=True)  # No one can talk

        vote_message: discord.Message = await self.village_channel.send(
            f"Everyone will now vote whether to lynch {target.mention}\n"
            "👍 to save, 👎 to lynch\n"
            "*Majority rules, no-lynch on ties, "
            "vote both or neither to abstain, 15 seconds to vote*",
            allowed_mentions=discord.AllowedMentions(everyone=False, users=[target]),
        )

        await vote_message.add_reaction("👍")
        await vote_message.add_reaction("👎")

        await asyncio.sleep(15)

        # Refetch for reactions
        vote_message = await self.village_channel.fetch_message(id=vote_message.id)
        reaction_list = vote_message.reactions

        log.debug(f"Vote results: {[p.emoji.__repr__() for p in reaction_list]}")
        raw_up_votes = sum(p for p in reaction_list if p.emoji == "👍" and not p.me)
        raw_down_votes = sum(p for p in reaction_list if p.emoji == "👎" and not p.me)

        if True:  # TODO: Allow customizable vote history deletion.
            await vote_message.delete()

        # TODO: Support vote count modifying roles. (Need notify and count function)
        voted_to_lynch = raw_down_votes > raw_up_votes

        if voted_to_lynch:
            embed = discord.Embed(
                title="Vote Results",
                description=f"**Voted to lynch {target.mention}!**",
                color=0xFF0000,
            )
        else:
            embed = discord.Embed(
                title="Vote Results",
                description=f"**{target.mention} has been spared!**",
                color=0x80FF80,
            )

        embed.add_field(name="👎", value=f"**{raw_up_votes}**", inline=True)
        embed.add_field(name="👍", value=f"**{raw_down_votes}**", inline=True)

        await self.village_channel.send(embed=embed)

        if voted_to_lynch:
            await self.lynch(target)
            self.any_votes_remaining = False
        else:
            if self.used_votes >= self.day_vote_count:
                await self.village_channel.send("**All votes have been used! Day is now over!**")
                self.any_votes_remaining = False
            else:
                await self.village_channel.send(
                    f"**{self.used_votes}**/**{self.day_vote_count}** of today's votes have been used!\n"
                    "Nominate carefully.."
                )

        self.ongoing_vote = False

        if not self.any_votes_remaining and self.day_time:
            self.current_action.cancel()
        else:
            await self.normal_perms(self.village_channel)  # No point if about to be night

    async def _at_kill(self, target):  # ID 3
        if self.game_over:
            return
        await self._notify("at_kill", player=target)

    async def _at_hang(self, target):  # ID 4
        if self.game_over:
            return
        await self._notify("at_hang", player=target)

    async def _at_day_end(self):  # ID 5
        await self._check_game_over()

        if self.game_over:
            return

        self.any_votes_remaining = False
        self.day_vote = {}
        self.vote_totals = {}
        self.day_time = False

        await self.night_perms(self.village_channel)

        await self.village_channel.send(
            embed=discord.Embed(title=random.choice(self.day_end_messages))
        )

        await self._notify("at_day_end")
        await asyncio.sleep(5)
        self.action_queue.append(self._at_night_start())

    async def _at_night_start(self):  # ID 6
        if self.game_over:
            return

        # await self.village_channel.edit(reason="WW Night Start", name="werewolf-🌑")

        await self._notify("at_night_start")

        await asyncio.sleep(HALF_NIGHT_LENGTH)  # 2 minutes FixMe to 120 later
        await self.village_channel.send(
            embed=discord.Embed(title=f"**{HALF_NIGHT_LENGTH / 60} minutes of night remain...**")
        )
        await asyncio.sleep(HALF_NIGHT_LENGTH)  # 1.5 minutes FixMe to 90 later

        await asyncio.sleep(3)  # .5 minutes FixMe to 30 Later

        self.action_queue.append(self._at_night_end())

    async def _at_night_end(self):  # ID 7
        if self.game_over:
            return
        await self._notify("at_night_end")

        await asyncio.sleep(10)
        self.action_queue.append(self._at_day_start())

    async def _at_visit(self, target, source):  # ID 8
        if self.game_over:
            return
        await self._notify("at_visit", target=target, source=source)

    async def _notify(self, event_name, **kwargs):
        for i in range(1, 7):  # action guide 1-6 (0 is no action)
            tasks = [
                asyncio.create_task(event(**kwargs))
                for event in self.listeners.get(event_name, {}).get(i, [])
            ]

            # Run same-priority task simultaneously
            await asyncio.gather(*tasks)

            # self.bot.dispatch(f"red.fox.werewolf.{event}", data=data, priority=i)
            # self.bot.extra_events
            # tasks = []
            # # Role priorities
            # role_order = [role for role in self.roles if role.action_list[event][1] == i]
            # for role in role_order:
            #     tasks.append(asyncio.ensure_future(role.on_event(event, data), loop=self.loop))
            # # VoteGroup priorities
            # vote_order = [vg for vg in self.vote_groups.values() if vg.action_list[event][1] == i]
            # for vote_group in vote_order:
            #     tasks.append(
            #         asyncio.ensure_future(vote_group.on_event(event, data), loop=self.loop)
            #     )
            # if tasks:
            #     await asyncio.gather(*tasks)
            # Run same-priority task simultaneously

    # ###########END Notify structure############

    async def generate_targets(self, channel, with_roles=False):
        embed = discord.Embed(title="Remaining Players", description="[ID] - [Name]")
        for i, player in enumerate(self.players):
            status = "" if player.alive else "*[Dead]*-"
            if with_roles or not player.alive:
                embed.add_field(
                    name=f"{i} - {status}{player.member.display_name}",
                    value=f"{player.role}",
                    inline=False,
                )
            else:
                embed.add_field(
                    name=f"{i} - {status}{player.member.display_name}",
                    inline=False,
                    value="____",
                )

        return await channel.send(embed=embed)

    async def register_channel(self, channel_id, role, votegroup=None):
        """
        Queue a channel to be created by game_start
        """
        if channel_id not in self.p_channels:
            self.p_channels[channel_id] = self.default_secret_channel.copy()

        for _ in range(10):  # Retry 10 times
            try:
                await asyncio.sleep(1)  # This will have multiple calls
                self.p_channels[channel_id]["players"].append(role.player)
            except AttributeError:
                continue
            else:
                break

        if votegroup is not None:
            self.p_channels[channel_id]["votegroup"] = votegroup

    async def join(self, ctx, member: discord.Member):
        """
        Have a member join a game
        """
        if self.started:
            await ctx.maybe_send_embed("Game has already started!")
            return

        if member.bot:
            await ctx.maybe_send_embed("Bots can't play games")
            return

        if await self.get_player_by_member(member) is not None:
            await ctx.maybe_send_embed(f"{member.display_name} is already in the game!")
            return

        self.players.append(Player(member))

        # Add the role during setup, not before
        # if self.game_role is not None:
        #     try:
        #         await member.add_roles(*[self.game_role])
        #     except discord.Forbidden:
        #         await channel.send(
        #             f"Unable to add role **{self.game_role.name}**\n"
        #             f"Bot is missing `manage_roles` permissions"
        #         )

        await ctx.maybe_send_embed(
            f"{member.display_name} has been added to the game, "
            f"total players is **{len(self.players)}**"
        )

    async def quit(self, member: discord.Member, channel: discord.TextChannel = None):
        """
        Have a member quit a game
        """
        player = await self.get_player_by_member(member)

        if player is None:
            return "You're not in a game!"

        if self.started:
            await self._quit(player)
            await channel.send(
                f"{member.mention} has left the game",
                allowed_mentions=discord.AllowedMentions(everyone=False, users=[member]),
            )
        else:
            self.players = [player for player in self.players if player.member != member]
            await member.remove_roles(*[self.game_role])
            await channel.send(
                f"{member.mention} chickened out, player count is now **{len(self.players)}**",
                allowed_mentions=discord.AllowedMentions(everyone=False, users=[member]),
            )

    async def choose(self, ctx, data):
        """
        Arbitrary decision making
        Example: seer picking target to see
        """
        player = await self.get_player_by_member(ctx.author)

        if player is None:
            await ctx.maybe_send_embed("You're not in this game!")
            return

        if not player.alive:
            await ctx.maybe_send_embed("**Corpses** can't participate...")
            return

        if player.role.blocked:
            await ctx.maybe_send_embed("Something is preventing you from doing this...")
            return

        # Let role do target validation, might be alternate targets
        # I.E. Go on alert? y/n

        await player.role.choose(ctx, data)

    async def _visit(self, target, source):
        await target.role.visit(source)
        await self._at_visit(target, source)

    async def visit(self, target_id, source) -> Union[Player, None]:
        """
        Night visit target_id
        Returns a target for role information (i.e. Seer)
        """
        if source.role.blocked:
            # Blocker handles text
            return None
        target = await self.get_night_target(target_id, source)
        await self._visit(target, source)
        return target

    async def vote(self, author, target_id, channel):
        """
        Member attempts to cast a vote (usually to lynch)
        Also used in vote groups
        """
        player = await self.get_player_by_member(author)

        if player is None:
            await channel.send("You're not in this game!")
            return

        if not player.alive:
            await channel.send("Corpses can't vote...")
            return

        if channel == self.village_channel:
            if not self.any_votes_remaining:
                await channel.send("Voting is not allowed right now")
                return
        elif channel.name not in self.p_channels:
            # Not part of the game
            await channel.send("Cannot vote in this channel")
            return

        try:
            target = self.players[target_id]
        except IndexError:
            target = None

        if target is None:
            await channel.send("Not a valid ID")
            return

        # Now handle village vote or send to votegroup
        if channel == self.village_channel:
            await self._village_vote(target, author, target_id)
        elif self.p_channels[channel.name]["votegroup"] is not None:
            await self.vote_groups[channel.name].vote(target, author, target_id)
        else:  # Somehow previous check failed
            await channel.send("Cannot vote in this channel")
            return

    async def _village_vote(self, target, author, target_id):
        if author in self.day_vote:
            self.vote_totals[self.day_vote[author]] -= 1

        self.day_vote[author] = target_id
        if target_id not in self.vote_totals:
            self.vote_totals[target_id] = 1
        else:
            self.vote_totals[target_id] += 1

        required_votes = len([player for player in self.players if player.alive]) // 7 + 2

        if self.vote_totals[target_id] < required_votes:
            await self.village_channel.send(
                f"{author.mention} has voted to put {target.member.mention} to trial. "
                f"{required_votes - self.vote_totals[target_id]} more votes needed",
                allowed_mentions=discord.AllowedMentions(everyone=False, users=[author, target]),
            )
        else:
            self.vote_totals[target_id] = 0
            self.day_vote = {
                k: v for k, v in self.day_vote.items() if v != target_id
            }  # Remove votes for this id
            await self._at_voted(target)

    async def eval_results(self, target, source=None, method=None):
        if method is None:
            return "**{ID}** - {target} the {role} was found dead".format(
                ID=target.id,
                target=target.member.display_name,
                role=await target.role.get_role(),
            )

        out = "**{ID}** - " + method
        return out.format(ID=target.id, target=target.member.display_name)

    async def _quit(self, player):
        """
        Have player quit the game
        """

        player.alive = False
        await self._at_kill(player)
        player.alive = False  # Do not allow resurrection
        await self.dead_perms(self.village_channel, player.member)
        # Add a punishment system for quitting games later

    async def kill(self, target_id, source=None, method: str = None, novisit=False):
        """
        Attempt to kill a target
        Source allows admin override
        Be sure to remove permissions appropriately
        Important to finish execution before triggering notify
        """

        if source is None:
            target = self.players[target_id]
        elif self.day_time:
            target = await self.get_day_target(target_id, source)
        else:
            target = await self.get_night_target(target_id, source)

        if source is not None:
            if source.role.blocked:
                # Do nothing if blocked, blocker handles text
                return

            if not novisit:
                # Arsonist wouldn't visit before killing
                await self._visit(target, source)  # Visit before killing

        if not target.protected:
            target.alive = False  # Set them as dead first
            await target.role.kill(source)  # Notify target that someone is trying to kill them
            await self._at_kill(target)  # Notify other roles of the kill attempt
            if not target.alive:  # Still dead after notifying
                if not self.day_time:
                    self.night_results.append(await self.eval_results(target, source, method))
                await self.dead_perms(self.village_channel, target.member)
        else:
            target.protected = False

    async def lynch(self, target_id):
        """
        Attempt to lynch a target
        Important to finish execution before triggering notify
        """
        target = await self.get_day_target(target_id)  # Allows target modification
        target.alive = False  # Kill them,
        await self._at_hang(target)
        if not target.alive:  # Still dead after notifying
            await self.dead_perms(self.village_channel, target.member)

    async def get_night_target(self, target_id, source=None) -> Player:
        return self.players[target_id]  # ToDo check source

    async def get_day_target(self, target_id, source=None) -> Player:
        return self.players[target_id]  # ToDo check source

    async def set_code(self, ctx: commands.Context, game_code):
        if game_code is not None:
            self.game_code = game_code
        await ctx.maybe_send_embed("Code has been set")

    async def get_roles(self, ctx, game_code=None):
        if game_code is not None:
            self.game_code = game_code

        if self.game_code is None:
            return False

        try:
            self.roles = await parse_code(self.game_code, self)
        except ValueError as e:
            await ctx.maybe_send_embed(
                "Invalid Code: Code contains unknown character\n{}".format(e)
            )
            return False
        except IndexError as e:
            await ctx.maybe_send_embed("Invalid Code: Code references unknown role\n{}".format(e))

        if not self.roles:
            return False

    async def assign_roles(self):
        """len(self.roles) must == len(self.players)"""
        random.shuffle(self.roles)
        self.players.sort(key=lambda pl: pl.member.display_name.lower())

        if len(self.roles) != len(self.players):
            await self.village_channel.send("Unhandled error - roles!=players")
            return False

        for idx, role in enumerate(self.roles):
            await self.roles[idx].assign_player(self.players[idx])
            # Sorted players, now assign id's
            await self.players[idx].assign_id(idx)

    async def get_player_by_member(self, member: discord.Member):
        for player in self.players:
            if player.member == member:
                return player
        return None

    async def dead_perms(self, channel, member):
        await channel.set_permissions(member, overwrite=None)
        await member.remove_roles(*[self.game_role])

    async def night_perms(self, channel):
        await channel.set_permissions(self.game_role, read_messages=True, send_messages=False)

    async def day_perms(self, channel):
        await channel.set_permissions(self.game_role, read_messages=True, send_messages=True)

    async def speech_perms(self, channel, member, undo=False):
        if undo:
            await channel.set_permissions(member, overwrite=None)
        else:
            await channel.set_permissions(self.game_role, read_messages=True, send_messages=False)
            await channel.set_permissions(member, send_messages=True)

    async def normal_perms(self, channel):
        await channel.set_permissions(self.game_role, read_messages=True, send_messages=True)

    async def _check_game_over(self):
        # return  # ToDo: re-enable game-over checking
        alive_players = [player for player in self.players if player.alive]

        if len(alive_players) <= 0:
            await self.village_channel.send(
                embed=discord.Embed(title="**Everyone is dead! Game Over!**")
            )
            self.game_over = True
        elif len(alive_players) == 1:
            self.game_over = True
            await self._announce_winners(alive_players)
        elif len(alive_players) == 2:
            # Check 1v1 victory conditions ToDo
            self.game_over = True
            alignment1 = alive_players[0].role.alignment
            alignment2 = alive_players[1].role.alignment
            # Same team and not neutral
            if alignment1 == alignment2 and alignment1 != ALIGNMENT_NEUTRAL:
                winners = alive_players
            else:
                winners = [max(alive_players, key=lambda p: p.role.alignment)]

            await self._announce_winners(winners)
        else:
            # Check if everyone is on the same team
            alignment = alive_players[0].role.alignment  # Get first allignment and compare to rest
            for player in alive_players:
                if player.role.alignment != alignment:
                    return

            # Only remaining team wins
            self.game_over = True
            await self._announce_winners(alive_players)

        # If no return, cleanup and end game
        # await self._end_game()

    async def _announce_winners(self, winnerlist):
        await self.village_channel.send(self.game_role.mention)
        embed = discord.Embed(title="Game Over", description="The Following Players have won!")
        for player in winnerlist:
            embed.add_field(name=player.member.display_name, value=str(player.role), inline=True)
        embed.set_thumbnail(
            url="https://emojipedia-us.s3.amazonaws.com/thumbs/160/twitter/134/trophy_1f3c6.png"
        )
        await self.village_channel.send(embed=embed)

        await self.generate_targets(self.village_channel, True)

    async def _end_game(self):
        # Remove game_role access for potential archiving for now
        reason = "(BOT) End of WW game"
        for obj in self.to_delete:
            log.debug(f"End_game: Deleting object {obj.__repr__()}")
            try:
                await obj.delete(reason=reason)
            except discord.NotFound:
                # Already deleted
                pass

        try:
            asyncio.create_task(self.village_channel.edit(reason=reason, name="werewolf"))
            async for channel, overwrites in AsyncIter(self.save_perms.items()):
                async for target, overwrite in AsyncIter(overwrites.items()):
                    await channel.set_permissions(target, overwrite=overwrite, reason=reason)
            # for target, overwrites in self.save_perms[self.village_channel]:
            #     await self.village_channel.set_permissions(
            #         target, overwrite=overwrites, reason=reason
            #     )
            await self.village_channel.set_permissions(
                self.game_role, overwrite=None, reason=reason
            )
        except (discord.HTTPException, discord.NotFound, discord.errors.NotFound):
            pass

        for player in self.players:
            try:
                await player.member.remove_roles(*[self.game_role])
            except discord.Forbidden:
                log.exception(f"Unable to add remove **{self.game_role.name}**")
                # await ctx.send(
                #     f"Unable to add role **{self.game_role.name}**\n"
                #     f"Bot is missing `manage_roles` permissions"
                # )
                pass

        # Optional dynamic channels/categories

    def add_ww_listener(self, func, priority=0, name=None):
        """Adds a listener from the pool of listeners.

        Parameters
        -----------
        func: :ref:`coroutine <coroutine>`
            The function to call.
        priority: Optional[:class:`int`]
            Priority of the listener. Defaults to 0 (no-action)
        name: Optional[:class:`str`]
            The name of the event to listen for. Defaults to ``func.__name__``.
        do_sort: Optional[:class:`bool`]
            Whether or not to sort listeners after. Skip sorting during mass appending

        """
        name = func.__name__ if name is None else name

        if not asyncio.iscoroutinefunction(func):
            raise TypeError("Listeners must be coroutines")

        if name in self.listeners:
            if priority in self.listeners[name]:
                self.listeners[name][priority].append(func)
            else:
                self.listeners[name][priority] = [func]
        else:
            self.listeners[name] = {priority: [func]}

        # self.listeners[name].sort(reverse=True)

    # def remove_wolf_listener(self, func, name=None):
    #     """Removes a listener from the pool of listeners.
    #
    #     Parameters
    #     -----------
    #     func
    #         The function that was used as a listener to remove.
    #     name: :class:`str`
    #         The name of the event we want to remove. Defaults to
    #         ``func.__name__``.
    #     """
    #
    #     name = func.__name__ if name is None else name
    #
    #     if name in self.listeners:
    #         try:
    #             self.listeners[name].remove(func)
    #         except ValueError:
    #             pass
