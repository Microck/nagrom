import os
import sys
import yaml
from nicegui import ui

# --- Configuration State ---
config_path = os.path.join("config", "bot.yaml")
os.makedirs("config", exist_ok=True)
os.makedirs("data", exist_ok=True)

# Default State
state = {
    "discord": {"token": "", "prefix": "t!", "owner_id": 0},
    "llm": {
        "provider": "google_ai_studio",
        "api_key": "",
        "base_url": "https://generativelanguage.googleapis.com",
        "model": "gemini-2.0-flash-exp",
        "temperature": 0.0,
        "max_tokens": 500,
    },
    "database": {"url": "sqlite+aiosqlite:///data/ava.db"},
    "rate_limits": {
        "user_cooldown": 30,
        "daily_guild_limit": 100,
        "bucket_tokens": 5,
        "bucket_refill_rate": 1.0,
        "queue_max_size": 50,
    },
}

# Load existing if available
if os.path.exists(config_path):
    try:
        with open(config_path, "r") as f:
            loaded = yaml.safe_load(f)
            if loaded:
                # Deep merge would be better, but simple update works for flat structures
                state["discord"].update(loaded.get("discord", {}))
                state["llm"].update(loaded.get("llm", {}))
                state["rate_limits"].update(loaded.get("rate_limits", {}))
    except Exception as e:
        print(f"Error loading existing config: {e}")

# --- Logic ---

def update_llm_defaults(e):
    provider = state["llm"]["provider"]
    if provider == "openai":
        state["llm"]["base_url"] = "https://api.openai.com/v1"
        state["llm"]["model"] = "gpt-4o-mini"
    elif provider == "openrouter":
        state["llm"]["base_url"] = "https://openrouter.ai/api/v1"
        state["llm"]["model"] = "openai/gpt-4o-mini"
    elif provider == "google_ai_studio" or provider == "google":
        state["llm"]["base_url"] = "https://generativelanguage.googleapis.com"
        state["llm"]["model"] = "gemini-2.0-flash-exp"
    elif provider == "anthropic":
        state["llm"]["base_url"] = "https://api.anthropic.com"
        state["llm"]["model"] = "claude-3-5-sonnet-20241022"
    # Update UI elements binding
    base_url_input.value = state["llm"]["base_url"]
    model_input.value = state["llm"]["model"]

def save_config():
    try:
        # Ensure numbers are numbers
        state["discord"]["owner_id"] = int(state["discord"]["owner_id"])
        
        # Fix model name for Google AI Studio
        if state["llm"]["provider"] == "google_ai_studio" and state["llm"]["model"] == "gemini-2.0-flash-exp":
            state["llm"]["model"] = "gemini-2.0-flash-exp"
        
        with open(config_path, "w") as f:
            yaml.dump(state, f, default_flow_style=False, sort_keys=False)
        
        ui.notify(f"✅ Configuration saved to {config_path}!", type="positive", timeout=5000)
        ui.notify("🚀 You can now run the bot with: python -m src", type="info", timeout=5000)
    except Exception as e:
        ui.notify(f"❌ Error saving: {e}", type="negative", timeout=5000)

# --- UI Layout ---

