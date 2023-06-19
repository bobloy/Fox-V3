import discord
from pylint import epylint as lint
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.commands import Cog
from redbot.core.data_manager import cog_data_path


class CogLint(Cog):
    """
    Automatically lint code in python codeblocks
    """

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9811198108111121, force_registration=True)
        default_global = {"lint": True}
        default_guild = {}

        self.path = str(cog_data_path(self)).replace("\\", "/")

        self.do_lint = None
        self.counter = 0

        # self.answer_path = self.path + "/tmpfile.py"

        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    @commands.command()
    async def autolint(self, ctx: commands.Context):
        """Toggles automatically linting code"""
        curr = await self.config.lint()

        self.do_lint = not curr
        await self.config.lint.set(not curr)
        await ctx.maybe_send_embed("Autolinting is now set to {}".format(not curr))

    @commands.command()
    async def lint(self, ctx: commands.Context, *, code):
        """Lint python code

        Toggle autolinting with `[p]autolint`
        """
        await self.lint_message(ctx.message)
        await ctx.maybe_send_embed("Hello World")

    async def lint_code(self, code):
        self.counter += 1
        path = self.path + "/{}.py".format(self.counter)
        with open(path, "w") as codefile:
            codefile.write(code)

        future = await self.bot.loop.run_in_executor(None, lint.py_run, path, "return_std=True")

        (pylint_stdout, pylint_stderr) = future or (None, None)
        # print(pylint_stderr)
        # print(pylint_stdout)

        return pylint_stdout, pylint_stderr

    async def lint_message(self, message):
        if self.do_lint is None:
            self.do_lint = await self.config.lint()
        if not self.do_lint:
            return
        code_blocks = message.content.split("```")[1::2]

        for c in code_blocks:
            is_python, code = c.split(None, 1)
            is_python = is_python.lower() in ["python", "py"]
            if is_python:  # Then we're in business
                linted, errors = await self.lint_code(code)
                linted = linted.getvalue()
                errors = errors.getvalue()
                await message.channel.send(linted)
                # await message.channel.send(errors)

    async def on_message(self, message: discord.Message):
        await self.lint_message(message)
