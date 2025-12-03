import os
import yaml

def main():
    print("AVA Setup Wizard")
    print("----------------")
    
    if os.path.exists("config/bot.yaml"):
        print("config/bot.yaml already exists. Exiting.")
        return

    token = input("Discord Bot Token: ").strip()
    openai_key = input("LLM API Key: ").strip()
    
    config = {
        "discord": {"token": token, "prefix": "!", "owner_id": 0},
        "llm": {
            "provider": "openai",
            "api_key": openai_key,
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-4-turbo",
            "temperature": 0.2,
            "max_tokens": 500
        },
        "database": {"url": "sqlite+aiosqlite:///data/ava.db"},
        "rate_limits": {
            "user_cooldown": 60,
            "daily_guild_limit": 100,
            "bucket_tokens": 5,
            "bucket_refill_rate": 1
        }
    }
    
    os.makedirs("config", exist_ok=True)
    with open("config/bot.yaml", "w") as f:
        yaml.dump(config, f)
    
    print("Configuration saved to config/bot.yaml")

if __name__ == "__main__":
    main()