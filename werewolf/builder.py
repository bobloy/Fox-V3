import asyncio
import discord

# Import all roles here
from werewolf.role import Role
from werewolf.roles.vanillawerewolf import VanillaWerewolf
from werewolf.roles.villager import Villager
from werewolf.roles.seer import Seer

# All roles in this list for iterating
role_list = [Villager, VanillaWerewolf] 

#Example code:
# 0 = Villager
# 1 = VanillaWerewolf
# E1 = Random Town
# R1 = Random Werewolf
# J1 = Benign Neutral

# 0001-1112E11R112P2
# 0,0,0,1,11,12,E1,R1,R1,R1,R2,P2

# pre-letter = exact role position
# double digit position pre-empted by `-`

async def parse_code(code):
    out = []
    #Do the magic described above
    decode = code.copy() # for now, pass exact names
    for role_id in decode:
        print(role_id)
        if role_id == "Villager":
            role = Villager
        if role_id == "VanillaWerewolf":
            role = VanillaWerewolf
        if role_id == "Seer":
            role = Seer
        out.append(role)
    
    return out
            
async def build_game(channel: discord.TextChannel):
    await channel.send("Not currently available")
    
    
    code = 12345678
    
    await channel.send("Your game code is **`{}`**".format(code))
    # Make this embeds
