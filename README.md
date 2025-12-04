<p align="center">
  <a href="https://github.com/Microck/nagrom">
    <img src="assets/logo/icon.png" alt="logo" width="150">
  </a>
</p>

<p align="center">nagrom is a self-hostable discord bot designed for rigorous fact-checking against a tiered hierarchy of trusted sources. </p>

<p align="center">
  <a href="LICENSE"><img alt="license" src="https://img.shields.io/badge/license-O’Saasy-pink.svg" /></a>
  <a href="https://www.python.org/"><img alt="python" src="https://img.shields.io/badge/python-3.11+-blue.svg" /></a>
  <a href="https://github.com/Rapptz/discord.py"><img alt="discord" src="https://img.shields.io/badge/discord-py-lilac.svg" /></a>
</p>

---

### quickstart

```bash
# clone the repo
git clone https://github.com/microck/nagrom.git
cd nagrom

# setup venv because we aren't savages
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on windows

# install dependencies
pip install -r requirements.txt

# minimal config setup
cp config/examples/minimal.yaml config/bot.yaml
# you need to edit bot.yaml with your keys now. don't skip this.

# run it
python -m src
```

---

### table of contents

*   [features](#features)
*   [how it works](#how-it-works)
*   [installation](#installation)
*   [configuration](#configuration)
*   [usage](#usage)
*   [troubleshooting](#troubleshooting)
*   [dependencies](#dependencies)

---

### features

nagrom isn't just a wrapper around chatgpt. it enforces a specific logic loop to verify facts.

*   **bring your own key:** supports openrouter, openai, anthropic, or generic openai-compatible endpoints. i'm not paying for your tokens.
*   **strict verification:** uses a tiered source hierarchy. snopes ranks higher than reddit.
*   **async architecture:** built on `discord.py` 2.4+ and `aiohttp`. no blocking calls allowed here.
*   **structured output:** the llm is forced to output json, which we parse into pretty embeds.
*   **rate limiting:** built-in token buckets and cooldowns so your server doesn't bankrupt you.
*   **flexible triggers:** supports slash commands, replies, mentions, and context menus.
*   **database backed:** keeps a history of checks in sqlite using `sqlalchemy`.

---

### how it works

nagrom acts as a "logic engine." it doesn't just chat. when you ask it to verify something, it goes through a pipeline:

1.  **intent classification:** figures out if you are asking for a fact check or just trying to write a poem.
2.  **extraction:** pulls out the claims, dates, and entities.
3.  **retrieval:** looks for sources based on a trust tier (tier 1 is reuters/snopes, tier 4 is twitter).
4.  **synthesis:** compares sources against internal knowledge. external evidence wins.
5.  **response:** formats the verdict as `true`, `false`, `mixed`, or `unverifiable`.

> **note:** checking facts requires an llm capable of tool use or browsing if you want live internet access. otherwise it relies on the model's training data cutoff.

---

### installation

this assumes you have python 3.11 or higher installed. docker instructions are further down if you prefer containers.

#### 1. clone and prep

```bash
git clone https://github.com/microck/nagrom.git
cd nagrom
mkdir data
```

#### 2. virtual environment

always use a virtual environment. installing global packages is a bad habit.

**windows (powershell)**
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**linux / macos**
```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

#### 3. dependencies

```bash
pip install -r requirements.txt
```

---

### configuration

configuration is split between `config/bot.yaml` for settings and `config/system_prompt.txt` for the brain.

#### the yaml file

create `config/bot.yaml`. here is a sane default configuration:

```yaml
discord_token: "${DISCORD_TOKEN}" # loads from env var
database_url: "sqlite+aiosqlite:///./data/nagrom.db"

llm:
  default_provider: "openrouter"
  
  providers:
    openrouter:
      enabled: true
      api_key: "${OPENROUTER_KEY}"
      model: "google/gemini-2.5-flash-preview"
      max_tokens: 4000
      temperature: 0.0 # keep this low for facts

rate_limits:
  user_cooldown_seconds: 30
  guild_daily_limit: 100

features:
  enable_reply_detection: true
  enable_context_menu: true
```

#### the system prompt

nagrom relies on a very specific system prompt to force the llm to output json. if you mess this up, the bot will crash trying to parse the response.

ensure `config/system_prompt.txt` exists and contains the verification logic. see the example in `config/examples/` if you lost it.

#### environment variables

you can set keys directly in the yaml if you don't care about security, but using environment variables is the recommended way.

```bash
export DISCORD_TOKEN="your_token_here"
export OPENROUTER_KEY="your_key_here"
```

---

### usage

once the bot is running and invited to your server, you have four ways to annoy your friends with facts.

#### 1. the reply (recommended)
someone posts something wrong. you reply to their message and tag the bot.
> **user a:** the earth is flat actually.
> **you (replying to a):** @nagrom check this.

#### 2. the slash command
good for settling bets in real time.
> `/check statement: the us gdp grew by 2.5% in 2023`

#### 3. direct mention
just ping the bot with a statement.
> `@nagrom did the pope wear a puffer jacket?`

#### 4. context menu
right click a message, go to **apps**, and select **check facts**. this is the stealthy way to do it.

---

### troubleshooting

things go wrong. here is how to fix them.

| problem | likely cause | fix |
| :--- | :--- | :--- |
| **bot ignores commands** | missing scope | re-invite bot with `applications.commands` scope selected. |
| **"interaction failed"** | timeout | the llm is taking too long. try a faster model like gemini flash. |
| **json parse error** | bad model | your model is ignoring the system prompt. switch to a smarter model (gpt-4o, claude 3.5). |
| **rate limited immediately** | clock drift | check your server time. or you set the limit to 1 request per day. |

> **warning:** do not use small local models (like 7b params) for this. they are terrible at following the strict json schema required for the verification result and will likely hallucinate the format.

---

### dependencies

the heavy lifting is done by these libraries. big thanks to the maintainers.

*   `discord.py` for the bot interface
*   `aiohttp` for async requests
*   `sqlalchemy` + `aiosqlite` for the database
*   `pydantic` for strict config validation
*   `mcp` for the model context protocol support

---

### license

o'saasy license
