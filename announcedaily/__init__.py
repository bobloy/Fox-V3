from .announcedaily import AnnounceDaily


def setup(bot):
    bot.add_cog(AnnounceDaily(bot))
