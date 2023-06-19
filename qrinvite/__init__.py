from .qrinvite import QRInvite


async def setup(bot):
    cog = QRInvite(bot)
    r = bot.add_cog(cog)
    if r is not None:
        await r
