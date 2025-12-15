from __future__ import annotations

import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..bot import NagromBot
from ..models.database import ConfigPreset
from ..config_manager import LLMConfig # For default values
from ..utils.crypto import CryptoManager

logger = logging.getLogger(__name__)

# Helper function to check if the user is the bot owner
def is_owner():
    async def predicate(interaction: discord.Interaction):
        return await interaction.client.is_owner(interaction.user)
    return app_commands.check(predicate)

class ConfigCog(commands.Cog):
    def __init__(self, bot: NagromBot):
        self.bot = bot

    config_group = app_commands.Group(
        name="config",
        description="Manage bot LLM configuration presets (Owner Only).",
        default_permissions=discord.Permissions(manage_guild=True) # Or owner_id directly
    )

    @config_group.command(name="view", description="View the currently active LLM configuration.")
    @is_owner()
    async def view_config(self, interaction: discord.Interaction):
        current_config = self.bot.config.llm
        active_preset_name = "N/A"
        async with self.bot.db.session_maker() as session:
            active_preset = await session.scalar(select(ConfigPreset).where(ConfigPreset.is_active == True))
            if active_preset:
                active_preset_name = active_preset.name

        embed = discord.Embed(
            title="Current LLM Configuration",
            color=discord.Color.blue()
        )
        embed.add_field(name="Active Preset", value=active_preset_name, inline=False)
        embed.add_field(name="Provider", value=current_config.provider, inline=True)
        embed.add_field(name="Model", value=current_config.model, inline=True)
        embed.add_field(name="Base URL", value=current_config.base_url, inline=False)
        embed.add_field(name="API Key (masked)", value=current_config.api_key[:4] + "...", inline=True)
        embed.add_field(name="Fallback Models", value=", ".join(current_config.fallback_models) or "None", inline=False)
        embed.add_field(name="Temperature", value=str(current_config.temperature), inline=True)
        embed.add_field(name="Max Tokens", value=str(current_config.max_tokens), inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @config_group.command(name="edit", description="Edit the currently active LLM configuration (Owner Only).")
    @is_owner()
    async def edit_config(self, interaction: discord.Interaction):
        current_config = self.bot.config.llm

        class ConfigEditModal(discord.ui.Modal, title="Edit LLM Configuration"):
            provider_input = discord.ui.TextInput(
                label="Provider",
                default=current_config.provider,
                required=True,
                max_length=50,
            )
            model_input = discord.ui.TextInput(
                label="Model",
                default=current_config.model,
                required=True,
                max_length=100,
            )
            base_url_input = discord.ui.TextInput(
                label="Base URL",
                default=current_config.base_url,
                required=True,
                max_length=200,
            )
            api_key_input = discord.ui.TextInput(
                label="API Key",
                default=current_config.api_key, # Pre-fill for convenience
                required=True,
                max_length=200,
                style=discord.TextStyle.short,
            )
            fallback_models_input = discord.ui.TextInput(
                label="Fallback Models (comma-separated)",
                default=", ".join(current_config.fallback_models),
                required=False,
                max_length=500,
            )

            async def on_submit(self, interaction: discord.Interaction):
                new_llm_config = LLMConfig(
                    provider=self.provider_input.value,
                    api_key=self.api_key_input.value,
                    base_url=self.base_url_input.value,
                    model=self.model_input.value,
                    fallback_models=[m.strip() for m in self.fallback_models_input.value.split(',') if m.strip()],
                    temperature=current_config.temperature, # Keep old for now, could add to modal
                    max_tokens=current_config.max_tokens,   # Keep old for now, could add to modal
                )

                # Update bot's active config
                self.bot.config.llm = new_llm_config
                # Reload LLM provider
                await self.bot.reload_llm_provider()

                await interaction.response.send_message("LLM configuration updated and reloaded!", ephemeral=True)

            async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
                logger.exception("Error in config edit modal: %s", error)
                await interaction.response.send_message("An error occurred during config update.", ephemeral=True)

        await interaction.response.send_modal(ConfigEditModal(bot=self.bot))


    @config_group.command(name="save_preset", description="Save the current active config as a new preset (Owner Only).")
    @is_owner()
    async def save_preset(self, interaction: discord.Interaction, name: str):
        current_llm_config = self.bot.config.llm
        async with self.bot.db.session_maker() as session:
            # Check if preset name already exists
            existing_preset = await session.scalar(select(ConfigPreset).where(ConfigPreset.name == name))
            if existing_preset:
                await interaction.response.send_message(f"A preset named '{name}' already exists. Please choose a different name.", ephemeral=True)
                return

            new_preset = ConfigPreset(
                name=name,
                provider=current_llm_config.provider,
                api_key=CryptoManager.encrypt(current_llm_config.api_key),
                base_url=current_llm_config.base_url,
                model=current_llm_config.model,
                fallback_models=", ".join(current_llm_config.fallback_models),
                temperature=current_llm_config.temperature,
                max_tokens=current_llm_config.max_tokens,
                is_active=False # Not active by default, needs to be loaded
            )
            session.add(new_preset)
            await session.commit()
            await interaction.response.send_message(f"Configuration saved as preset '{name}'.", ephemeral=True)

    @config_group.command(name="load_preset", description="Load a saved configuration preset (Owner Only).")
    @is_owner()
    async def load_preset(self, interaction: discord.Interaction):
        async with self.bot.db.session_maker() as session:
            presets = await session.scalars(select(ConfigPreset))
            
            if not presets:
                await interaction.response.send_message("No presets found. Save one first!", ephemeral=True)
                return

            options = [
                discord.SelectOption(label=p.name, value=str(p.id), description=p.model)
                for p in presets
            ]

            class PresetSelect(discord.ui.Select):
                def __init__(self):
                    super().__init__(placeholder="Choose a preset to load...", options=options)
                
                async def callback(self, interaction: discord.Interaction):
                    selected_id = int(self.values[0])
                    async with self.bot.db.session_maker() as session:
                        # Deactivate all other presets
                        await session.execute(ConfigPreset.__table__.update().values(is_active=False))

                        # Set selected preset as active
                        selected_preset = await session.scalar(select(ConfigPreset).where(ConfigPreset.id == selected_id))
                        if selected_preset:
                            selected_preset.is_active = True
                            await session.commit()
                            
                            # Update bot's active config
                            self.bot.config.llm = LLMConfig(
                                provider=selected_preset.provider,
                                api_key=CryptoManager.decrypt(selected_preset.api_key),
                                base_url=selected_preset.base_url,
                                model=selected_preset.model,
                                fallback_models=[m.strip() for m in selected_preset.fallback_models.split(',') if m.strip()],
                                temperature=selected_preset.temperature,
                                max_tokens=selected_preset.max_tokens,
                            )
                            await self.bot.reload_llm_provider()
                            await interaction.response.edit_message(content=f"Preset '{selected_preset.name}' loaded and activated!", view=None)
                        else:
                            await interaction.response.edit_message(content="Preset not found.", view=None)


            view = discord.ui.View()
            view.add_item(PresetSelect())
            await interaction.response.send_message("Select a configuration preset:", view=view, ephemeral=True)

async def setup(bot: NagromBot):
    await bot.add_cog(ConfigCog(bot))