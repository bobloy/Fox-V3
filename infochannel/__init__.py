from .infochannel import InfoChannel


async def setup(bot):
    ic_cog = InfoChannel(bot)
    bot.add_cog(ic_cog)
    await ic_cog.initialize()
