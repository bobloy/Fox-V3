import asyncio
import functools
import logging

import discord
import launchlibrary as ll
from redbot.core import Config, commands
from redbot.core.bot import Red

from launchlib.countrymapper import country_mapping

log = logging.getLogger("red.fox_v3.launchlib")


class LaunchLib(commands.Cog):
    """
    Cog Description

    Less important information about the cog
    """

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=7697117110991047610598, force_registration=True
        )

        default_guild = {}

        self.config.register_guild(**default_guild)

        self.api = ll.Api()

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    async def _embed_launch_data(self, launch: ll.AsyncLaunch):
        status: ll.AsyncLaunchStatus = await launch.get_status()

        rocket: ll.AsyncRocket = launch.rocket

        title = launch.name
        description = status.description

        urls = launch.vid_urls + launch.info_urls
        if not urls and rocket:
            urls = rocket.info_urls + [rocket.wiki_url]
        if urls:
            url = urls[0]
        else:
            url = None

        color = discord.Color.green() if status.id in [1, 3] else discord.Color.red()

        em = discord.Embed(title=title, description=description, url=url, color=color)

        if rocket and rocket.image_url and rocket.image_url != "Array":
            em.set_image(url=rocket.image_url)

        agency = getattr(launch, "agency", None)
        if agency is not None:
            em.set_author(
                name=agency.name,
                url=agency.wiki_url,
                icon_url=f"https://www.countryflags.io/{country_mapping(agency.country_code)}/flat/64.png",
            )

        field_options = [
            ("failreason", "Fail Reason"),
            ("holdreason", "Hold Reason"),
            ("id", "ID"),
            ("hashtag", "Hashtag"),
        ]
        for f in field_options:
            data = getattr(launch, f[0], None)
            if data is not None and data:
                em.add_field(name=f[1], value=data)

        if launch.missions:
            field_options = [
                ("description", "Mission Description"),
                ("typeName", "Mission Type"),
                ("name", "Mission Name"),
            ]
            for mission in launch.missions:
                for f in field_options:
                    data = mission.get(f[0], None)
                    if data is not None and data:
                        em.add_field(name=f[1], value=data)

        if rocket and rocket.family:
            em.add_field(name="Rocket Family", value=rocket.family)

        em.timestamp = launch.windowstart

        em.set_footer()

        return em

    @commands.group()
    async def launchlib(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            pass

    @launchlib.command()
    async def next(self, ctx: commands.Context, num_launches: int = 1):
        # launches = await api.async_next_launches(num_launches)
        # loop = asyncio.get_running_loop()
        #
        # launches = await loop.run_in_executor(
        #     None, functools.partial(self.api.fetch_launch, num=num_launches)
        # )
        #
        launches = await self.api.async_fetch_launch(num=num_launches)

        async with ctx.typing():
            for x, launch in enumerate(launches):
                if x >= num_launches:
                    return

                em = await self._embed_launch_data(launch)
                if em is not None:
                    try:
                        await ctx.send(embed=em)
                    except discord.HTTPException:
                        await ctx.send(str(launch))
                        log.exception("Failed to send embed")
                await asyncio.sleep(2)
