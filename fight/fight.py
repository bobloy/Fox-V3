import discord
import os
import math
from discord.ext import commands

from .utils.chat_formatting import pagify
from .utils.chat_formatting import box
from .utils.dataIO import dataIO
from .utils import checks
from random import randint


# 0 - Robin, 1 - Single, 2 - Double, 3 - Triple, 4 - Guarentee, 5 - Compass
T_TYPES = {0: "Round Robin", 1: "Single Elimination",
           2: "Double Elimination", 3: "Triple Elimination",
           4: "3 Game Guarentee", 5: "Compass Draw"}


class Fight:
    """Cog for organizing fights"""

    def __init__(self, bot):
        self.bot = bot
        self.path = "data/Fox-Cogs/fight/"
        self.file_path = "data/Fox-Cogs/fight/fight.json"
        self.the_data = dataIO.load_json(self.file_path)

    def save_data(self):
        """Saves the json"""
        dataIO.save_json(self.file_path, self.the_data)


# ************************Fight command group start************************
    @commands.group(pass_context=True, no_pm=True)
    async def fight(self, ctx):
        """Participate in active fights!"""
        server = ctx.message.server

        if not self._activefight(server.id):
            await self.bot.say("No tournament currently running!")
        else:
            await self.bot.say("Current tournament ID: " + self._activefight(server.id))

        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)
            # await self.bot.say("I can do stuff!")

    @fight.command(name="join", pass_context=True)
    async def fight_join(self, ctx, user: discord.Member=None):
        """Join the active fight"""
        server = ctx.message.server
        if not user:
            user = ctx.message.author

        currFight = self._getcurrentfight(server.id)
        tID = self._activefight(server.id)
        if not currFight:
            await self.bot.say("No tournament currently running!")
            return

        if not currFight["OPEN"]:
            await self.bot.say("Tournament currently not accepting new players")
            return

        if self._infight(server.id, tID, user.id):
            await self.bot.say("You are already in this tournament!")
            return

        currFight["PLAYERS"].append(user.id)

        self.save_data()

        await self.bot.say("User has been added to tournament")

    @fight.command(name="score", pass_context=True)
    async def fight_score(self, ctx, tID=None, score1=None, score2=None):
        """Enters score for current match, or for passed tournament ID"""
        server = ctx.message.server
        user = ctx.message.author

        currFight = self._getcurrentfight(server.id)
        if not currFight:
            await self.bot.say("No tournament currently running!")
            return

        if not tID:
            tID = self._activefight(server.id)

        if not self._infight(server.id, tID, user.id):
            await self.bot.say("You are not in a current tournament")
            return

        mID = self._parseuser(server.id, tID, user.id)
        if not mID:
            await self.bot.say("You have no match to update!")
            return

        if currFight["RULES"]["TYPE"] == 0:  # Round-Robin
            await self._rr_score(server.id, tID, mID, user, score1, score2)

    @fight.command(name="leave", pass_context=True)
    async def fight_leave(self, ctx, tID=None, user: discord.Member=None):
        """Forfeit your match and all future matches"""
        server = ctx.message.server
        if not user:
            user = ctx.message.author

        if not tID:
            tID = self._activefight(serverid)
        await self.bot.say("Todo Leave")

#    @fight.command(name="leaderboard", pass_context=True)
#    async def fight_leaderboard(self, ctx, ctag, ckind="Unranked", irank=0):
#        await self.bot.say("Todo Leaderboard")
#        """Adds clan to grab-list"""

    @fight.group(name="bracket", pass_context=True)
    async def fight_bracket(self, ctx, tID):
        """Shows your current match your next opponent,
            run [p]fight bracket full to see all matches"""
        await self.bot.say("Todo Bracket")

    @fight_bracket.command(name="full")
    async def fight_bracket_full(self, tID):
        """Shows the full bracket"""
        await self.bot.say("Todo Bracket Full")

