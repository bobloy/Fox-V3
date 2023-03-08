from .firstmessage import FirstMessage


async def setup(bot):
    await bot.add_cog(FirstMessage(bot))
