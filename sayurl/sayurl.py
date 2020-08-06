import aiohttp
import html2text
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.commands import Cog
from redbot.core.utils.chat_formatting import pagify


async def fetch_url(session, url):
    async with session.get(url) as response:
        assert response.status == 200
        return await response.text()


class SayUrl(Cog):
    """
    V3 Cog Template
    """

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9811198108111121, force_registration=True)
        default_global = {}
        default_guild = {}

        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    @commands.command()
    async def sayurl(self, ctx: commands.Context, url):
        """
        Converts a URL to something readable

        Works better on smaller websites
        """

        h = html2text.HTML2Text()
        h.ignore_links = True
        # h.ignore_images = True
        h.images_to_alt = True

        h.escape_snob = True
        h.skip_internal_links = True
        h.ignore_tables = True
        h.single_line_break = True
        h.mark_code = True
        h.wrap_links = True
        h.ul_item_mark = "-"

        async with aiohttp.ClientSession() as session:
            site = await fetch_url(session, url)

        for page in pagify(h.handle(site)):
            await ctx.send(page)
