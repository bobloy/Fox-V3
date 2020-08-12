from .infochannel import InfoChannel


def setup(bot):
    bot.add_cog(InfoChannel(bot))
