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
    "discord": {"token": "", "prefix": "!", "owner_id": 0},
    "llm": {
        "provider": "openai",
        "api_key": "",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
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
    # Update UI elements binding
    base_url_input.value = state["llm"]["base_url"]
    model_input.value = state["llm"]["model"]

def save_config():
    try:
        # Ensure numbers are numbers
        state["discord"]["owner_id"] = int(state["discord"]["owner_id"])
        
        with open(config_path, "w") as f:
            yaml.dump(state, f, default_flow_style=False, sort_keys=False)
        
        ui.notify(f"Saved to {config_path}!", type="positive")
        ui.notify("You can now run the bot.", type="info")
    except Exception as e:
        ui.notify(f"Error saving: {e}", type="negative")

# --- UI Layout ---

@ui.page("/")
def main_page():
    ui.colors(primary="#5865F2", secondary="#2ECC71", accent="#EB459E")
    ui.query('body').style('background-color: #121212; color: #e0e0e0')
    
    with ui.column().classes("w-full items-center justify-center q-pa-md"):
        ui.label("Nagrom Setup").classes("text-4xl font-bold mb-4 text-primary")
        
        with ui.stepper().props("vertical").classes("w-full max-w-2xl bg-grey-9 rounded-lg p-4 shadow-lg") as stepper:
            
            # Step 1: Discord
            with ui.step("Discord Configuration"):
                ui.input("Bot Token", password=True).bind_value(state["discord"], "token").classes("w-full")
                ui.input("Command Prefix").bind_value(state["discord"], "prefix").classes("w-full")
                ui.number("Owner ID (Optional)", format="%.0f").bind_value(state["discord"], "owner_id").classes("w-full")
                with ui.stepper_navigation():
                    ui.button("Next", on_click=stepper.next)

            # Step 2: LLM
            with ui.step("AI / LLM Settings"):
                ui.select(
                    ["openai", "openrouter", "custom"], 
                    label="Provider", 
                    on_change=update_llm_defaults
                ).bind_value(state["llm"], "provider").classes("w-full")
                
                ui.input("API Key", password=True).bind_value(state["llm"], "api_key").classes("w-full")
                
                global base_url_input, model_input
                base_url_input = ui.input("Base URL").bind_value(state["llm"], "base_url").classes("w-full")
                model_input = ui.input("Model Name").bind_value(state["llm"], "model").classes("w-full")
                
                with ui.stepper_navigation():
                    ui.button("Next", on_click=stepper.next)
                    ui.button("Back", on_click=stepper.previous).props("flat")

            # Step 3: Rate Limits
            with ui.step("Rate Limits & Security"):
                with ui.grid(columns=2).classes("w-full gap-4"):
                    ui.number("User Cooldown (s)").bind_value(state["rate_limits"], "user_cooldown")
                    ui.number("Daily Guild Limit").bind_value(state["rate_limits"], "daily_guild_limit")
                    ui.number("Token Bucket Cap").bind_value(state["rate_limits"], "bucket_tokens")
                    ui.number("Refill Rate (/s)").bind_value(state["rate_limits"], "bucket_refill_rate")
                
                with ui.stepper_navigation():
                    ui.button("Finish & Save", on_click=save_config).props("color=green")
                    ui.button("Back", on_click=stepper.previous).props("flat")

        # Footer Actions
        with ui.row().classes("mt-8 gap-4"):
             ui.button("Exit", on_click=app.shutdown).props("color=red outline")

# Run the app
ui.run(title="Nagrom Setup", dark=True, reload=False, port=8080)