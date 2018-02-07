import discord

from discord.ext import commands

from .utils.chat_formatting import pagify
from .utils.chat_formatting import box

from howdoi import howdoi


class Howdoi:
    """Cog for answering coding questions"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=104111119100111105)
        self.query = ""
        default_global = {
            "query": "",
            "pos": 1,
            "all": False,
            "link": True,
            "color": False,
            "num_answers": 1,
            "clear_cache": False,
            "version": False
            }

        self.config.register_global(**default_global)

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
        
        await self.config.num_answers.set(num_answers)
        await self.bot.say("Number of answers provided will now be {}".format(num_answers))
    
    @howdoiset.command(pass_context=True, name="link")
    async def howdoiset_link(self, ctx):
        """Toggles providing in-line answers or a link
        Default On"""
        
        await self.config.link.set(not (await self.config.link()))
        
        if (await self.config.link()):
            await self.bot.say("Answers will now be provided as a link")
        else:
            await self.bot.say("Answers will now be provided as the response")
            
    @howdoiset.command(pass_context=True, name="full")
    async def howdoiset_full(self, ctx):
        """Toggles providing full answers or just first code found
        Default Off
        Only works if links are turned off"""
        
        await self.config.all.set(not (await self.config.all()))
        
        if (await self.config.all()):
            await self.bot.say("Answers will now be provided in full context")
        else:
            await self.bot.say("Answers will now be provided as a code snippet")
        
    @commands.command(pass_context=True)
    async def howdoi(self, ctx, *question):
        """Ask a coding question"""
        self.query = " ".join(question)
        
        await self.config.query.set(self.query)
        
        argcopy = await self.config()
        await self.bot.say(str(argcopy))
        out = howdoi.howdoi(argcopy) # .encode('utf-8', 'ignore')
        
        if await self.config.link():
            await self.bot.say(out)
        else:
            await self.bot.say(box(out,"python"))
        # for page in pagify(out, shorten_by=24):
            # await self.bot.say(box(page))
        
def setup(bot):
    n = Howdoi(bot)
    bot.add_cog(n)