# **********************Fightset command group start*********************
#    def fightsetdec(func):
#        async def decorated(self, ctx, *args, **kwargs):
#            server = ctx.message.server
#            await func(self, ctx, server, *args, **kwargs)
#        return decorated

    @commands.group(pass_context=True, no_pm=True, aliases=['setfight'])
    @checks.mod_or_permissions(administrator=True)
    async def fightset(self, ctx):
        """Admin command for starting or managing tournaments"""
        server = ctx.message.server

        if server.id not in self.the_data or True:
            self.the_data[server.id] = {
                "CURRENT": None,
                "TOURNEYS": {},
                "SETTINGS": {    
                    "SELFREPORT": True,
                    "REPORTCHNNL": None,
                    "ANNOUNCECHNNL": None,
                    "ADMIN": None
                    },  
                "SRTRACKER": {
                    "ROUND": None,
                    "CHNNLS": None,
                    },
                "EMOJI": {
                    "NUMS": [],
                    "UNDO": None,
                    "APPR": None
                    }
                }
                
            self.save_data()

        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)
        # await self.bot.say("I can do stuff!")

    @fightset.command(name="bestof", pass_context=True)
    async def fightset_bestof(self, ctx, incount, tID=None):
        """Adjust # of games played per match. Must be an odd number"""
        server = ctx.message.server
        if not tID and not self._activefight(server.id):
            await self.bot.say("No active fight to adjust")
            return

        if not tID:
            tID = self._activefight(server.id)

        try:
            num = int(incount)
        except:
            await self.bot.say("That is not a number")
            return

        if num % 2 != 1:
            await self.bot.say("Must be an odd number")
            return

        if num < 1:
            await self.bot.say("Must be greater than 0, idiot")
            return
            
        if num > 17:
            await self.bot.say("I can't go that high! Max 17")
            return

        self._getfight(server.id, tID)["RULES"]["BESTOF"] = num
        self.save_data()
        await self.bot.say("Tourney ID "+tID+" is now Best of "+str(num))

    @fightset.command(name="bestoffinal", pass_context=True)
    async def fightset_bestoffinal(self, ctx, incount, tID=None):
        """Adjust # of games played in finals. Must be an odd number
        (Does not apply to tournament types without finals, such as Round Robin)"""
        server = ctx.message.server
        if not tID and not self._activefight(server.id):
            await self.bot.say("No active fight to adjust")
            return

        if not tID:
            tID = self._activefight(server.id)

        try:
            num = int(incount)
        except:
            await self.bot.say("That is not a number")
            return

        if num % 2 != 1:
            await self.bot.say("Must be an odd number")
            return

        if num < 1:
            await self.bot.say("Must be greater than 0, idiot")
            return

        self._getfight(server.id, tID)["RULES"]["BESTOFFINAL"] = num
        self.save_data()
        await self.bot.say("Tourney ID "+tID+" is now Best of "+str(num))

    @fightset.command(name="current", pass_context=True)
    async def fightset_current(self, ctx, tID):
        """Sets the current tournament to passed ID"""
        server = ctx.message.server
        aFight = self._getfight(server.id, tID)

        if not aFight:
            await self.bot.say("No tourney found with that ID")
            return

        self.the_data[server.id]["CURRENT"] = tID
        self.save_data()

        await self.bot.say("Current tournament set to "+tID)

    @fightset.command(name="list", pass_context=True)
    async def fightset_list(self, ctx):
        """Lists all current and past fights"""
        server = ctx.message.server

        for page in pagify(str(self.the_data[server.id]["TOURNEYS"])):
            await self.bot.say(box(page))

        await self.bot.say("Done")

    @fightset.command(name="open", pass_context=True)
    async def fightset_open(self, ctx):
        """Toggles the open status of current tournament"""
        server = ctx.message.server
        if not self._activefight(server.id):
            await self.bot.say("No active fight to adjust")
            return

        currFight = self._getcurrentfight(server.id)
        currFight["OPEN"] = not currFight["OPEN"]

        self.save_data()

        await self.bot.say("Tournament Open status is now set to: " + str(currFight["OPEN"]))
        
    @fightset.command(name="name", pass_context=True)
    async def fightset_name(self, ctx, inname, tID=None):
        """Renames the tournament"""
        server = ctx.message.server
        if not tID and not self._activefight(server.id):
            await self.bot.say("No active fight to adjust")
            return
        
        if not tID:
            tID = self._activefight(server.id)
        
        self._getfight(server.id, tID)["NAME"] = inname
        self.save_data()
        await self.bot.say("Tourney ID "+tID+" is now called "+self._getfight(server.id, tID)["NAME"])
        
    @fightset.command(name="start", pass_context=True)
    async def fightset_start(self, ctx):
        """Starts the current tournament, must run setup first"""
        server = ctx.message.server
        author = ctx.message.author
        currFight = self._getcurrentfight(server.id)
        tID = self._activefight(server.id)
        
        if not tID:
            await self.bot.say("No current fight to start")
            return
            
        if currFight["TYPEDATA"]:  # Empty dicionary {} resolves to False
            await self.bot.say("Looks like this tournament has already started.\nDo you want to delete all match data and restart? (yes/no)")
            answer = await self.bot.wait_for_message(timeout=120, author=author)

            if not answer.content and answer.content.upper() in ["YES", "Y"]:
                await self.bot.say("Cancelled")
                return
        
        currFight["OPEN"] = False  # first close the tournament
        self.save_data()                                         
        
        if currFight["RULES"]["TYPE"] == 0:  # Round-Robin
            await self._rr_start(server.id, tID)

    @fightset.command(name="setup", pass_context=True)
    async def fightset_setup(self, ctx):
        """Setup a new tournament!
        Default settings are as follows
        Name: Tourney # (counts from 0)
        Best of: 1
        Best of (final): 1
        Self Report: True
        Type: 0 (Round Robin)"""
        server = ctx.message.server
        currServ = self.the_data[server.id]
        tID = str(len(currServ["TOURNEYS"]))  # Can just be len without +1, tourney 0 makes len 1, tourney 1 makes len 2, etc
        currServ["CURRENT"] = tID
        currServ["TOURNEYS"][tID] = {
                                        "PLAYERS": [],
                                        "NAME": "Tourney "+str(tID),
                                        "RULES": {"BESTOF": 1, "BESTOFFINAL": 1, "TYPE": 0},
                                        "TYPEDATA": {},
                                        "OPEN": False,
                                        "WINNER": None
                                        }

        self.save_data()

        await self.bot.say("Tournament has been created!\n\n" + str(currServ["TOURNEYS"][tID]))

        await self.bot.say("Adjust settings as necessary, then open the tournament with [p]fightset toggleopen")

    @fightset.command(name="stop", pass_context=True)
    async def fightset_stop(self, ctx):
        """Stops current tournament"""
        server = ctx.message.server
        if not self._activefight(server.id):
            await self.bot.say("No active fight to adjust")
            return

        author = ctx.message.author
        currServ = self.the_data[server.id]

        await self.bot.say("Current fight ID is "+str(currServ["CURRENT"])+"\nOkay to stop? (yes/no)")

        answer = await self.bot.wait_for_message(timeout=120, author=author)

        if not answer.content.upper() in ["YES", "Y"]:
            await self.bot.say("Cancelled")
            return

        currServ["CURRENT"] = None

        self.save_data()
        await self.bot.say("Fight has been stopped")

