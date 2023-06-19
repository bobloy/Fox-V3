from .tts import TTS


async def setup(bot):
    cog = TTS(bot)
    r = bot.add_cog(cog)
    if r is not None:
        await r
