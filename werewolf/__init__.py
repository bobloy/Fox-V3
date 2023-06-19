from .werewolf import Werewolf


async def setup(bot):
    cog = Werewolf(bot)
    r = bot.add_cog(cog)
    if r is not None:
        await r
