import asyncio
import collections
import copy
import datetime
import json
import time
from random import choice
from typing import Literal

import discord
from redbot.core import Config, bank, commands
from redbot.core.bot import Red
from redbot.core.data_manager import bundled_data_path
from redbot.core.utils import AsyncIter


class Gardener:
    """Gardener class"""

    def __init__(self, user: discord.User, config: Config):
        self.user = user
        self.config = config
        self.badges = []
        self.points = 0
        self.products = {}
        self.current = {}

    def __str__(self):
        return (
            "Gardener named {}\n"
            "Badges: {}\n"
            "Points: {}\n"
            "Products: {}\n"
            "Current: {}".format(self.user, self.badges, self.points, self.products, self.current)
        )

    def __repr__(self):
        return "{} - {} - {} - {} - {}".format(
            self.user, self.badges, self.points, self.products, self.current
        )

    async def load_config(self):
        self.badges = await self.config.user(self.user).badges()
        self.points = await self.config.user(self.user).points()
        self.products = await self.config.user(self.user).products()
        self.current = await self.config.user(self.user).current()

    async def save_gardener(self):
        await self.config.user(self.user).badges.set(self.badges)
        await self.config.user(self.user).points.set(self.points)
        await self.config.user(self.user).products.set(self.products)
        await self.config.user(self.user).current.set(self.current)

    async def is_complete(self, now):
        message = None
        if self.current:
            then = self.current["timestamp"]
            health = self.current["health"]
            grow_time = self.current["time"]
            badge = self.current["badge"]
            reward = self.current["reward"]
            if (now - then) > grow_time:
                self.points += reward
                if badge not in self.badges:
                    self.badges.append(badge)
                message = (
                    "Your plant made it! "
                    "You are rewarded with the **{}** badge and you have received **{}** Thneeds.".format(
                        badge, reward
                    )
                )
            if health < 0:
                message = "Your plant died!"

        if message is not None:
            self.current = {}
            await self.save_gardener()
            await self.user.send(message)


async def _die_in(gardener, degradation):
    #
    # Calculating how much time in minutes remains until the plant's health hits 0
    #

    return int(gardener.current["health"] / degradation.degradation)


async def _grow_time(gardener):
    #
    # Calculating the remaining grow time for a plant
    #

    now = int(time.time())
    then = gardener.current["timestamp"]
    return (gardener.current["time"] - (now - then)) / 60


async def _send_message(channel, message):
    """Sendsa message"""

    em = discord.Embed(description=message, color=discord.Color.green())
    await channel.send(embed=em)


async def _withdraw_points(gardener: Gardener, amount):
    #
    # Substract points from the gardener
    #

    if (gardener.points - amount) < 0:
        return False
    gardener.points -= amount
    return True


