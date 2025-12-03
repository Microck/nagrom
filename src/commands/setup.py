from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from ..bot import AVABot


class SetupCog(commands.Cog):
    def __init__(self, bot: AVABot):
        self.bot = bot

    @app_commands.command(name="check", description="Manually verify a statement")
    async def check(self, interaction: discord.Interaction, statement: str) -> None:
        if len(statement) > 500:
            await interaction.response.send_message(
                "Statement too long. Maximum length is 500 characters.",
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

        ok, queue_reason = await self.bot.submit_fact_check(
            guild_id=interaction.guild_id,
            channel_id=interaction.channel_id,
            source_message_id=None,
            requestor_id=interaction.user.id,
            statement_author_id=interaction.user.id,
            input_text=statement,
            trigger_type="slash",
        )
        if not ok:
            await interaction.response.send_message(
                queue_reason, ephemeral=True
            )
            return

        await interaction.response.send_message(
            "Your fact-check request has been queued. Results will be posted here shortly.",
            ephemeral=True,
        )


async def setup(bot: AVABot) -> None:
    await bot.add_cog(SetupCog(bot))