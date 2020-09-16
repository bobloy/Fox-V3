from .firstmessage import FirstMessage


async def setup(bot):
    bot.add_cog(FirstMessage(bot))
