from redbot.core.bot import Red

from .audiotrivia import AudioTrivia


async def setup(bot: Red):
    if bot.get_cog("Trivia"):
        print("Trivia is already loaded, attempting to unload it first")
        await bot.remove_cog("Trivia")
        await bot.remove_loaded_package("trivia")
        await bot.unload_extension("trivia")

    cog = AudioTrivia(bot)
    r = bot.add_cog(cog)
    if r is not None:
        await r
