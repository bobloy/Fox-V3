import math

import discord
import asyncio

from discord.ext import commands
from redbot.core import Config
from redbot.core import checks
from redbot.core.utils.chat_formatting import box
from redbot.core.utils.chat_formatting import pagify

# from typing import Union

# 0 - Robin, 1 - Single, 2 - Double, 3 - Triple, 4 - Guarantee, 5 - Compass
T_TYPES = {
    0: "Round Robin",
    1: "Single Elimination",
    2: "Double Elimination",
    3: "Triple Elimination",
    4: "3 Game Guarantee",
    5: "Compass Draw",
}


class Fight:
    """Cog for organizing fights"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=49564952847684, force_registration=True)
        default_global = {
            "srtracker": {},
            "win": None,
            "winu": None,
            "loss": None,
            "lossu": None,
            "dispute": None,
            "disputeu": None,
        }
        default_guild = {
            "current": None,
            "tourneys": {},
            "settings": {
                "selfreport": True,
                "reportchnnl": None,
                "announcechnnl": None,
                "admin": None,
            },
            "emoji": {"nums": [], "undo": None, "appr": None},
        }
        self.default_tourney = {
            "PLAYERS": [],
            "NAME": "Tourney 0",
            "RULES": {"BESTOF": 1, "BESTOFFINAL": 1, "TYPE": 0},
            "TYPEDATA": {},
            "OPEN": False,
            "WINNER": None,
        }
        self.default_match = {
            "TEAM1": [],
            "TEAM2": [],
            "SCORE1": None,
            "SCORE2": None,
            "USERSCORE1": {"SCORE1": None, "SCORE2": None},
            "USERSCORE2": {"SCORE1": None, "SCORE2": None},
            "WINNER": None,
            "DISPUTE": False,
        }
        self.default_tracker = {"TID": None, "MID": None, "RID": None, "GUILDID": None}
        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

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
            pass
            # await ctx.send("I can do stuff!")

    @fight.command(name="join")
    async def fight_join(self, ctx, user: discord.Member = None):
        """Join the active fight"""
        # guild = ctx.message.guild
        if not user:
            user = ctx.author

        curr_fight = await self._getcurrentfight(ctx)
        t_id = await self._activefight(ctx)
        if not curr_fight:
            await ctx.send("No tournament currently running!")
            return

        if not curr_fight["OPEN"]:
            await ctx.send("Tournament currently not accepting new players")
            return

        if await self._infight(ctx, t_id, user.id):
            await ctx.send("You are already in this tournament!")
            return

        curr_fight["PLAYERS"].append(user.id)

        await self._save_fight(ctx, t_id, curr_fight)

        await ctx.send("User has been added to tournament")

    # @fight.command(name="score")
    # async def fight_score(self, ctx, tID=None, score1=None, score2=None):
    # """Enters score for current match, or for passed tournament ID"""
    # # guild = ctx.message.guild
    # # user = ctx.message.author

    # currFight = await self._getcurrentfight(ctx)
    # if not currFight:
    # await ctx.send("No tournament currently running!")
    # return

    # if not tID:
    # tID = await self._activefight(ctx)

    # if not await self._infight(ctx, tID, ctx.author.id):
    # await ctx.send("You are not in a current tournament")
    # return

    # if not currFight["TYPEDATA"]:
    # await ctx.send("Tournament has not started yet")
    # return

    # mID = await self._parseuser(ctx.guild, tID, ctx.author.id)
    # if not mID:
    # await ctx.send("You have no match to update!")
    # return

    # if currFight["RULES"]["TYPE"] == 0:  # Round-Robin
    # await self._rr_score(ctx, tID, mID, score1, score2)

    @fight.command(name="leave")
    async def fight_leave(self, ctx, t_id=None, user: discord.Member = None):
        """Forfeit your match and all future matches"""
        # guild = ctx.message.guild
        if not user:
            user = ctx.author

        if not t_id:
            t_id = await self._activefight(ctx)
        await ctx.send("Todo Leave")

    @fight.group(name="bracket")
    async def fight_bracket(self, ctx, t_id):
        """Shows your current match your next opponent,
            run [p]fight bracket full to see all matches"""
        # ToDo Bracket
        await ctx.send("Todo Bracket")

    @fight_bracket.command(name="full")
    async def fight_bracket_full(self, ctx, t_id):
        """Shows the full bracket"""
        # ToDo Bracket Full
        await ctx.send("Todo Bracket Full")

    # **********************Fightset command group start*********************

    @commands.group()
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def fadmin(self, ctx):
        """Admin command for managing the current tournament"""
        if ctx.invoked_subcommand is None:
            pass

    @fadmin.command(name="score")
    async def fadmin_score(self, ctx, m_id, score1, score2):
        """Set's the score for matchID and clears disputes"""
        curr_fight = await self._getcurrentfight(ctx)
        t_id = await self._activefight(ctx)
        if not curr_fight:
            await ctx.send("No tournament currently running!")
            return

        # ToDo allow score adjustment

    # **********************Fightset command group start*********************

    @commands.group(aliases=["setfight"])
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def fightset(self, ctx):
        """Admin command for starting or managing tournaments"""
        if ctx.invoked_subcommand is None:
            pass
        # await ctx.send("I can do stuff!")

    @fightset.command(name="emoji")
    async def fightset_emoji(self, ctx):
        """Set the global reaction emojis for reporting matches"""
        message = await ctx.send("Emoji Tests")
        message2 = await ctx.send("Secondary Emoji Tests")

        needed = ["reporting a win", "reporting a loss", "disputing results"]

        for need in needed:
            try:
                emoji, actual_emoji, is_unicode = await self._wait_for_emoji(ctx, need)
            except asyncio.TimeoutError:
                await ctx.send("You didn't respond in time, please redo this command.")
                return

            try:
                await message.add_reaction(actual_emoji)
            except discord.HTTPException:
                await ctx.send(
                    "I can't add that emoji because I'm not in the guild that" " owns it."
                )
                return

            if need == "reporting a win":
                win_emoji = emoji
                win_unicode = is_unicode
            if need == "reporting a loss":
                loss_emoji = emoji
                loss_unicode = is_unicode
            if need == "disputing results":
                dispute_emoji = emoji
                dis_unicode = is_unicode

        await self.config.win.set(win_emoji)
        await self.config.winu.set(win_unicode)
        await self.config.loss.set(loss_emoji)
        await self.config.lossu.set(loss_unicode)
        await self.config.dispute.set(dispute_emoji)
        await self.config.disputeu.set(dis_unicode)

        await self._add_wld(message2)

        await ctx.send("Success")

    @fightset.command(name="reset")
    async def fightset_reset(self, ctx):
        """Clears all data, be careful!"""
        await self.config.clear_all()
        await ctx.send("Success")

    @fightset.command(name="trackreset")
    async def fightset_trackreset(self, ctx):
        """Clears all message trackers!"""
        await self.config.srtracker.set({})
        await ctx.send("Success")

    @fightset.command(name="bestof")
    async def fightset_bestof(self, ctx, incount, t_id=None):
        """Adjust # of games played per match. Must be an odd number"""
        # guild = ctx.message.guild
        if not t_id and not await self._activefight(ctx):
            await ctx.send("No active fight to adjust")
            return

        if not t_id:
            t_id = await self._activefight(ctx)

        curr_fight = await self._getfight(ctx.guild, t_id)

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

        curr_fight["RULES"]["BESTOF"] = num
        await self._save_fight(ctx, t_id, curr_fight)
        await ctx.send("Tourney ID " + t_id + " is now Best of " + str(num))

    @fightset.command(name="bestoffinal")
    async def fightset_bestoffinal(self, ctx, incount, t_id=None):
        """Adjust # of games played in finals. Must be an odd number
        (Does not apply to tournament types without finals, such as Round Robin)"""
        # guild = ctx.message.guild
        if not t_id and not await self._activefight(ctx):
            await ctx.send("No active fight to adjust")
            return

        if not t_id:
            t_id = await self._activefight(ctx)

        curr_fight = await self._getfight(ctx.guild, t_id)

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

        curr_fight["RULES"]["BESTOFFINAL"] = num
        await self._save_fight(ctx, t_id, curr_fight)
        await ctx.send("Tourney ID " + t_id + " is now Best of " + str(num) + " in the Finals")

    @fightset.command(name="current")
    async def fightset_current(self, ctx, t_id):
        """Sets the current tournament to passed ID"""
        # guild = ctx.message.guild
        curr_fight = await self._getfight(ctx.guild, t_id)

        if not curr_fight:
            await ctx.send("No tourney found with that ID")
            return

        # self.the_data[guild.id]["CURRENT"] = t_id
        # self.save_data()
        await self.config.guild(ctx.guild).current.set(t_id)

        await ctx.send("Current tournament set to " + t_id)

    @fightset.command(name="list")
    async def fightset_list(self, ctx):
        """Lists all current and past fights"""
        # guild = ctx.message.guild

        for page in pagify(str(await self.config.guild(ctx.guild).tourneys())):
            await ctx.send(box(page))

        await ctx.send("Done")

    @fightset.command(name="test")
    async def fightset_test(self, ctx):
        """testing"""
        await ctx.send(str(await self.config.all_guilds()))

    @fightset.command(name="open")
    async def fightset_open(self, ctx):
        """Toggles the open status of current tournament"""
        # guild = ctx.message.guild
        if not await self._activefight(ctx):
            await ctx.send("No active fight to adjust")
            return

        t_id = await self._activefight(ctx)
        curr_fight = await self._getcurrentfight(ctx)
        curr_fight["OPEN"] = not curr_fight["OPEN"]

        await self._save_fight(ctx, t_id, curr_fight)

        await ctx.send("Tournament Open status is now set to: " + str(curr_fight["OPEN"]))

    @fightset.command(name="name")
    async def fightset_name(self, ctx, inname, t_id=None):
        """Renames the tournament"""
        # guild = ctx.message.guild
        if not t_id and not await self._activefight(ctx):
            await ctx.send("No active fight to adjust")
            return

        if not t_id:
            t_id = await self._activefight(ctx)

        curr_fight = await self._getfight(ctx.guild, t_id)

        curr_fight["NAME"] = inname
        await self._save_fight(ctx, t_id, curr_fight)
        await ctx.send("Tourney ID " + t_id + " is now called " + inname)

    @fightset.command(name="start")
    async def fightset_start(self, ctx):
        """Starts the current tournament, must run setup first"""

        def check(m):  # Check Message from author
            return m.author == ctx.author and m.channel == ctx.channel

        curr_fight = await self._getcurrentfight(ctx)
        t_id = await self._activefight(ctx)

        if not t_id:
            await ctx.send("No current fight to start")
            return

        if (await self.config.win()) is None:  # Emoji not setup
            await ctx.send("Emojis have not been configured, see `[p]fightset emoji`")
            return

        if (await self._get_announcechnnl(ctx.guild)) is None:  # Announcechnnl not setup
            await ctx.send(
                "Announcement channel has not been configured, see `[p]fightset guild announce`"
            )
            return

        if (await self._get_reportchnnl(ctx.guild)) is None:  # Reportchnnl not setup
            await ctx.send(
                "Self-Report channel has not been configured, see `[p]fightset guild report`"
            )
            return

        if curr_fight["TYPEDATA"]:  # Empty dicionary {} resolves to False
            await ctx.send(
                "Looks like this tournament has already started.\nDo you want to delete all match data and restart? "
                "(yes/no)"
            )

            try:
                answer = await self.bot.wait_for("message", check=check, timeout=120)
            except asyncio.TimeoutError:
                await ctx.send("Cancelled due to timeout")
                return

            if not answer.content or answer.content.upper() not in ["YES", "Y"]:
                await ctx.send("Cancelled")
                return

        curr_fight["OPEN"] = False  # first close the tournament
        await self._save_fight(ctx, t_id, curr_fight)

        if curr_fight["RULES"]["TYPE"] == 0:  # Round-Robin
            await self._rr_start(ctx, t_id)

    @fightset.command(name="setup")
    async def fightset_setup(self, ctx):
        """Setup a new tournament!
        Default settings are as follows
        Name: Tourney # (counts from 0)
        Best of: 1
        Best of (final): 1
        Self Report: True
        Type: 0 (Round Robin)"""
        # guild = ctx.message.guild
        # currServ = self.the_data[guild.id]
        t_id = str(
            len(await self.config.guild(ctx.guild).tourneys())
        )  # Can just be len without +1, tourney 0 makes len 1, tourney 1 makes len 2, etc

        # currServ["CURRENT"] = t_id
        curr_fight = self.default_tourney.copy()
        curr_fight["NAME"] = "Tourney " + str(t_id)

        await self._save_fight(ctx, t_id, curr_fight)

        await ctx.send("Tournament has been created!\n\n" + str(curr_fight))

        await ctx.send(
            "Adjust settings as necessary, then open the tournament with [p]fightset open"
        )

    @fightset.command(name="stop")
    async def fightset_stop(self, ctx):
        """Stops current tournament"""

        def check(m):  # Check Message from author
            return m.author == ctx.author and m.channel == ctx.channel

        # guild = ctx.message.guild
        if not await self._activefight(ctx):
            await ctx.send("No active fight to adjust")
            return

        # author = ctx.message.author
        # currServ = self.the_data[guild.id]

        await ctx.send(
            "Current fight ID is "
            + str(await self.config.guild(ctx.guild).current())
            + "\nOkay to stop? (yes/no)"
        )

        try:
            answer = await self.bot.wait_for("message", check=check, timeout=120)
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
        if ctx.invoked_subcommand is None or isinstance(ctx.invoked_subcommand, commands.Group):
            pass

    @fightset_guild.command(name="selfreport")
    async def fightset_guild_selfreport(self, ctx):
        """Toggles the ability to self-report scores for all tournaments"""
        curflag = await self.config.guild(ctx.guild).settings.selfreport()

        await self.config.guild(ctx.guild).settings.selfreport.set(not curflag)

        await ctx.send("Self-Reporting ability is now set to: " + str(not curflag))

    @fightset_guild.command(name="report")
    async def fightset_guild_report(self, ctx, channel: discord.TextChannel = None):
        """Set the channel for self-reporting matches"""
        if channel is None:
            channel = ctx.channel

        await self.config.guild(ctx.guild).settings.reportchnnl.set(channel.id)

        channel = await self._get_reportchnnl(ctx.guild)
        await ctx.send("Self-Reporting Channel is now set to: " + channel.mention)

    @fightset_guild.command(name="announce")
    async def fightset_guild_announce(self, ctx, channel: discord.TextChannel = None):
        """Set the channel for tournament announcements"""
        if channel is None:
            channel = ctx.channel

        await self.config.guild(ctx.guild).settings.announcechnnl.set(channel.id)

        channel = await self._get_announcechnnl(ctx.guild)
        await ctx.send("Announcement Channel is now set to: " + channel.mention)

    @fightset_guild.command(name="setadmin")
    async def fightset_guild_setadmin(self, ctx, role: discord.Role = None):
        """Chooses the tournament-admin role. CAREFUL: This grants the ability to override self-reported scores!"""
        await self.config.guild(ctx.guild).settings.admin.set(role.id)

        await ctx.send("Tournament Admin role is now set to: " + role.mention)

    # **********************Private command group start*********************
    async def _add_wld(self, message: discord.Message):
        """Adds assigned Win-Loss-Dispute reactions to message"""

        win = await self.config.win()
        loss = await self.config.loss()
        dispute = await self.config.dispute()

        if not (await self.config.winu()):  # If not unicode
            win = self.bot.get_emoji(win)
        if not (await self.config.lossu()):
            loss = self.bot.get_emoji(loss)
        if not (await self.config.disputeu()):
            dispute = self.bot.get_emoji(dispute)

        await message.add_reaction(win)
        await message.add_reaction(loss)
        await message.add_reaction(dispute)

    async def _get_win_str(self):
        """Returns win emoji ready for str"""
        win = await self.config.win()

        if not (await self.config.winu()):  # If not unicode
            win = str(self.bot.get_emoji(win))
        return win

    async def _get_loss_str(self):
        """Returns loss emoji ready for str"""

        loss = await self.config.loss()

        if not (await self.config.lossu()):
            loss = str(self.bot.get_emoji(loss))
        return loss

    async def _get_dispute_str(self):
        """Returns dispute emoji ready for str"""
        dispute = await self.config.dispute()

        if not (await self.config.disputeu()):
            dispute = str(self.bot.get_emoji(dispute))
        return dispute

    async def _wait_for_emoji(self, ctx: commands.Context, messagetext):
        """
        Asks the user to react to this message and returns the emoji string if unicode
        or ID if custom.

        :param ctx:
        :raises asyncio.TimeoutError:
            If the user does not respond in time.
        :return:
        """
        if messagetext:
            message = await ctx.send(
                "Please react to this message with the reaction you"
                " would like for " + messagetext + ", you have 20 seconds to"
                " respond."
            )
        else:
            message = await ctx.send(
                "Please react to this message with the reaction you"
                " would like, you have 20 seconds to"
                " respond."
            )

        def _wait_check(react, user):
            msg = react.message
            return msg.id == message.id and user.id == ctx.author.id

        reaction, _ = await ctx.bot.wait_for("reaction_add", check=_wait_check, timeout=20)

        try:
            ret = reaction.emoji.id
            is_unicode = False
        except AttributeError:
            # The emoji is unicode
            ret = reaction.emoji
            is_unicode = True

        return ret, reaction.emoji, is_unicode

    async def _save_fight(self, ctx, t_id, curr_fight):
        """Save a passed fight"""

        guild_group = self.config.guild(ctx.guild)
        async with guild_group.tourneys() as allTourney:
            allTourney[t_id] = curr_fight

        # allTourney = await self.config.guild(ctx.guild).tourneys()
        # allTourney[t_id] = curr_fight
        # await self.config.guild(ctx.guild).tourneys.set(allTourney)

    async def _save_tracker(self, ctx, messageid: int, match_data):
        """Save a passed fight"""

        async with self.config.srtracker() as allTracker:
            allTracker[str(messageid)] = match_data

        # allTracker = dict(await self.config.srtracker())
        # allTracker[messageid] = match_data

        # await self.config.srtracker.set(allTracker)

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

    async def _infight(self, ctx: commands.Context, t_id, userid):
        """Checks if passed member is already in the tournament"""
        # return userid in self.the_data[guildID]["TOURNEYS"][t_id]["PLAYERS"]
        return userid in (await self.config.guild(ctx.guild).tourneys())[t_id]["PLAYERS"]

    async def _embed_tourney(self, ctx, t_id):
        """Prints a pretty embed of the tournament"""
        # _placeholder Todo
        pass

    async def _comparescores(self, ctx):
        """Checks user submitted scores for inconsistancies"""
        # _comparescores Todo
        pass

    async def _parseuser(self, guild: discord.Guild, t_id, userid):
        """Finds user in the tournament"""
        # if self._getfight(guildID, t_id)["RULES"]["TYPE"] == 0:  # RR

        the_fight = await self._getfight(guild, t_id)

        if userid not in the_fight["PLAYERS"]:  # Shouldn't happen, _infight check first
            return False

        if the_fight["RULES"]["TYPE"] == 0:
            return await self._rr_parseuser(guild, t_id, userid)

        return False

    def _get_team(self, ctx: commands.Context, teaminfo):
        """Team info is a list of userid's. Returns a list of user objects"""
        outlist = []
        for playerid in teaminfo:
            outlist.append(self._get_user_from_id(playerid))
        return outlist

    # async def _getsettings(self, ctx: commands.Context):
    # # return self.the_data[guildID]["SETTINGS"]
    # return await self.config.guild(ctx.guild).settings()

    # async def _get_message_from_id_old(self, channelid, messageid):
    # return await self.bot.get_message(self._get_channel_from_id(channelid), messageid)

    async def _get_message_from_id(self, guild: discord.Guild, message_id: int):
        """
        Tries to find a message by ID in the current guild context.
        :param ctx:
        :param message_id:
        :return:
        """
        for channel in guild.text_channels:
            try:
                return await channel.get_message(message_id)
            except discord.NotFound:
                pass
            except AttributeError:  # VoiceChannel object has no attribute 'get_message'
                pass

        return None

    async def _get_announcechnnl(self, guild: discord.Guild):
        channelid = await self.config.guild(guild).settings.announcechnnl()
        channel = self._get_channel_from_id(channelid)
        return channel

    async def _get_reportchnnl(self, guild: discord.Guild):
        channelid = await self.config.guild(guild).settings.reportchnnl()
        channel = self._get_channel_from_id(channelid)
        return channel

    def _get_channel_from_id(self, channelid):
        return self.bot.get_channel(channelid)

    def _get_user_from_id(self, userid):
        # guild = self._get_guild_from_id(guildID)
        # return discord.utils.get(guild.members, id=userid)
        return self.bot.get_user(userid)

    def _get_guild_from_id(self, guild_id):
        return self.bot.get_guild(guild_id)

    async def _getfight(self, guild: discord.Guild, t_id):
        # return self.the_data[guildID]["TOURNEYS"][t_id]
        return (await self.config.guild(guild).tourneys())[t_id]

    async def _getcurrentfight(self, ctx: commands.Context):
        # if not self._activefight(guildID):
        # return None

        # return self._getfight(guildID, self._activefight(guildID))
        is_active = await self._activefight(ctx)
        if not is_active:
            return None
        return await self._getfight(ctx.guild, is_active)

    async def _report_win(self, guild: discord.Guild, t_id, m_id, member: discord.Member):
        """Reports a win for member in match"""
        the_fight = await self._getfight(guild, t_id)

        if member.id not in the_fight["PLAYERS"]:  # Shouldn't happen
            return False

        if the_fight["RULES"]["TYPE"] == 0:
            return await self._rr_report_wl(guild, t_id, m_id, member, True)

    async def _report_loss(self, guild: discord.Guild, t_id, m_id, member: discord.Member):
        """Reports a win for member in match"""
        the_fight = await self._getfight(guild, t_id)

        if member.id not in the_fight["PLAYERS"]:  # Shouldn't happen
            return False

        if the_fight["RULES"]["TYPE"] == 0:
            return await self._rr_report_wl(guild, t_id, m_id, member, False)

    async def _report_dispute(self, guild: discord.Guild, t_id, m_id):
        """Reports a win for member in match"""
        the_fight = await self._getfight(guild, t_id)
        # ToDo: What is this supposed to be again?
        # if member.id not in the_fight["PLAYERS"]:  # Shouldn't happen
        #     return False

        if the_fight["RULES"]["TYPE"] == 0:
            return await self._rr_report_dispute(guild, t_id, m_id)

        return False

    # *********** References to "TYPEDATA" must be done per tournament mode (Below this line) *******

    # **********************Single Elimination***************************
    async def _elim_setup(self, t_id):
        # ToDo Elim setup
        pass

    async def _elim_start(self, t_id):
        # ToDo Elim start
        pass

    async def _elim_update(self, m_id):
        # ToDo elim update
        pass

    # **********************Round-Robin**********************************

    async def _rr_report_wl(self, guild: discord.Guild, t_id, m_id, user: discord.Member, is_win):
        """User reports a win or loss for member in match"""
        the_fight = await self._getfight(guild, t_id)

        teamnum = await self._rr_matchperms(guild, t_id, user.id, m_id)

        # _rr_parseuser has already be run in on_raw_reaction_add, should be safe to proceed without checking again

        if (is_win and teamnum == 1) or (not is_win and teamnum == 2):
            score1 = math.ceil(the_fight["RULES"]["BESTOF"] / 2)
            score2 = 0
        else:
            score1 = 0
            score2 = math.ceil(the_fight["RULES"]["BESTOF"] / 2)

        if teamnum == 1:
            the_fight["TYPEDATA"]["MATCHES"][m_id]["USERSCORE1"]["SCORE1"] = score1
            the_fight["TYPEDATA"]["MATCHES"][m_id]["USERSCORE1"]["SCORE2"] = score2

        if teamnum == 2:
            the_fight["TYPEDATA"]["MATCHES"][m_id]["USERSCORE2"]["SCORE1"] = score1
            the_fight["TYPEDATA"]["MATCHES"][m_id]["USERSCORE2"]["SCORE2"] = score2

        await self._save_fight(None, t_id, the_fight)

    async def _rr_report_dispute(self, guild: discord.Guild, t_id, m_id):
        """Reports a disputed match"""
        the_fight = await self._getfight(guild, t_id)

        the_fight["TYPEDATA"]["MATCHES"][m_id]["DISPUTE"] = True

        await self._save_fight(None, t_id, the_fight)

    async def _rr_finalize(self, guild: discord.Guild, t_id):
        """Applies scores to all non-disputed matches"""
        the_fight = await self._getfight(guild, t_id)
        the_round = the_fight["TYPEDATA"]["SCHEDULE"][the_fight["TYPEDATA"]["ROUND"]]

        for m_id in the_round:
            if not await self._rr_matchover(guild, t_id, m_id):
                match = the_fight["TYPEDATA"]["MATCHES"][m_id]
                if (
                    (match["USERSCORE1"]["SCORE1"] == math.ceil(the_fight["RULES"]["BESTOF"] / 2))
                    != (
                        match["USERSCORE1"]["SCORE2"]
                        == math.ceil(the_fight["RULES"]["BESTOF"] / 2)
                    )
                    and (
                        match["USERSCORE2"]["SCORE1"]
                        == math.ceil(the_fight["RULES"]["BESTOF"] / 2)
                    )
                    != (
                        match["USERSCORE2"]["SCORE2"]
                        == math.ceil(the_fight["RULES"]["BESTOF"] / 2)
                    )
                    and (match["USERSCORE1"]["SCORE1"] == match["USERSCORE2"]["SCORE1"])
                    and (match["USERSCORE1"]["SCORE2"] == match["USERSCORE2"]["SCORE2"])
                ):

                    the_fight["TYPEDATA"]["MATCHES"][m_id]["SCORE1"] = the_fight["TYPEDATA"][
                        "MATCHES"
                    ][m_id]["USERSCORE1"]["SCORE1"]
                    the_fight["TYPEDATA"]["MATCHES"][m_id]["SCORE1"] = the_fight["TYPEDATA"][
                        "MATCHES"
                    ][m_id]["USERSCORE2"]["SCORE2"]
                    await self._save_fight(None, t_id, the_fight)
                else:
                    await self._rr_report_dispute(guild, t_id, m_id)

    async def _rr_parseuser(self, guild: discord.Guild, t_id, userid):
        the_fight = await self._getfight(guild, t_id)
        matches = the_fight["TYPEDATA"]["MATCHES"]
        schedule = the_fight["TYPEDATA"]["SCHEDULE"]

        for rnd in schedule:
            for mID in rnd:
                teamnum = await self._rr_matchperms(guild, t_id, userid, mID)
                if teamnum and not await self._rr_matchover(
                    guild, t_id, mID
                ):  # User is in this match, check if it's done yet
                    return mID

        return False  # All matches done or not in tourney

    async def _rr_matchover(self, guild: discord.Guild, t_id, m_id):
        the_fight = await self._getfight(guild, t_id)
        match = the_fight["TYPEDATA"]["MATCHES"][m_id]

        if (match["SCORE1"] == math.ceil(the_fight["RULES"]["BESTOF"] / 2)) != (
            match["SCORE2"] == math.ceil(the_fight["RULES"]["BESTOF"] / 2)
        ):
            return True

        return False

    async def _rr_roundover(self, ctx: commands.Context, t_id):
        the_fight = await self._getfight(ctx.guild, t_id)
        the_round = the_fight["TYPEDATA"]["SCHEDULE"][the_fight["TYPEDATA"]["ROUND"]]

        for m_id in the_round:
            if not await self._rr_matchover(ctx.guild, t_id, m_id):
                return False
        return True

    async def _rr_matchperms(self, guild: discord.Guild, t_id, userid, m_id):
        # if self._get_user_from_id(guildID, userid) # Do an if-admin at start
        the_fight = await self._getfight(guild, t_id)
        if userid in the_fight["TYPEDATA"]["MATCHES"][m_id]["TEAM1"]:
            return 1

        if userid in the_fight["TYPEDATA"]["MATCHES"][m_id]["TEAM2"]:
            return 2

        return False

    async def _rr_setup(self, ctx: commands.Context, t_id):

        the_fight = await self._getfight(ctx.guild, t_id)
        fight_data = the_fight["TYPEDATA"]

        get_schedule = self._rr_schedule(the_fight["PLAYERS"])

        fight_data["SCHEDULE"] = get_schedule[0]
        fight_data["MATCHES"] = get_schedule[1]
        fight_data["ROUND"] = 0

        await self._save_fight(ctx, t_id, the_fight)

    async def _rr_printround(self, ctx: commands.Context, t_id, r_id):

        the_fight = await self._getfight(ctx.guild, t_id)
        fight_data = the_fight["TYPEDATA"]

        channel = await self._get_announcechnnl(ctx.guild)
        if channel:  # r_id starts at 0, so print +1. Never used for computation, so doesn't matter
            await channel.send("**Round " + str(r_id + 1) + " is starting**")

        channel = await self._get_reportchnnl(ctx.guild)

        for m_id in fight_data["SCHEDULE"][r_id]:
            team1 = self._get_team(ctx, fight_data["MATCHES"][m_id]["TEAM1"])
            team2 = self._get_team(ctx, fight_data["MATCHES"][m_id]["TEAM2"])

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
            outembed = discord.Embed(title="Match ID: " + m_id, color=0x0000BF)
            outembed.add_field(name="Team 1", value=mention1, inline=False)
            outembed.add_field(name="Team 2", value=mention2, inline=False)
            outembed.set_footer(
                text=(await self._get_win_str())
                + " Report Win || "
                + (await self._get_loss_str())
                + " Report Loss || "
                + (await self._get_dispute_str())
                + " Dispute Result"
            )

            if channel:
                message = await channel.send(embed=outembed)

                await self._add_wld(message)

                trackmessage = self.default_tracker.copy()
                trackmessage["TID"] = t_id
                trackmessage["MID"] = m_id
                trackmessage["RID"] = r_id
                trackmessage["GUILDID"] = ctx.guild.id
                await self._save_tracker(ctx, message.id, trackmessage)

            # await ctx.send(team1 + " vs " + team2 + " || Match ID: " + match)

    async def _rr_start(self, ctx, t_id):

        await self._rr_setup(ctx, t_id)
        channel = await self._get_announcechnnl(ctx.guild)
        if channel:
            await channel.send("**Tournament is Starting**")

        await self._rr_printround(ctx, t_id, 0)

    # async def _rr_score(self, ctx: commands.Context, tID, mID, t1points, t2points):
    # def check(m):    #Check Message from author
    # return m.author == ctx.author and m.channel == ctx.channel
    # theT = await self._getfight(ctx.guild, tID)
    # theD = theT["TYPEDATA"]

    # # if t1points and t2points:
    # #    theD["MATCHES"][mID]["SCORE1"] = t1points
    # #    theD["MATCHES"][mID]["SCORE2"] = t2points
    # #    self.save_data()
    # #    return

    # if not t1points:
    # await ctx.send("Entering scores for match ID: " + mID + "\n\n")
    # await ctx.send("How many points did TEAM1 get?")
    # if await self._rr_matchperms(ctx.guild, tID, ctx.author.id, mID) == 1:
    # await ctx.send("*HINT: You are on TEAM1*")
    # # answer = await self.bot.wait_for_message(timeout=120, author=author)

    # try:
    # answer = await self.bot.wait_for('message', check=check, timeout=120)
    # except asyncio.TimeoutError:
    # await ctx.send("Cancelled due to timeout")
    # return

    # try:
    # t1points = int(answer.content)
    # except:
    # await ctx.send("That's not a number!")
    # return

    # if not t2points:
    # await ctx.send("How many points did TEAM2 get?")
    # if await self._rr_matchperms(ctx.guild, tID, ctx.author.id, mID) == 2:
    # await ctx.send("*HINT: You are on TEAM2*")
    # # answer = await self.bot.wait_for_message(timeout=120, author=author)
    # try:
    # answer = await self.bot.wait_for('message', check=check, timeout=120)
    # except asyncio.TimeoutError:
    # await ctx.send("Cancelled due to timeout")
    # return

    # try:
    # t2points = int(answer.content)
    # except:
    # await ctx.send("That's not a number!")
    # return

    # if (t1points == math.ceil(theT["RULES"]["BESTOF"]/2) or
    # t2points == math.ceil(theT["RULES"]["BESTOF"]/2)):
    # theD["MATCHES"][mID]["SCORE1"] = t1points
    # theD["MATCHES"][mID]["SCORE2"] = t2points
    # else:
    # await ctx.send("Invalid scores, nothing will be updated")
    # return

    # await self._save_fight(theT)
    # await ctx.send("Scores have been saved successfully!")

    # # if self._rr_checkround(guildID, tID)

    def _rr_schedule(self, inlist):
        """ Create a schedule for the teams in the list and return it"""
        s = []  # Schedule list
        out_id = {}  # Matches

        first_id = [
            "A",
            "B",
            "C",
            "D",
            "E",
            "F",
            "G",
            "H",
            "I",
            "J",
            "K",
            "L",
            "M",
            "N",
            "O",
            "P",
            "Q",
            "R",
            "S",
            "T",
            "U",
            "V",
            "W",
            "X",
            "Y",
            "Z",
        ]  # God dammit this could've been a string

        if len(inlist) % 2 == 1:
            inlist = inlist + ["BYE"]

        for i in range(len(inlist)):

            mid = int(len(inlist) / 2)
            l1 = inlist[:mid]
            l2 = inlist[mid:]
            l2.reverse()

            match_letter = ""
            j = i
            while j + 1 > 26:
                match_letter += first_id[int(j + 1) % 26 - 1]

                j = (j + 1) / 26 - 1
            match_letter += first_id[int(j + 1) % 26 - 1]
            match_letter = match_letter[::-1]

            m_id = []
            for ix in range(len(l1)):
                m_id += [match_letter + str(ix)]

            r_players = list(zip(l1, l2))
            team_cnt = 0
            for ID in m_id:
                out_id[ID] = self.default_match.copy()
                out_id[ID]["TEAM1"] = [r_players[team_cnt][0]]
                out_id[ID]["TEAM2"] = [r_players[team_cnt][1]]
                # out_id[ID] = {
                # "TEAM1": [r_players[team_cnt][0]],
                # "TEAM2": [r_players[team_cnt][1]],
                # "SCORE1": 0,
                # "SCORE2": 0,
                # "USERSCORE1": {"SCORE1": 0, "SCORE2": 0},
                # "USERSCORE2": {"SCORE1": 0, "SCORE2": 0}
                # }

                team_cnt += 1

            # List of match ID's is now done

            s += [m_id]  # Schedule of matches
            inlist.insert(1, inlist.pop())

        outlist = [[], {}]
        outlist[0] = s
        outlist[1] = out_id
        # outlist[0] is list schedule of matches
        # outlist[1] is dict data of matches

        return outlist

    # **************** Attempt 2, borrow from Squid*******

    async def on_raw_reaction_add(
        self, emoji: discord.PartialEmoji, message_id: int, channel_id: int, user_id: int
    ):
        """
        Event handler for long term reaction watching.
        :param discord.PartialReactionEmoji emoji:
        :param int message_id:
        :param int channel_id:
        :param int user_id:
        :return:
        """
        tracker = await self.config.srtracker()

        if str(message_id) not in tracker:
            return

        log_channel = self._get_channel_from_id(390927071553126402)

        # await log_channel.send("Message ID: "+str(message_id)+" was just reacted to")

        tracker = tracker[str(message_id)]

        guild = self.bot.get_guild(tracker["GUILDID"])
        member = guild.get_member(user_id)
        if member.bot:
            return

        if tracker["MID"] != (await self._parseuser(guild, tracker["TID"], member.id)):
            message = await self._get_message_from_id(guild, message_id)
            await message.remove_reaction(emoji, member)
            return

        channel = guild.get_channel(channel_id)
        message = await channel.get_message(message_id)

        if emoji.is_custom_emoji():
            emoji_id = emoji.id
        else:
            emoji_id = emoji.name

        wld = [
            (await self.config.win()),
            (await self.config.loss()),
            (await self.config.dispute()),
        ]
        if emoji_id not in wld:  # Not sure if this works # It does
            await message.remove_reaction(emoji, member)
            return

        if emoji_id == wld[0]:
            await self._report_win()
            await log_channel.send("Message ID: " + str(message_id) + " was reporting a win")
        if emoji_id == wld[1]:
            await self._report_loss()
            await log_channel.send("Message ID: " + str(message_id) + " was reporting a loss")
        if emoji_id == wld[2]:
            await self._report_dispute(guild, tracker["TID"], tracker["MID"])
            await log_channel.send("Message ID: " + str(message_id) + " was reporting a dispute")
