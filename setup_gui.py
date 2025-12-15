#!/usr/bin/env python3
"""
nagrom Setup GUI - A NiceGUI-based configuration interface for the nagrom bot.

Run with: python setup_gui.py
Opens a browser tab at http://localhost:8080
"""

import os
import sys
from pathlib import Path

import yaml
from nicegui import ui, app

CONFIG_PATH = Path("config/bot.yaml")
EXAMPLE_PATH = Path("config/examples/minimal.yaml")

PROVIDERS = {
    "google_ai_studio": {
        "name": "Google AI Studio",
        "base_url": "https://generativelanguage.googleapis.com",
        "default_model": "gemini-2.5-flash",
        "api_key_url": "https://aistudio.google.com/app/apikey"
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "api_key_url": "https://platform.openai.com/api-keys"
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "openai/gpt-4o-mini",
        "api_key_url": "https://openrouter.ai/keys"
    },
    "anthropic": {
        "name": "Anthropic",
        "base_url": "https://api.anthropic.com",
        "default_model": "claude-3-5-sonnet-20241022",
        "api_key_url": "https://console.anthropic.com/"
    },
    "custom": {
        "name": "Custom (OpenAI-Compatible)",
        "base_url": "",
        "default_model": "",
        "api_key_url": ""
    }
}


