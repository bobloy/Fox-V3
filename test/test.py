import discord
import os
from datetime import datetime
from discord.ext import commands

from .utils.dataIO import dataIO
from .utils import checks

class Test:
    def __init__(self, bot):
        self.bot = bot
        self.path = "data/Fox-Cogs/test"
        self.file_path = "data/Fox-Cogs/test/test.json"
        self.the_data = dataIO.load_json(self.file_path)

    def save_data(self):
         dataIO.save_json(self.file_path, self.the_data)

    @commands.command()
    async def test(self):
        self.the_data["WOAH"] = True
        #self.the_data["WOAH"]["knarly"] = "Biiiiiitch"
        if "Yeah dude" not in self.the_data:
            self.the_data["Yeah dude"]={}
        self.the_data["Yeah dude"]["knarly"]= {"ur lyin" : True,
                                               "kick-ass" : { "no way!!!" : "Biiiiiitch" },
                                               "created_at" : datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                               }
        
        #self.the_data["Yeah dude"]["knarly"] = "ur lyin"
        #self.the_data["Yeah dude"]["knarly"]["kick-ass"]["no way!!!"] = "Biiiiiitch"
        self.save_data()


def check_folders():
    if not os.path.exists("data/Fox-Cogs"):
        print("Creating data/Fox-Cogs folder...")
        os.makedirs("data/Fox-Cogs")

    if not os.path.exists("data/Fox-Cogs/test"):
        print("Creating data/Fox-Cogs/test folder...")
        os.makedirs("data/Fox-Cogs/test")

        
def check_files():
    if not dataIO.is_valid_json("data/Fox-Cogs/test/test.json"):
        dataIO.save_json("data/Fox-Cogs/test/test.json" ,{})

def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(Test(bot))
