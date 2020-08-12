import asyncio
import random
from typing import List, Any, Dict, Set, Union

import discord
from redbot.core import commands

from .builder import parse_code
from .player import Player
from .role import Role
from .votegroup import VoteGroup


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
        "votegroup": None  # uninitialized VoteGroup
    }

    morning_messages = [
        "**The sun rises on day {} in the village..**",
        "**Morning has arrived on day {}..**"
    ]

    day_vote_count = 3

    def __init__(self, guild: discord.Guild, role: discord.Role = None,
                 category: discord.CategoryChannel = None, village: discord.TextChannel = None,
                 log_channel: discord.TextChannel = None, game_code=None):
        self.guild = guild
        self.game_code = game_code

        self.roles = []  # List[Role]
        self.players = []  # List[Player]

        self.day_vote = {}  # author: target
        self.vote_totals = {}  # id: total_votes

        self.started = False
        self.game_over = False
        self.can_vote = False
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
            await ctx.send("Player count does not match role count, cannot start\n"
                           "Currently **{} / {}**\n"
                           "Use `{}ww code` to pick a new game"
                           "".format(len(self.players), len(self.roles), ctx.prefix))
            self.roles = []
            return False

        if self.game_role is None:
            try:
                self.game_role = await ctx.guild.create_role(name="WW Players",
                                                             hoist=True,
                                                             mentionable=True,
                                                             reason="(BOT) Werewolf game role")
                self.to_delete.add(self.game_role)
            except (discord.Forbidden, discord.HTTPException):
                await ctx.send("Game role not configured and unable to generate one, cannot start")
                self.roles = []
                return False
            try:
                for player in self.players:
                    await player.member.add_roles(*[self.game_role])
            except discord.Forbidden:
                await ctx.send(
                    "Unable to add role **{}**\nBot is missing `manage_roles` permissions".format(self.game_role.name))
                return False

        await self.assign_roles()

        # Create category and channel with individual overwrites
        overwrite = {
            self.guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False,
                                                                 add_reactions=False),
            self.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, add_reactions=True,
                                                       manage_messages=True, manage_channels=True,
                                                       manage_roles=True),
            self.game_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        if self.channel_category is None:
            self.channel_category = await self.guild.create_category("Werewolf Game",
                                                                     overwrites=overwrite,
                                                                     reason="(BOT) New game of werewolf")
        else:  # No need to modify categories
            pass
            # await self.channel_category.edit(name="🔴 Werewolf Game (ACTIVE)", reason="(BOT) New game of werewolf")
            # for target, ow in overwrite.items():
            #     await self.channel_category.set_permissions(target=target,
            #                                                 overwrite=ow,
            #                                                 reason="(BOT) New game of werewolf")
        if self.village_channel is None:
            try:
                self.village_channel = await self.guild.create_text_channel("🔵Werewolf",
                                                                            overwrites=overwrite,
                                                                            reason="(BOT) New game of werewolf",
                                                                            category=self.channel_category)
            except discord.Forbidden:
                await ctx.send("Unable to create Game Channel and none was provided\n"
                               "Grant Bot appropriate permissions or assign a game_channel")
                return False
        else:
            self.save_perms[self.village_channel] = self.village_channel.overwrites
            try:
                await self.village_channel.edit(name="🔵Werewolf",
                                                category=self.channel_category,
                                                reason="(BOT) New game of werewolf")
            except discord.Forbidden as e:
                print("Unable to rename Game Channel")
                print(e)
                await ctx.send("Unable to rename Game Channel, ignoring")

            try:
                for target, ow in overwrite.items():
                    curr = self.village_channel.overwrites_for(target)
                    curr.update(**{perm: value for perm, value in ow})
                    await self.village_channel.set_permissions(target=target,
                                                               overwrite=curr,
                                                               reason="(BOT) New game of werewolf")
            except discord.Forbidden:
                await ctx.send("Unable to edit Game Channel permissions\n"
                               "Grant Bot appropriate permissions to manage permissions")
                return
        self.started = True
        # Assuming everything worked so far
        print("Pre at_game_start")
        await self._at_game_start()  # This will queue channels and votegroups to be made
        print("Post at_game_start")
        for channel_id in self.p_channels:
            print("Channel id: " + channel_id)
            overwrite = {
                self.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                self.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, add_reactions=True,
                                                           manage_messages=True, manage_channels=True,
                                                           manage_roles=True)
            }

            for player in self.p_channels[channel_id]["players"]:
                overwrite[player.member] = discord.PermissionOverwrite(read_messages=True)

            channel = await self.guild.create_text_channel(channel_id,
                                                           overwrites=overwrite,
                                                           reason="(BOT) WW game secret channel",
                                                           category=self.channel_category)

            self.p_channels[channel_id]["channel"] = channel

            if self.p_channels[channel_id]["votegroup"] is not None:
                vote_group = self.p_channels[channel_id]["votegroup"](self, channel)

                await vote_group.register_players(*self.p_channels[channel_id]["players"])

                self.vote_groups[channel_id] = vote_group

        print("Pre-cycle")
        await asyncio.sleep(1)
        asyncio.ensure_future(self._cycle())  # Start the loop

    ############START Notify structure############
    async def _cycle(self):
        """
        Each event calls the next event
        
        

        _at_day_start()
            _at_voted()
                _at_kill()
        _at_day_end()
        _at_night_begin()
        _at_night_end()
        
        and repeat with _at_day_start() again
        """
        await self._at_day_start()
        # Once cycle ends, this will trigger end_game
        await self._end_game()  # Handle open channels

    async def _at_game_start(self):  # ID 0
        if self.game_over:
            return

        await self.village_channel.send(
            embed=discord.Embed(title="Game is starting, please wait for setup to complete"))

        await self._notify(0)

    async def _at_day_start(self):  # ID 1
        if self.game_over:
            return

        def check():
            return not self.can_vote or not self.day_time or self.game_over

        self.day_count += 1
        embed = discord.Embed(title=random.choice(self.morning_messages).format(self.day_count))
        for result in self.night_results:
            embed.add_field(name=result, value="________", inline=False)

        self.day_time = True

        self.night_results = []  # Clear for next day

        await self.village_channel.send(embed=embed)
        await self.generate_targets(self.village_channel)

        await self.day_perms(self.village_channel)
        await self._notify(1)

        await self._check_game_over()
        if self.game_over:
            return
        self.can_vote = True

        await asyncio.sleep(24)  # 4 minute days FixMe to 120 later
        if check():
            return
        await self.village_channel.send(embed=discord.Embed(title="**Two minutes of daylight remain...**"))
        await asyncio.sleep(24)  # 4 minute days FixMe to 120 later

        # Need a loop here to wait for trial to end (can_vote?)
        while self.ongoing_vote:
            asyncio.sleep(5)

        if check():
            return

        await self._at_day_end()

    async def _at_voted(self, target):  # ID 2
        if self.game_over:
            return
        data = {"player": target}
        await self._notify(2, data)

        self.ongoing_vote = True

        self.used_votes += 1

        await self.speech_perms(self.village_channel, target.member)  # Only target can talk
        await self.village_channel.send(
            "**{} will be put to trial and has 30 seconds to defend themselves**".format(target.mention))

        await asyncio.sleep(30)

        await self.speech_perms(self.village_channel, target.member, undo=True)  # No one can talk

        message = await self.village_channel.send(
            "Everyone will now vote whether to lynch {}\n"
            "👍 to save, 👎 to lynch\n"
            "*Majority rules, no-lynch on ties, "
            "vote both or neither to abstain, 15 seconds to vote*".format(target.mention))

        await message.add_reaction("👍")
        await message.add_reaction("👎")

        await asyncio.sleep(15)
        reaction_list = message.reactions

        up_votes = sum(p for p in reaction_list if p.emoji == "👍" and not p.me)
        down_votes = sum(p for p in reaction_list if p.emoji == "👎" and not p.me)

        if down_votes > up_votes:
            embed = discord.Embed(title="Vote Results", color=0xff0000)
        else:
            embed = discord.Embed(title="Vote Results", color=0x80ff80)

        embed.add_field(name="👎", value="**{}**".format(up_votes), inline=True)
        embed.add_field(name="👍", value="**{}**".format(down_votes), inline=True)

        await self.village_channel.send(embed=embed)

        if down_votes > up_votes:
            await self.village_channel.send("**Voted to lynch {}!**".format(target.mention))
            await self.lynch(target)
            self.can_vote = False
        else:
            await self.village_channel.send("**{} has been spared!**".format(target.mention))

            if self.used_votes >= self.day_vote_count:
                await self.village_channel.send("**All votes have been used! Day is now over!**")
                self.can_vote = False
            else:
                await self.village_channel.send(
                    "**{}**/**{}** of today's votes have been used!\n"
                    "Nominate carefully..".format(self.used_votes, self.day_vote_count))

        self.ongoing_vote = False

        if not self.can_vote:
            await self._at_day_end()
        else:
            await self.normal_perms(self.village_channel)  # No point if about to be night

    async def _at_kill(self, target):  # ID 3
        if self.game_over:
            return
        data = {"player": target}
        await self._notify(3, data)

    async def _at_hang(self, target):  # ID 4
        if self.game_over:
            return
        data = {"player": target}
        await self._notify(4, data)

    async def _at_day_end(self):  # ID 5
        await self._check_game_over()

        if self.game_over:
            return

        self.can_vote = False
        self.day_vote = {}
        self.vote_totals = {}
        self.day_time = False

        await self.night_perms(self.village_channel)

        await self.village_channel.send(embed=discord.Embed(title="**The sun sets on the village...**"))

        await self._notify(5)
        await asyncio.sleep(5)
        await self._at_night_start()

    async def _at_night_start(self):  # ID 6
        if self.game_over:
            return
        await self._notify(6)

        await asyncio.sleep(12)  # 2 minutes FixMe to 120 later
        await self.village_channel.send(embed=discord.Embed(title="**Two minutes of night remain...**"))
        await asyncio.sleep(9)  # 1.5 minutes FixMe to 90 later
        await self.village_channel.send(embed=discord.Embed(title="**Thirty seconds until sunrise...**"))
        await asyncio.sleep(3)  # .5 minutes FixMe to 3 Later

        await self._at_night_end()

    async def _at_night_end(self):  # ID 7
        if self.game_over:
            return
        await self._notify(7)

        await asyncio.sleep(10)
        await self._at_day_start()

    async def _at_visit(self, target, source):  # ID 8
        if self.game_over:
            return
        data = {"target": target, "source": source}
        await self._notify(8, data)

    async def _notify(self, event, data=None):
        for i in range(1, 7):  # action guide 1-6 (0 is no action)
            tasks = []
            # Role priorities
            role_order = [role for role in self.roles if role.action_list[event][1] == i]
            for role in role_order:
                tasks.append(asyncio.ensure_future(role.on_event(event, data), loop=self.loop))
            # VoteGroup priorities    
            vote_order = [vg for vg in self.vote_groups.values() if vg.action_list[event][1] == i]
            for vote_group in vote_order:
                tasks.append(asyncio.ensure_future(vote_group.on_event(event, data), loop=self.loop))
            if tasks:
                await asyncio.gather(*tasks)
            # Run same-priority task simultaneously

    ############END Notify structure############

    async def generate_targets(self, channel, with_roles=False):
        embed = discord.Embed(title="Remaining Players")
        for i in range(len(self.players)):
            player = self.players[i]
            if player.alive:
                status = ""
            else:
                status = "*[Dead]*-"
            if with_roles or not player.alive:
                embed.add_field(name="ID# **{}**".format(i),
                                value="{}{}-{}".format(status, player.member.display_name, str(player.role)),
                                inline=True)
            else:
                embed.add_field(name="ID# **{}**".format(i),
                                value="{}{}".format(status, player.member.display_name),
                                inline=True)

        return await channel.send(embed=embed)

    async def register_channel(self, channel_id, role, votegroup=None):
        """
        Queue a channel to be created by game_start
        """
        if channel_id not in self.p_channels:
            self.p_channels[channel_id] = self.default_secret_channel.copy()

        for x in range(10):  # Retry 10 times
            try:
                await asyncio.sleep(1)  # This will have multiple calls
                self.p_channels[channel_id]["players"].append(role.player)
                if votegroup is not None:
                    self.p_channels[channel_id]["votegroup"] = votegroup
            except AttributeError:
                continue
            else:
                break

    async def join(self, member: discord.Member, channel: discord.TextChannel):
        """
        Have a member join a game
        """
        if self.started:
            await channel.send("**Game has already started!**")
            return

        if await self.get_player_by_member(member) is not None:
            await channel.send("{} is already in the game!".format(member.mention))
            return

        self.players.append(Player(member))

        if self.game_role is not None:
            try:
                await member.add_roles(*[self.game_role])
            except discord.Forbidden:
                await channel.send(
                    "Unable to add role **{}**\nBot is missing `manage_roles` permissions".format(self.game_role.name))

        await channel.send("{} has been added to the game, "
                           "total players is **{}**".format(member.mention, len(self.players)))

    async def quit(self, member: discord.Member, channel: discord.TextChannel = None):
        """
        Have a member quit a game
        """
        player = await self.get_player_by_member(member)

        if player is None:
            return "You're not in a game!"

        if self.started:
            await self._quit(player)
            await channel.send("{} has left the game".format(member.mention))
        else:
            self.players = [player for player in self.players if player.member != member]
            await member.remove_roles(*[self.game_role])
            await channel.send("{} chickened out, player count is now **{}**".format(member.mention, len(self.players)))

    async def choose(self, ctx, data):
        """
        Arbitrary decision making
        Example: seer picking target to see
        """
        player = await self.get_player_by_member(ctx.author)

        if player is None:
            await ctx.send("You're not in this game!")
            return

        if not player.alive:
            await ctx.send("**Corpses** can't participate...")
            return

        if player.role.blocked:
            await ctx.send("Something is preventing you from doing this...")
            return

        # Let role do target validation, might be alternate targets
        # I.E. Go on alert? y/n

        await player.role.choose(ctx, data)

    async def _visit(self, target, source):
        await target.role.visit(source)
        await self._at_visit(target, source)

    async def visit(self, target_id, source):
        """
        Night visit target_id
        Returns a target for role information (i.e. Seer)
        """
        if source.role.blocked:
            # Blocker handles text
            return
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
            if not self.can_vote:
                await channel.send("Voting is not allowed right now")
                return
        elif channel.name in self.p_channels:
            pass
        else:
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
            await self.village_channel.send(""
                                            "{} has voted to put {} to trial. "
                                            "{} more votes needed".format(author.mention,
                                                                          target.member.mention,
                                                                          required_votes - self.vote_totals[target_id]))
        else:
            self.vote_totals[target_id] = 0
            self.day_vote = {k: v for k, v in self.day_vote.items() if v != target_id}  # Remove votes for this id
            await self._at_voted(target)

    async def eval_results(self, target, source=None, method=None):
        if method is not None:
            out = "**{ID}** - " + method
            return out.format(ID=target.id, target=target.member.display_name)
        else:
            return "**{ID}** - {target} the {role} was found dead".format(ID=target.id,
                                                                          target=target.member.display_name,
                                                                          role=await target.role.get_role())

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
        target = await self.get_day_target(target_id)
        target.alive = False
        await self._at_hang(target)
        if not target.alive:  # Still dead after notifying
            await self.dead_perms(self.village_channel, target.member)

    async def get_night_target(self, target_id, source=None):
        return self.players[target_id]  # ToDo check source

    async def get_day_target(self, target_id, source=None):
        return self.players[target_id]  # ToDo check source

    async def set_code(self, ctx: commands.Context, game_code):
        if game_code is not None:
            self.game_code = game_code
        await ctx.send("Code has been set")

    async def get_roles(self, ctx, game_code=None):
        if game_code is not None:
            self.game_code = game_code

        if self.game_code is None:
            return False

        try:
            self.roles = await parse_code(self.game_code, self)
        except ValueError as e:
            await ctx.send("Invalid Code: Code contains unknown character\n{}".format(e))
            return False
        except IndexError as e:
            await ctx.send("Invalid Code: Code references unknown role\n{}".format(e))

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

    async def get_player_by_member(self, member):
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
            await self.village_channel.send(embed=discord.Embed(title="**Everyone is dead! Game Over!**"))
            self.game_over = True
        elif len(alive_players) == 1:
            self.game_over = True
            await self._announce_winners(alive_players)
        elif len(alive_players) == 2:
            # Check 1v1 victory conditions ToDo
            self.game_over = True
            alignment1 = alive_players[0].role.alignment
            alignment2 = alive_players[1].role.alignment
            if alignment1 == alignment2:  # Same team
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
        await self._end_game()

    async def _announce_winners(self, winnerlist):
        await self.village_channel.send(self.game_role.mention)
        embed = discord.Embed(title='Game Over', description='The Following Players have won!')
        for player in winnerlist:
            embed.add_field(name=player.member.display_name, value=str(player.role), inline=True)
        embed.set_thumbnail(url='https://emojipedia-us.s3.amazonaws.com/thumbs/160/twitter/134/trophy_1f3c6.png')
        await self.village_channel.send(embed=embed)

        await self.generate_targets(self.village_channel, True)

    async def _end_game(self):
        # Remove game_role access for potential archiving for now
        reason = '(BOT) End of WW game'
        for obj in self.to_delete:
            print(obj)
            await obj.delete(reason=reason)

        try:
            await self.village_channel.edit(reason=reason, name="Werewolf")
            for target, overwrites in self.save_perms[self.village_channel]:
                await self.village_channel.set_permissions(target, overwrite=overwrites, reason=reason)
            await self.village_channel.set_permissions(self.game_role, overwrite=None, reason=reason)
        except (discord.HTTPException, discord.NotFound, discord.errors.NotFound):
            pass

        # Optional dynamic channels/categories