# ***************************Fightset_server command group start**************************        
    @fightset.group(name="server", pass_context=True)
    async def fightset_server(self, ctx):
        """Adjust server wide settings"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)
    
    @fightset_server.command(name="selfreport", pass_context=True)
    async def fightset_server_selfreport(self, ctx):
        """Toggles the ability to self-report scores for all tournaments"""
        server = ctx.message.server
        
        settings = self._getsettings(server.id)
        
        settings["SELFREPORT"] = not settings["SELFREPORT"]

        self.save_data()

        await self.bot.say("Self-Reporting ability is now set to: " + str(settings["SELFREPORT"]))
        
    @fightset_server.command(name="reportchnnl", pass_context=True)
    async def fightset_server_reportchnnl(self, ctx, channel: discord.Channel=None):
        """Set the channel for self-reporting"""
        server = ctx.message.server
        
        settings = self._getsettings(server.id)
        
        settings["REPORTCHNNL"] = channel.id

        self.save_data()

        await self.bot.say("Self-Reporting Channel is now set to: " + channel.mention)
        
    @fightset_server.command(name="announcechnnl", pass_context=True)
    async def fightset_server_announcechnnl(self, ctx, channel: discord.Channel=None):
        """Set the channel for tournament announcements"""
        server = ctx.message.server
        
        settings = self._getsettings(server.id)
        
        settings["ANNOUNCECHNNL"] = channel.id

        self.save_data()

        await self.bot.say("Announcement Channel is now set to: " + channel.mention)
        
    @fightset_server.command(name="announcechnnl", pass_context=True)
    async def fightset_server_announcechnnl(self, ctx, channel: discord.Channel=None):
        """Set the channel for tournament announcements"""
        server = ctx.message.server
        
        settings = self._getsettings(server.id)
        
        settings["ANNOUNCECHNNL"] = channel.id

        self.save_data()

        await self.bot.say("Announcement Channel is now set to: " + channel.mention)
        
    @fightset_server.command(name="setadmin", pass_context=True)
    async def fightset_server_setadmin(self, ctx, role: discord.Role=None):
        """Chooses the tournament-admin role. CAREFUL: This grants the ability to override self-reported scores!"""
        server = ctx.message.server
        
        settings = self._getsettings(server.id)
        
        settings["ADMIN"] = role.id

        self.save_data()

        await self.bot.say("Tournament Admin role is now set to: " + role.mention)

# **********************Private command group start*********************
    def _serversettings(self, serverid):
        """Returns the dictionary of server settings"""
        return self.the_data[serverid]["SETTINGS"]
        
    def _messagetracker(self, serverid):
        """Returns the dictionary of message tracking"""
        return self.the_data[serverid]["SRTRACKER"]
    
    def _activefight(self, serverid):
        """Returns id for active fight, or None if no active fight"""
        return self.the_data[serverid]["CURRENT"]

    def _infight(self, serverid, tID, userid):
        """Checks if passed member is already in the tournament"""

        return userid in self.the_data[serverid]["TOURNEYS"][tID]["PLAYERS"]

    async def _embed_tourney(self, serverid, tID):
        """Prints a pretty embed of the tournament"""
        await self.bot.say("_placeholder Todo")

    async def _comparescores(self):
        """Checks user submitted scores for inconsistancies"""
        await self.bot.say("_comparescores Todo")

    def _parseuser(self, serverid, tID, userid):
        """Finds user in the tournament"""
        if self._getfight(serverid, tID)["RULES"]["TYPE"] == 0:  # RR
            return self._rr_parseuser(serverid, tID, userid)

        return False
        
    def _get_team(self, serverid, teaminfo):
        """Team info is a list of userid's. Returns a list of user objects"""
        outlist = []
        for player in teaminfo:
            outlist.append(self._get_user_from_id(serverid, player))
        return outlist
        
    def _getsettings(self, serverid):
        return self.the_data[serverid]["SETTINGS"]
    
    async def _get_message_from_id(self, channelid, messageid):
        return await self.bot.get_message(self._get_channel_from_id(channelid), messageid)
    
    def _get_message_from_id_recent(self, messageid):
        return discord.utils.get(self.bot.messages, id=messageid)
        
    def _get_channel_from_id(self, serverid, channelid):
        server = self._get_server_from_id(serverid)
        return discord.utils.get(server.channels, id=channelid)
        
    def _get_user_from_id(self, serverid, userid):
        server = self._get_server_from_id(serverid)
        return discord.utils.get(server.members, id=userid)
        
    def _get_server_from_id(self, serverid):
        return discord.utils.get(self.bot.servers, id=serverid)
    
    def _getfight(self, serverid, tID):
        return self.the_data[serverid]["TOURNEYS"][tID]
    
    def _getcurrentfight(self, serverid):
        if not self._activefight(serverid):
            return None

        return self._getfight(serverid, self._activefight(serverid))

