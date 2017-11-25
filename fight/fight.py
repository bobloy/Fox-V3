import os
import math

from typing import Union

import discord
from discord.ext import commands

from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.chat_formatting import box
from redbot.core import Config
from redbot.core import checks

from random import randint


# 0 - Robin, 1 - Single, 2 - Double, 3 - Triple, 4 - Guarentee, 5 - Compass
T_TYPES = {0: "Round Robin", 1: "Single Elimination",
           2: "Double Elimination", 3: "Triple Elimination",
           4: "3 Game Guarentee", 5: "Compass Draw"}
           



class Fight:
    """Cog for organizing fights"""

    def __init__(self, bot):
        self.bot = bot
        # self.path = "data/Fox-Cogs/fight/"
        # self.file_path = "data/Fox-Cogs/fight/fight.json"
        # self.the_data = dataIO.load_json(self.file_path)
        self.config = Config.get_conf(self, identifier=49564952847684)
        default_global = {  
                "srtracker": {},
                "win": None,
                "loss": None,
                "dispute": None
                }
        default_guild = {
                "current": None,
                "tourneys": {},
                "settings": {    
                    "selfreport": True,
                    "reportchnnl": None,
                    "announcechnnl": None,
                    "admin": None
                    },
                "emoji": {
                    "nums": [],
                    "undo": None,
                    "appr": None
                    }
                }
        self.default_tourney = {
                "PLAYERS": [],
                "NAME": "Tourney 0",
                "RULES": {"BESTOF": 1, "BESTOFFINAL": 1, "TYPE": 0},
                "TYPEDATA": {},
                "OPEN": False,
                "WINNER": None
                }
        self.default_match = {
                "TEAM1": [],
                "TEAM2": [],
                "SCORE1": 0,
                "SCORE2": 0,
                "USERSCORE1": {
                    "SCORE1": 0, 
                    "SCORE2": 0
                    },
                "USERSCORE2": {
                    "SCORE1": 0,
                    "SCORE2": 0
                    }
                }
        self.default_tracker = {
                "TID": None,
                "MID": None,
                "RID": None,
                "GUILDID": None
                }
        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

    # def save_data(self):
        # """Saves the json"""
        # dataIO.save_json(self.file_path, self.the_data)
        
 # ************************v3 Shit************************  
 
#    def check(m):    #Check Message from author
#            return m.author == ctx.author and m.channel == ctx.channel

# ************************Fight command group start************************


    @commands.group()
    @commands.guild_only()
    async def fight(self, ctx):
        """Participate in active fights!"""
        # guild = ctx.message.guild

        if not await self._activefight(ctx):
            await ctx.send("No tournament currently running!")
        else:
            await ctx.send("Current tournament ID: " + await self._activefight(ctx))

        if ctx.invoked_subcommand is None:
            await ctx.send_help()
            # await ctx.send("I can do stuff!")

    @fight.command(name="join")
    async def fight_join(self, ctx, user: discord.Member=None):
        """Join the active fight"""
        # guild = ctx.message.guild
        if not user:
            user = ctx.author

        currFight = await self._getcurrentfight(ctx)
        tID = await self._activefight(ctx)
        if not currFight:
            await ctx.send("No tournament currently running!")
            return

        if not currFight["OPEN"]:
            await ctx.send("Tournament currently not accepting new players")
            return

        if await self._infight(ctx, tID, user.id):
            await ctx.send("You are already in this tournament!")
            return

        currFight["PLAYERS"].append(user.id)

        await self._save_fight(ctx, tID, currFight)

        await ctx.send("User has been added to tournament")

    @fight.command(name="score")
    async def fight_score(self, ctx, tID=None, score1=None, score2=None):
        """Enters score for current match, or for passed tournament ID"""
        # guild = ctx.message.guild
        # user = ctx.message.author

        currFight = await self._getcurrentfight(ctx)
        if not currFight:
            await ctx.send("No tournament currently running!")
            return

        if not tID:
            tID = await self._activefight(ctx)

        if not await self._infight(ctx, tID, ctx.author.id):
            await ctx.send("You are not in a current tournament")
            return
        
        if not currFight["TYPEDATA"]:
            await ctx.send("Tournament has not started yet")
            return
        
        mID = await self._parseuser(ctx.guild, tID, ctx.author.id)
        if not mID:
            await ctx.send("You have no match to update!")
            return

        if currFight["RULES"]["TYPE"] == 0:  # Round-Robin
            await self._rr_score(ctx, tID, mID, score1, score2)

    @fight.command(name="leave")
    async def fight_leave(self, ctx, tID=None, user: discord.Member=None):
        """Forfeit your match and all future matches"""
        # guild = ctx.message.guild
        if not user:
            user = ctx.author

        if not tID:
            tID = await self._activefight(ctx)
        await ctx.send("Todo Leave")

