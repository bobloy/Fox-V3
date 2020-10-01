"""Module to manage audio trivia sessions."""
import asyncio
import logging

from redbot.cogs.trivia import TriviaSession
from redbot.cogs.trivia.session import _parse_answers
from redbot.core.utils.chat_formatting import bold

log = logging.getLogger("red.fox_v3.audiotrivia.audiosession")


class AudioSession(TriviaSession):
    """Class to run a session of audio trivia"""

    def __init__(self, ctx, question_list: dict, settings: dict, audio=None):
        super().__init__(ctx, question_list, settings)

        self.audio = audio

    @classmethod
    def start(cls, ctx, question_list, settings, audio=None):
        session = cls(ctx, question_list, settings, audio)
        loop = ctx.bot.loop
        session._task = loop.create_task(session.run())
        return session

    async def run(self):
        """Run the audio trivia session.

        In order for the trivia session to be stopped correctly, this should
        only be called internally by `TriviaSession.start`.
        """
        await self._send_startup_msg()
        max_score = self.settings["max_score"]
        delay = self.settings["delay"]
        audio_delay = self.settings["audio_delay"]
        timeout = self.settings["timeout"]
        if self.audio is not None:
            import lavalink

            player = lavalink.get_player(self.ctx.guild.id)
            player.store("channel", self.ctx.channel.id)  # What's this for? I dunno
            await self.audio.set_player_settings(self.ctx)
        else:
            lavalink = None
            player = False

        for question, answers, audio_url in self._iter_questions():
            async with self.ctx.typing():
                await asyncio.sleep(3)
            self.count += 1
            msg = bold(f"Question number {self.count}!") + f"\n\n{question}"
            if player:
                await player.stop()
            if audio_url:
                if not player:
                    log.debug("Got an audio question in a non-audio trivia session")
                    continue

                load_result = await player.load_tracks(audio_url)
                if (
                    load_result.has_error
                    or load_result.load_type != lavalink.enums.LoadType.TRACK_LOADED
                ):
                    await self.ctx.maybe_send_embed(
                        "Audio Track has an error, skipping. See logs for details"
                    )
                    log.info(f"Track has error: {load_result.exception_message}")
                    continue
                tracks = load_result.tracks
                track = tracks[0]
                seconds = track.length / 1000
                track.uri = ""  # Hide the info from `now`
                if self.settings["repeat"] and seconds < audio_delay:
                    # Append it until it's longer than the delay
                    tot_length = seconds + 0
                    while tot_length < audio_delay:
                        player.add(self.ctx.author, track)
                        tot_length += seconds
                else:
                    player.add(self.ctx.author, track)

                if not player.current:
                    await player.play()
            await self.ctx.maybe_send_embed(msg)
            log.debug(f"Audio question: {question}")

            continue_ = await self.wait_for_answer(
                answers, audio_delay if audio_url else delay, timeout
            )
            if continue_ is False:
                break
            if any(score >= max_score for score in self.scores.values()):
                await self.end_game()
                break
        else:
            await self.ctx.maybe_send_embed("There are no more questions!")
            await self.end_game()

    async def end_game(self):
        await super().end_game()
        if self.audio is not None:
            await self.ctx.invoke(self.audio.command_disconnect)

    def _iter_questions(self):
        """Iterate over questions and answers for this session.

        Yields
        ------
        `tuple`
            A tuple containing the question (`str`) and the answers (`tuple` of
            `str`).

        """
        for question, q_data in self.question_list:
            answers = _parse_answers(q_data["answers"])
            _audio = q_data["audio"]
            if _audio:
                yield _audio, answers, question.strip("<>")
            else:
                yield question, answers, _audio
