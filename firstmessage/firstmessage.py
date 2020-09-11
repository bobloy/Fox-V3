import logging

import discord
from redbot.core import Config, commands
from redbot.core.bot import Red

log = logging.getLogger("red.fox_v3.firstmessage")


class FirstMessage(commands.Cog):
    """
    Provides a link to the first message in the provided channel
    """

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=701051141151167710111511597103101, force_registration=True
        )

        default_guild = {}

        self.config.register_guild(**default_guild)

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    @commands.command()
    async def firstmessage(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """
        Provide a link to the first message in current or provided channel.
        """
        if channel is None:
            channel = ctx.channel
        try:
            message: discord.Message = (
                await channel.history(limit=1, oldest_first=True).flatten()
            )[0]
        except (discord.Forbidden, discord.HTTPException):
            log.exception(f"Unable to read message history for {channel.id=}")
            await ctx.maybe_send_embed("Unable to read message history for that channel")
            return

        em = discord.Embed(description=f"[First Message in {channel.mention}]({message.jump_url})")
        em.set_author(name=message.author.display_name, icon_url=message.author.avatar_url)

        await ctx.send(embed=em)