#    @fight.command(name="leaderboard", pass_context=True)
#    async def fight_leaderboard(self, ctx, ctag, ckind="Unranked", irank=0):
#        await ctx.send("Todo Leaderboard")
#        """Adds clan to grab-list"""

    @fight.group(name="bracket")
    async def fight_bracket(self, ctx, tID):
        """Shows your current match your next opponent,
            run [p]fight bracket full to see all matches"""
        await ctx.send("Todo Bracket")

    @fight_bracket.command(name="full")
    async def fight_bracket_full(self, ctx, tID):
        """Shows the full bracket"""
        await ctx.send("Todo Bracket Full")

# **********************Fightset command group start*********************
#    def fightsetdec(func):
#        async def decorated(self, ctx, *args, **kwargs):
#            guild = ctx.message.guild
#            await func(self, ctx, guild, *args, **kwargs)
#        return decorated

    @commands.group(aliases=['setfight'])
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def fightset(self, ctx):
        """Admin command for starting or managing tournaments"""
        # guild = ctx.message.guild
        
        # if guild.id not in self.the_data:
            # self.the_data[guild.id] = {
                # "CURRENT": None,
                # "TOURNEYS": {},
                # "SETTINGS": {    
                    # "SELFREPORT": True,
                    # "REPORTCHNNL": None,
                    # "ANNOUNCECHNNL": None,
                    # "ADMIN": None
                    # },  
                # "SRTRACKER": {
                    # "ROUND": None,
                    # "CHNNLS": None,
                    # },
                # "EMOJI": {
                    # "NUMS": [],
                    # "UNDO": None,
                    # "APPR": None
                    # }
                # }
                
            # self.save_data()

        if ctx.invoked_subcommand is None:
            await ctx.send_help()
        # await ctx.send("I can do stuff!")
    
    @fightset.command(name="emoji")
    async def fightset_emoji(self, ctx, winEmoji: discord.Emoji, lossEmoji: discord.Emoji, disputeEmoji: discord.Emoji):
        """Set the global emojis for reactions"""
        message = await ctx.send("Testing emojis")
        
        # try:
        await ctx.send(str(winEmoji) + " | " + str(lossEmoji) + " | " + str(disputeEmoji))

        await message.add_reaction(str(winEmoji))
        await message.add_reaction(str(lossEmoji))
        await message.add_reaction(str(disputeEmoji))
        # except:
            # await ctx.send("Emoji failure")
            # return
            
        await self.config.win.set(str(winEmoji))
        await self.config.loss.set(str(lossEmoji))
        await self.config.dispute.set(str(lossEmoji))
        
        await ctx.send("Success")

    @fightset.command(name="reset")
    async def fightset_reset(self, ctx):
        """Clears all data, be careful!"""
        await self.config.clear_all()
        await ctx.send("Success")
        
    @fightset.command(name="bestof")
    async def fightset_bestof(self, ctx, incount, tID=None):
        """Adjust # of games played per match. Must be an odd number"""
        # guild = ctx.message.guild
        if not tID and not await self._activefight(ctx):
            await ctx.send("No active fight to adjust")
            return

        if not tID:
            tID = await self._activefight(ctx)
        
        currFight = await self._getfight(ctx.guild, tID)
        
        try:
            num = int(incount)
        except:
            await ctx.send("That is not a number")
            return

        if num % 2 != 1:
            await ctx.send("Must be an odd number")
            return

        if num < 1:
            await ctx.send("Must be greater than 0, idiot")
            return
            
        if num > 17:
            await ctx.send("I can't go that high! Max 17")
            return

        currFight["RULES"]["BESTOF"] = num
        await self._save_fight(ctx, tID, currFight)
        await ctx.send("Tourney ID "+tID+" is now Best of "+str(num))

    @fightset.command(name="bestoffinal")
    async def fightset_bestoffinal(self, ctx, incount, tID=None):
        """Adjust # of games played in finals. Must be an odd number
        (Does not apply to tournament types without finals, such as Round Robin)"""
        #guild = ctx.message.guild
        if not tID and not await self._activefight(ctx):
            await ctx.send("No active fight to adjust")
            return

        if not tID:
            tID = await self._activefight(ctx)
        
        currFight = await self._getfight(ctx.guild, tID)
        
        try:
            num = int(incount)
        except:
            await ctx.send("That is not a number")
            return

        if num % 2 != 1:
            await ctx.send("Must be an odd number")
            return

        if num < 1:
            await ctx.send("Must be greater than 0, idiot")
            return

        currFight["RULES"]["BESTOFFINAL"] = num
        await self._save_fight(ctx, tID, currFight)
        await ctx.send("Tourney ID "+tID+" is now Best of "+str(num)+" in the Finals")

    @fightset.command(name="current")
    async def fightset_current(self, ctx, tID):
        """Sets the current tournament to passed ID"""
        #guild = ctx.message.guild
        currFight = await self._getfight(ctx.guild, tID)

        if not currFight:
            await ctx.send("No tourney found with that ID")
            return

        # self.the_data[guild.id]["CURRENT"] = tID
        # self.save_data()
        await self.config.guild(ctx.guild).current.set(tID)

        await ctx.send("Current tournament set to "+tID)

    @fightset.command(name="list")
    async def fightset_list(self, ctx):
        """Lists all current and past fights"""
        #guild = ctx.message.guild

        for page in pagify(str(await self.config.guild(ctx.guild).tourneys())):
            await ctx.send(box(page))

        await ctx.send("Done")

    @fightset.command(name="open")
    async def fightset_open(self, ctx):
        """Toggles the open status of current tournament"""
        #guild = ctx.message.guild
        if not await self._activefight(ctx):
            await ctx.send("No active fight to adjust")
            return
        
        tID = await self._activefight(ctx)
        currFight = await self._getcurrentfight(ctx)
        currFight["OPEN"] = not currFight["OPEN"]

        await self._save_fight(ctx, tID, currFight)

        await ctx.send("Tournament Open status is now set to: " + str(currFight["OPEN"]))

    @fightset.command(name="name")
    async def fightset_name(self, ctx, inname, tID=None):
        """Renames the tournament"""
        #guild = ctx.message.guild
        if not tID and not await self._activefight(ctx):
            await ctx.send("No active fight to adjust")
            return
        
        if not tID:
            tID = await self._activefight(ctx)
            
        currFight = await self._getfight(ctx.guild, tID)

        currFight["NAME"] = inname
        await self._save_fight(ctx, tID, currFight)
        await ctx.send("Tourney ID "+tID+" is now called "+inname)

    @fightset.command(name="start")
    async def fightset_start(self, ctx):
        """Starts the current tournament, must run setup first"""
        def check(m):    #Check Message from author
            return m.author == ctx.author and m.channel == ctx.channel
            
        #guild = ctx.message.guild
        #author = ctx.message.author
        currFight = await self._getcurrentfight(ctx)
        tID = await self._activefight(ctx)

        if not tID:
            await ctx.send("No current fight to start")
            return

        if currFight["TYPEDATA"]:  # Empty dicionary {} resolves to False
            await ctx.send("Looks like this tournament has already started.\nDo you want to delete all match data and restart? (yes/no)")