@ui.page("/")
def main_page():
    ui.colors(primary="#5865F2", secondary="#2ECC71", accent="#EB459E")
    ui.query('body').style('background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: #ffffff')
    
    with ui.column().classes("w-full items-center justify-center q-pa-md"):
        # Logo and Title
        with ui.row().classes("items-center gap-4 mb-6"):
            try:
                ui.image("/assets/logo/logo.png").classes("w-20 h-20 rounded-lg shadow-lg")
            except:
                ui.icon("settings").classes("text-6xl text-primary")
            ui.label("Nagrom Discord Bot Setup").classes("text-5xl font-bold text-white")
        
        with ui.card().classes("w-full max-w-3xl bg-white/10 backdrop-blur-md rounded-xl shadow-2xl p-6"):
            ui.label("Configure your AI-powered fact-checking Discord bot").classes("text-xl text-grey-200 mb-6 text-center")
            
            with ui.stepper().props("vertical").classes("w-full bg-transparent") as stepper:
                # Step 1: Discord
                with ui.step("Discord Configuration"):
                    with ui.card().classes("w-full p-4 bg-white/5 rounded-lg mb-4"):
                        ui.label("🤖 Discord Bot Settings").classes("text-lg font-semibold mb-3 text-white")
                        ui.input("Bot Token", password=True, placeholder="Paste your Discord bot token here").bind_value(state["discord"], "token").classes("w-full q-mb-md")
                        ui.input("Command Prefix", placeholder="Default: t!").bind_value(state["discord"], "prefix").classes("w-full q-mb-md")
                        ui.number("Owner ID (Optional)", format="%.0f", placeholder="Your Discord user ID").bind_value(state["discord"], "owner_id").classes("w-full")
                    
                    with ui.stepper_navigation():
                        ui.button("Next", on_click=stepper.next).props("color=primary")

                # Step 2: LLM
                with ui.step("AI / LLM Settings"):
                    with ui.card().classes("w-full p-4 bg-white/5 rounded-lg mb-4"):
                        ui.label("🧠 AI Provider Configuration").classes("text-lg font-semibold mb-3 text-white")
                        ui.select(
                            ["google_ai_studio", "openai", "openrouter", "anthropic", "custom"], 
                            label="AI Provider", 
                            on_change=update_llm_defaults,
                            value="google_ai_studio"
                        ).bind_value(state["llm"], "provider").classes("w-full q-mb-md")
                        
                        ui.input("API Key", password=True, placeholder="Your API key for the selected provider").bind_value(state["llm"], "api_key").classes("w-full q-mb-md")
                        
                        global base_url_input, model_input
                        base_url_input = ui.input("Base URL", placeholder="API endpoint URL").bind_value(state["llm"], "base_url").classes("w-full q-mb-md")
                        model_input = ui.input("Model Name", placeholder="Model to use").bind_value(state["llm"], "model").classes("w-full")
                        
                        # Provider info
                        ui.markdown("""
                        **Provider Info:**
                        - **Google AI Studio**: Uses Google's Gemini models (recommended, default)
                        - **OpenAI**: GPT models from OpenAI
                        - **OpenRouter**: Access to multiple models via OpenRouter
                        - **Anthropic**: Claude models from Anthropic
                        - **Custom**: Your own OpenAI-compatible endpoint
                        """).classes("text-sm text-grey-300 mt-3")
                    
                    with ui.stepper_navigation():
                        ui.button("Next", on_click=stepper.next).props("color=primary")
                        ui.button("Back", on_click=stepper.previous).props("flat")

                # Step 3: Rate Limits
                with ui.step("Rate Limits & Security"):
                    with ui.card().classes("w-full p-4 bg-white/5 rounded-lg mb-4"):
                        ui.label("⚡ Rate Limiting Settings").classes("text-lg font-semibold mb-3 text-white")
                        ui.markdown("Configure rate limits to prevent spam and manage API costs.").classes("text-sm text-grey-300 mb-4")
                        
                        with ui.grid(columns=2).classes("w-full gap-4"):
                            ui.number("User Cooldown (s)").bind_value(state["rate_limits"], "user_cooldown").props("suffix='seconds'")
                            ui.number("Daily Guild Limit").bind_value(state["rate_limits"], "daily_guild_limit").props("suffix='requests'")
                            ui.number("Token Bucket Cap").bind_value(state["rate_limits"], "bucket_tokens").props("suffix='tokens'")
                            ui.number("Refill Rate (/s)").bind_value(state["rate_limits"], "bucket_refill_rate").props("suffix='tokens/s'")
                    
                    with ui.stepper_navigation():
                        ui.button("Finish & Save", on_click=save_config).props("color=green icon=save")
                        ui.button("Back", on_click=stepper.previous).props("flat")

            # Footer Actions
            with ui.row().classes("mt-8 gap-4"):
                 ui.button("Exit", on_click=app.shutdown).props("color=red outline")

# Run the app
ui.run(title="Nagrom Setup", dark=True, reload=False, port=8080)