# bot.py

import os
import asyncio
import logging
from dotenv import load_dotenv
from datetime import datetime

import discord
from discord.ext import commands
from discord import app_commands

# ================
# CONFIG / TOKEN
# ================
# Option A: read from environment variable (recommended)
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Option B: hardcode for local testing ONLY (never commit to git)
# TOKEN = "YOUR_BOT_TOKEN_HERE"

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN not set. Set env var or hardcode temporarily in bot.py")


# ==========
# Logging
# ==========
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(
            f"logs/bot_{datetime.now().strftime('%Y%m%d')}.log",
            encoding="utf-8",
        ),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("bot")


# ==========
# Intents
# ==========
# For this simple gallery bot, default + message_content is enough.
intents = discord.Intents.default()
intents.message_content = True  # needed if you add text commands later


# ==========
# Bot class
# ==========
class GalleryBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",      # you can change this
            intents=intents,
            help_command=None,
        )

    async def setup_hook(self):
        """
        Called before the bot connects to Discord.
        Load cogs and sync slash commands here.
        """
        initial_cogs = [
            "cogs.carousel",   # our gallery/slider feature
            "cogs.greetings",
            "cogs.memory"
        ]

        for ext in initial_cogs:
            try:
                await self.load_extension(ext)
                logger.info("Loaded extension: %s", ext)
            except Exception as e:
                logger.exception("Failed to load extension %s: %s", ext, e)

        # Sync application (slash) commands globally
        try:
            await self.tree.sync()
            logger.info("Synced application commands globally")
        except Exception as e:
            logger.exception("Failed to sync application commands: %s", e)

    async def on_ready(self):
        logger.info("Logged in as %s (ID: %s)", self.user, self.user.id)
        activity = discord.Game(name="/gallery")
        await self.change_presence(status=discord.Status.online, activity=activity)


bot = GalleryBot()


# ==========
# Simple /ping test
# ==========

@bot.tree.command(name="ping", description="Check if the bot is alive")
async def ping_slash(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!", ephemeral=True)


# ==========
# Entrypoint
# ==========

async def main():
    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
