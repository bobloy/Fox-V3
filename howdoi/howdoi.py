import discord

from discord.ext import commands

from .utils.chat_formatting import pagify
from .utils.chat_formatting import box

from howdoi import howdoi


class Howdoi:
    """Cog for answering coding questions"""

    def __init__(self, bot):
        self.bot = bot
        self.query = ""
        self.args = {
            "query": self.query,
            "pos": 1,
            "all": False,
            "link": True,
            "color": False,
            "num_answers": 1,
            "clear_cache": False,
            "version": False
            }

    @commands.group(pass_context=True)
    async def howdoiset(self, ctx):
        """Adjust howdoi settings
        Settings are reset on reload"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)
    
    @howdoiset.command(pass_context=True, name="answers")
    async def howdoiset_answers(self, ctx, num_answers: int=1):
        """Adjust number of answers provided.
        Defaults to 1"""
        
        self.args['num_answers'] = num_answers
        await self.bot.say("Number of answers provided will now be {}".format(num_answers))
    
    @howdoiset.command(pass_context=True, name="link")
    async def howdoiset_link(self, ctx):
        """Toggles providing in-line answers or a link
        Default On"""
        
        self.args['link'] = not self.args['link']
        
        if self.args['link']:
            await self.bot.say("Answers will now be provided as a link")
        else:
            await self.bot.say("Answers will now be provided as the response")
            
    @howdoiset.command(pass_context=True, name="full")
    async def howdoiset_full(self, ctx):
        """Toggles providing full answers or just first code found
        Default Off
        Only works if links are turned off"""
        
        self.args['all'] = not self.args['all']
        
        if self.args['all']:
            await self.bot.say("Answers will now be provided in full context")
        else:
            await self.bot.say("Answers will now be provided as a code snippet")
        
    @commands.command(pass_context=True)
    async def howdoi(self, ctx, *question):
        """Ask a coding question"""
        self.query = " ".join(question)
        
        self.args["query"] = self.query
        
        out = howdoi.howdoi(self.args.copy()) # .encode('utf-8', 'ignore')
        
        if self.args['link']:
            await self.bot.say(out)
        else:
            await self.bot.say(box(out,"python"))
        # for page in pagify(out, shorten_by=24):
            # await self.bot.say(box(page))
        
def setup(bot):
    n = Howdoi(bot)
    bot.add_cog(n)
