import asyncio

import discord

from datetime import datetime,timedelta

from random import shuffle

from .builder import parse_code

class Game:
    """
    Base class to run a single game of Werewolf
    """
    def __new__(cls, game_code):
        game_code = ["DefaultWerewolf", "Villager", "Villager""]
        return Game(game_code)

    def __init__(self, game_code):
        self.roles = []
        self.game_code = game_code
        
        if self.game_code:
            self.get_roles()
        
        self.players = []
        self.day_vote = {}  # ID, votes
        
        self.started = False
        self.game_over = False
        self.can_vote = False
        
        self.village_channel = None
        self.secret_channels = {}
        self.vote_groups = []
        
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
        if len(self.players) != self.roles:
            ctx.send("Players does not match roles, cannot start")
            return False
        
        
        
        
    async def _cycle(self):
        """
        Each event calls the next event
        
        _at_start()
        
        _at_day_start()
            _at_voted()
                _at_kill()
        _at_day_end()
        _at_night_begin()
        _at_night_end()
        
        and repeat with _at_morning_start() again
        """
        await self._at_start():
    
    async def _at_game_start(self):  # ID 0
        if self.game_over:
            return
        await self._notify(0)
        
        asyncio.sleep(60)
        await self._at_day_start()
        
    async def _at_day_start(self):  # ID 1
        if self.game_over:
            return
        await self._notify(1)
        
        self.can_vote = True
        
        asyncio.sleep(240)  # 4 minute days
        await self._at_day_end()
        
    async def _at_voted(self, target):  # ID 2
        if self.game_over:
            return
        await self._notify(2, target)
    
    async def _at_kill(self, target):  # ID 3
        if self.game_over:
            return
        await self._notify(3, target)
    
    async def _at_hang(self, target):  # ID 4
        if self.game_over:
            return
        await self._notify(4, target)
        
    async def _at_day_end(self):  # ID 5
        if self.game_over:
            return
        await self._notify(5)
        
        self.can_vote = False
        
        asyncio.sleep(30)
        await self._at_night_start()
        
    async def _at_night_start(self):  # ID 6
        if self.game_over:
            return
        await self._notify(6)
        
        asyncio.sleep(120) # 2 minutes

        asyncio.sleep(90)  # 1.5 minutes

        asyncio.sleep(30) # .5 minutes
        
        await self._at_night_end()
        
    async def _at_night_end(self):  # ID 7
        if self.game_over:
            return
        await self._notify(7)
        
        asyncio.sleep(15)
        await self._at_day_start()
            
    async def _notify(self, event, data=None):
        for i in range(10):
            tasks = []
            
            # Role priorities
            role_order = [role for role in self.roles if role.action_list[event][1]==i]
            for role in role_order:
                tasks.append(asyncio.ensure_future(role.on_event(event, data))
            # VoteGroup priorities    
            vote_order = [votes for votes in self.vote_groups if votes.action_list[event][1]==i]
            for vote_group in vote_order:
                tasks.append(asyncio.ensure_future(vote_group.on_event(event, data))
                
            # self.loop.create_task(role.on_event(event))
            self.loop.run_until_complete(asyncio.gather(*tasks))
            # Run same-priority task simultaneously
    
    async def generate_targets(self, channel):
        embed=discord.Embed(title="Remaining Players")
        for i in range(len(self.players)):
            player = self.players[i]
            if player.alive:
                status=""
            else:
                status="*Dead*"
            embed.add_field(name="ID# **{}**".format(i), value="{} {}".format(status, player.member.display_name, inline=True)
  
        return await channel.send(embed=embed)
    
    async def register_channel(self, channel_id, votegroup = None):
        
        
    
    async def join(self, member: discord.Member, channel: discord.Channel):
        """
        Have a member join a game
        """
        if self.started:
            return "**Game has already started!**"
        
        if member in self.players:
            return "{} is already in the game!".format(member.mention)
        
        self.started.append(member)
        
        channel.send("{} has been added to the game, total players is **{}**".format(member.mention, len(self.players)))
        
    async def quit(self, member: discord.Member):
        """
        Have a member quit a game
        """
        player = await self.get_player_by_member(member)
        
        if not player:
            return "You're not in a game!"

        if self.started:
            await self.kill()
        
        if member in self.players:
            return "{} is already in the game!".format(member.mention)
        
        self.started.append(member)
        
        channel.send("{} has been added to the game, total players is **{}**".format(member.mention, len(self.players)))
    
    async def vote(self, author, id, channel):
        """
        Member attempts to cast a vote (usually to lynch)
        """
        player = self._get_player(author)
        
        if player is None:
            channel.send("You're not in this game!")
            return
            
        if not player.alive:
            channel.send("Corpses can't vote")
            return
        
        if channel in self.secret_channels.values():
            
        if channel == self.village_channel:
            if not self.can_vote:
                channel.send("Voting is not allowed right now")
                return
                
        
        try:
            target = self.players[id]
        except IndexError:
            target = None
        
        if target is None:
            channel.send("Not a valid target")
            return
        
        
    
    async def get_roles(self, game_code=None):
        if game_code:
            self.game_code=game_code
        
        if not self.game_code:
            return False
        
        self.roles = await parse_code(self.game_code)
        
        if not self.roles:
            return False
    
