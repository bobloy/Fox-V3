import logging
import re

import aiohttp
from redbot.core import Config, commands
from redbot.core.bot import Red

log = logging.getLogger("red.fox_v3.isitdown")


class IsItDown(commands.Cog):
    """
    Cog Description

    Less important information about the cog
    """

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=0, force_registration=True)

        default_guild = {"iids": []}  # List of tuple pairs (channel_id, website)

        self.config.register_guild(**default_guild)

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    @commands.command(alias=["iid"])
    async def isitdown(self, ctx: commands.Context, url_to_check):
        """
        Check if the provided url is down

        Alias: iid
        """
        try:
            resp = await self._check_if_down(url_to_check)
        except AssertionError:
            await ctx.maybe_send_embed("Invalid URL provided. Make sure not to include `http://`")
            return

        if resp["isitdown"]:
            await ctx.maybe_send_embed(f"{url_to_check} is DOWN!")
        else:
            await ctx.maybe_send_embed(f"{url_to_check} is UP!")

    async def _check_if_down(self, url_to_check):
        url = re.compile(r"https?://(www\.)?")
        url.sub("", url_to_check).strip().strip("/")

        url = f"https://isitdown.site/api/v3/{url}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                assert response.status == 200
                resp = await response.json()
        return resp
