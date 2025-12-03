from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from ..bot import AVABot


class ContextMenu(commands.Cog):
    def __init__(self, bot: AVABot):
        self.bot = bot
        self.ctx_menu = app_commands.ContextMenu(
            name="Check Facts",
            callback=self.check_facts_context,
        )
        self.bot.tree.add_command(self.ctx_menu)

    async def check_facts_context(
        self, interaction: discord.Interaction, message: discord.Message
    ) -> None:
        if not message.content:
            await interaction.response.send_message(
                "Message has no text content to verify.",
                ephemeral=True,
            )
            return

        allowed, reason = self.bot.rate_limiter.check(
            interaction.user.id, interaction.guild_id or 0
        )
        if not allowed:
            await interaction.response.send_message(
                f"Rate limit: {reason}", ephemeral=True
            )
            return

        text_to_check = message.content[:500]

        ok, queue_reason = await self.bot.submit_fact_check(
            guild_id=interaction.guild_id,
            channel_id=interaction.channel_id,
            source_message_id=message.id,
            requestor_id=interaction.user.id,
            statement_author_id=message.author.id,
            input_text=text_to_check,
            trigger_type="context",
        )
        if not ok:
            await interaction.response.send_message(
                queue_reason, ephemeral=True
            )
            return

        await interaction.response.send_message(
            "Fact-check request queued. Results will be posted in this channel.",
            ephemeral=True,
        )


async def setup(bot: AVABot) -> None:
    await bot.add_cog(ContextMenu(bot))