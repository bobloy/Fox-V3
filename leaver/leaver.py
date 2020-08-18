import discord
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.commands import Cog, Context


class Leaver(Cog):
    """
    Creates a goodbye message when people leave
    """

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9811198108111121, force_registration=True)
        default_guild = {"channel": ""}

        self.config.register_guild(**default_guild)

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    @commands.group(aliases=["setleaver"])
    @checks.mod_or_permissions(administrator=True)
    async def leaverset(self, ctx):
        """Adjust leaver settings"""
        if ctx.invoked_subcommand is None:
            pass

    @leaverset.command()
    async def channel(self, ctx: Context):
        """Choose the channel to send leave messages to"""
        guild = ctx.guild
        await self.config.guild(guild).channel.set(ctx.channel.id)
        await ctx.maybe_send_embed("Channel set to " + ctx.channel.name)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        guild = member.guild

        if await self.bot.cog_disabled_in_guild(self, guild):
            return

        channel = await self.config.guild(guild).channel()

        if channel != "":
            channel = guild.get_channel(channel)
            out = "{}{} has left the server".format(
                member, member.nick if member.nick is not None else ""
            )
            if await self.bot.embed_requested(channel, member):
                await channel.send(
                    embed=discord.Embed(
                        description=out, color=(await self.bot.get_embed_color(channel))
                    )
                )
            else:
                await channel.send(out)
        else:
            pass
