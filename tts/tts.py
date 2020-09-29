import io

import discord
from gtts import gTTS
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.commands import Cog


class TTS(Cog):
    """
    Send Text-to-Speech messages
    """

    def __init__(self, bot: Red, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

        self.config = Config.get_conf(self, identifier=9811198108111121, force_registration=True)
        default_global = {}
        default_guild = {}

        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    @commands.command(aliases=["t2s", "text2"])
    async def tts(self, ctx: commands.Context, *, text: str):
        """
        Send Text to speech messages as an mp3
        """
        mp3_fp = io.BytesIO()
        tts = gTTS(text, lang="en")
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        await ctx.send(file=discord.File(mp3_fp, "text.mp3"))
