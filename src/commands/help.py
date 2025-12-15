from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from ..bot import NagromBot


class HelpCommands(commands.Cog):
    def __init__(self, bot: NagromBot):
        self.bot = bot

    @app_commands.command(name="help", description="Learn how to use the bot and see available commands.")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="nagrom - Fact Verification Bot",
            description=(
                "nagrom is a fact-checking bot that verifies claims using a tiered hierarchy of trusted sources. "
                "It searches for evidence from fact-checkers (Snopes, PolitiFact, Reuters), official sources (.gov, .edu), "
                "and reputable news outlets, then synthesizes a verdict."
            ),
            color=discord.Color.blue()
        )

        embed.add_field(
            name="How to Use",
            value=(
                "**Reply Method:** Reply to any message and mention the bot to fact-check it.\n"
                "**Mention Method:** Mention the bot with a claim inline.\n"
                "**Slash Command:** Use `/check` with your statement.\n"
                "**Context Menu:** Right-click a message > Apps > Check Facts"
            ),
            inline=False
        )

        embed.add_field(
            name="Context Mode",
            value=(
                "For claims spanning multiple messages:\n"
                "- Reply with `@nagrom context 5` to include 5 previous messages.\n"
                "- Mention with `@nagrom last 10` to read the last 10 messages."
            ),
            inline=False
        )

        embed.add_field(
            name="User Commands",
            value=(
                "`/check <statement>` - Verify a claim\n"
                "`/stats [user]` - View accuracy stats\n"
                "`/history` - See your past fact-checks\n"
                "`/help` - Show this message"
            ),
            inline=True
        )

        embed.add_field(
            name="Owner Commands",
            value=(
                "`/cost` - View estimated LLM costs\n"
                "`/config view` - View current LLM config\n"
                "`/config edit` - Edit LLM config\n"
                "`t!logs [n]` - View last n log lines\n"
                "`t!retry <msg_id>` - Retry a failed check\n"
                "`t!reload` - Reload all extensions"
            ),
            inline=True
        )

        embed.add_field(
            name="Verdicts",
            value=(
                "**True** - Claim is supported by evidence\n"
                "**False** - Claim is contradicted by evidence\n"
                "**Mixed** - Partially true or context-dependent\n"
                "**Unverifiable** - Insufficient evidence found"
            ),
            inline=False
        )

        embed.set_footer(text="Source hierarchy: Tier 1 (Fact-checkers) > Tier 2 (.gov/.edu) > Tier 3 (News) > Tier 4 (Social)")

        await interaction.response.send_message(embed=embed)


async def setup(bot: NagromBot):
    await bot.add_cog(HelpCommands(bot))