class PlantTycoon(commands.Cog):
    """Grow your own plants! Be sure to take proper care of it."""

    def __init__(self, bot: Red, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.config = Config.get_conf(self, identifier=80108971101168412199111111110)

        default_user = {"badges": [], "points": 0, "products": {}, "current": {}}

        self.config.register_user(**default_user)

        self.plants = None

        self.products = None

        self.defaults = {
            "points": {
                "buy": 5,
                "add_health": 5,
                "fertilize": 10,
                "pruning": 20,
                "pesticide": 25,
                "growing": 5,
                "damage": 25,
            },
            "timers": {"degradation": 1, "completion": 1, "notification": 5},
            "degradation": {"base_degradation": 1.5},
            "notification": {"max_health": 50},
        }

        self.badges = {
            "badges": {
                "Flower Power": {},
                "Fruit Brute": {},
                "Sporadic": {},
                "Odd-pod": {},
                "Greenfingers": {},
                "Nobel Peas Prize": {},
                "Annualsary": {},
            }
        }

        self.notifications = {
            "messages": [
                "The soil seems dry, maybe you could give your plant some water?",
                "Your plant seems a bit droopy. I would give it some fertilizer if I were you.",
                "Your plant seems a bit too overgrown. You should probably trim it a bit.",
            ]
        }

        #
        # Starting loops
        #

        self.completion_task = bot.loop.create_task(self.check_completion_loop())
        # self.degradation_task = bot.loop.create_task(self.check_degradation())
        self.notification_task = bot.loop.create_task(self.send_notification())

        #
        # Loading bank
        #

        # self.bank = bot.get_cog('Economy').bank

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ):
        await self.config.user_from_id(user_id).clear()

    async def _load_plants_products(self):
        """Runs in __init__.py before cog is added to the bot"""
        plant_path = bundled_data_path(self) / "plants.json"
        product_path = bundled_data_path(self) / "products.json"
        with plant_path.open() as json_data:
            self.plants = json.load(json_data)

        await self._load_event_seeds()

        with product_path.open() as json_data:
            self.products = json.load(json_data)

        for product in self.products:
            print("PlantTycoon: Loaded {}".format(product))

    async def _load_event_seeds(self):
        self.plants["all_plants"] = copy.deepcopy(self.plants["plants"])
        plant_options = self.plants["all_plants"]

        d = datetime.date.today()
        month = d.month
        if month == 1:
            plant_options.append(self.plants["event"]["January"])
        elif month == 2:
            plant_options.append(self.plants["event"]["February"])
        elif month == 3:
            plant_options.append(self.plants["event"]["March"])
        elif month == 4:
            plant_options.append(self.plants["event"]["April"])
        elif month == 10:
            plant_options.append(self.plants["event"]["October"])
        elif month == 11:
            plant_options.append(self.plants["event"]["November"])
        elif month == 12:
            plant_options.append(self.plants["event"]["December"])

    async def _gardener(self, user: discord.User) -> Gardener:
        #
        # This function returns a Gardener object for the user
        #

        g = Gardener(user, self.config)
        await g.load_config()
        return g

    async def _degradation(self, gardener: Gardener):
        #
        # Calculating the rate of degradation per check_completion_loop() cycle.
        #
        if self.products is None:
            await self._load_plants_products()

        modifiers = sum(
            self.products[product]["modifier"]
            for product in gardener.products
            if gardener.products[product] > 0
        )

        degradation = (
            100
            / (gardener.current["time"] / 60)
            * (self.defaults["degradation"]["base_degradation"] + gardener.current["degradation"])
        ) + modifiers

        d = collections.namedtuple("degradation", "degradation time modifiers")

        return d(degradation=degradation, time=gardener.current["time"], modifiers=modifiers)

    # async def _get_member(self, user_id):
    #
    #     #
    #     # Return a member object
    #     #
    #
    #     return discord.User(id=user_id)  # I made it a string just to be sure
    #
    # async def _send_notification(self, user_id, message):
    #
    #     #
    #     # Sends a Direct Message to the gardener
    #     #
    #
    #     member = await self._get_member(user_id)
    #     em = discord.Embed(description=message, color=discord.Color.green())
    #     await self.bot.send_message(member, embed=em)

    async def _add_health(self, channel, gardener: Gardener, product, product_category):
        #
        # The function to add health
        #
        if self.products is None:
            await self._load_plants_products()
        product = product.lower()
        product_category = product_category.lower()
        if product in self.products and self.products[product]["category"] == product_category:
            if product in gardener.products and gardener.products[product] > 0:
                gardener.current["health"] += self.products[product]["health"]
                gardener.products[product] -= 1
                if gardener.products[product] == 0:
                    del gardener.products[product.lower()]
                if product_category == "fertilizer":
                    emoji = ":poop:"
                elif product_category == "water":
                    emoji = ":sweat_drops:"
                else:
                    emoji = ":scissors:"
                message = "Your plant got some health back! {}".format(emoji)
                if gardener.current["health"] > gardener.current["threshold"]:
                    gardener.current["health"] -= self.products[product]["damage"]
                    if product_category == "tool":
                        damage_msg = "You used {} too many times!".format(product)
                    else:
                        damage_msg = "You gave too much of {}.".format(product)
                    message = "{} Your plant lost some health. :wilted_rose:".format(damage_msg)
                gardener.points += self.defaults["points"]["add_health"]
                await gardener.save_gardener()
            elif product in gardener.products or product_category != "tool":
                message = "You have no {}. Go buy some!".format(product)
            else:
                message = "You don't have a {}. Go buy one!".format(product)
        else:
            message = "Are you sure you are using {}?".format(product_category)

        if product_category == "water":
            emcolor = discord.Color.blue()
        elif product_category == "fertilizer":
            emcolor = discord.Color.dark_gold()
        # elif product_category == "tool":
        else:
            emcolor = discord.Color.dark_grey()

        em = discord.Embed(description=message, color=emcolor)
        await channel.send(embed=em)

    @commands.group(name="gardening", autohelp=False)
    async def _gardening(self, ctx: commands.Context):
        """Gardening commands."""
        if ctx.invoked_subcommand is None:
            prefix = ctx.prefix

            title = "**Welcome to Plant Tycoon.**\n"
            description = """'Grow your own plant. Be sure to take proper care of yours.\n
            If it successfully grows, you get a reward.\n
            As you nurture your plant, you gain Thneeds which can be exchanged for credits.\n\n
            **Commands**\n\n
            ``{0}gardening seed``: Plant a seed inside the earth.\n
            ``{0}gardening profile``: Check your gardening profile.\n
            ``{0}gardening plants``: Look at the list of the available plants.\n
            ``{0}gardening plant``: Look at the details of a plant.\n
            ``{0}gardening state``: Check the state of your plant.\n
            ``{0}gardening buy``: Buy gardening supplies.\n
            ``{0}gardening convert``: Exchange Thneeds for credits.\n
            ``{0}shovel``: Shovel your plant out.\n
            ``{0}water``: Water your plant.\n
            ``{0}fertilize``: Fertilize the soil.\n
            ``{0}prune``: Prune your plant.\n"""

            em = discord.Embed(
                title=title,
                description=description.format(prefix),
                color=discord.Color.green(),
            )
            em.set_thumbnail(url="https://image.prntscr.com/image/AW7GuFIBSeyEgkR2W3SeiQ.png")
            em.set_footer(
                text="This cog was made by SnappyDragon18 and PaddoInWonderland. Inspired by The Lorax (2012)."
            )
            await ctx.send(embed=em)

    @commands.cooldown(1, 60 * 10, commands.BucketType.user)
    @_gardening.command(name="seed")
    async def _seed(self, ctx: commands.Context):
        """Plant a seed inside the earth."""
        if self.plants is None:
            await self._load_plants_products()
        author = ctx.author
        # server = context.message.server
        # if author.id not in self.gardeners:
        #     self.gardeners[author.id] = {}
        #     self.gardeners[author.id]['current'] = False
        #     self.gardeners[author.id]['points'] = 0
        #     self.gardeners[author.id]['badges'] = []
        #     self.gardeners[author.id]['products'] = {}
        gardener = await self._gardener(author)

        if not gardener.current:
            plant_options = self.plants["all_plants"]

            plant = choice(plant_options)
            plant["timestamp"] = int(time.time())
            plant["degrade_count"] = 0
            # index = len(self.plants["plants"]) - 1
            # del [self.plants["plants"][index]]
            message = (
                "During one of your many heroic adventures, you came across a mysterious bag that said "
                '"pick one". To your surprise it had all kinds of different seeds in them. '
                "And now that you're home, you want to plant it. "
                "You went to a local farmer to identify the seed, and the farmer "
                "said it was {} **{} ({})** seed.\n\n"
                "Take good care of your seed and water it frequently. "
                "Once it blooms, something nice might come from it. "
                "If it dies, however, you will get nothing.".format(
                    plant["article"], plant["name"], plant["rarity"]
                )
            )
            if "water" not in gardener.products:
                gardener.products["water"] = 0
            gardener.products["water"] += 5
            gardener.current = plant
            await gardener.save_gardener()

        else:
            plant = gardener.current
            message = "You're already growing {} **{}**, silly.".format(
                plant["article"], plant["name"]
            )
        em = discord.Embed(description=message, color=discord.Color.green())
        await ctx.send(embed=em)

    @_gardening.command(name="profile")
    async def _profile(self, ctx: commands.Context, *, member: discord.Member = None):
        """Check your gardening profile."""
        author = member if member is not None else ctx.author
        gardener = await self._gardener(author)
        try:
            await self._apply_degradation(gardener)
        except discord.Forbidden:
            await ctx.send("ERROR\nYou blocked me, didn't you?")

        em = discord.Embed(color=discord.Color.green())  # , description='\a\n')
        avatar = author.avatar_url if getattr(author, 'avatar_url', None) else None
        em.set_author(name=f"Gardening profile of {author.display_name}", icon_url=avatar)
        em.add_field(name="**Thneeds**", value=str(gardener.points))
        if gardener.current:
            em.set_thumbnail(url=gardener.current["image"])
            em.add_field(
                name="**Currently growing**",
                value="{0} ({1:.2f}%)".format(
                    gardener.current["name"], gardener.current["health"]
                ),
            )
        else:
            em.add_field(name="**Currently growing**", value="None")
        if not gardener.badges:
            em.add_field(name="**Badges**", value="None")
        else:
            badges = "".join("{}\n".format(badge.capitalize()) for badge in gardener.badges)

            em.add_field(name="**Badges**", value=badges)
        if gardener.products:
            products = ""
            for product_name, product_data in gardener.products.items():
                if self.products[product_name] is None:
                    continue
                products += "{} ({}) {}\n".format(
                    product_name.capitalize(),
                    product_data / self.products[product_name]["uses"],
                    self.products[product_name]["modifier"],
                )
            em.add_field(name="**Products**", value=products)
        else:
            em.add_field(name="**Products**", value="None")
        if gardener.current:
            degradation = await self._degradation(gardener)
            die_in = await _die_in(gardener, degradation)
            to_grow = await _grow_time(gardener)
            em.set_footer(
                text="Total degradation: {0:.2f}% / {1} min (100 / ({2} / 60) * (BaseDegr {3:.2f} + PlantDegr {4:.2f}))"
                " + ModDegr {5:.2f}) Your plant will die in {6} minutes "
                "and {7:.1f} minutes to go for flowering.".format(
                    degradation.degradation,
                    self.defaults["timers"]["degradation"],
                    degradation.time,
                    self.defaults["degradation"]["base_degradation"],
                    gardener.current["degradation"],
                    degradation.modifiers,
                    die_in,
                    to_grow,
                )
            )
        await ctx.send(embed=em)

    @_gardening.command(name="plants")
    async def _plants(self, ctx):
        """Look at the list of the available plants."""
        if self.plants is None:
            await self._load_plants_products()
        tick = ""
        tock = ""
        tick_tock = 0
        for plant in self.plants["all_plants"]:
            if tick_tock == 0:
                tick += "**{}**\n".format(plant["name"])
                tick_tock = 1
            else:
                tock += "**{}**\n".format(plant["name"])
                tick_tock = 0
        em = discord.Embed(title="All plants that are growable", color=discord.Color.green())
        em.add_field(name="\a", value=tick)
        em.add_field(name="\a", value=tock)
        await ctx.send(embed=em)

    @_gardening.command(name="plant")
    async def _plant(self, ctx: commands.Context, *, plantname):
        """Look at the details of a plant."""
        if not plantname:
            await ctx.send_help()
        if self.plants is None:
            await self._load_plants_products()
        t = False
        plant = None
        for p in self.plants["all_plants"]:
            if p["name"].lower() == plantname.lower().strip('"'):
                plant = p
                t = True
                break

        if t:
            em = discord.Embed(
                title="Plant statistics of {}".format(plant["name"]),
                color=discord.Color.green(),
            )
            em.set_thumbnail(url=plant["image"])
            em.add_field(name="**Name**", value=plant["name"])
            em.add_field(name="**Rarity**", value=plant["rarity"].capitalize())
            em.add_field(name="**Grow Time**", value="{0:.1f} minutes".format(plant["time"] / 60))
            em.add_field(name="**Damage Threshold**", value="{}%".format(plant["threshold"]))
            em.add_field(name="**Badge**", value=plant["badge"])
            em.add_field(name="**Reward**", value="{} τ".format(plant["reward"]))
        else:
            message = "I can't seem to find that plant."
            em = discord.Embed(description=message, color=discord.Color.red())
        await ctx.send(embed=em)

    @_gardening.command(name="state")
    async def _state(self, ctx):
        """Check the state of your plant."""
        author = ctx.author
        gardener = await self._gardener(author)
        try:
            await self._apply_degradation(gardener)
        except discord.Forbidden:
            # Couldn't DM the degradation
            await ctx.send("ERROR\nYou blocked me, didn't you?")

        if not gardener.current:
            message = "You're currently not growing a plant."
            em_color = discord.Color.red()
        else:
            plant = gardener.current
            degradation = await self._degradation(gardener)
            die_in = await _die_in(gardener, degradation)
            to_grow = await _grow_time(gardener)
            message = (
                "You're growing {0} **{1}**. "
                "Its health is **{2:.2f}%** and still has to grow for **{3:.1f}** minutes. "
                "It is losing **{4:.2f}%** per minute and will die in **{5:.1f}** minutes.".format(
                    plant["article"],
                    plant["name"],
                    plant["health"],
                    to_grow,
                    degradation.degradation,
                    die_in,
                )
            )
            em_color = discord.Color.green()
        em = discord.Embed(description=message, color=em_color)
        await ctx.send(embed=em)

    @_gardening.command(name="buy")
    async def _buy(self, ctx, product=None, amount: int = 1):
        """Buy gardening supplies."""
        if self.products is None:
            await self._load_plants_products()

        author = ctx.author
        if product is None:
            em = discord.Embed(
                title="All gardening supplies that you can buy:",
                color=discord.Color.green(),
            )
            for pd in self.products:
                em.add_field(
                    name="**{}**".format(pd.capitalize()),
                    value="Cost: {} τ\n+{} health\n-{}% damage\nUses: {}\nCategory: {}".format(
                        self.products[pd]["cost"],
                        self.products[pd]["health"],
                        self.products[pd]["damage"],
                        self.products[pd]["uses"],
                        self.products[pd]["category"],
                    ),
                )
        else:
            if amount <= 0:
                message = "Invalid amount! Must be greater than 1"
            else:
                gardener = await self._gardener(author)
                if product.lower() in self.products and amount > 0:
                    cost = self.products[product.lower()]["cost"] * amount
                    withdraw_points = await _withdraw_points(gardener, cost)
                    if withdraw_points:
                        if product.lower() not in gardener.products:
                            gardener.products[product.lower()] = 0
                        # gardener.products[product.lower()] += amount
                        # Only add it once
                        gardener.products[product.lower()] += (
                            amount * self.products[product.lower()]["uses"]
                        )
                        await gardener.save_gardener()
                        message = "You bought {}.".format(product.lower())
                    else:
                        message = (
                            "You don't have enough Thneeds. You have {}, but need {}.".format(
                                gardener.points,
                                self.products[product.lower()]["cost"] * amount,
                            )
                        )
                else:
                    message = "I don't have this product."
            em = discord.Embed(description=message, color=discord.Color.green())

        await ctx.send(embed=em)

    @_gardening.command(name="convert")
    async def _convert(self, ctx: commands.Context, amount: int):
        """Exchange Thneeds for credits."""
        author = ctx.author
        gardener = await self._gardener(author)

        withdraw_points = await _withdraw_points(gardener, amount)
        plural = ""
        if amount > 0:
            plural = "s"
        if withdraw_points:
            await bank.deposit_credits(author, amount)
            message = "{} Thneed{} successfully exchanged for credits.".format(amount, plural)
            await gardener.save_gardener()
        else:
            message = "You don't have enough Thneed{}. " "You have {}, but need {}.".format(
                plural, gardener.points, amount
            )

        em = discord.Embed(description=message, color=discord.Color.green())
        await ctx.send(embed=em)

    @commands.command(name="shovel")
    async def _shovel(self, ctx: commands.Context):
        """Shovel your plant out."""
        author = ctx.author
        gardener = await self._gardener(author)
        if not gardener.current:
            message = "You're currently not growing a plant."
        else:
            gardener.current = {}
            message = "You successfully shovelled your plant out."
            gardener.points = max(gardener.points, 0)
            await gardener.save_gardener()

        em = discord.Embed(description=message, color=discord.Color.dark_grey())
        await ctx.send(embed=em)

    @commands.command(name="water")
    async def _water(self, ctx):
        """Water your plant."""
        author = ctx.author
        channel = ctx.channel
        gardener = await self._gardener(author)
        try:
            await self._apply_degradation(gardener)
        except discord.Forbidden:
            # Couldn't DM the degradation
            await ctx.send("ERROR\nYou blocked me, didn't you?")
        if not gardener.current:
            message = "You're currently not growing a plant."
            await _send_message(channel, message)
        else:
            product = "water"
            product_category = "water"
            await self._add_health(channel, gardener, product, product_category)

    @commands.command(name="fertilize")
    async def _fertilize(self, ctx, fertilizer):
        """Fertilize the soil."""
        gardener = await self._gardener(ctx.author)
        try:
            await self._apply_degradation(gardener)
        except discord.Forbidden:
            # Couldn't DM the degradation
            await ctx.send("ERROR\nYou blocked me, didn't you?")
        channel = ctx.channel
        product = fertilizer
        if not gardener.current:
            message = "You're currently not growing a plant."
            await _send_message(channel, message)
        else:
            product_category = "fertilizer"
            await self._add_health(channel, gardener, product, product_category)

    @commands.command(name="prune")
    async def _prune(self, ctx):
        """Prune your plant."""
        gardener = await self._gardener(ctx.author)
        try:
            await self._apply_degradation(gardener)
        except discord.Forbidden:
            # Couldn't DM the degradation
            await ctx.send("ERROR\nYou blocked me, didn't you?")
        channel = ctx.channel
        if not gardener.current:
            message = "You're currently not growing a plant."
            await _send_message(channel, message)
        else:
            product = "pruner"
            product_category = "tool"
            await self._add_health(channel, gardener, product, product_category)

    # async def check_degradation(self):
    #     while "PlantTycoon" in self.bot.cogs:
    #         users = await self.config.all_users()
    #         for user_id in users:
    #             user = self.bot.get_user(user_id)
    #             gardener = await self._gardener(user)
    #             await self._apply_degradation(gardener)
    #         await asyncio.sleep(self.defaults["timers"]["degradation"] * 60)

    async def _apply_degradation(self, gardener):
        if gardener.current:
            degradation = await self._degradation(gardener)
            now = int(time.time())
            timestamp = gardener.current["timestamp"]
            degradation_count = (now - timestamp) // (self.defaults["timers"]["degradation"] * 60)
            degradation_count -= gardener.current["degrade_count"]
            gardener.current["health"] -= degradation.degradation * degradation_count
            gardener.points += self.defaults["points"]["growing"] * degradation_count
            gardener.current["degrade_count"] += degradation_count
            await gardener.save_gardener()
            await gardener.is_complete(now)

    async def check_completion_loop(self):
        while "PlantTycoon" in self.bot.cogs:
            now = int(time.time())
            users = await self.config.all_users()
            for user_id in users:
                user = self.bot.get_user(user_id)
                if not user:
                    continue
                gardener = await self._gardener(user)
                if not gardener:
                    continue
                try:
                    await self._apply_degradation(gardener)
                    await gardener.is_complete(now)
                except discord.Forbidden:
                    # Couldn't DM the results
                    pass
            await asyncio.sleep(self.defaults["timers"]["completion"] * 60)

    async def send_notification(self):
        while "PlantTycoon" in self.bot.cogs:
            users = await self.config.all_users()
            for user_id in users:
                user = self.bot.get_user(user_id)
                if not user:
                    continue
                gardener = await self._gardener(user)
                if not gardener:
                    continue
                try:
                    await self._apply_degradation(gardener)
                except discord.Forbidden:
                    # Couldn't DM the degradation
                    pass

                if gardener.current:
                    health = gardener.current["health"]
                    if health < self.defaults["notification"]["max_health"]:
                        message = choice(self.notifications["messages"])
                        try:
                            await user.send(message)
                        except discord.Forbidden:
                            # Couldn't DM the results
                            pass
            await asyncio.sleep(self.defaults["timers"]["notification"] * 60)

    def cog_unload(self):
        self.completion_task.cancel()
        # self.degradation_task.cancel()
        self.notification_task.cancel()
