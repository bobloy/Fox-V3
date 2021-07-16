import io
import logging
from typing import Optional, TYPE_CHECKING

import discord
from discord.ext.commands import BadArgument, Converter
from gtts import gTTS
from gtts.lang import _fallback_deprecated_lang, tts_langs
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.commands import Cog

log = logging.getLogger("red.fox_v3.tts")

if TYPE_CHECKING:
    ISO639Converter = str
else:

    class ISO639Converter(Converter):
        async def convert(self, ctx, argument) -> str:
            lang = _fallback_deprecated_lang(argument)

            try:
                langs = tts_langs()
                if lang not in langs:
                    raise BadArgument("Language not supported: %s" % lang)
            except RuntimeError as e:
                log.debug(str(e), exc_info=True)
                log.warning(str(e))

            return lang


class TTS(Cog):
    """
    Send Text-to-Speech messages
    """

    def __init__(self, bot: Red, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

        self.config = Config.get_conf(self, identifier=9811198108111121, force_registration=True)
        default_global = {}
        default_guild = {"language": "en"}

        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    @commands.mod()
    @commands.command()
    async def ttslang(self, ctx: commands.Context, lang: ISO639Converter):
        """
        Sets the default language for TTS in this guild.

        Default is `en` for English
        """
        await self.config.guild(ctx.guild).language.set(lang)
        await ctx.send(f"Default tts language set to {lang}")

    @commands.command(aliases=["t2s", "text2"])
    async def tts(
        self, ctx: commands.Context, lang: Optional[ISO639Converter] = None, *, text: str
    ):
        """
        Send Text to speech messages as an mp3
        """
        if lang is None:
            lang = await self.config.guild(ctx.guild).language()

        mp3_fp = io.BytesIO()
        tts = gTTS(text, lang=lang)
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        await ctx.send(file=discord.File(mp3_fp, "text.mp3"))
