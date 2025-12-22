# cogs/greetings.py

import random
from datetime import datetime, time, timedelta, timezone

import discord
from discord.ext import commands, tasks

GREET_CHANNEL_ID = 1452696895507005460  # your channel ID
YOU_ID = 431090838022651915           # your ID
LOVE_ID = 763029626594525214          # partner ID

WIB = timezone(timedelta(hours=7))

MORNING_TIME = time(hour=8, minute=0, tzinfo=WIB)
NIGHT_TIME = time(hour=0, minute=0, tzinfo=WIB)


class Greetings(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        you = f"<@{YOU_ID}>"
        love = f"<@{LOVE_ID}>"
        pair = f"{you} {love}"

        self.morning_messages = [
            f"Good morning {pair}! ☀️ New day, new chances to love each other even more.",
            f"Rise and shine {pair}! Today is another chapter in your love story.",
            f"Morning {pair}! Don’t forget: coffee first, cuddles always. ☕❤️",
            f"Good morning {pair}! May your day be as soft and warm as your hugs.",
            f"Hey {pair}, wake up slowly and gently. The world can wait while you two exist together. 🌤️",
            f"Good morning {pair}! Remember: you’re each other’s best plot twist.",
            f"Sun’s up {pair}! Today is a good day to fall in love with each other all over again.",
            f"Good morning {pair}! Whatever happens today, you’ve already won because you have each other. 💕",
            f"Hi {pair}! Deep breaths, soft hearts, and a lot of love for today.",
            f"Morning {pair}! If today was a playlist, it would start with your smiles. 🎵",
        ]

        self.night_messages = [
            f"Good night {pair} 🌙 Close your eyes, rest your hearts, you’re safe in each other.",
            f"Sleep well {pair}! The day is over, but your love is still shining.",
            f"Time to sleep {pair} 😴 Leave the worries to tomorrow, keep the love for tonight.",
            f"Good night {pair}! May your dreams be soft and full of each other.",
            f"Nighty night {pair} 💫 You’ve survived today, that’s more than enough.",
            f"Sweet dreams {pair}! Even the stars are jealous of how bright your love is.",
            f"Good night {pair} 🌌 No matter how far or near, your hearts sleep side by side.",
            f"Rest well {pair}! Refill your energy and your love bar for tomorrow. ❤️‍🔥",
            f"Lights off, hearts on {pair}. Good night and sleep in peace.",
            f"Good night {pair}! Hug your pillow like you’re hugging each other.",
        ]

        self.morning_task.start()
        self.night_task.start()

    # ==========
    # Helpers
    # ==========

    def _next_datetime_for(self, target: time) -> datetime:
        """Return the next datetime in WIB for the given time today or tomorrow."""
        now = datetime.now(WIB)
        today_dt = datetime.combine(now.date(), target, tzinfo=WIB)
        if today_dt <= now:
            today_dt += timedelta(days=1)
        return today_dt

    # ==========
    # Auto tasks
    # ==========

    @tasks.loop(time=MORNING_TIME)
    async def morning_task(self):
        channel = self.bot.get_channel(GREET_CHANNEL_ID)
        if not isinstance(channel, discord.TextChannel):
            return
        msg = random.choice(self.morning_messages)
        await channel.send(msg)

    @morning_task.before_loop
    async def before_morning(self):
        await self.bot.wait_until_ready()

    @tasks.loop(time=NIGHT_TIME)
    async def night_task(self):
        channel = self.bot.get_channel(GREET_CHANNEL_ID)
        if not isinstance(channel, discord.TextChannel):
            return
        msg = random.choice(self.night_messages)
        await channel.send(msg)

    @night_task.before_loop
    async def before_night(self):
        await self.bot.wait_until_ready()

    # ==========
    # Test commands
    # ==========

    @commands.command(name="testmorning")
    async def test_morning(self, ctx: commands.Context):
        """Send one random morning message immediately."""
        msg = random.choice(self.morning_messages)
        await ctx.send(msg)

    @commands.command(name="testnight")
    async def test_night(self, ctx: commands.Context):
        """Send one random night message immediately."""
        msg = random.choice(self.night_messages)
        await ctx.send(msg)

    # ==========
    # Next run info
    # ==========

    @commands.command(name="nextmorning")
    async def next_morning(self, ctx: commands.Context):
        """Show when the next automatic morning message will run."""
        dt = self._next_datetime_for(MORNING_TIME)
        # Format nicely in WIB and also show Discord timestamp
        unix = int(dt.timestamp())
        text = dt.strftime("%Y-%m-%d %H:%M WIB")
        await ctx.send(
            f"Next **morning** message will run at: {text} (<t:{unix}:R>)"
        )

    @commands.command(name="nextnight")
    async def next_night(self, ctx: commands.Context):
        """Show when the next automatic night message will run."""
        dt = self._next_datetime_for(NIGHT_TIME)
        unix = int(dt.timestamp())
        text = dt.strftime("%Y-%m-%d %H:%M WIB")
        await ctx.send(
            f"Next **night** message will run at: {text} (<t:{unix}:R>)"
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Greetings(bot))
