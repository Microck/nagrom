from __future__ import annotations

import discord
from discord import app_commands, ui
from discord.ext import commands

from ..bot import NagromBot


class ContextModal(ui.Modal, title="Context Options"):
    """Modal to select how many context messages to include."""
    
    context_count = ui.TextInput(
        label="Context messages (0-10)",
        placeholder="0",
        default="0",
        max_length=2,
        required=False
    )
    
    def __init__(self, bot: NagromBot, message: discord.Message):
        super().__init__()
        self.bot = bot
        self.target_message = message
    
    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=False)
        
        try:
            count = int(self.context_count.value or "0")
            count = max(0, min(count, 10))
        except ValueError:
            count = 0
        
        if not self.target_message.content:
            await interaction.followup.send(
                "Message has no text content to verify.",
                ephemeral=True,
            )
            return

        allowed, reason = self.bot.rate_limiter.check(
            interaction.user.id, interaction.guild_id or 0
        )
        if not allowed:
            await interaction.followup.send(
                f"Rate limit: {reason}", ephemeral=True
            )
            return

        text_to_check = self.target_message.content[:500]
        
        if count > 0:
            try:
                history = [msg async for msg in self.target_message.channel.history(
                    limit=count, before=self.target_message
                )]
                if history:
                    context_text = "\n".join([
                        f"{m.author.name}: {m.content}" for m in reversed(history)
                    ])
                    text_to_check = (
                        f"Context:\n{context_text}\n\n"
                        f"{self.target_message.author.name}: {self.target_message.content}\n\n"
                        f"Target Claim: {self.target_message.content[:500]}"
                    )
            except Exception:
                pass

        # Send loading placeholder
        loading_embed = discord.Embed(
            description="Searching sources and analyzing...",
            color=discord.Color.blue()
        )
        loading_embed.set_footer(text="This may take a moment.")
        
        placeholder_msg = await interaction.followup.send(embed=loading_embed, wait=True)

        ok, queue_reason = await self.bot.submit_fact_check(
            guild_id=interaction.guild_id,
            channel_id=interaction.channel_id,
            source_message_id=self.target_message.id,
            requestor_id=interaction.user.id,
            statement_author_id=self.target_message.author.id,
            input_text=text_to_check,
            trigger_type="context",
            placeholder_message_id=placeholder_msg.id
        )
        if not ok:
            await placeholder_msg.edit(content=queue_reason, embed=None)


class ContextMenu(commands.Cog):
    def __init__(self, bot: NagromBot):
        self.bot = bot
        self.ctx_menu = app_commands.ContextMenu(
            name="Check Facts",
            callback=self.check_facts_context,
        )
        self.ctx_menu_with_context = app_commands.ContextMenu(
            name="Check Facts (with context)",
            callback=self.check_facts_with_context,
        )
        self.bot.tree.add_command(self.ctx_menu)
        self.bot.tree.add_command(self.ctx_menu_with_context)

    async def check_facts_context(
        self, interaction: discord.Interaction, message: discord.Message
    ) -> None:
        """Quick fact-check without context."""
        await interaction.response.defer(ephemeral=False)

        if not message.content:
            await interaction.followup.send(
                "Message has no text content to verify.",
                ephemeral=True,
            )
            return

        allowed, reason = self.bot.rate_limiter.check(
            interaction.user.id, interaction.guild_id or 0
        )
        if not allowed:
            await interaction.followup.send(
                f"Rate limit: {reason}", ephemeral=True
            )
            return

        text_to_check = message.content[:500]

        # Send loading placeholder
        loading_embed = discord.Embed(
            description="Searching sources and analyzing...",
            color=discord.Color.blue()
        )
        loading_embed.set_footer(text="This may take a moment.")
        
        placeholder_msg = await interaction.followup.send(embed=loading_embed, wait=True)

        ok, queue_reason = await self.bot.submit_fact_check(
            guild_id=interaction.guild_id,
            channel_id=interaction.channel_id,
            source_message_id=message.id,
            requestor_id=interaction.user.id,
            statement_author_id=message.author.id,
            input_text=text_to_check,
            trigger_type="context",
            placeholder_message_id=placeholder_msg.id
        )
        if not ok:
            await placeholder_msg.edit(content=queue_reason, embed=None)
            return

    async def check_facts_with_context(
        self, interaction: discord.Interaction, message: discord.Message
    ) -> None:
        """Fact-check with context modal."""
        modal = ContextModal(self.bot, message)
        await interaction.response.send_modal(modal)


async def setup(bot: NagromBot) -> None:
    await bot.add_cog(ContextMenu(bot))