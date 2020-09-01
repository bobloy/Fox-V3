from datetime import datetime
from typing import TYPE_CHECKING

from discord.ext.commands import BadArgument, Converter
from dateutil import parser

from fifo.timezones import assemble_timezones

if TYPE_CHECKING:
    DatetimeConverter = datetime
else:
    class DatetimeConverter(Converter):
        async def convert(self, ctx, argument) -> datetime:
            dt = parser.parse(argument, fuzzy=True, tzinfos=assemble_timezones())
            if dt is not None:
                return dt
            raise BadArgument()