#            answer = await self.bot.wait_for_message(timeout=120, author=author)
            try:
                answer = await self.bot.wait_for('message', check=check, timeout=120)
            except asyncio.TimeoutError:
                await ctx.send("Cancelled due to timeout")
                return
                
            if not answer.content or answer.content.upper() not in ["YES", "Y"]:
                await ctx.send("Cancelled")
                return
        
        currFight["OPEN"] = False  # first close the tournament
        await self._save_fight(ctx, tID, currFight)                                         
        
        if currFight["RULES"]["TYPE"] == 0:  # Round-Robin
            await self._rr_start(ctx, tID)

    @fightset.command(name="setup")
    async def fightset_setup(self, ctx):
        """Setup a new tournament!
        Default settings are as follows
        Name: Tourney # (counts from 0)
        Best of: 1
        Best of (final): 1
        Self Report: True
        Type: 0 (Round Robin)"""
        #guild = ctx.message.guild
        # currServ = self.the_data[guild.id]
        tID = str(len(await self.config.guild(ctx.guild).tourneys()))  # Can just be len without +1, tourney 0 makes len 1, tourney 1 makes len 2, etc
        
        # currServ["CURRENT"] = tID
        currFight = self.default_tourney
        currFight["NAME"] = "Tourney "+str(tID)

        await self._save_fight(ctx, tID, currFight)
        
        await ctx.send("Tournament has been created!\n\n" + str(currFight))

        await ctx.send("Adjust settings as necessary, then open the tournament with [p]fightset toggleopen")

    @fightset.command(name="stop")
    async def fightset_stop(self, ctx):
        """Stops current tournament"""
        def check(m):    #Check Message from author
            return m.author == ctx.author and m.channel == ctx.channel
        # guild = ctx.message.guild
        if not await self._activefight(ctx):
            await ctx.send("No active fight to adjust")
            return

        # author = ctx.message.author
        # currServ = self.the_data[guild.id]

        await ctx.send("Current fight ID is "+str(await self.config.guild(ctx.guild).current())+"\nOkay to stop? (yes/no)")

        try:
            answer = await self.bot.wait_for('message', check=check, timeout=120)
        except asyncio.TimeoutError:
            await ctx.send("Cancelled due to timeout")
            return
            
        if not answer.content or answer.content.upper() not in ["YES", "Y"]:
            await ctx.send("Cancelled")
            return

        await self.config.guild(ctx.guild).current.set(None)

        await ctx.send("Fight has been stopped")

