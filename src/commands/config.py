import discord
from discord import app_commands
from discord.ext import commands
from ..bot import AVABot

class ConfigCommands(commands.Cog):
    def __init__(self, bot: AVABot):
        self.bot = bot

    @app_commands.command(name="settings", description="View bot configuration")
    @app_commands.checks.has_permissions(administrator=True)
    async def show_settings(self, interaction: discord.Interaction):
        conf = self.bot.config
        embed = discord.Embed(title="AVA Settings", color=discord.Color.blue())
        embed.add_field(name="LLM Model", value=conf.llm.model)
        embed.add_field(name="User Cooldown", value=f"{conf.rate_limits.user_cooldown}s")
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: AVABot):
    await bot.add_cog(ConfigCommands(bot))