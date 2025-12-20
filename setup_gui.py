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

# Palette
COLOR_TAUPE = "#615F5B"
COLOR_SLATE = "#656B70"
COLOR_LIGHT_BLUE_GREY = "#8F989D"
COLOR_WARM_GREY = "#8A8280"
COLOR_CHARCOAL = "#2D3235"

# New Palette Colors
COLOR_INPUT_BG = "#7B8389"
COLOR_INPUT_TEXT = "#303438"
COLOR_CHARCOAL_NEW = "#2B3034" # Main background color
COLOR_LABEL_NEW = "#2B3033" # New label color

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
        # Force minimal CSS theme
        ui.add_head_html(f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Roboto+Flex:opsz,wght@8..144,100..1000&display=swap');
            
            body {{
                background-color: {COLOR_CHARCOAL_NEW} !important;
                color: {COLOR_LIGHT_BLUE_GREY} !important;
                font-family: 'Google Sans Flex', 'Roboto Flex', 'Roboto', sans-serif !important;
            }}
            .q-card {{
                background-color: {COLOR_CHARCOAL_NEW} !important;
                box-shadow: none !important;
                border: 1px solid {COLOR_TAUPE};
            }}
            .q-tab {{
                color: {COLOR_WARM_GREY};
            }}
            .q-tab--active {{
                color: {COLOR_LIGHT_BLUE_GREY};
            }}
            .q-field__control {{
                background-color: {COLOR_INPUT_BG} !important; 
                color: {COLOR_INPUT_TEXT} !important;
            }}
            .q-field__native, .q-field__prefix, .q-field__suffix, .q-field__input {{
                color: {COLOR_INPUT_TEXT} !important;
            }}
            .q-field__label {{
                color: {COLOR_LABEL_NEW} !important;
                font-weight: 500;
            }}
            .text-primary {{ /* For links, etc. */
                color: {COLOR_LIGHT_BLUE_GREY} !important;
            }}
            .bg-primary {{ /* Override for default primary background */
                background-color: {COLOR_INPUT_BG} !important;
            }}
            .q-btn {{
                background-color: {COLOR_INPUT_BG} !important;
                color: {COLOR_LABEL_NEW} !important;
                font-weight: bold;
            }}
            .q-btn--flat {{ /* Styling for the Reset button */
                background-color: transparent !important;
                color: {COLOR_LIGHT_BLUE_GREY} !important;
            }}
            .q-btn .q-icon {{ /* Icons inside buttons, e.g., password toggle */
                color: {COLOR_LABEL_NEW} !important;
            }}
            .q-select__dropdown-icon, .q-field__marginal {{ /* Dropdown arrow, input icons */
                color: {COLOR_LABEL_NEW} !important;
            }}
            .q-menu.q-position-engine.q-popup--menu {{ /* Dropdown menu background */
                background-color: {COLOR_CHARCOAL_NEW} !important;
                color: {COLOR_LIGHT_BLUE_GREY} !important;
                border: 1px solid {COLOR_INPUT_BG};
            }}
            .q-item {{ /* Dropdown menu items */
                color: {COLOR_LIGHT_BLUE_GREY} !important;
            }}
            .q-item--active, .q-item--highlighted {{ /* Dropdown active/hover item */
                background-color: {COLOR_SLATE} !important;
            }}
            .q-toggle__thumb {{ /* For ui.switch */
                color: {COLOR_TAUPE} !important;
            }}
            .q-toggle__track {{
                background-color: {COLOR_SLATE} !important;
            }}
        </style>
        """)

        # Main Container
        with ui.column().classes("w-full max-w-3xl mx-auto items-center p-8 gap-8"):
            
            # Logo
            if Path("assets/logo/logo.png").exists():
                ui.image("assets/logo/logo.png").classes("w-32 opacity-80 hover:opacity-100 transition-opacity")
            
            # Tabs
            with ui.tabs().classes("w-full text-lg") as tabs:
                discord_tab = ui.tab("Discord")
                llm_tab = ui.tab("LLM")
                search_tab = ui.tab("Search")
                rate_tab = ui.tab("Limits")
                advanced_tab = ui.tab("Advanced")
            
            # Panels
            with ui.tab_panels(tabs, value=discord_tab).classes("w-full bg-transparent"):
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
            
            # Action Buttons (Minimal)
            with ui.row().classes("w-full justify-end gap-4 mt-8"):
                ui.button("Reset", on_click=self.on_reset).props("flat")
                ui.button("Save", on_click=self.on_save)

    def build_discord_panel(self):
        with ui.column().classes("w-full gap-6"):
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
                    "Prefix",
                    value=discord_cfg.get("prefix", "t!")
                ).classes("w-32").props('outlined')
                self.discord_prefix.on("blur", lambda: self.update_config("discord", "prefix", self.discord_prefix.value))
                
                self.discord_owner = ui.input(
                    "Owner ID",
                    value=str(discord_cfg.get("owner_id", 0))
                ).classes("flex-1").props('outlined')
                self.discord_owner.on("blur", lambda: self.update_config("discord", "owner_id", int(self.discord_owner.value or 0)))
            
            ui.separator().classes(f"bg-{COLOR_TAUPE}")
            
            with ui.row().classes("w-full gap-4 items-end"):
                self.bot_client_id = ui.input(
                    "Bot Client ID (for invite)",
                    value=discord_cfg.get("client_id", "")
                ).classes("flex-1").props('outlined')
                self.bot_client_id.on("blur", lambda: self.update_config("discord", "client_id", self.bot_client_id.value))
                
                ui.button("Generate Invite", on_click=self.generate_invite_url).props('outline')
            
            self.invite_url_display = ui.input(
                "Invite URL",
                value=""
            ).classes("w-full").props('outlined readonly')
            
            with ui.row().classes("w-full gap-2"):
                ui.button("Copy", on_click=self.copy_invite_url).props('flat dense')
                ui.link("Open in Browser", target="_blank").bind_visibility_from(
                    self, 'invite_url_display', backward=lambda x: bool(x.value)
                ).props('flat dense').bind_text_from(self.invite_url_display, 'value', backward=lambda _: "Open in Browser")
    
    def build_llm_panel(self):
        with ui.column().classes("w-full gap-6"):
            llm_cfg = self.config.setdefault("llm", {})
            current_provider = llm_cfg.get("provider", "google_ai_studio")
            
            provider_options = {k: v["name"] for k, v in PROVIDERS.items()}
            self.llm_provider = ui.select(
                options=provider_options,
                label="Provider",
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
                    "Temp",
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
        with ui.column().classes("w-full gap-6"):
            search_cfg = self.config.setdefault("search", {})
            
            self.search_enabled = ui.switch(
                "Enable Web Search",
                value=search_cfg.get("enabled", True)
            ).props('color=grey-5')
            self.search_enabled.on("change", lambda: self.update_config("search", "enabled", self.search_enabled.value))
            
            ui.separator().classes(f"bg-{COLOR_TAUPE}")
            
            self.tavily_key = ui.input(
                "Tavily API Key",
                value=search_cfg.get("tavily_api_key", ""),
                password=True,
                password_toggle_button=True
            ).classes("w-full").props('outlined')
            self.tavily_key.on("blur", lambda: self.update_config("search", "tavily_api_key", self.tavily_key.value))
            
            self.tavily_results = ui.number(
                "Results Count",
                value=search_cfg.get("tavily_max_results", 5),
                min=1,
                max=10
            ).classes("w-32").props('outlined')
            self.tavily_results.on("blur", lambda: self.update_config("search", "tavily_max_results", int(self.tavily_results.value or 5)))
    
    def build_rate_limits_panel(self):
        with ui.column().classes("w-full gap-6"):
            rate_cfg = self.config.setdefault("rate_limits", {})
            
            with ui.row().classes("w-full gap-4"):
                self.rate_cooldown = ui.number(
                    "Cooldown (s)",
                    value=rate_cfg.get("user_cooldown", 30),
                    min=0,
                    max=300
                ).classes("flex-1").props('outlined')
                self.rate_cooldown.on("blur", lambda: self.update_config("rate_limits", "user_cooldown", int(self.rate_cooldown.value or 30)))
                
                self.rate_daily = ui.number(
                    "Daily Limit",
                    value=rate_cfg.get("daily_guild_limit", 100),
                    min=1,
                    max=10000
                ).classes("flex-1").props('outlined')
                self.rate_daily.on("blur", lambda: self.update_config("rate_limits", "daily_guild_limit", int(self.rate_daily.value or 100)))
            
            with ui.row().classes("w-full gap-4"):
                self.rate_tokens = ui.number(
                    "Bucket Size",
                    value=rate_cfg.get("bucket_tokens", 5),
                    min=1,
                    max=100
                ).classes("flex-1").props('outlined')
                self.rate_tokens.on("blur", lambda: self.update_config("rate_limits", "bucket_tokens", int(self.rate_tokens.value or 5)))
                
                self.rate_refill = ui.number(
                    "Refill Rate",
                    value=rate_cfg.get("bucket_refill_rate", 1.0),
                    min=0.1,
                    max=10.0,
                    step=0.1
                ).classes("flex-1").props('outlined')
                self.rate_refill.on("blur", lambda: self.update_config("rate_limits", "bucket_refill_rate", float(self.rate_refill.value or 1.0)))
    
    def build_advanced_panel(self):
        with ui.column().classes("w-full gap-6"):
            db_cfg = self.config.setdefault("database", {})
            
            self.db_url = ui.input(
                "Database URL",
                value=db_cfg.get("url", "sqlite+aiosqlite:///data/nagrom.db")
            ).classes("w-full").props('outlined')
            self.db_url.on("blur", lambda: self.update_config("database", "url", self.db_url.value))
            
            ui.label("Raw Config").classes("text-sm opacity-50 mt-4")
            self.raw_config = ui.textarea(
                value=yaml.dump(self.config, default_flow_style=False, sort_keys=False)
            ).classes("w-full h-64 font-mono text-xs").props('outlined')
    
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
        
        self.update_config("llm", "base_url", provider_info["base_url"])
        self.update_config("llm", "model", provider_info["default_model"])
    
    def on_save(self):
        try:
            self.save_config()
            ui.notify("Saved", type="positive", color=COLOR_TAUPE)
        except Exception as e:
            ui.notify(f"Error: {e}", type="negative")
    
    def on_reset(self):
        self.config = self.default_config()
        ui.notify("Reset to defaults", type="warning")
        ui.navigate.reload()
    
    def generate_invite_url(self):
        client_id = self.bot_client_id.value.strip()
        if not client_id:
            ui.notify("Enter Bot Client ID first", type="warning")
            return
        
        permissions = 274878024704
        scopes = "bot%20applications.commands"
        url = f"https://discord.com/api/oauth2/authorize?client_id={client_id}&permissions={permissions}&scope={scopes}"
        self.invite_url_display.value = url
        ui.notify("Invite URL generated", type="positive", color=COLOR_TAUPE)
    
    def copy_invite_url(self):
        url = self.invite_url_display.value
        if not url:
            ui.notify("Generate URL first", type="warning")
            return
        ui.run_javascript(f'navigator.clipboard.writeText("{url}")')
        ui.notify("Copied to clipboard", type="positive", color=COLOR_TAUPE)


def main():
    Path("config").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)
    
    gui = SetupGUI()
    gui.build_ui()
    
    ui.run(
        title="setup", # Minimal title
        host="127.0.0.1",
        port=8080,
        reload=False,
        show=True,
        favicon="assets/logo/icon.png" if Path("assets/logo/icon.png").exists() else None
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()