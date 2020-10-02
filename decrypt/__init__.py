from .decrypt import Decrypt


async def setup(bot):
    bot.add_cog(Decrypt(bot))
