from redbot.core.bot import Red

from .announcedaily import AnnounceDaily


async def setup(bot: Red):
    daily = AnnounceDaily(bot)
    r = bot.add_cog(daily)
    if r is not None:
        await r
        bot.loop.create_task(daily.check_day())
