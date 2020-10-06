import asyncio
import logging
import os
from concurrent.futures.process import ProcessPoolExecutor
from concurrent.futures.thread import ThreadPoolExecutor
from typing import Optional


import discord
from ciphey import decrypt, iface
from redbot.core import Config, commands
from redbot.core.bot import Red
from ciphey.__main__ import main

log = logging.getLogger("red.fox_v3.decrypt")


class Decrypt(commands.Cog):
    """
    Fast generic decryption on any string
    """

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=0, force_registration=True)

        default_guild = {}

        self.config.register_guild(**default_guild)

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    @commands.command(name="decrypt")
    async def _decrypt(self, ctx: commands.Context, *, encrypted_string):
        """Attempt to decrypt any encrypted text"""
        async with ctx.typing():
            iconfig = iface.Config().library_default()
            iconfig.timeout = 10
            iconfig.complete_config()

            future = self.bot.loop.run_in_executor(
                None,
                decrypt,
                iconfig,
                encrypted_string,
            )

            # TODO: This kills the bot somehow, waiting
            try:
                result = await asyncio.wait_for(future, timeout=15, loop=self.bot.loop)
            except asyncio.TimeoutError:
                result = None

            if result:
                await ctx.maybe_send_embed(result)
            else:
                await ctx.maybe_send_embed("Failed to decrypt")
