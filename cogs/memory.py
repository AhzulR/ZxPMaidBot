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

    def _build_list_embed(self, guild: discord.Guild, count: int = 5) -> discord.Embed | None:
        guild_memories = self._get_guild_memories(guild.id)
        if not guild_memories:
            return None

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

            author = guild.get_member(mem.get("author_id")) if guild else None
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

        return embed

    # ==========
    # Basic commands (still usable)
    # ==========

    @commands.command(name="addmemory")
    async def add_memory_cmd(self, ctx: commands.Context, *, text: str):
        """CLI version: add memory by command."""
        if not ctx.guild:
            await ctx.send("This command can only be used in a server.")
            return

        mem = self._add_memory(
            guild_id=ctx.guild.id,
            author_id=ctx.author.id,
            text=text,
            message_link=ctx.message.jump_url,
        )

        embed = self._build_memory_embed(mem, ctx.guild)
        await ctx.send("Memory saved. 💌", embed=embed)

    @commands.command(name="randommemory")
    async def random_memory_cmd(self, ctx: commands.Context):
        """CLI version: random memory."""
        if not ctx.guild:
            await ctx.send("This command can only be used in a server.")
            return

        guild_memories = self._get_guild_memories(ctx.guild.id)
        if not guild_memories:
            await ctx.send("No memories saved yet. Use `!addmemory` or the panel to add one.")
            return

        mem = random.choice(guild_memories)
        embed = self._build_memory_embed(mem, ctx.guild)
        await ctx.send(embed=embed)

    @commands.command(name="listmemory")
    async def list_memory_cmd(self, ctx: commands.Context, count: int = 5):
        """CLI version: list memories."""
        if not ctx.guild:
            await ctx.send("This command can only be used in a server.")
            return

        embed = self._build_list_embed(ctx.guild, count=count)
        if embed is None:
            await ctx.send("No memories saved yet. Use `!addmemory` or the panel to add one.")
            return

        await ctx.send(embed=embed)

    # ==========
    # Panel + modal
    # ==========

    @commands.command(name="memorypanel")
    async def memory_panel(self, ctx: commands.Context):
        """Show the interactive Memory Panel."""
        if not ctx.guild:
            await ctx.send("This command can only be used in a server.")
            return

        view = MemoryPanelView(self)
        embed = discord.Embed(
            title="💞 Memory Panel",
            description=(
                "Use the buttons below to manage your memories:\n"
                "• **Add** – open a modal to add a new memory\n"
                "• **List** – show latest memories\n"
                "• **Random** – show a random memory"
            ),
            color=0xffc0e0,
        )
        msg = await ctx.send(embed=embed, view=view)
        view.message = msg  # store message so view can delete it later


class MemoryModal(discord.ui.Modal, title="Add a Memory"):
    def __init__(self, cog: Memory, interaction: discord.Interaction, panel_message: discord.Message):
        super().__init__(timeout=300)
        self.cog = cog
        self.interaction = interaction
        self.panel_message = panel_message

        self.memory_text = discord.ui.TextInput(
            label="Your memory",
            style=discord.TextStyle.paragraph,
            placeholder="Write something sweet…",
            max_length=500,
            required=True,
        )

        self.add_item(self.memory_text)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("This only works in a server.", ephemeral=True)
            return

        text = str(self.memory_text.value)

        # Save memory
        mem = self.cog._add_memory(
            guild_id=guild.id,
            author_id=interaction.user.id,
            text=text,
            message_link=self.panel_message.jump_url,
        )

        # Delete old panel message
        try:
            await self.panel_message.delete()
        except discord.HTTPException:
            pass

        # Show memory embed
        embed = self.cog._build_memory_embed(mem, guild)
        await interaction.response.send_message("Memory saved. 💌", embed=embed)

        # Respawn a fresh panel at the bottom
        view = MemoryPanelView(self.cog)
        panel_embed = discord.Embed(
            title="💞 Memory Panel",
            description=(
                "Use the buttons below to manage your memories:\n"
                "• **Add** – open a modal to add a new memory\n"
                "• **List** – show latest memories\n"
                "• **Random** – show a random memory"
            ),
            color=0xffc0e0,
        )
        new_msg = await interaction.followup.send(embed=panel_embed, view=view)
        view.message = new_msg


class MemoryPanelView(discord.ui.View):
    def __init__(self, cog: Memory):
        super().__init__(timeout=None)
        self.cog = cog
        self.message: discord.Message | None = None

    async def _respawn_panel(self, interaction: discord.Interaction):
        # Delete old panel message
        if self.message:
            try:
                await self.message.delete()
            except discord.HTTPException:
                pass

        # Send new panel
        new_view = MemoryPanelView(self.cog)
        embed = discord.Embed(
            title="💞 Memory Panel",
            description=(
                "Use the buttons below to manage your memories:\n"
                "• **Add** – open a modal to add a new memory\n"
                "• **List** – show latest memories\n"
                "• **Random** – show a random memory"
            ),
            color=0xffc0e0,
        )
        new_msg = await interaction.followup.send(embed=embed, view=new_view)
        new_view.message = new_msg

    @discord.ui.button(label="Add", style=discord.ButtonStyle.success)
    async def add_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Open modal to collect memory text
        if self.message is None:
            self.message = interaction.message
        modal = MemoryModal(self.cog, interaction, self.message)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="List", style=discord.ButtonStyle.primary)
    async def list_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("This only works in a server.", ephemeral=True)
            return

        embed = self.cog._build_list_embed(guild, count=5)
        if embed is None:
            await interaction.response.send_message(
                "No memories saved yet. Add one first.",
                ephemeral=True,
            )
            return

        # Show list, then respawn panel
        await interaction.response.send_message(embed=embed)
        await self._respawn_panel(interaction)

    @discord.ui.button(label="Random", style=discord.ButtonStyle.secondary)
    async def random_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("This only works in a server.", ephemeral=True)
            return

        guild_memories = self.cog._get_guild_memories(guild.id)
        if not guild_memories:
            await interaction.response.send_message(
                "No memories saved yet. Add one first.",
                ephemeral=True,
            )
            return

        mem = random.choice(guild_memories)
        embed = self.cog._build_memory_embed(mem, guild)

        # Show random, then respawn panel
        await interaction.response.send_message(embed=embed)
        await self._respawn_panel(interaction)


async def setup(bot: commands.Bot):
    await bot.add_cog(Memory(bot))
