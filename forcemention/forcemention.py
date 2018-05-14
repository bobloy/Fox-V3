import discord

from redbot.core import Config, checks, commands

from redbot.core.bot import Red


class ForceMention:
    """
    V3 Cog Template
    """

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9811198108111121, force_registration=True)
        default_global = {}
        default_guild = {}

        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

    @checks.admin_or_permissions(manage_roles=True)
    @commands.command()
    async def forcemention(self, ctx: commands.Context, role: discord.Role):
        """
       Mentions that role, regardless if it's unmentionable
       """
        if not role.mentionable:
            await role.edit(mentionable=True)
            await ctx.send(role.mention)
            await role.edit(mentionable=False)
        else:
            await ctx.send(role.mention)
