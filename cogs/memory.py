# cogs/memory.py

import json
import os
import random
from datetime import datetime, timezone

import discord
from discord.ext import commands

DATA_DIR = "data"
MEMORY_FILE = os.path.join(DATA_DIR, "memories.json")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryPanelView(discord.ui.View):
    def __init__(self, cog: "Memory"):
        super().__init__(timeout=300)  # 5 minutes
        self.cog = cog

    @discord.ui.button(label="Add", style=discord.ButtonStyle.success)
    async def add_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Ask user for a memory via modal or follow-up message.
        For simplicity here, we ask user to type their memory in the chat.
        """
        await interaction.response.send_message(
            "Please type your memory in the chat within 60 seconds:",
            ephemeral=True
        )

        def check(m: discord.Message):
            return (
                m.author == interaction.user
                and m.channel == interaction.channel
            )

        try:
            msg = await self.cog.bot.wait_for("message", timeout=60.0, check=check)
        except Exception:
            await interaction.followup.send("Timed out waiting for your memory.", ephemeral=True)
            return

        ctx = await self.cog.bot.get_context(msg)
        # Reuse the existing add_memory logic
        await self.cog.add_memory(ctx, text=msg.content)

    @discord.ui.button(label="📃List", style=discord.ButtonStyle.primary)
    async def list_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Show latest memories (same as !listmemory).
        """
        # Build a fake ctx-like object: we just need channel/guild
        class DummyCtx:
            def __init__(self, interaction: discord.Interaction):
                self.guild = interaction.guild
                self.channel = interaction.channel

            async def send(self, *args, **kwargs):
                # Send into channel, public
                return await interaction.channel.send(*args, **kwargs)

        dummy_ctx = DummyCtx(interaction)
        await self.cog.list_memory(dummy_ctx, count=5)
        await interaction.response.defer()  # acknowledge button

    @discord.ui.button(label="🎲Random", style=discord.ButtonStyle.secondary)
    async def random_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Show one random memory (same as !randommemory).
        """
        class DummyCtx:
            def __init__(self, interaction: discord.Interaction):
                self.guild = interaction.guild
                self.channel = interaction.channel

            async def send(self, *args, **kwargs):
                return await interaction.channel.send(*args, **kwargs)

        dummy_ctx = DummyCtx(interaction)
        await self.cog.random_memory(dummy_ctx)
        await interaction.response.defer()


class Memory(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        os.makedirs(DATA_DIR, exist_ok=True)
        self.memories = self._load_memories()

    # ==========
    # JSON helpers
    # ==========

    def _load_memories(self):
        if not os.path.exists(MEMORY_FILE):
            return []
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            return []
        except Exception:
            return []

    def _save_memories(self):
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.memories, f, ensure_ascii=False, indent=2)

    def _add_memory(self, guild_id: int, author_id: int, text: str, message_link: str | None):
        entry = {
            "guild_id": guild_id,
            "author_id": author_id,
            "text": text,
            "message_link": message_link,
            "created_at": _now_iso(),
        }
        self.memories.append(entry)
        self._save_memories()
        return entry

    def _get_guild_memories(self, guild_id: int):
        return [m for m in self.memories if m.get("guild_id") == guild_id]

    def _build_memory_embed(self, mem: dict, guild: discord.Guild | None) -> discord.Embed:
        created_at = mem.get("created_at")
        try:
            dt = datetime.fromisoformat(created_at)
            unix = int(dt.timestamp())
            when_text = f"<t:{unix}:F> (<t:{unix}:R>)"
        except Exception:
            when_text = created_at or "Unknown time"

        author = guild.get_member(mem.get("author_id")) if guild else None
        author_name = author.mention if author else f"User ID {mem.get('author_id')}"

        embed = discord.Embed(
            title="💖 Memory",
            description=mem.get("text", ""),
            color=0xffa6c9,
        )
        embed.add_field(name="From", value=author_name, inline=False)
        embed.add_field(name="When", value=when_text, inline=False)

        link = mem.get("message_link")
        if link:
            embed.add_field(name="Original message", value=link, inline=False)

        return embed

    # ==========
    # Commands
    # ==========

    @commands.command(name="addmemory")
    async def add_memory(self, ctx: commands.Context, *, text: str):
        """
        Save a love memory and show it as embed.
        Usage: !addmemory We watched a movie together today
        """
        if not ctx.guild:
            await ctx.send("This command can only be used in a server.")
            return

        message_link = ctx.message.jump_url
        mem = self._add_memory(
            guild_id=ctx.guild.id,
            author_id=ctx.author.id,
            text=text,
            message_link=message_link,
        )

        embed = self._build_memory_embed(mem, ctx.guild)
        await ctx.send("Memory saved. 💌", embed=embed)

    @commands.command(name="randommemory")
    async def random_memory(self, ctx: commands.Context):
        """
        Show one random saved memory.
        """
        if not ctx.guild:
            await ctx.send("This command can only be used in a server.")
            return

        guild_memories = self._get_guild_memories(ctx.guild.id)
        if not guild_memories:
            await ctx.send("No memories saved yet. Use `!addmemory` to add one.")
            return

        mem = random.choice(guild_memories)
        embed = self._build_memory_embed(mem, ctx.guild)
        await ctx.send(embed=embed)

    @commands.command(name="listmemory")
    async def list_memory(self, ctx: commands.Context, count: int = 5):
        """
        List latest N memories (default 5).
        Usage: !listmemory
               !listmemory 10
        """
        if not ctx.guild:
            await ctx.send("This command can only be used in a server.")
            return

        guild_memories = self._get_guild_memories(ctx.guild.id)
        if not guild_memories:
            await ctx.send("No memories saved yet. Use `!addmemory` to add one.")
            return

        try:
            guild_memories.sort(
                key=lambda m: datetime.fromisoformat(m.get("created_at", ""))  # type: ignore[arg-type]
            )
        except Exception:
            pass

        count = max(1, min(count, 20))
        latest = guild_memories[-count:]

        embed = discord.Embed(
            title=f"📜 Last {len(latest)} Memories",
            color=0xffd1e3,
        )

        for mem in latest:
            created_at = mem.get("created_at")
            try:
                dt = datetime.fromisoformat(created_at)
                unix = int(dt.timestamp())
                when_short = f"<t:{unix}:R>"
            except Exception:
                when_short = created_at or "Unknown time"

            author = ctx.guild.get_member(mem.get("author_id")) if ctx.guild else None
            author_name = author.mention if author else f"User ID {mem.get('author_id')}"

            text = mem.get("text", "")
            link = mem.get("message_link")
            value_parts = [f"{text}", f"By: {author_name}", f"When: {when_short}"]
            if link:
                value_parts.append(f"[Jump to message]({link})")

            embed.add_field(
                name="\u200b",
                value="\n".join(value_parts),
                inline=False,
            )

        await ctx.send(embed=embed)

    # ==========
    # Panel command
    # ==========

    @commands.command(name="memorypanel")
    async def memory_panel(self, ctx: commands.Context):
        """
        Show a panel with buttons: Add, List, Random.
        """
        view = MemoryPanelView(self)
        embed = discord.Embed(
            title="💞 Memory Panel",
            description=(
                "Use the buttons below to manage your memories:\n"
                "• **Add** – add a new memory\n"
                "• **List** – show latest memories\n"
                "• **Random** – show a random memory"
            ),
            color=0xffc0e0,
        )
        await ctx.send(embed=embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(Memory(bot))
