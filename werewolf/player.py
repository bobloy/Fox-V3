import logging

import discord

log = logging.getLogger("red.fox_v3.werewolf.player")


class Player:
    """
    Base player class for Werewolf game
    """

    def __init__(self, member: discord.Member):
        self.member = member
        self.mention = member.mention
        self.role = None
        self.id = None

        self.alive = True
        self.muted = False
        self.protected = False

    def __repr__(self):
        return f"{self.__class__.__name__}({self.member})"

    async def assign_role(self, role):
        """
        Give this player a role
        """
        role.player = self
        self.role = role

    async def assign_id(self, target_id):
        self.id = target_id

    async def send_dm(self, message):
        try:
            await self.member.send(message)  # Lets do embeds later
        except discord.Forbidden:
            await self.role.game.village_channel.send(
                f"Couldn't DM {self.mention}, uh oh",
                allowed_mentions=discord.AllowedMentions(users=[self.member]),
            )
