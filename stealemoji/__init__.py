from .stealemoji import StealEmoji


async def setup(bot):
    cog = StealEmoji(bot)
    r = bot.add_cog(cog)
    if r is not None:
        await r
