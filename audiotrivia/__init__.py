from redbot.core.bot import Red

from .audiotrivia import AudioTrivia


async def setup(bot: Red):
    if bot.get_cog("Trivia"):
        print("Trivia is already loaded, attempting to unload it first")
        bot.remove_cog("Trivia")
        await bot.remove_loaded_package("trivia")
        bot.unload_extension("trivia")

    bot.add_cog(AudioTrivia(bot))