class SetupGUI:
    def __init__(self):
        self.config = self.load_config()
        
    def load_config(self) -> dict:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        elif EXAMPLE_PATH.exists():
            with open(EXAMPLE_PATH, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return self.default_config()
    
    def default_config(self) -> dict:
        return {
            "discord": {
                "token": "",
                "prefix": "t!",
                "owner_id": 0
            },
            "llm": {
                "provider": "google_ai_studio",
                "api_key": "",
                "base_url": "https://generativelanguage.googleapis.com",
                "model": "gemini-2.5-flash",
                "fallback_models": [],
                "temperature": 0.0,
                "max_tokens": 500
            },
            "database": {
                "url": "sqlite+aiosqlite:///data/nagrom.db"
            },
            "rate_limits": {
                "user_cooldown": 30,
                "daily_guild_limit": 100,
                "bucket_tokens": 5,
                "bucket_refill_rate": 1.0,
                "queue_max_size": 50
            },
            "search": {
                "enabled": True,
                "provider": "auto",
                "tavily_api_key": "",
                "tavily_max_results": 5
            }
        }
    
    def save_config(self):
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
    
    def build_ui(self):
        ui.dark_mode().enable()
        
        with ui.header().classes("items-center justify-between"):
            ui.label("nagrom Setup").classes("text-2xl font-bold")
            ui.link("Documentation", "/docs").classes("text-white")
        
        with ui.tabs().classes("w-full") as tabs:
            discord_tab = ui.tab("Discord")
            llm_tab = ui.tab("LLM Provider")
            search_tab = ui.tab("Search")
            rate_tab = ui.tab("Rate Limits")
            advanced_tab = ui.tab("Advanced")
        
        with ui.tab_panels(tabs, value=discord_tab).classes("w-full"):
            with ui.tab_panel(discord_tab):
                self.build_discord_panel()
            
            with ui.tab_panel(llm_tab):
                self.build_llm_panel()
            
            with ui.tab_panel(search_tab):
                self.build_search_panel()
            
            with ui.tab_panel(rate_tab):
                self.build_rate_limits_panel()
            
            with ui.tab_panel(advanced_tab):
                self.build_advanced_panel()
        
        with ui.footer().classes("items-center justify-between"):
            ui.button("Save Configuration", on_click=self.on_save).props("color=primary")
            ui.button("Reset to Defaults", on_click=self.on_reset).props("color=negative")
    
    def build_discord_panel(self):
        with ui.card().classes("w-full max-w-2xl mx-auto"):
            ui.label("Discord Bot Settings").classes("text-xl font-semibold mb-4")
            
            discord_cfg = self.config.setdefault("discord", {})
            
            self.discord_token = ui.input(
                "Bot Token",
                value=discord_cfg.get("token", ""),
                password=True,
                password_toggle_button=True
            ).classes("w-full").props('outlined')
            self.discord_token.on("blur", lambda: self.update_config("discord", "token", self.discord_token.value))
            
            with ui.row().classes("w-full gap-4"):
                self.discord_prefix = ui.input(
                    "Command Prefix",
                    value=discord_cfg.get("prefix", "t!")
                ).classes("w-32").props('outlined')
                self.discord_prefix.on("blur", lambda: self.update_config("discord", "prefix", self.discord_prefix.value))
                
                self.discord_owner = ui.input(
                    "Owner ID (Discord User ID)",
                    value=str(discord_cfg.get("owner_id", 0))
                ).classes("flex-1").props('outlined')
                self.discord_owner.on("blur", lambda: self.update_config("discord", "owner_id", int(self.discord_owner.value or 0)))
            
            ui.markdown("""
**How to get your Bot Token:**
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application or select existing
3. Go to Bot tab and click "Reset Token"
4. Copy the token and paste it above

**How to get your Owner ID:**
1. Enable Developer Mode in Discord Settings > Advanced
2. Right-click your username and select "Copy User ID"
            """).classes("text-sm text-gray-400 mt-4")
    
    def build_llm_panel(self):
        with ui.card().classes("w-full max-w-2xl mx-auto"):
            ui.label("LLM Provider Settings").classes("text-xl font-semibold mb-4")
            
            llm_cfg = self.config.setdefault("llm", {})
            current_provider = llm_cfg.get("provider", "google_ai_studio")
            
            provider_options = {k: v["name"] for k, v in PROVIDERS.items()}
            self.llm_provider = ui.select(
                "Provider",
                options=provider_options,
                value=current_provider,
                on_change=self.on_provider_change
            ).classes("w-full").props('outlined')
            
            self.llm_api_key = ui.input(
                "API Key",
                value=llm_cfg.get("api_key", ""),
                password=True,
                password_toggle_button=True
            ).classes("w-full").props('outlined')
            self.llm_api_key.on("blur", lambda: self.update_config("llm", "api_key", self.llm_api_key.value))
            
            self.api_key_link = ui.link(
                f"Get API Key from {PROVIDERS[current_provider]['name']}",
                PROVIDERS[current_provider]["api_key_url"],
                new_tab=True
            ).classes("text-blue-400 text-sm")
            
            self.llm_base_url = ui.input(
                "Base URL",
                value=llm_cfg.get("base_url", PROVIDERS[current_provider]["base_url"])
            ).classes("w-full").props('outlined')
            self.llm_base_url.on("blur", lambda: self.update_config("llm", "base_url", self.llm_base_url.value))
            
            self.llm_model = ui.input(
                "Model",
                value=llm_cfg.get("model", PROVIDERS[current_provider]["default_model"])
            ).classes("w-full").props('outlined')
            self.llm_model.on("blur", lambda: self.update_config("llm", "model", self.llm_model.value))
            
            with ui.row().classes("w-full gap-4"):
                self.llm_temp = ui.number(
                    "Temperature",
                    value=llm_cfg.get("temperature", 0.0),
                    min=0.0,
                    max=2.0,
                    step=0.1
                ).classes("w-32").props('outlined')
                self.llm_temp.on("blur", lambda: self.update_config("llm", "temperature", float(self.llm_temp.value or 0)))
                
                self.llm_max_tokens = ui.number(
                    "Max Tokens",
                    value=llm_cfg.get("max_tokens", 500),
                    min=100,
                    max=8000,
                    step=100
                ).classes("w-32").props('outlined')
                self.llm_max_tokens.on("blur", lambda: self.update_config("llm", "max_tokens", int(self.llm_max_tokens.value or 500)))
            
            self.llm_fallback = ui.input(
                "Fallback Models (comma-separated)",
                value=", ".join(llm_cfg.get("fallback_models", []))
            ).classes("w-full").props('outlined')
            self.llm_fallback.on("blur", lambda: self.update_config(
                "llm", "fallback_models", 
                [m.strip() for m in self.llm_fallback.value.split(",") if m.strip()]
            ))
    
    def build_search_panel(self):
        with ui.card().classes("w-full max-w-2xl mx-auto"):
            ui.label("Search Provider Settings").classes("text-xl font-semibold mb-4")
            
            search_cfg = self.config.setdefault("search", {})
            
            self.search_enabled = ui.switch(
                "Enable Web Search",
                value=search_cfg.get("enabled", True)
            )
            self.search_enabled.on("change", lambda: self.update_config("search", "enabled", self.search_enabled.value))
            
            ui.label("Tavily API (Recommended)").classes("text-lg font-medium mt-4")
            
            self.tavily_key = ui.input(
                "Tavily API Key",
                value=search_cfg.get("tavily_api_key", ""),
                password=True,
                password_toggle_button=True
            ).classes("w-full").props('outlined')
            self.tavily_key.on("blur", lambda: self.update_config("search", "tavily_api_key", self.tavily_key.value))
            
            ui.link("Get Tavily API Key", "https://tavily.com/", new_tab=True).classes("text-blue-400 text-sm")
            
            self.tavily_results = ui.number(
                "Max Search Results",
                value=search_cfg.get("tavily_max_results", 5),
                min=1,
                max=10
            ).classes("w-32").props('outlined')
            self.tavily_results.on("blur", lambda: self.update_config("search", "tavily_max_results", int(self.tavily_results.value or 5)))
            
            ui.markdown("""
**Note:** Without a search provider configured, fact checks will return UNVERIFIABLE 
as the bot cannot fetch external sources. Tavily is recommended for best results.
            """).classes("text-sm text-gray-400 mt-4")
    
    def build_rate_limits_panel(self):
        with ui.card().classes("w-full max-w-2xl mx-auto"):
            ui.label("Rate Limit Settings").classes("text-xl font-semibold mb-4")
            
            rate_cfg = self.config.setdefault("rate_limits", {})
            
            with ui.row().classes("w-full gap-4"):
                self.rate_cooldown = ui.number(
                    "User Cooldown (seconds)",
                    value=rate_cfg.get("user_cooldown", 30),
                    min=0,
                    max=300
                ).classes("flex-1").props('outlined')
                self.rate_cooldown.on("blur", lambda: self.update_config("rate_limits", "user_cooldown", int(self.rate_cooldown.value or 30)))
                
                self.rate_daily = ui.number(
                    "Daily Guild Limit",
                    value=rate_cfg.get("daily_guild_limit", 100),
                    min=1,
                    max=10000
                ).classes("flex-1").props('outlined')
                self.rate_daily.on("blur", lambda: self.update_config("rate_limits", "daily_guild_limit", int(self.rate_daily.value or 100)))
            
            with ui.row().classes("w-full gap-4"):
                self.rate_tokens = ui.number(
                    "Bucket Tokens",
                    value=rate_cfg.get("bucket_tokens", 5),
                    min=1,
                    max=100
                ).classes("flex-1").props('outlined')
                self.rate_tokens.on("blur", lambda: self.update_config("rate_limits", "bucket_tokens", int(self.rate_tokens.value or 5)))
                
                self.rate_refill = ui.number(
                    "Bucket Refill Rate (per sec)",
                    value=rate_cfg.get("bucket_refill_rate", 1.0),
                    min=0.1,
                    max=10.0,
                    step=0.1
                ).classes("flex-1").props('outlined')
                self.rate_refill.on("blur", lambda: self.update_config("rate_limits", "bucket_refill_rate", float(self.rate_refill.value or 1.0)))
            
            self.rate_queue = ui.number(
                "Queue Max Size",
                value=rate_cfg.get("queue_max_size", 50),
                min=1,
                max=500
            ).classes("w-48").props('outlined')
            self.rate_queue.on("blur", lambda: self.update_config("rate_limits", "queue_max_size", int(self.rate_queue.value or 50)))
    
    def build_advanced_panel(self):
        with ui.card().classes("w-full max-w-2xl mx-auto"):
            ui.label("Advanced Settings").classes("text-xl font-semibold mb-4")
            
            db_cfg = self.config.setdefault("database", {})
            
            self.db_url = ui.input(
                "Database URL",
                value=db_cfg.get("url", "sqlite+aiosqlite:///data/nagrom.db")
            ).classes("w-full").props('outlined')
            self.db_url.on("blur", lambda: self.update_config("database", "url", self.db_url.value))
            
            ui.markdown("""
**Database URL Format:**
- SQLite: `sqlite+aiosqlite:///data/nagrom.db`
- PostgreSQL: `postgresql+asyncpg://user:pass@host:5432/dbname`
            """).classes("text-sm text-gray-400 mt-2")
            
            ui.separator().classes("my-4")
            
            ui.label("Raw Configuration").classes("text-lg font-medium")
            self.raw_config = ui.textarea(
                value=yaml.dump(self.config, default_flow_style=False, sort_keys=False)
            ).classes("w-full h-64 font-mono text-sm").props('outlined')
    
    def update_config(self, section: str, key: str, value):
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
        if hasattr(self, "raw_config"):
            self.raw_config.value = yaml.dump(self.config, default_flow_style=False, sort_keys=False)
    
    def on_provider_change(self, e):
        provider = e.value
        self.update_config("llm", "provider", provider)
        
        provider_info = PROVIDERS[provider]
        self.llm_base_url.value = provider_info["base_url"]
        self.llm_model.value = provider_info["default_model"]
        self.api_key_link.text = f"Get API Key from {provider_info['name']}"
        self.api_key_link.props(f'href="{provider_info["api_key_url"]}"')
        
        self.update_config("llm", "base_url", provider_info["base_url"])
        self.update_config("llm", "model", provider_info["default_model"])
    
    def on_save(self):
        try:
            self.save_config()
            ui.notify("Configuration saved successfully!", type="positive")
        except Exception as e:
            ui.notify(f"Error saving configuration: {e}", type="negative")
    
    def on_reset(self):
        self.config = self.default_config()
        ui.notify("Configuration reset to defaults. Click Save to apply.", type="warning")
        ui.navigate.reload()


def main():
    Path("config").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)
    
    gui = SetupGUI()
    gui.build_ui()
    
    ui.run(
        title="nagrom Setup",
        host="127.0.0.1",
        port=8080,
        reload=False,
        show=True,
        dark=True
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
