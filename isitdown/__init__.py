from .isitdown import IsItDown


async def setup(bot):
    bot.add_cog(IsItDown(bot))
