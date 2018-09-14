"""Module to manage audio trivia sessions."""
import asyncio

from redbot.cogs.audio import Audio
from redbot.cogs.trivia import TriviaSession


class AudioSession(TriviaSession):
    """Class to run a session of audio trivia"""

    def __init__(self, ctx, question_list: dict, settings: dict, audio_cog: Audio):
        super().__init__(ctx, question_list, settings)

        self.audio = audio_cog

    @classmethod
    def start(cls, ctx, question_list, settings, audio_cog: Audio = None):
        session = cls(ctx, question_list, settings, audio_cog)
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
        timeout = self.settings["timeout"]
        for question, answers in self._iter_questions():
            async with self.ctx.typing():
                await asyncio.sleep(3)
            self.count += 1
            msg = "**Question number {}!**\n\nName this audio!".format(self.count)
            await self.ctx.send(msg)
            print(question)

            await self.audio.play(ctx=self.ctx, query=question)

            continue_ = await self.wait_for_answer(answers, delay, timeout)
            if continue_ is False:
                break
            if any(score >= max_score for score in self.scores.values()):
                await self.end_game()
                break
        else:
            await self.ctx.send("There are no more questions!")
            await self.end_game()
