from .flask import Flask


def setup(bot):
    bot.add_cog(Flask(bot))
