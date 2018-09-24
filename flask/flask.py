import asyncio
import threading

from quart import Quart, websocket, Response
from redbot.core import Config, checks, commands
from redbot.core.bot import Red


class EndpointAction(object):

    def __init__(self, action):
        self.action = action

    async def __call__(self, *args):
        response = await self.action()
        return Response(response, status=200, headers={})


class Flask:
    """
    Run an owner only quart (async flask) server for issuing commands.
    """
    app = Quart(__name__)
    test_name = "FlaskQuart"

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9811198108111121, force_registration=True)
        default_global = {}
        default_guild = {}

        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

        self.threads = []
        self.t = threading.Thread(target=self.worker)
        self.t.daemon = True
        self.threads.append(self.t)

        self.context = None

    def __unload(self):
        try:
            self.t._stop()
        except:
            self.t._stop()  # No really, stop

    @checks.is_owner()
    @commands.command()
    async def flask(self, ctx: commands.Context):
        """Starts a quart server"""
        self.context = ctx
        self.add_endpoint(endpoint="/name", endpoint_name="name", handler=self.bot_name)
        self.add_endpoint(endpoint="/help", endpoint_name="help", handler=self.quart_help)
        self.t.start()
        await ctx.send("Done")

    def add_endpoint(self, endpoint=None, endpoint_name=None, handler=None):
        self.app.add_url_rule(endpoint, endpoint_name, EndpointAction(handler))

    @staticmethod
    @app.route('/')
    async def hello():
        return "hello"

    async def bot_name(self):
        return self.test_name

    async def quart_help(self):
        f = commands.HelpFormatter()
        msgs = await f.format_help_for(self.context, self.bot)
        out = ""
        for msg in msgs:
            for line in msg.split('\n'):
                if line == '```':
                    continue
                if line.endswith(":"):
                    out += "<h1>" + line + "</h1>\n"
                else:
                    line = line.strip().split(" ")
                    out += "<p><b>" + line[0] + "</b> " + " ".join(line[1:]) + "</p>\n"

        return '''
        <html>
            <head>
                <title>Red Bot - Help</title>
            </head>
            <body>
                {}
            </body>
        </html>'''.format(out)

    @staticmethod
    @app.websocket('/ws')
    async def ws():
        while True:
            await websocket.send('hello')

    def worker(self):
        second_loop = asyncio.new_event_loop()
        asyncio.ensure_future(self.app.run(loop=second_loop))
        return
