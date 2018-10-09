from .qrinvite import QRInvite


def setup(bot):
    bot.add_cog(QRInvite(bot))
