from .planttycoon import PlantTycoon


def setup(bot):
    bot.add_cog(PlantTycoon(bot))
