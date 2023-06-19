from .flag import Flag


async def setup(bot):
    r = bot.add_cog(Flag(bot))
    if r is not None:
        await r
