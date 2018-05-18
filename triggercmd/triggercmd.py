import asyncio

import discord

from redbot.core import Config, checks, commands

from redbot.core.bot import Red


class TriggerCmd:
    """
    Trigger cog to end all trigger cogs
    """

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9811198108111121, force_registration=True)

        default_global = {
            "triggers": []
        }
        default_guild = {
            "triggers": []
        }
        default_role = {
            "triggers": []
        }
        default_channel = {
            "triggers": []
        }
        default_user = {
            "triggers": []
        }
        default_member = {
            "triggers": []
        }

        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)
        self.config.register_role(**default_role)
        self.config.register_channel(**default_channel)
        self.config.register_user(**default_user)
        self.config.register_member(**default_member)


    @commands.group()
    async def trigger(self, ctx: commands.Context):
        """
        My custom cog
       
        Extra information goes here
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @trigger.command(name="add")
    async def _trigger_add(self, ctx: commands.Context, *, trigger: str):
        """
        Add a new trigger

        Trigger can be a word, phrase, or regex
        This will begin the setup process for configuring the triggers
        """
        guild = ctx.guild
        author = ctx.author
        channel = ctx.channel

        def check(m):
            return m.author == author and m.channel == channel and m.content.upper() in ["Y","N","YES","NO"]

        await ctx.send("Is `{}` a regex trigger? (Y\\N)".format(trigger))
        try:
            answer = await self.bot.wait_for('message', timeout=30, check=check)
        except asyncio.TimeoutError:
            await ctx.send("Timed out, canceling")
            return

        is_regex = answer.content.upper() in ["Y", "YES"]

        await ctx.send("Regex processing for this trigger is **{}**".format("Enabled" if is_regex else "Disabled"))


        await ctx.send("Should this trigger apply to all guilds?")
        try:
            answer = await self.bot.wait_for('message', timeout=30, check=check)
        except asyncio.TimeoutError:
            await ctx.send("Timed out, canceling")
            return

        is_global = answer.content.upper() in ["Y", "YES"]

        await ctx.send("Should this trigger apply to only one user?")
        try:
            answer = await self.bot.wait_for('message', timeout=30, check=check)
        except asyncio.TimeoutError:
            await ctx.send("Timed out, canceling")
            return
        if not is_global: # Options: Guild only, Channel only, Member only, Role only
            pass




    async def on_message(self, message):
        pass


class Trigger:
    """
    Trigger class
    """

    def __init__(self, trigger: str, is_regex: bool, scope: str, response_text: str, *response_code: str):
        self.trigger = trigger
        self.is_regex = is_regex
        self.scope = scope.lower()
        self.response_text = response_text
        self.response_code = response_code

    async def save(self, config, obj=None):
        if self.scope == "global":
            self.config = config
        elif self.scope == "guild":
            self.config = config.guild(obj)
        elif self.scope == "role":
            self.config = config.role(obj)
        elif self.scope == "channel":
            self.config = config.channel(obj)
        elif self.scope == "user":
            self.config = config.user(obj)
        elif self.scope == "member":
            self.config = config.member(obj)
        else:
            # Failed to save
            return

        async with self.config.triggers() as tr:
            tr.append(
                {
                    "trigger": self.trigger,
                    "is_regex": self.is_regex,
                    "response_text": self.response_text,
                    "response_code": self.response_code
                }
            )