# ***************************Fightset_guild command group start**************************        
    @fightset.group(name="guild")
    async def fightset_guild(self, ctx):
        """Adjust guild wide settings"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()
    
    @fightset_guild.command(name="selfreport")
    async def fightset_guild_selfreport(self, ctx):
        """Toggles the ability to self-report scores for all tournaments"""
        #guild = ctx.message.guild
        
        curflag = await self.config.guild(ctx.guild).settings.selfreport()
        
        await self.config.guild(ctx.guild).settings.selfreport.set(not curflag)
        # settings["SELFREPORT"] = not settings["SELFREPORT"]

        # self.save_data()

        await ctx.send("Self-Reporting ability is now set to: " + str(not curflag))
        
    @fightset_guild.command(name="reportchnnl")
    async def fightset_guild_reportchnnl(self, ctx, channel: discord.TextChannel=None):
        """Set the channel for self-reporting"""
        #guild = ctx.message.guild
        
        # settings = self._getsettings(guild.id)
        
        # settings["REPORTCHNNL"] = channel.id
        if not channel:
            channel = ctx.channel
        await self.config.guild(ctx.guild).settings.reportchnnl.set(channel.id)

        await ctx.send("Self-Reporting Channel is now set to: " + channel.mention)
        
    @fightset_guild.command(name="announcechnnl")
    async def fightset_guild_announcechnnl(self, ctx, channel: discord.TextChannel=None):
        """Set the channel for tournament announcements"""
        #guild = ctx.message.guild
        
        # settings = self._getsettings(guild.id)
        
        # settings["ANNOUNCECHNNL"] = channel.id

        # self.save_data()
        if not channel:
            channel = ctx.channel

        await self.config.guild(ctx.guild).settings.announcechnnl.set(channel.id)
        
        await ctx.send("Announcement Channel is now set to: " + channel.mention)

    @fightset_guild.command(name="setadmin")
    async def fightset_guild_setadmin(self, ctx, role: discord.Role=None):
        """Chooses the tournament-admin role. CAREFUL: This grants the ability to override self-reported scores!"""
        #guild = ctx.message.guild
        
        # settings = self._getsettings(ctx)
        
        # settings["ADMIN"] = role.id

        # self.save_data()
        
        await self.config.guild(ctx.guild).settings.admin.set(role.id)
        
        await ctx.send("Tournament Admin role is now set to: " + role.mention)

# **********************Private command group start*********************
    async def _save_fight(self, ctx, tID, currFight):
        """Save a passed fight"""
        allTourney = await self.config.guild(ctx.guild).tourneys()
        allTourney[tID] = currFight
        await self.config.guild(ctx.guild).tourneys.set(allTourney)
        
    async def _save_tracker(self, ctx, messageid, matchData):
        """Save a passed fight"""
        allTracker = await self.config.srtracker()
        allTracker[messageid] = matchData
        await self.config.srtracker.set(allTracker)
        
    async def _guildsettings(self, ctx: commands.Context):
        """Returns the dictionary of guild settings"""
        # return self.the_data[guildID]["SETTINGS"]
        return await self.config.guild(ctx.guild).settings()
        
    async def _messagetracker(self, ctx: commands.Context):
        """Returns the dictionary of message tracking"""
        # return self.the_data[guildID]["SRTRACKER"]
        return await self.config.srtracker()
    
    async def _activefight(self, ctx: commands.Context):
        """Returns id for active fight, or None if no active fight"""
        # return self.the_data[guildID]["CURRENT"]
        return await self.config.guild(ctx.guild).current()

    async def _infight(self, ctx: commands.Context, tID, userid):
        """Checks if passed member is already in the tournament"""
        # return userid in self.the_data[guildID]["TOURNEYS"][tID]["PLAYERS"]
        return userid in (await self.config.guild(ctx.guild).tourneys())[tID]["PLAYERS"]

    async def _embed_tourney(self, ctx, tID):
        """Prints a pretty embed of the tournament"""
        await ctx.send("_placeholder Todo")

    async def _comparescores(self):
        """Checks user submitted scores for inconsistancies"""
        await ctx.send("_comparescores Todo")

    async def _parseuser(self, guild: discord.Guild, tID, userid):
        """Finds user in the tournament"""
        # if self._getfight(guildID, tID)["RULES"]["TYPE"] == 0:  # RR
        
        theT = await self._getfight(guild, tID)
        
        if userid not in theT["PLAYERS"]:  # Shouldn't happen, _infight check first
            return False
        
        if theT["RULES"]["TYPE"] == 0:
            return await self._rr_parseuser(guild, tID, userid)

        return False
        
    def _get_team(self, ctx: commands.Context, teaminfo):
        """Team info is a list of userid's. Returns a list of user objects"""
        outlist = []
        for player in teaminfo:
            outlist.append(self._get_user_from_id(ctx, player))
        return outlist
        
    # async def _getsettings(self, ctx: commands.Context):
        return self.the_data[guildID]["SETTINGS"]
        # return await self.config.guild(ctx.guild).settings()
    
    async def _get_message_from_id_old(self, channelid, messageid):
        return await self.bot.get_message(self._get_channel_from_id(channelid), messageid)
        
    async def _get_message_from_id(self, ctx: commands.Context, message_id: int)\
            -> Union[discord.Message, None]:
        """
        Tries to find a message by ID in the current guild context.
        :param ctx:
        :param message_id:
        :return:
        """
        for channel in ctx.guild.text_channels:
            try:
                return await channel.get_message(message_id)
            except discord.NotFound:
                pass
            except AttributeError: # VoiceChannel object has no attribute 'get_message'
                pass

        return None

    def _get_channel_from_id(self, ctx: commands.Context, channelid):
        # guild = self._get_guild_from_id(guildID)
        # return discord.utils.get(guild.channels, id=channelid)
        return discord.utils.get(ctx.guild.channels, id=channelid)
        
    def _get_user_from_id(self, userid):
        # guild = self._get_guild_from_id(guildID)
        # return discord.utils.get(guild.members, id=userid)
        return self.bot.get_user(userid)
        
    def _get_guild_from_id(self, guildID):
        return self.bot.get_guild(guildID)
    
    async def _getfight(self, guild: discord.Guild, tID):
        # return self.the_data[guildID]["TOURNEYS"][tID]
        return (await self.config.guild(guild).tourneys())[tID]
    
    async def _getcurrentfight(self, ctx: commands.Context):
        # if not self._activefight(guildID):
            # return None

        # return self._getfight(guildID, self._activefight(guildID))
        isactive = await self._activefight(ctx)
        if not isactive:
            return None
        return await self._getfight(ctx.guild, isactive)

