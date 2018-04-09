import asyncio
import discord

from datetime import datetime, timedelta

from random import shuffle

from werewolf.player import Player

from werewolf.builder import parse_code


class Game:
    """
    Base class to run a single game of Werewolf
    """
    
    default_secret_channel = {
                "channel": None,
                "players": [],
                "votegroup": None  # uninitialized VoteGroup
                }
    
    # def __new__(cls, guild, game_code):
        # game_code = ["DefaultWerewolf", "Villager", "Villager"]
        
        # return super().__new__(cls, guild, game_code)

    def __init__(self, guild, game_code):
        self.guild = guild
        self.game_code = ["VanillaWerewolf"]
        
        self.roles = []
        
        self.players = []
        self.day_vote = {}  # ID, votes
        
        self.started = False
        self.game_over = False
        self.can_vote = False
        self.used_votes = 0
        
        self.channel_category = None
        self.village_channel = None
                
        self.p_channels = {}  # uses default_secret_channel
        self.vote_groups = {}  # ID : VoteGroup()
        
        self.loop = asyncio.get_event_loop()

    async def setup(self, ctx):
        """
        Runs the initial setup
        
        1. Assign Roles
        2. Create Channels
        2a.  Channel Permissions :eyes:
        3. Check Initial role setup (including alerts)
        4. Start game
        """
        if self.game_code:
            await self.get_roles()

        if len(self.players) != len(self.roles):
            await ctx.send("Player count does not match role count, cannot start")
            self.roles = []
            return False
        
        await self.assign_roles()
        
        # Create category and channel with individual overwrites
        overwrite = {
                    self.guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=True),
                    self.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                    }

        self.channel_category = await self.guild.create_category("ww-game", overwrites=overwrite, reason="New game of werewolf")
        
        for player in self.players:
            overwrite[player.member] = discord.PermissionOverwrite(read_messages=True)
        
        self.village_channel = await self.guild.create_text_channel("Village Square", overwrites=overwrite, reason="New game of werewolf", category=self.channel_category)
        
        # Assuming everything worked so far
        print("Pre-game_start")
        await self._at_game_start()  # This will queue channels and votegroups to be made
        
        for channel_id in self.p_channels:
            overwrite = {
                self.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                self.guild.me: discord.PermissionOverwrite(read_messages=True)
                }
                
            for player in self.p_channels[channel_id]["players"]:
                overwrite[player.member] = discord.PermissionOverwrite(read_messages=True)
                
            channel = await self.guild.create_text_channel(channel_id, overwrites=overwrite, reason="Ww game secret channel", category=self.channel_category)
            
            self.p_channels[channel_id]["channel"] = channel
            
            if self.p_channels[channel_id]["votegroup"] is not None:
                vote_group = self.p_channels[channel_id]["votegroup"](self, channel)
                
                await vote_group.register_players([player in self.p_channels[channel_id]["players"]])
                
                self.vote_groups[channel_id] = vote_group

        print("Pre-cycle")
        await asyncio.sleep(1)
        await self._cycle() # Start the loop
        
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
    
    async def _at_game_start(self):  # ID 0
        if self.game_over:
            return
        await self.village_channel.send("Game is starting, please wait for setup to complete")
        
        await self._notify(0)

    async def _at_day_start(self):  # ID 1
        if self.game_over:
            return
        await self.village_channel.send("The sun rises on a new day in the village")
        
        await self.day_perms(self.village_channel)
        await self._notify(1)
        
        self.can_vote = True
        
        await asyncio.sleep(240)  # 4 minute days
        
        if not self.can_vote or self.game_over:
            return
            
        await self._at_day_end()
        
    async def _at_voted(self, target):  # ID 2
        if self.game_over:
            return
        data = {"player": target}
        await self._notify(2, data)
        
        self.used_votes += 1
        
        await self.all_but_perms(self.village_channel, target)
        await self.village_channel.send("{} will be put to trial and has 30 seconds to defend themselves".format(target.mention))
        
        await asyncio.sleep(30)
        
        await self.village_channel.set_permissions(target, read_messages=True)
        
        message = await self.village_channel.send("Everyone will now vote whether to lynch {}\n👍 to save, 👎 to lynch\n*Majority rules, no-lynch on ties, vote for both or neither to abstain, 15 seconds to vote*".format(target.mention))
        
        await self.village_channel.add_reaction("👍")
        await self.village_channel.add_reaction("👎")
        
        await asyncio.sleep(15)
        
        reaction_list = message.reactions
        
        up_votes = sum(p.emoji == "👍" and not p.me for p in reaction_list)
        down_votes = sum(p.emoji == "👎" and not p.me for p in reaction_list)
        
        if len(down_votes) > len(up_votes):
            embed=discord.Embed(title="Vote Results", color=0xff0000)
        else:
            embed=discord.Embed(title="Vote Results", color=0x80ff80)
        
        embed.add_field(name="👎", value="**{}**".format(len(up_votes)), inline=True)
        embed.add_field(name="👍", value="**{}**".format(len(down_votes)), inline=True)
        
        await self.village_channel.send(embed=embed)
        
        if len(down_votes) > len(up_votes):
            await self.village_channel.send("Voted to lynch {}!".format(target.mention))
            await self.kill(target)
            self.can_vote = False
        elif self.used_votes >= 3:
            self.can_vote = False
        
        if not self.can_vote:
            await self._at_day_end()
    
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
        if self.game_over:
            return

        self.can_vote = False
        await self.night_perms(self.village_channel)
        
        await self.village_channel.send("**The sun sets on the village...**")
        
        await self._notify(5)
        await asyncio.sleep(30)
        await self._at_night_start()
        
    async def _at_night_start(self):  # ID 6
        if self.game_over:
            return
        await self._notify(6)
        
        await asyncio.sleep(120)  # 2 minutes

        await asyncio.sleep(90)   # 1.5 minutes

        await asyncio.sleep(30)  # .5 minutes
        
        await self._at_night_end()
        
    async def _at_night_end(self):  # ID 7
        if self.game_over:
            return
        await self._notify(7)
        
        await asyncio.sleep(15)
        await self._at_day_start()
            
    async def _notify(self, event, data=None):
        for i in range(8):
            tasks = []
            # Role priorities
            role_order = [role for role in self.roles if role.action_list[event][1]==i]
            for role in role_order:
                tasks.append(asyncio.ensure_future(role.on_event(event, data), loop=self.loop))
            # VoteGroup priorities    
            vote_order = [vg for vg in self.vote_groups.values() if vg.action_list[event][1]==i]
            for vote_group in vote_order:
                tasks.append(asyncio.ensure_future(vote_group.on_event(event, data), loop=self.loop))
                
            await asyncio.gather(*tasks)
            # Run same-priority task simultaneously

    ############END Notify structure############

    async def generate_targets(self, channel):
        embed=discord.Embed(title="Remaining Players")
        for i in range(len(self.players)):
            player = self.players[i]
            if player.alive:
                status=""
            else:
                status="*Dead*"
            embed.add_field(name="ID# **{}**".format(i), value="{} {}".format(status, player.member.display_name), inline=True)
  
        return await channel.send(embed=embed)
    
    
    async def register_channel(self, channel_id, role, votegroup=None):
        """
        Queue a channel to be created by game_start
        """
        if channel_id not in self.p_channels:
            self.p_channels[channel_id] = self.default_secret_channel.copy()

        await asyncio.sleep(1)
        
        self.p_channels[channel_id]["players"].append(role.player)
        
        if votegroup:
            self.p_channels[channel_id]["votegroup"] = votegroup

    async def join(self, member: discord.Member, channel: discord.TextChannel):
        """
        Have a member join a game
        """
        if self.started:
            await channel.send("**Game has already started!**")
            return 
        
        if await self.get_player_by_member(member):
            await channel.send("{} is already in the game!".format(member.mention))
            return 
        
        self.players.append(Player(member))
        
        await channel.send("{} has been added to the game, total players is **{}**".format(member.mention, len(self.players)))
        
    async def quit(self, member: discord.Member, channel: discord.TextChannel = None):
        """
        Have a member quit a game
        """
        player = await self.get_player_by_member(member)
        
        if not player:
            return "You're not in a game!"

        if self.started:
            await self.kill(member)
            await channel.send("{} has left the game".format(member.mention))
        else:
            self.players = [player for player in self.players if player.member != member]
            await channel.send("{} chickened out, player count is now **{}**".format(member.mention, len(self.players)))
    
    async def vote(self, author, id, channel):
        """
        Member attempts to cast a vote (usually to lynch)
        """
        player = self._get_player(author)
        
        if player is None:
            await channel.send("You're not in this game!")
            return
            
        if not player.alive:
            await channel.send("Corpses can't vote")
            return
            
        if channel == self.village_channel:
            if not self.can_vote:
                await channel.send("Voting is not allowed right now")
                return
        elif channel not in self.p_channels.values():
            # Not part of the game
            return  # Don't say anything
            
        try:
            target = self.players[id]
        except IndexError:
            target = None
        
        if target is None:
            await channel.send("Not a valid target")
            return
            
        # Now handle village vote or send to votegroup
        
    async def kill(self, target, source=None, method: str=None):    
        """
        Attempt to kill a target
        Source allows admin override
        Be sure to remove permissions appropriately
        Important to finish execution before triggering notify
        """
        if not target.protected:
            target.alive = False
            await self._at_kill(target)
            if not target.alive:  # Still dead after notifying
                await self.dead_perms(target.member)
        else:
            target.protected = False
        
    async def lynch(self, target):    
        """
        Attempt to lynch a target
        Important to finish execution before triggering notify
        """
        target.alive = False
        await self._at_hang(target)
        if not target.alive:  # Still dead after notifying
            await self.dead_perms(target.member)
        
    async def get_roles(self, game_code=None):
        if game_code is not None:
            self.game_code=game_code
        
        if self.game_code is None:
            return False
        
        self.roles = await parse_code(self.game_code)
        
        if not self.roles:
            return False
    
    async def assign_roles(self):
        """len(self.roles) must == len(self.players)"""
        shuffle(self.roles)
        
        for idx, role in enumerate(self.roles):
            self.roles[idx] = role(self)
            await self.roles[idx].assign_player(self.players[idx])
            
    async def get_player_by_member(self, member):
        for player in self.players:
            if player.member == member:
                return player
        return False
    
    async def dead_perms(self, channel, member):
        await channel.set_permissions(member, read_messages=True, send_message=False, add_reactions=False)
        
        
    async def night_perms(self, channel):
        await channel.set_permissions(self.guild.default_role, read_messages=False, send_messages=False)
    
    async def day_perms(self, channel):
        await channel.set_permissions(self.guild.default_role, read_messages=False)
        
    async def speech_perms(self, channel, member, undo=False):
        if undo:
            await channel.set_permissions(self.guild.default_role, read_messages=False)
            await channel.set_permissions(member, read_messages=True)
        else:
            await channel.set_permissions(self.guild.default_role, read_messages=False, send_messages=False)
            await channel.set_permissions(member, read_messages=True, send_messages=True)
    
    async def normal_perms(self, channel, member_list):
        await channel.set_permissions(self.guild.default_role, read_messages=False)
        for member in member_list:
            await channel.set_permissions(member, read_messages=True)
