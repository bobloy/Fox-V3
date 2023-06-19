from .infochannel import InfoChannel


async def setup(bot):
    cog = InfoChannel(bot)
    r = bot.add_cog(cog)
    if r is not None:
        await r
        await cog.initialize()
