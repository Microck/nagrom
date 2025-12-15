from __future__ import annotations

import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import func, select

from ..bot import NagromBot
from ..models.database import FactCheck, User

logger = logging.getLogger(__name__)

class StatsCommands(commands.Cog):
    def __init__(self, bot: NagromBot):
        self.bot = bot

    @app_commands.command(name="stats", description="View fact-checking statistics.")
    async def stats(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
        target_user = user or interaction.user
        
        async with self.bot.db.session_maker() as session:
            total_checks = await session.scalar(
                select(func.count(FactCheck.id)).where(FactCheck.user_id == target_user.id)
            ) or 0
            
            verdicts = await session.execute(
                select(FactCheck.verdict, func.count(FactCheck.id))
                .where(FactCheck.user_id == target_user.id)
                .group_by(FactCheck.verdict)
            )
            verdict_map = {row[0].upper(): row[1] for row in verdicts}
            
            true_count = verdict_map.get("TRUE", 0)
            false_count = verdict_map.get("FALSE", 0)
            total_verifiable = true_count + false_count
            accuracy = (true_count / total_verifiable * 100) if total_verifiable > 0 else 0.0

        embed = discord.Embed(title=f"Stats for {target_user.display_name}", color=discord.Color.blue())
        embed.set_thumbnail(url=target_user.display_avatar.url)
        
        embed.add_field(name="Total Checks", value=str(total_checks), inline=True)
        embed.add_field(name="Accuracy Score", value=f"{accuracy:.1f}%", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        
        embed.add_field(name="True Claims", value=str(true_count), inline=True)
        embed.add_field(name="False Claims", value=str(false_count), inline=True)
        embed.add_field(name="Unverifiable", value=str(verdict_map.get("UNVERIFIABLE", 0)), inline=True)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="cost", description="View estimated LLM usage costs (Owner Only).")
    async def cost(self, interaction: discord.Interaction):
        if not await self.bot.is_owner(interaction.user):
            await interaction.response.send_message("Only the bot owner can view costs.", ephemeral=True)
            return

        async with self.bot.db.session_maker() as session:
            result = await session.execute(
                select(
                    func.sum(FactCheck.input_tokens),
                    func.sum(FactCheck.output_tokens),
                    func.sum(FactCheck.cost)
                )
            )
            row = result.first()
            input_tokens = row[0] or 0
            output_tokens = row[1] or 0
            total_cost = row[2] or 0.0

        embed = discord.Embed(title="Estimated LLM Costs", color=discord.Color.green())
        embed.add_field(name="Input Tokens", value=f"{input_tokens:,}", inline=True)
        embed.add_field(name="Output Tokens", value=f"{output_tokens:,}", inline=True)
        embed.add_field(name="Total Cost (Est.)", value=f"${total_cost:.4f}", inline=False)
        embed.set_footer(text="Based on naive blended rate ($0.50/1M). Actuals may vary.")

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: NagromBot):
    await bot.add_cog(StatsCommands(bot))
