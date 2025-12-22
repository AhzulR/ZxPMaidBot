# cogs/carousel.py

import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from typing import List, Tuple

# Replace with your actual gallery channel ID (int)
GALLERY_CHANNEL_ID = 1407688670550560902  # <-- SET THIS


class CarouselView(discord.ui.View):
    def __init__(self, images: List[Tuple[str, str]], start_index: int = 0, auto_loop: bool = True, loop_delay: int = 10):
        """
        images: list of tuples (image_url, caption_text)
        start_index: starting slide index
        auto_loop: whether to auto-advance slides
        loop_delay: seconds between auto-advances
        """
        super().__init__(timeout=300)  # 5 minutes view lifetime
        self.images = images
        self.index = start_index
        self.message: discord.Message | None = None
        self.auto_loop = auto_loop
        self.loop_delay = loop_delay
        self._loop_task: asyncio.Task | None = None

    def build_embed(self) -> discord.Embed:
        url, text = self.images[self.index]
        embed = discord.Embed(
            title=f"Gallery ({self.index + 1}/{len(self.images)})",
            description=text or " ",
            color=0x00bfff,
        )
        embed.set_image(url=url)
        return embed

    async def start(self, interaction: discord.Interaction):
        # Send the initial message and start optional auto loop
        embed = self.build_embed()
        self.message = await interaction.response.send_message(embed=embed, view=self)
        # If using followup, adjust to: self.message = await interaction.followup.send(...)
        if self.auto_loop:
            self._loop_task = asyncio.create_task(self._auto_advance())

    async def _auto_advance(self):
        # Simple auto-advance loop
        try:
            while True:
                await asyncio.sleep(self.loop_delay)
                if self.message is None:
                    break
                # advance index
                self.index = (self.index + 1) % len(self.images)
                embed = self.build_embed()
                await self.message.edit(embed=embed, view=self)
        except asyncio.CancelledError:
            pass

    async def on_timeout(self):
        # Stop auto loop and disable buttons after timeout
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        if self.message:
            await self.message.edit(view=self)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index - 1) % len(self.images)
        embed = self.build_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index + 1) % len(self.images)
        embed = self.build_embed()
        await interaction.response.edit_message(embed=embed, view=self)


class Carousel(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _load_gallery_images(self, guild: discord.Guild) -> List[Tuple[str, str]]:
        """
        Read recent messages from the gallery channel
        and collect image URLs + simple text.
        """
        channel = guild.get_channel(GALLERY_CHANNEL_ID)
        if channel is None or not isinstance(channel, discord.TextChannel):
            raise RuntimeError("Gallery channel not found or not a text channel")

        images: List[Tuple[str, str]] = []

        # Tune limit as needed (e.g. 200)
        async for msg in channel.history(limit=100):
            # Attachments-based images
            for attachment in msg.attachments:
                if attachment.content_type and attachment.content_type.startswith("image/"):
                    caption = msg.content or attachment.filename
                    images.append((attachment.url, caption))
            # If you also want image URLs in content, you can add link-detection here

        # Reverse to show oldest first, or remove this to show newest first
        images.reverse()

        if not images:
            raise RuntimeError("No images found in the gallery channel")

        return images

    @app_commands.command(name="gallery", description="Show a looping image gallery from the gallery channel")
    async def gallery(self, interaction: discord.Interaction):
        # Ensure we have a guild
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        try:
            images = await self._load_gallery_images(interaction.guild)
        except RuntimeError as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return

        view = CarouselView(images=images, auto_loop=True, loop_delay=10)
        await view.start(interaction)


async def setup(bot: commands.Bot):
    await bot.add_cog(Carousel(bot))
