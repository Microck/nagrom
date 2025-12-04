#!/usr/bin/env bash
set -euo pipefail

echo "=== nagrom Quick Interactive Setup ==="
echo
echo "This script will:"
echo "  - (Optionally) create a Python virtual environment and install dependencies"
echo "  - Ask for your Discord bot token and LLM settings"
echo "  - Generate config/bot.yaml for you"
echo

read -r -p "Set up Python virtualenv and install requirements? [Y/n]: " DO_ENV_SETUP
DO_ENV_SETUP=${DO_ENV_SETUP:-Y}

if [[ "$DO_ENV_SETUP" =~ ^[Yy]$ ]]; then
  PYTHON_BIN="${PYTHON_BIN:-python3}"

  if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    if command -v python >/dev/null 2>&1; then
      PYTHON_BIN="python"
    else
      echo "Error: Python 3.11+ is required but not found on PATH."
      echo "Install Python, then re-run this script."
      exit 1
    fi
  fi

  echo
  echo "Using Python: $PYTHON_BIN"
  "$PYTHON_BIN" - <<'EOF'
import sys
if sys.version_info < (3, 11):
    print("Error: Python 3.11+ required.", file=sys.stderr)
    sys.exit(1)
EOF

  if [ ! -d ".venv" ]; then
    echo "Creating virtual environment in .venv ..."
    "$PYTHON_BIN" -m venv .venv
  else
    echo "Virtual environment .venv already exists; reusing."
  fi

  # shellcheck disable=SC1091
  if [ -f ".venv/bin/activate" ]; then
    # Linux/macOS/Git Bash
    # shellcheck disable=SC1091
    source ".venv/bin/activate"
  elif [ -f ".venv/Scripts/activate" ]; then
    # Windows (Git Bash with Windows paths)
    # shellcheck disable=SC1091
    source ".venv/Scripts/activate"
  else
    echo "Warning: Could not auto-activate .venv. You may need to activate it manually later."
  fi

  if [ -f "requirements.txt" ]; then
    echo "Installing Python dependencies from requirements.txt ..."
    pip install --upgrade pip
    pip install -r requirements.txt
  else
    echo "Warning: requirements.txt not found; skipping dependency install."
  fi
else
  echo "Skipping Python environment setup."
fi

echo
echo "=== Discord Bot Configuration ==="
echo "You need a bot token from https://discord.com/developers/applications"
echo "Create an application, add a Bot user, and copy the token."
echo

read -r -p "Discord Bot Token: " DISCORD_TOKEN
if [ -z "$DISCORD_TOKEN" ]; then
  echo "Error: Discord bot token cannot be empty."
  exit 1
fi

read -r -p "Discord command prefix (default '!'): " DISCORD_PREFIX
DISCORD_PREFIX=${DISCORD_PREFIX:-!}

read -r -p "Discord owner ID (your user ID, optional, default 0): " DISCORD_OWNER
DISCORD_OWNER=${DISCORD_OWNER:-0}

echo
echo "=== LLM Provider Configuration ==="
echo "Supported providers in this config:"
echo "  - openai      (api.openai.com)"
echo "  - openrouter  (openrouter.ai)"
echo "You can also type a custom provider name."
echo

read -r -p "LLM provider name [openai/openrouter/custom] (default 'openai'): " LLM_PROVIDER
LLM_PROVIDER=${LLM_PROVIDER:-openai}

# Choose sensible defaults based on provider
case "$LLM_PROVIDER" in
  openrouter)
    DEFAULT_BASE_URL="https://openrouter.ai/api/v1"
    DEFAULT_MODEL="openai/gpt-4o-mini"
    ;;
  openai|*)
    DEFAULT_BASE_URL="https://api.openai.com/v1"
    DEFAULT_MODEL="gpt-4o-mini"
    ;;
esac

echo
echo "The base URL is where your LLM API requests are sent."
echo "Examples:"
echo "  OpenAI:      https://api.openai.com/v1"
echo "  OpenRouter:  https://openrouter.ai/api/v1"
echo

read -r -p "LLM base URL (default '$DEFAULT_BASE_URL'): " LLM_BASE_URL
LLM_BASE_URL=${LLM_BASE_URL:-$DEFAULT_BASE_URL}

echo
echo "Model name tells the provider which model to use."
echo "Examples:"
echo "  OpenAI:      gpt-4o-mini"
echo "  OpenRouter:  openai/gpt-4o-mini"
echo

read -r -p "LLM model name (default '$DEFAULT_MODEL'): " LLM_MODEL
LLM_MODEL=${LLM_MODEL:-$DEFAULT_MODEL}

echo
echo "Your LLM API key authenticates your requests."
echo "Get this from your provider's dashboard (OpenAI, OpenRouter, etc.)."
echo

# -s for silent (no echo), -p for prompt
read -r -s -p "LLM API Key: " LLM_API_KEY
echo
if [ -z "$LLM_API_KEY" ]; then
  echo "Error: LLM API key cannot be empty."
  exit 1
fi

echo
echo "=== Rate Limits (Advanced, press Enter to keep defaults) ==="
read -r -p "Per-user cooldown seconds (default 30): " RL_COOLDOWN
RL_COOLDOWN=${RL_COOLDOWN:-30}

read -r -p "Per-guild daily limit (default 100): " RL_DAILY
RL_DAILY=${RL_DAILY:-100}

read -r -p "Token bucket capacity per user (default 5): " RL_BUCKET
RL_BUCKET=${RL_BUCKET:-5}

read -r -p "Token refill rate per second (default 1.0): " RL_REFILL
RL_REFILL=${RL_REFILL:-1.0}

read -r -p "Processing queue max size (default 50): " RL_QUEUE
RL_QUEUE=${RL_QUEUE:-50}

mkdir -p config
mkdir -p data

if [ -f "config/bot.yaml" ]; then
  echo
  echo "Warning: config/bot.yaml already exists."
  read -r -p "Overwrite existing config/bot.yaml? [y/N]: " OVERWRITE
  OVERWRITE=${OVERWRITE:-N}
  if [[ ! "$OVERWRITE" =~ ^[Yy]$ ]]; then
    echo "Aborting without changes to config/bot.yaml."
    exit 0
  fi
fi

cat > "config/bot.yaml" <<EOF
discord:
  token: "$DISCORD_TOKEN"
  prefix: "$DISCORD_PREFIX"
  owner_id: $DISCORD_OWNER

llm:
  provider: "$LLM_PROVIDER"
  api_key: "$LLM_API_KEY"
  base_url: "$LLM_BASE_URL"
  model: "$LLM_MODEL"
  temperature: 0.0
  max_tokens: 500

database:
  url: "sqlite+aiosqlite:///data/ava.db"

rate_limits:
  user_cooldown: $RL_COOLDOWN
  daily_guild_limit: $RL_DAILY
  bucket_tokens: $RL_BUCKET
  bucket_refill_rate: $RL_REFILL
  queue_max_size: $RL_QUEUE
EOF

echo
echo "config/bot.yaml has been created with your settings."
echo
echo "Next steps:"
echo "  1) Ensure config/system_prompt.txt contains the AVA system prompt."
echo "  2) If you created a virtualenv:"
echo "       - Linux/macOS/Git Bash:  source .venv/bin/activate"
echo "       - Windows (Git Bash with Windows paths):  source .venv/Scripts/activate"
echo "  3) Run the bot from the project root:"
echo "       python -m src"
echo
echo "Setup finished."