# *********** References to "TYPEDATA" must be done per tournament mode (Below this line) *******
       
# **********************Single Elimination***************************
    async def _elim_setup(self, tID):
        await self.bot.say("Elim setup todo")

    async def _elim_start(self, tID):
        await self.bot.say("Elim start todo")

    async def _elim_update(self, matchID, ):
        await self.bot.say("Elim update todo")

# **********************Round-Robin**********************************
    def _rr_parseuser(self, serverid, tID, userid):
        theT = self._getfight(serverid, tID)
        matches = theT["TYPEDATA"]["MATCHES"]
        schedule = theT["TYPEDATA"]["SCHEDULE"]

        for round in schedule:
            for mID in round:
                teamnum = self._rr_matchperms(serverid, tID, userid, mID)
                if teamnum and not self._rr_matchover(serverid, tID, mID):  # User is in this match, check if it's done yet
                    return mID
    
        return False  # All matches done or not in tourney

    def _rr_matchover(self, serverid, tID, mID):
        theT = self._getfight(serverid, tID)
        match = theT["TYPEDATA"]["MATCHES"][mID]
        
        if (match["SCORE1"] == math.ceil(theT["RULES"]["BESTOF"]/2) or 
                match["SCORE1"] == math.ceil(theT["RULES"]["BESTOF"]/2)):
                
            return True
        return False

    def _rr_roundover(self, serverid, tID):
        currFight = self._getfight(serverid, tID)
        currRound = currFight["TYPEDATA"]["SCHEDULE"][currFight["TYPEDATA"]["ROUND"]]

        for mID in currRound:
            if not self._rr_matchover(serverid, tID, mID):
                return False
        return True

    def _rr_matchperms(self, serverid, tID, userid, mID):
        # if self._get_user_from_id(serverid, userid) # Do an if-admin at start
        theT = self._getfight(serverid, tID)
        if userid in theT["TYPEDATA"]["MATCHES"][mID]["TEAM1"]:           
            return 1

        if userid in theT["TYPEDATA"]["MATCHES"][mID]["TEAM2"]:
            return 2

        return False

    def _rr_setup(self, serverid, tID):

        theT = self._getfight(serverid, tID)
        theD = theT["TYPEDATA"]
        
        get_schedule = self._rr_schedule(theT["PLAYERS"])
        
        theD["SCHEDULE"] = get_schedule[0]
        theD["MATCHES"] = get_schedule[1]
        theD["ROUND"] = 0
        
        self.save_data()
    
    async def _rr_printround(self, serverid, tID, rID):

        theT = self._getfight(serverid, tID)
        theD = theT["TYPEDATA"]
        # rID starts at 0, so print +1. Never used for computation, so doesn't matter
        if self._serversettings(serverid)["ANNOUNCECHNNL"]:
            await self.bot.send_message(
                        self._get_channel_from_id(serverid, self._serversettings(serverid)["ANNOUNCECHNNL"]),
                        "Round "+str(rID+1)
                        )
        else:
            await self.bot.say("Round "+str(rID+1))
        
        
        for mID in theD["SCHEDULE"][rID]:
            team1 = self._get_team(serverid, theD["MATCHES"][mID]["TEAM1"])
            team2 = self._get_team(serverid, theD["MATCHES"][mID]["TEAM2"])
            
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
            outembed.set_footer(text="React your team's score, then your opponents score!")
            
            if self._serversettings(serverid)["REPORTCHNNL"]:
                message = await self.bot.send_message(
                            self._get_channel_from_id(serverid, self._serversettings(serverid)["REPORTCHNNL"]),
                            embed=outembed
                            )
            else:
                message = await self.bot.say(embed=outembed)
            
            self._messagetracker(serverid)[message.id] = {"TID": tID, "MID": mID, "RID": rID}
            self.save_data()
                
            
            # await self.bot.say(team1 + " vs " + team2 + " || Match ID: " + match)

    async def _rr_start(self, serverid, tID):

        self._rr_setup(serverid, tID)
        if self._serversettings(serverid)["ANNOUNCECHNNL"]:
            await self.bot.send_message(
                            self._get_channel_from_id(serverid, self._serversettings(serverid)["ANNOUNCECHNNL"]),
                            "**Tournament is Starting**"
                            )
        else:
            await self.bot.say("**Tournament is Starting**")
        
        await self._rr_printround(serverid, tID, 0)

    async def _rr_score(self, serverid, tID, mID, author, t1points, t2points):

        theT = self._getfight(serverid, tID)
        theD = theT["TYPEDATA"]
        
        # if t1points and t2points:
        #    theD["MATCHES"][mID]["SCORE1"] = t1points
        #    theD["MATCHES"][mID]["SCORE2"] = t2points
        #    self.save_data()
        #    return

        if not t1points:
            await self.bot.say("Entering scores for match ID: " + mID + "\n\n")
            await self.bot.say("How many points did TEAM1 get?")
            if self._rr_matchperms(serverid, tID, author.id, mID) == 1:
                await self.bot.say("*HINT: You are on TEAM1*")
            answer = await self.bot.wait_for_message(timeout=120, author=author)
            try:
                t1points = int(answer.content)
            except:
                await self.bot.say("That's not a number!")
                return

        if not t2points:
            await self.bot.say("How many points did TEAM2 get?")
            if self._rr_matchperms(serverid, tID, author.id, mID) == 2:
                await self.bot.say("*HINT: You are on TEAM2*")
            answer = await self.bot.wait_for_message(timeout=120, author=author)
            try:
                t2points = int(answer.content)
            except:
                await self.bot.say("That's not a number!")
                return

        if (t1points == math.ceil(theT["RULES"]["BESTOF"]/2) or
                t2points == math.ceil(theT["RULES"]["BESTOF"]/2)):
            theD["MATCHES"][mID]["SCORE1"] = t1points
            theD["MATCHES"][mID]["SCORE2"] = t2points
            self.save_data()
        else:
            await self.bot.say("Invalid scores, nothing will be updated")
            return

        await self.bot.say("Scores have been saved successfully!")

        # if self._rr_checkround(serverid, tID)

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
                outID[ID] = {
                             "TEAM1": [rPlayers[TeamCnt][0]],
                             "TEAM2": [rPlayers[TeamCnt][1]],
                             "SCORE1": 0,
                             "SCORE2": 0,
                             "USERSCORE1": {"SCORE1": 0, "SCORE2": 0},
                             "USERSCORE2": {"SCORE1": 0, "SCORE2": 0}
                             }

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


def check_folders():
    if not os.path.exists("data/Fox-Cogs"):
        print("Creating data/Fox-Cogs folder...")
        os.makedirs("data/Fox-Cogs")

    if not os.path.exists("data/Fox-Cogs/fight"):
        print("Creating data/Fox-Cogs/fight folder...")
        os.makedirs("data/Fox-Cogs/fight")


def check_files():
    if not dataIO.is_valid_json("data/Fox-Cogs/fight/fight.json"):
        dataIO.save_json("data/Fox-Cogs/fight/fight.json", {})


def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(Fight(bot))
