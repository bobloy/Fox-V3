from .fight import Fight

# def check_folders():
    # if not os.path.exists("data/Fox-Cogs"):
        # print("Creating data/Fox-Cogs folder...")
        # os.makedirs("data/Fox-Cogs")

    # if not os.path.exists("data/Fox-Cogs/fight"):
        # print("Creating data/Fox-Cogs/fight folder...")
        # os.makedirs("data/Fox-Cogs/fight")


# def check_files():
    # if not dataIO.is_valid_json("data/Fox-Cogs/fight/fight.json"):
        # dataIO.save_json("data/Fox-Cogs/fight/fight.json", {})


def setup(bot):
    # check_folders()
    # check_files()
    n = Fight(bot)
    bot.add_cog(n)