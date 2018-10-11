import io

import discord
from gtts import gTTS
from redbot.core import Config, commands
from redbot.core.bot import Red
from typing import Any

Cog: Any = getattr(commands, "Cog", object)


class TTS(Cog):
    """
    Send Text-to-Speech messages
    """

    def __init__(self, bot: Red):
        self.bot = bot

        self.config = Config.get_conf(self, identifier=9811198108111121, force_registration=True)
        default_global = {}
        default_guild = {}

        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

    @commands.command(aliases=["t2s", "text2"])
    async def tts(self, ctx: commands.Context, *, text: str):
        """
       Send Text to speech messages as an mp3
       """
        mp3_fp = io.BytesIO()
        tts = gTTS(text, "en")
        tts.write_to_fp(mp3_fp)
        await ctx.send(file=discord.File(mp3_fp.getvalue(), "text.mp3"))
