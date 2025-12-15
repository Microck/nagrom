from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from ..bot import NagromBot


class ContextMenu(commands.Cog):
    def __init__(self, bot: NagromBot):
        self.bot = bot
        self.ctx_menu = app_commands.ContextMenu(
            name="Check Facts",
            callback=self.check_facts_context,
        )
        self.bot.tree.add_command(self.ctx_menu)

    async def check_facts_context(
        self, interaction: discord.Interaction, message: discord.Message
    ) -> None:
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


async def setup(bot: NagromBot) -> None:
    await bot.add_cog(ContextMenu(bot))