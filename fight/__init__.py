from .fight import Fight


def setup(bot):
    # check_folders()
    # check_files()
    n = Fight(bot)
    bot.add_cog(n)
