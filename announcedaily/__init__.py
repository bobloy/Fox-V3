from redbot.core.bot import Red

from .announcedaily import AnnounceDaily


def setup(bot: Red):
    daily = AnnounceDaily(bot)
    bot.add_cog(daily)
    daily.announce_task = bot.loop.create_task(daily.check_day())
