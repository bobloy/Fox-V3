from .launchlib import LaunchLib


async def setup(bot):
    cog = LaunchLib(bot)
    r = bot.add_cog(cog)
    if r is not None:
        await r