# *********** References to "TYPEDATA" must be done per tournament mode (Below this line) *******
       
# **********************Single Elimination***************************
    async def _elim_setup(self, tID):
        await ctx.send("Elim setup todo")

    async def _elim_start(self, tID):
        await ctx.send("Elim start todo")

    async def _elim_update(self, matchID, ):
        await ctx.send("Elim update todo")

# **********************Round-Robin**********************************
    async def _rr_parseuser(self, guild: discord.Guild, tID, userid):
        theT = await self._getfight(guild, tID)
        matches = theT["TYPEDATA"]["MATCHES"]
        schedule = theT["TYPEDATA"]["SCHEDULE"]

        for round in schedule:
            for mID in round:
                teamnum = await self._rr_matchperms(guild, tID, userid, mID)
                if teamnum and not await self._rr_matchover(guild, tID, mID):  # User is in this match, check if it's done yet
                    return mID
    
        return False  # All matches done or not in tourney

    async def _rr_matchover(self, guild: discord.Guild, tID, mID):
        theT = await self._getfight(guild, tID)
        match = theT["TYPEDATA"]["MATCHES"][mID]
        
        if (match["SCORE1"] == math.ceil(theT["RULES"]["BESTOF"]/2) or 
                match["SCORE1"] == math.ceil(theT["RULES"]["BESTOF"]/2)):
                
            return True
        return False

    async def _rr_roundover(self, ctx: commands.Context, tID):
        theT = await self._getfight(ctx.guild, tID)
        theR = theT["TYPEDATA"]["SCHEDULE"][theT["TYPEDATA"]["ROUND"]]

        for mID in theR:
            if not await self._rr_matchover(ctx, tID, mID):
                return False
        return True

    async def _rr_matchperms(self, guild: discord.Guild, tID, userid, mID):
        # if self._get_user_from_id(guildID, userid) # Do an if-admin at start
        theT = await self._getfight(guild, tID)
        if userid in theT["TYPEDATA"]["MATCHES"][mID]["TEAM1"]:           
            return 1

        if userid in theT["TYPEDATA"]["MATCHES"][mID]["TEAM2"]:
            return 2

        return False

    async def _rr_setup(self, ctx: commands.Context, tID):

        theT = await self._getfight(ctx.guild, tID)
        theD = theT["TYPEDATA"]
        
        get_schedule = self._rr_schedule(theT["PLAYERS"])
        
        theD["SCHEDULE"] = get_schedule[0]
        theD["MATCHES"] = get_schedule[1]
        theD["ROUND"] = 0
        
        self._save_fight(ctx, tID, theT)
    
    async def _rr_printround(self, ctx: commands.Context, tID, rID):

        theT = await self._getfight(ctx.guild, tID)
        theD = theT["TYPEDATA"]
        # rID starts at 0, so print +1. Never used for computation, so doesn't matter
        if await self.config.guild(ctx.guild).settings.announcechnnl():
            # await self.bot.send_message(
                        # self._get_channel_from_id(guildID, self._guildsettings(guildID)["ANNOUNCECHNNL"]),
                        # "Round "+str(rID+1)
                        # )
            await self._get_channel_from_id(
                ctx, 
                (await self.config.guild(ctx.guild).settings)
                ).send("Round "+str(rID+1))
                
        # else:
            # await ctx.send("Round "+str(rID+1))
        
        
        for mID in theD["SCHEDULE"][rID]:
            team1 = self._get_team(ctx, theD["MATCHES"][mID]["TEAM1"])
            team2 = self._get_team(ctx, theD["MATCHES"][mID]["TEAM2"])
            
            for i in range(len(team1)):
                if team1[i]:
                    team1[i] = team1[i].mention
                else:
                    team1[i] = "BYE"
            
            for i in range(len(team2)):
                if team2[i]:
                    team2[i] = team2[i].mention
                else:
                    team2[i] = "BYE"
            
            mention1 = ", ".join(team1)
            mention2 = ", ".join(team2)
            outembed=discord.Embed(title="Match ID: " + mID, color=0x0000bf)
            outembed.add_field(name="Team 1", value=mention1, inline=True)
            outembed.add_field(name="Team 2", value=mention2, inline=True)
            outembed.set_footer(text=(await self.config.win())+" Report Win || "(await self.config.loss())+" Report Loss || "(await self.config.dispute())+" Dispute Result")
            
            if await self._guildsettings(ctx)["REPORTCHNNL"]:
                # message = await self.bot.send_message(
                            # self._get_channel_from_id(guildID, self._guildsettings(guildID)["REPORTCHNNL"]),
                            # embed=outembed
                            # )
                message = await self._get_channel_from_id(
                            ctx, 
                            self._guildsettings(ctx)["REPORTCHNNL"]
                            ).send(embed=outembed)
            else:
                message = await ctx.send(embed=outembed)
            
            # self._messagetracker(ctx)[message.id] = {"TID": tID, "MID": mID, "RID": rID}
            trackmessage = self.default_tracker
            trackmessage["TID"] = tID
            trackmessage["MID"] = mID
            trackmessage["RID"] = rID
            trackmessage["GUILDID"] = ctx.guild.id
            self._save_tracker(ctx, message.id, trackmessage )
                
            
            # await ctx.send(team1 + " vs " + team2 + " || Match ID: " + match)

    async def _rr_start(self, ctx, tID):

        self._rr_setup(ctx, tID)
        if await self.config.guild(ctx.guild).settings.announcechnnl():
            # await self.bot.send_message(
                            # self._get_channel_from_id(guildID, self._guildsettings(guildID)["ANNOUNCECHNNL"]),
                            # "**Tournament is Starting**"
                            # )
            await self._get_channel_from_id(
                            guildID, 
                            await self.config.guild(ctx.guild).settings.announcechnnl()
                            ).send("**Tournament is Starting**")
        # else:
            # await ctx.send("**Tournament is Starting**")
        
        await self._rr_printround(guildID, tID, 0)

    async def _rr_score(self, ctx: commands.Context, tID, mID, t1points, t2points):
        def check(m):    #Check Message from author
            return m.author == ctx.author and m.channel == ctx.channel
        theT = await self._getfight(ctx.guild, tID)
        theD = theT["TYPEDATA"]
        
        # if t1points and t2points:
        #    theD["MATCHES"][mID]["SCORE1"] = t1points
        #    theD["MATCHES"][mID]["SCORE2"] = t2points
        #    self.save_data()
        #    return

        if not t1points:
            await ctx.send("Entering scores for match ID: " + mID + "\n\n")
            await ctx.send("How many points did TEAM1 get?")
            if await self._rr_matchperms(ctx.guild, tID, ctx.author.id, mID) == 1:
                await ctx.send("*HINT: You are on TEAM1*")
            # answer = await self.bot.wait_for_message(timeout=120, author=author)
            
            try:
                answer = await self.bot.wait_for('message', check=check, timeout=120)
            except asyncio.TimeoutError:
                await ctx.send("Cancelled due to timeout")
                return

            try:
                t1points = int(answer.content)
            except:
                await ctx.send("That's not a number!")
                return

        if not t2points:
            await ctx.send("How many points did TEAM2 get?")
            if await self._rr_matchperms(ctx.guild, tID, ctx.author.id, mID) == 2:
                await ctx.send("*HINT: You are on TEAM2*")
            # answer = await self.bot.wait_for_message(timeout=120, author=author)
            try:
                answer = await self.bot.wait_for('message', check=check, timeout=120)
            except asyncio.TimeoutError:
                await ctx.send("Cancelled due to timeout")
                return

            try:
                t2points = int(answer.content)
            except:
                await ctx.send("That's not a number!")
                return

        if (t1points == math.ceil(theT["RULES"]["BESTOF"]/2) or
                t2points == math.ceil(theT["RULES"]["BESTOF"]/2)):
            theD["MATCHES"][mID]["SCORE1"] = t1points
            theD["MATCHES"][mID]["SCORE2"] = t2points
        else:
            await ctx.send("Invalid scores, nothing will be updated")
            return
        
        await self._save_fight(theT)
        await ctx.send("Scores have been saved successfully!")

        # if self._rr_checkround(guildID, tID)

    def _rr_schedule(self, inlist):
        """ Create a schedule for the teams in the list and return it"""
        s = []  # Schedule list
        outID = {}  # Matches

        firstID = ["A", "B", "C", "D", "E", "F",
                   "G", "H", "I", "J", "K", "L",
                   "M", "N", "O", "P", "Q", "R",
                   "S", "T", "U", "V", "W", "X",
                   "Y", "Z"]  # God dammit this could've been a string

        if len(inlist) % 2 == 1:
            inlist = inlist + ["BYE"]

        for i in range(len(inlist)):

            mid = int(len(inlist) / 2)
            l1 = inlist[:mid]
            l2 = inlist[mid:]
            l2.reverse()

            matchLetter = ""
            j = i
            while j+1 > 26:

                matchLetter += firstID[int(j + 1) % 26 - 1]

                j = (j + 1) / 26 - 1
            matchLetter += firstID[int(j+1) % 26-1]
            matchLetter = matchLetter[::-1]

            matchID = []
            for ix in range(len(l1)):
                matchID += [matchLetter+str(ix)]

            rPlayers = list(zip(l1, l2))
            TeamCnt = 0
            for ID in matchID:
                outID[ID] = self.default_match
                outID[ID]["TEAM1"] = [rPlayers[TeamCnt][0]]
                outID[ID]["TEAM2"] = [rPlayers[TeamCnt][1]]
                # outID[ID] = {
                             # "TEAM1": [rPlayers[TeamCnt][0]],
                             # "TEAM2": [rPlayers[TeamCnt][1]],
                             # "SCORE1": 0,
                             # "SCORE2": 0,
                             # "USERSCORE1": {"SCORE1": 0, "SCORE2": 0},
                             # "USERSCORE2": {"SCORE1": 0, "SCORE2": 0}
                             # }

                TeamCnt += 1

            # List of match ID's is now done

            s += [matchID]  # Schedule of matches
            inlist.insert(1, inlist.pop())

        outlist = [[], {}]
        outlist[0] = s
        outlist[1] = outID
        # outlist[0] is list schedule of matches
        # outlist[1] is dict data of matches

        return outlist
        
    #**************** Attempt 2, borrow from Squid*******

    async def on_raw_reaction_add(self, emoji: discord.PartialReactionEmoji,
                                  message_id: int, channel_id: int, user_id: int):
        """
        Event handler for long term reaction watching.
        :param discord.PartialReactionEmoji emoji:
        :param int message_id:
        :param int channel_id:
        :param int user_id:
        :return:
        """
        tracker = await self.config.srtracker()
        
        if message_id not in tracker:
            return 
        
        tracker = tracker[message_id]
            
        guild = self.bot.get_guild(tracker["GUILDID"])
        member = guild.get_member(user_id)
        if member.bot:
            return

        if tracker["MID"] != (await self._parseuser(guild, tracker["TID"], member.id)):
            message = guild.get_message(message_id)
            await message.remove_reaction(emoji, member)
            return

        channel = guild.get_channel(channel_id)
        message = channel.get_message(message_id)


        if emoji.is_custom_emoji():
            emoji_id = emoji.id
        else:
            emoji_id = emoji.name
        
        if emoji_id not in E_REACTS.keys():  # Not sure if this works
            await message.remove_reaction(emoji, member)
            return
        
        has_reactrestrict, combos = await self.has_reactrestrict_combo(message_id)

        if not has_reactrestrict:
            return

        try:
            member = self._get_member(channel_id, user_id)
        except LookupError:
            return

        if member.bot:
            return

        try:
            roles = [self._get_role(member.guild, c.role_id) for c in combos]
        except LookupError:
            return

        for apprrole in roles:
            if apprrole in member.roles:
                return
                
        message = await self._get_message_from_channel(channel_id, message_id)
        await message.remove_reaction(emoji, member)

    # async def on_raw_reaction_remove(self, emoji: discord.PartialReactionEmoji,
                                     # message_id: int, channel_id: int, user_id: int):
        # """
        # Event handler for long term reaction watching.
        # :param discord.PartialReactionEmoji emoji:
        # :param int message_id:
        # :param int channel_id:
        # :param int user_id:
        # :return:
        # """
        # if emoji.is_custom_emoji():
            # emoji_id = emoji.id
        # else:
            # emoji_id = emoji.name

        # has_reactrole, combos = await self.has_reactrole_combo(message_id, emoji_id)

        # if not has_reactrole:
            # return

        # try:
            # member = self._get_member(channel_id, user_id)
        # except LookupError:
            # return

        # if member.bot:
            # return

        # try:
            # roles = [self._get_role(member.guild, c.role_id) for c in combos]
        # except LookupError:
            # return

        # try:
            # await member.remove_roles(*roles)
        # except discord.Forbidden:
            # pass
    #**************** Socket attempt ********************
    
    # async def _on_react(self, reaction, user):
        # """do nothing (for now)"""
        
        
        
               # # if not self.the_data["trackmessage"]:
                   # # return
               
               # # if user == self.bot.user:
                   # # return  # Don't remove bot's own reactions
               # # message = reaction.message
               # # emoji = reaction.emoji
               
               # # if not message.id == self.the_data["trackmessage"]:
                   # # return
               
               # # if str(emoji) in self.letters:
                   # # letter = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[self.letters.index(str(emoji))]
                   # # await self._guessletter(letter, message.channel)
                   
                   
               # # if str(emoji) in self.navigate:
                   # # if str(emoji) == self.navigate[0]:
                       # # await self._reactmessage_am(message)
        
                   # # if str(emoji) == self.navigate[-1]:
                       # # await self._reactmessage_nz(message)
     
    # async def on_socket_response(self, obj):
        # if obj["t"] != "MESSAGE_REACTION_ADD":
            # return
        
        # if "emoji" not in obj["d"]:     # This reaction is in the messages deque, use other listener
            # return
        
        # # if message_id not in guildID for 
        # # for guildID in self.the_data:
           # # if not self._messagetracker(ctx)
        # message_id = obj["d"]["message_id"]
        # emoji = obj["d"]["emoji"]["name"]
        # user_id = obj["d"]["user_id"]

