from .audiotrivia import AudioTrivia


def setup(bot):
    bot.add_cog(AudioTrivia(bot))
