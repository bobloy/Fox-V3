import discord
from redbot.core import Config, commands
from redbot.core.bot import Red


class MapMaker(commands.Cog):
    """
    Create Maps to be used with Conquest
    """

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot

        self.config = Config.get_conf(
            self, identifier=77971127797107101114, force_registration=True
        )

        default_guild = {}
        default_global = {}
        self.config.register_guild(**default_guild)
        self.config.register_global(**default_global)

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    @commands.group()
    async def mapmaker(self, ctx: commands.context):
        """
        Base command for managing current maps or creating new ones
        """
        pass

    @mapmaker.command(name="upload")
    async def _mapmaker_upload(self, ctx: commands.Context, map_path=""):
        """Load a map image to be modified. Upload one with this command or provide a path"""
        message: discord.Message = ctx.message
        if not message.attachments and not map_path:
            await ctx.maybe_send_embed(
                "Either upload an image with this command or provide a path to the image"
            )
            return
        await ctx.maybe_send_embed("WIP")

    @mapmaker.command(name="load")
    async def _mapmaker_load(self, ctx: commands.Context, map_name=""):
        """Load an existing map to be modified."""
        await ctx.maybe_send_embed("WIP")
