# Setup Instructions

## Quick Setup

### Option 1: GUI Setup (Recommended)

1. **Install Dependencies:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Run GUI Setup:**
   ```bash
   python setup_gui.py
   ```
   
   The GUI will open in your browser at http://localhost:8080

3. **Configure:**
   - Discord Bot Token (required)
   - Command Prefix (default: t!)
   - AI Provider (default: Google AI Studio)
   - API Key for your chosen provider
   - Rate limits (defaults are recommended)

4. **Save and Run Bot:**
   ```bash
   python -m src
   ```

### Option 2: CLI Setup

1. **Run Setup Script:**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

2. **Follow the prompts** to configure:
   - Discord bot settings
   - LLM provider (Google AI Studio is default)
   - Rate limiting

3. **Run Bot:**
   ```bash
   source .venv/bin/activate
   python -m src
   ```

## Supported AI Providers

### Google AI Studio (Default)
- **Provider:** `google_ai_studio`
- **Default Model:** `gemini-2.5-flash`
- **API Key:** Get from [Google AI Studio](https://aistudio.google.com/app/apikey)
- **Base URL:** `https://generativelanguage.googleapis.com`

### OpenAI
- **Provider:** `openai`
- **Default Model:** `gpt-4o-mini`
- **API Key:** Get from [OpenAI Platform](https://platform.openai.com/api-keys)
- **Base URL:** `https://api.openai.com/v1`

### OpenRouter
- **Provider:** `openrouter`
- **Default Model:** `openai/gpt-4o-mini`
- **API Key:** Get from [OpenRouter](https://openrouter.ai/keys)
- **Base URL:** `https://openrouter.ai/api/v1`

### Anthropic
- **Provider:** `anthropic`
- **Default Model:** `claude-3-5-sonnet-20241022`
- **API Key:** Get from [Anthropic Console](https://console.anthropic.com/)
- **Base URL:** `https://api.anthropic.com`

### Custom/OpenAI-Compatible
- **Provider:** `custom`
- **Model:** Any OpenAI-compatible model
- **API Key:** Your provider's API key
- **Base URL:** Your provider's endpoint

## Discord Bot Setup

1. **Create Discord Application:**
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application
   - Add a bot user

2. **Enable Privileged Intents:**
   - Go to Bot tab
   - Enable **Message Content Intent**
   - Enable **Server Members Intent** (if needed)

3. **Generate Bot Token:**
   - Click "Reset Token" or "View Token"
   - Copy the token for setup

4. **Invite Bot to Server:**
   - Go to OAuth2 → URL Generator
   - Select scopes: `bot` and `applications.commands`
   - Select permissions: Read Messages, Send Messages, Embed Links
   - Copy the URL and invite to your server

## Configuration File

The configuration is saved to `config/bot.yaml`:

```yaml
discord:
  token: "YOUR_DISCORD_TOKEN"
  prefix: "t!"
  owner_id: 0

llm:
  provider: "google_ai_studio"
  api_key: "YOUR_API_KEY"
  base_url: "https://generativelanguage.googleapis.com"
  model: "gemini-2.5-flash"
  temperature: 0.0
  max_tokens: 500

database:
  url: "sqlite+aiosqlite:///data/ava.db"

rate_limits:
  user_cooldown: 30
  daily_guild_limit: 100
  bucket_tokens: 5
  bucket_refill_rate: 1.0
  queue_max_size: 50
```

## Features

- **Multi-provider Support:** Google AI Studio, OpenAI, OpenRouter, Anthropic, Custom
- **Visual Setup GUI:** Modern web interface for configuration
- **CLI Setup:** Interactive command-line setup
- **Default Avatar:** Automatically sets bot avatar to logo
- **Rate Limiting:** Configurable cooldowns and limits
- **Fact Checking:** AI-powered fact verification with source hierarchy

## Troubleshooting

### Bot Won't Start
- Ensure privileged intents are enabled in Discord Developer Portal
- Check that the token is correct and hasn't expired
- Verify API keys are valid for your chosen provider

### GUI Won't Open
- Make sure `nicegui` is installed: `pip install nicegui`
- Check that port 8080 is not in use
- Try running with `python setup_gui.py` directly

### API Errors
- Verify your API key has sufficient credits/quotas
- Check that the model name is correct for your provider
- Ensure the base URL is correct

## Default Settings

- **Command Prefix:** `t!`
- **AI Provider:** Google AI Studio
- **Model:** gemini-2.0-flash-exp
- **User Cooldown:** 30 seconds
- **Daily Guild Limit:** 100 requests
- **Bot Avatar:** Uses `assets/logo/logo.png` automatically