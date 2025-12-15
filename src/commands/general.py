from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from sqlalchemy import select, func
import psutil

from ..bot import NagromBot
from ..models.database import FactCheck


class GeneralCommands(commands.Cog):
    def __init__(self, bot: NagromBot):
        self.bot = bot

    @app_commands.command(name="check", description="Manually verify a statement")
    async def check(self, interaction: discord.Interaction, statement: str) -> None:
        await interaction.response.defer(ephemeral=False)

        if len(statement) > 500:
            await interaction.followup.send(
                "Statement too long. Maximum length is 500 characters.",
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
            source_message_id=None,
            requestor_id=interaction.user.id,
            statement_author_id=interaction.user.id,
            input_text=statement,
            trigger_type="slash",
            placeholder_message_id=placeholder_msg.id
        )
        if not ok:
            await placeholder_msg.edit(content=queue_reason, embed=None)
            return

    @app_commands.command(name="health", description="Show bot health, system metrics, and performance (Owner Only)")
    async def health(self, interaction: discord.Interaction):
        """Renamed from stats to avoid collision with user stats"""
        if not await self.bot.is_owner(interaction.user):
            await interaction.response.send_message("This command is owner-only.", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True)
        
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        guild_count = len(self.bot.guilds)
        user_count = sum(guild.member_count for guild in self.bot.guilds if guild.member_count)
        uptime = datetime.utcnow() - self.bot.start_time
        
        queue_size = self.bot.fact_check_queue.qsize()
        queue_max = self.bot.config.rate_limits.queue_max_size
        
        async with self.bot.db.session_maker() as session:
            total_checks = await session.scalar(
                select(func.count(FactCheck.id))
            )
            
            recent_checks = await session.scalar(
                select(func.count(FactCheck.id)).where(
                    FactCheck.created_at >= datetime.utcnow() - timedelta(hours=24)
                )
            )
        
        llm_config = self.bot.config.llm
        provider_name = type(self.bot.llm).__name__
        
        embed = discord.Embed(
            title="🤖 System Health",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="💻 System",
            value=f"CPU: {cpu_percent}%\nMemory: {memory.percent}% ({memory.used // (1024**3):.1f}GB / {memory.total // (1024**3):.1f}GB)\nDisk: {disk.percent}% ({disk.used // (1024**3):.1f}GB / {disk.total // (1024**3):.1f}GB)",
            inline=False
        )
        
        embed.add_field(
            name="🤖 Bot",
            value=f"Servers: {guild_count:,}\nUsers: {user_count:,}\nUptime: {str(uptime).split('.')[0]}\nPing: {self.bot.latency * 1000:.0f}ms",
            inline=True
        )
        
        embed.add_field(
            name="🔍 Fact Checks",
            value=f"Total: {total_checks:,}\nLast 24h: {recent_checks:,}\nQueue: {queue_size}/{queue_max}",
            inline=True
        )
        
        embed.add_field(
            name="🧠 LLM Provider",
            value=f"Type: {provider_name}\nModel: {llm_config.model}\nProvider: {llm_config.provider}\nTemperature: {llm_config.temperature}\nMax Tokens: {llm_config.max_tokens}",
            inline=False
        )
        
        rate_config = self.bot.config.rate_limits
        embed.add_field(
            name="⚡ Rate Limits",
            value=f"User Cooldown: {rate_config.user_cooldown_seconds}s\nGuild Daily: {rate_config.guild_daily_limit}\nQueue Max: {rate_config.queue_max_size}",
            inline=True
        )
        
        embed.set_footer(text="Last updated")
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="history", description="Display your past fact-check results")
    async def history(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        async with self.bot.db.session_maker() as session:
            results = await session.execute(
                select(FactCheck)
                .where(FactCheck.user_id == interaction.user.id)
                .order_by(FactCheck.created_at.desc())
                .limit(10)
            )
            fact_checks = results.scalars().all()
            
            if not fact_checks:
                await interaction.followup.send(
                    "You haven't performed any fact checks yet.", 
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title=f"📋 Your Fact Check History",
                description=f"Showing your last {len(fact_checks)} fact checks",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            for i, check in enumerate(fact_checks, 1):
                statement = check.statement[:100] + "..." if check.statement and len(check.statement) > 100 else (check.statement or "N/A")
                verdict_str = check.verdict or "unknown"
                verdict_emoji = {
                    "true": "✅",
                    "false": "❌", 
                    "mixed": "⚠️",
                    "unverifiable": "❓"
                }.get(verdict_str.lower(), "🤔")
                
                confidence_val = check.confidence if check.confidence is not None else 0.0
                created_at_str = check.created_at.strftime('%Y-%m-%d %H:%M') if check.created_at else "N/A"
                
                embed.add_field(
                    name=f"{i}. {verdict_emoji} {verdict_str.title()}",
                    value=f"**Statement:** {statement}\n**Confidence:** {confidence_val * 100:.1f}%\n**Date:** {created_at_str}",
                    inline=False
                )
            
            embed.set_footer(text=f"Requested by {interaction.user.display_name}")
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: NagromBot) -> None:
    await bot.add_cog(GeneralCommands(bot))
