from typing import TYPE_CHECKING, Union

import discord
from discord.ext.commands import BadArgument, Converter
from redbot.core import commands

from werewolf.player import Player

if TYPE_CHECKING:
    PlayerConverter = Union[int, discord.Member]
    CronConverter = str
else:

    class PlayerConverter(Converter):
        async def convert(self, ctx, argument) -> Player:
            try:
                target = await commands.MemberConverter().convert(ctx, argument)
            except BadArgument:
                try:
                    target = int(argument)
                    assert target >= 0
                except (ValueError, AssertionError):
                    raise BadArgument

            # TODO: Get the game for context without making a new one
            # TODO: Get player from game based on either ID or member object
            return target
