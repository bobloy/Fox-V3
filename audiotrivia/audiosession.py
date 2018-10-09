"""Module to manage audio trivia sessions."""
import asyncio

import lavalink
from redbot.cogs.trivia import TriviaSession


class AudioSession(TriviaSession):
    """Class to run a session of audio trivia"""

    def __init__(self, ctx, question_list: dict, settings: dict, player: lavalink.Player):
        super().__init__(ctx, question_list, settings)

        self.player = player

    @classmethod
    def start(cls, ctx, question_list, settings, player: lavalink.Player = None):
        session = cls(ctx, question_list, settings, player)
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
            await self.player.stop()

            msg = "**Question number {}!**\n\nName this audio!".format(self.count)
            await self.ctx.send(msg)
            # print("Audio question: {}".format(question))

            # await self.ctx.invoke(self.audio.play(ctx=self.ctx, query=question))
            # ctx_copy = copy(self.ctx)

            # await self.ctx.invoke(self.player.play, query=question)
            query = question.strip("<>")
            tracks = await self.player.get_tracks(query)
            seconds = tracks[0].length / 1000

            if self.settings["repeat"] and seconds < delay:
                tot_length = seconds + 0
                while tot_length < delay:
                    self.player.add(self.ctx.author, tracks[0])
                    tot_length += seconds
            else:
                self.player.add(self.ctx.author, tracks[0])

            if not self.player.current:
                await self.player.play()

            continue_ = await self.wait_for_answer(answers, delay, timeout)
            if continue_ is False:
                break
            if any(score >= max_score for score in self.scores.values()):
                await self.end_game()
                break
        else:
            await self.ctx.send("There are no more questions!")
            await self.end_game()

    async def end_game(self):
        await super().end_game()
        await self.player.disconnect()
