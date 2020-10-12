from .cogguide import CogGuide


async def setup(bot):
    bot.add_cog(CogGuide(bot))
