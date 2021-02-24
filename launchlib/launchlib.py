import asyncio
import functools
import logging
import re
import discord
import launchlibrary as ll
from redbot.core import Config, commands
from redbot.core.bot import Red

from launchlib.countrymapper import country_mapping

log = logging.getLogger("red.fox_v3.launchlib")


class LaunchLib(commands.Cog):
    """
    Cog using `thespacedevs` API to get details about rocket launches
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

        if False:
            example_launch = ll.AsyncLaunch(
                id="9279744e-46b2-4eca-adea-f1379672ec81",
                name="Atlas LV-3A | Samos 2",
                tbddate=False,
                tbdtime=False,
                status={"id": 3, "name": "Success"},
                inhold=False,
                windowstart="1961-01-31 20:21:19+00:00",
                windowend="1961-01-31 20:21:19+00:00",
                net="1961-01-31 20:21:19+00:00",
                info_urls=[],
                vid_urls=[],
                holdreason=None,
                failreason=None,
                probability=0,
                hashtag=None,
                agency=None,
                changed=None,
                pad=ll.Pad(
                    id=93,
                    name="Space Launch Complex 3W",
                    latitude=34.644,
                    longitude=-120.593,
                    map_url="http://maps.google.com/maps?q=34.644+N,+120.593+W",
                    retired=None,
                    total_launch_count=3,
                    agency_id=161,
                    wiki_url=None,
                    info_url=None,
                    location=ll.Location(
                        id=11,
                        name="Vandenberg AFB, CA, USA",
                        country_code="USA",
                        total_launch_count=83,
                        total_landing_count=3,
                        pads=None,
                    ),
                    map_image="https://spacelaunchnow-prod-east.nyc3.digitaloceanspaces.com/media/launch_images/pad_93_20200803143225.jpg",
                ),
                rocket=ll.Rocket(
                    id=2362,
                    name=None,
                    default_pads=None,
                    family=None,
                    wiki_url=None,
                    info_url=None,
                    image_url=None,
                ),
                missions=None,
            )

        # status: ll.AsyncLaunchStatus = await launch.get_status()
        status = launch.status

        rocket: ll.AsyncRocket = launch.rocket

        title = launch.name
        description = status["name"]

        urls = launch.vid_urls + launch.info_urls
        if rocket:
            urls += [rocket.info_url, rocket.wiki_url]
        if launch.pad:
            urls += [launch.pad.info_url, launch.pad.wiki_url]

        if urls:
            url = next((url for url in urls if urls is not None), None)
        else:
            url = None

        color = discord.Color.green() if status["id"] in [1, 3] else discord.Color.red()

        em = discord.Embed(title=title, description=description, url=url, color=color)

        if rocket and rocket.image_url and rocket.image_url != "Array":
            em.set_image(url=rocket.image_url)
        elif launch.pad and launch.pad.map_image:
            em.set_image(url=launch.pad.map_image)

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
        if launch.pad:
            location_url = getattr(launch.pad, "map_url", None)
            pad_name = getattr(launch.pad, "name", None)

            if pad_name is not None:
                if location_url is not None:
                    location_url = re.sub("[^a-zA-Z0-9/:.'+\"°?=,-]", "", location_url)  # Fix bad URLS
                    em.add_field(name="Launch Pad Name", value=f"[{pad_name}]({location_url})")
                else:
                    em.add_field(name="Launch Pad Name", value=pad_name)

        if rocket and rocket.family:
            em.add_field(name="Rocket Family", value=rocket.family)

        em.timestamp = launch.windowstart

        em.set_footer()

        return em

    @commands.group()
    async def launchlib(self, ctx: commands.Context):
        """Base command for getting launches"""
        if ctx.invoked_subcommand is None:
            pass

    @launchlib.command()
    async def next(self, ctx: commands.Context, num_launches: int = 1):
        """
        Show the next launches

        Use `num_launches` to get more than one.
        """
        # launches = await api.async_next_launches(num_launches)
        # loop = asyncio.get_running_loop()
        #
        # launches = await loop.run_in_executor(
        #     None, functools.partial(self.api.fetch_launch, num=num_launches)
        # )
        #
        launches = await self.api.async_fetch_launch(num=num_launches)

        # log.debug(str(launches))

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
