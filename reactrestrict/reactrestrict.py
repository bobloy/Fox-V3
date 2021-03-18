import logging
from typing import List, Union

import discord
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.commands import Cog

log = logging.getLogger("red.fox_v3.reactrestrict")


class ReactRestrictCombo:
    def __init__(self, message_id, role_id):
        self.message_id = message_id
        self.role_id = role_id

    def __eq__(self, other: "ReactRestrictCombo"):
        return self.message_id == other.message_id and self.role_id == other.role_id

    def to_json(self):
        return {"message_id": self.message_id, "role_id": self.role_id}

    @classmethod
    def from_json(cls, data):
        return cls(data["message_id"], data["role_id"])


class ReactRestrict(Cog):
    """
    Prevent specific roles from reacting to specific messages
    """

    def __init__(self, red: Red):
        super().__init__()
        self.bot = red
        self.config = Config.get_conf(
            self, 8210197991168210111511611410599116, force_registration=True
        )
        self.config.register_global(registered_combos=[])

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    async def combo_list(self) -> List[ReactRestrictCombo]:
        """
        Returns a list of reactrestrict combos.

        :return:
        """
        cmd = self.config.registered_combos()

        return [ReactRestrictCombo.from_json(data) for data in await cmd]

    async def set_combo_list(self, combo_list: List[ReactRestrictCombo]):
        """
        Helper method to set the list of reactrestrict combos.

        :param combo_list:
        :return:
        """
        raw = [combo.to_json() for combo in combo_list]
        await self.config.registered_combos.set(raw)

    async def is_registered(self, message_id: int) -> bool:
        """
        Determines if a message ID has been registered.

        :param message_id:
        :return:
        """
        return any(message_id == combo.message_id for combo in await self.combo_list())

    async def add_reactrestrict(self, message_id: int, role: discord.Role):
        """
        Adds a react|role combo.
        """
        # is_custom = True
        # if isinstance(emoji, str):
        # is_custom = False

        combo = ReactRestrictCombo(message_id, role.id)

        current_combos = await self.combo_list()

        if combo not in current_combos:
            current_combos.append(combo)
            await self.set_combo_list(current_combos)

    async def remove_react(self, message_id: int, role: discord.Role):
        """
        Removes a given reaction

        :param message_id:
        :param role:
        :return:
        """
        current_combos = await self.combo_list()

        to_keep = [c for c in current_combos if c.message_id != message_id or c.role_id != role.id]

        if to_keep != current_combos:
            await self.set_combo_list(to_keep)

    async def has_reactrestrict_combo(self, message_id: int) -> (bool, List[ReactRestrictCombo]):
        """
         Determines if there is an existing role combo for a given message
        and emoji ID.

        :param message_id:
        :return:
        """
        if not await self.is_registered(message_id):
            return False, []

        combos = await self.combo_list()

        ret = [c for c in combos if c.message_id == message_id]

        return len(ret) > 0, ret

    def _get_member(self, channel_id: int, user_id: int) -> discord.Member:
        """
        Tries to get a member with the given user ID from the guild that has
        the given channel ID.

        :param int channel_id:
        :param int user_id:
        :rtype:
            discord.Member
        :raises LookupError:
            If no such channel or member can be found.
        """
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            raise LookupError("no channel found.")
        try:
            member = channel.guild.get_member(user_id)
        except AttributeError as e:
            raise LookupError("No member found.") from e

        if member is None:
            raise LookupError("No member found.")

        return member

    @staticmethod
    def _get_role(guild: discord.Guild, role_id: int) -> discord.Role:
        """
        Gets a role object from the given guild with the given ID.

        :param discord.Guild guild:
        :param int role_id:
        :rtype:
            discord.Role
        :raises LookupError:
            If no such role exists.
        """
        role = discord.utils.get(guild.roles, id=role_id)

        if role is None:
            raise LookupError("No role found.")

        return role

    async def _get_message_from_channel(
        self, channel_id: int, message_id: int
    ) -> Union[discord.Message, None]:
        """
        Tries to find a message by ID in the current guild context.
        """
        channel = self.bot.get_channel(channel_id)
        try:
            return await channel.fetch_message(message_id)
        except discord.NotFound:
            pass
        except AttributeError:  # VoiceChannel object has no attribute 'get_message'
            pass

        return None

    async def _get_message(
        self, ctx: commands.Context, message_id: int
    ) -> Union[discord.Message, None]:
        """
        Tries to find a message by ID in the current guild context.

        :param ctx:
        :param message_id:
        :return:
        """

        guild: discord.Guild = ctx.guild
        for channel in guild.text_channels:
            try:
                return await channel.fetch_message(message_id)
            except discord.NotFound:
                pass
            except AttributeError:  # VoiceChannel object has no attribute 'get_message'
                pass
            except discord.Forbidden:  # No access to channel, skip
                pass

        return None

    @commands.group()
    async def reactrestrict(self, ctx: commands.Context):
        """
        Base command for this cog. Check help for the commands list.
        """
        pass

    @reactrestrict.command()
    async def add(self, ctx: commands.Context, message_id: int, *, role: discord.Role):
        """
        Adds a reaction|role combination to a registered message, don't use quotes for the role name.
        """
        message = await self._get_message(ctx, message_id)
        if message is None:
            await ctx.maybe_send_embed("That message doesn't seem to exist.")
            return

        # try:
        #     emoji, actual_emoji = await self._wait_for_emoji(ctx)
        # except asyncio.TimeoutError:
        #     await ctx.send("You didn't respond in time, please redo this command.")
        #     return
        #
        # try:
        #     await message.add_reaction(actual_emoji)
        # except discord.HTTPException:
        #     await ctx.send("I can't add that emoji because I'm not in the guild that"
        #                    " owns it.")
        #     return
        #
        # noinspection PyTypeChecker
        await self.add_reactrestrict(message_id, role)

        await ctx.maybe_send_embed("Message|Role restriction added.")

    @reactrestrict.command()
    async def remove(self, ctx: commands.Context, message_id: int, role: discord.Role):
        """
        Removes role associated with a given reaction.
        """
        # try:
        #     emoji, actual_emoji = await self._wait_for_emoji(ctx)
        # except asyncio.TimeoutError:
        #     await ctx.send("You didn't respond in time, please redo this command.")
        #     return

        # noinspection PyTypeChecker
        await self.remove_react(message_id, role)

        await ctx.send("React restriction removed.")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """
        Event handler for long term reaction watching.
        """

        emoji = payload.emoji
        message_id = payload.message_id
        channel_id = payload.channel_id
        user_id = payload.user_id

        # if emoji.is_custom_emoji():
        #     emoji_id = emoji.id
        # else:
        #     emoji_id = emoji.name

        has_reactrestrict, combos = await self.has_reactrestrict_combo(message_id)

        if not has_reactrestrict:
            log.debug("Message not react restricted")
            return

        try:
            member = self._get_member(channel_id, user_id)
        except LookupError:
            log.exception("Unable to get member from guild")
            return

        if member.bot:
            log.debug("Won't remove reactions added by bots")
            return

        if await self.bot.cog_disabled_in_guild(self, member.guild):
            return

        try:
            roles = [self._get_role(member.guild, c.role_id) for c in combos]
        except LookupError:
            log.exception("Couldn't get approved roles from combos")
            return

        for apprrole in roles:
            if apprrole in member.roles:
                log.debug("Has approved role")
                return

        message = await self._get_message_from_channel(channel_id, message_id)
        try:
            await message.remove_reaction(emoji, member)
        except (discord.Forbidden, discord.NotFound, discord.HTTPException):
            log.exception("Unable to remove reaction")

    #     try:
    #         await member.add_roles(*roles)
    #     except discord.Forbidden:
    #         pass
    #
    # async def on_raw_reaction_remove(self, emoji: discord.PartialReactionEmoji,
    #                                  message_id: int, channel_id: int, user_id: int):
    #     """
    #     Event handler for long term reaction watching.
    #
    #     :param discord.PartialReactionEmoji emoji:
    #     :param int message_id:
    #     :param int channel_id:
    #     :param int user_id:
    #     :return:
    #     """
    #     if emoji.is_custom_emoji():
    #         emoji_id = emoji.id
    #     else:
    #         emoji_id = emoji.name
    #
    #     has_reactrestrict, combos = await self.has_reactrestrict_combo(message_id, emoji_id)
    #
    #     if not has_reactrestrict:
    #         return
    #
    #     try:
    #         member = self._get_member(channel_id, user_id)
    #     except LookupError:
    #         return
    #
    #     if member.bot:
    #         return
    #
    #     try:
    #         roles = [self._get_role(member.guild, c.role_id) for c in combos]
    #     except LookupError:
    #         return
    #
    #     try:
    #         await member.remove_roles(*roles)
    #     except discord.Forbidden:
    #         pass
