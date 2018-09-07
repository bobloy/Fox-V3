from .tts import TTS


def setup(bot):
    bot.add_cog(TTS(bot))
