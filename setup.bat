@echo off
setlocal EnableDelayedExpansion

rem === nagrom Quick Interactive Setup ===
echo === nagrom Quick Interactive Setup ===
echo.
echo This script will:
echo   - (Optionally) create a Python virtual environment and install dependencies
echo   - Ask for your Discord bot token and LLM settings
echo   - Generate config\bot.yaml for you
echo.

set /p DO_ENV_SETUP="Set up Python virtualenv and install requirements? [Y/n]: "
if not defined DO_ENV_SETUP set DO_ENV_SETUP=Y

if /i "%DO_ENV_SETUP%"=="Y" (
    rem Check for Python binary
    if defined PYTHON_BIN (
        where %PYTHON_BIN% >nul 2>&1
        if !errorlevel! neq 0 (
            echo Error: Python binary '%PYTHON_BIN%' not found.
            exit /b 1
        )
    ) else (
        where python3 >nul 2>&1
        if !errorlevel! equ 0 (
            set PYTHON_BIN=python3
        ) else (
            where python >nul 2>&1
            if !errorlevel! equ 0 (
                set PYTHON_BIN=python
            ) else (
                echo Error: Python 3.11+ is required but not found on PATH.
                echo Install Python, then re-run this script.
                exit /b 1
            )
        )
    )

    echo.
    echo Using Python: %PYTHON_BIN%

    rem Check Python version (3.11+)
    %PYTHON_BIN% -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>nul
    if !errorlevel! neq 0 (
        echo Error: Python 3.11+ required.
        exit /b 1
    )

    rem Create virtual environment
    if not exist ".venv" (
        echo Creating virtual environment in .venv ...
        %PYTHON_BIN% -m venv .venv
        if !errorlevel! neq 0 (
            echo Error: Failed to create virtual environment.
            exit /b 1
        )
    ) else (
        echo Virtual environment .venv already exists; reusing.
    )

    rem Install requirements
    if exist "requirements.txt" (
        echo Installing Python dependencies from requirements.txt ...
        .venv\Scripts\python -m pip install --upgrade pip >nul 2>&1
        .venv\Scripts\pip install -r requirements.txt
        if !errorlevel! neq 0 (
            echo Warning: Failed to install some dependencies.
        )
    ) else (
        echo Warning: requirements.txt not found; skipping dependency install.
    )
) else (
    echo Skipping Python environment setup.
)

rem === Discord Bot Configuration ===
echo.
echo === Discord Bot Configuration ===
echo You need a bot token from https://discord.com/developers/applications
echo Create an application, add a Bot user, and copy the token.
echo.

:GET_DISCORD_TOKEN
set /p DISCORD_TOKEN="Discord Bot Token: "
if not defined DISCORD_TOKEN (
    echo Error: Discord bot token cannot be empty.
    goto GET_DISCORD_TOKEN
)

set /p DISCORD_PREFIX="Discord command prefix (default '!'): "
if not defined DISCORD_PREFIX set DISCORD_PREFIX=!

set /p DISCORD_OWNER="Discord owner ID (your user ID, optional, default 0): "
if not defined DISCORD_OWNER set DISCORD_OWNER=0

rem === LLM Provider Configuration ===
echo.
echo === LLM Provider Configuration ===
echo Supported providers in this config:
echo   - openai      (api.openai.com)
echo   - openrouter  (openrouter.ai)
echo You can also type a custom provider name.
echo.

set /p LLM_PROVIDER="LLM provider name [openai/openrouter/custom] (default 'openai'): "
if not defined LLM_PROVIDER set LLM_PROVIDER=openai

rem Set defaults based on provider
if /i "%LLM_PROVIDER%"=="openrouter" (
    set DEFAULT_BASE_URL=https://openrouter.ai/api/v1
    set DEFAULT_MODEL=openai/gpt-4o-mini
) else (
    set DEFAULT_BASE_URL=https://api.openai.com/v1
    set DEFAULT_MODEL=gpt-4o-mini
)

echo.
echo The base URL is where your LLM API requests are sent.
echo Examples:
echo   OpenAI:      https://api.openai.com/v1
echo   OpenRouter:  https://openrouter.ai/api/v1
echo.

set /p LLM_BASE_URL="LLM base URL (default '%DEFAULT_BASE_URL%'): "
if not defined LLM_BASE_URL set LLM_BASE_URL=%DEFAULT_BASE_URL%

echo.
echo Model name tells the provider which model to use.
echo Examples:
echo   OpenAI:      gpt-4o-mini
echo   OpenRouter:  openai/gpt-4o-mini
echo.

set /p LLM_MODEL="LLM model name (default '%DEFAULT_MODEL%'): "
if not defined LLM_MODEL set LLM_MODEL=%DEFAULT_MODEL%

echo.
echo Your LLM API key authenticates your requests.
echo Get this from your provider's dashboard (OpenAI, OpenRouter, etc.).
echo.

rem Use PowerShell for silent input
set PS_CMD=powershell -Command "$secure = Read-Host -AsSecureString -Prompt 'LLM API Key: ';"
set PS_CMD=%PS_CMD% $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure);"
set PS_CMD=%PS_CMD% $key = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr);"
set PS_CMD=%PS_CMD% [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr);"
set PS_CMD=%PS_CMD% Write-Output $key"

for /f "usebackq delims=" %%i in (`%PS_CMD%`) do set LLM_API_KEY=%%i
echo.

if not defined LLM_API_KEY (
    echo Error: LLM API key cannot be empty.
    exit /b 1
)

rem === Rate Limits (Advanced, press Enter to keep defaults) ===
echo.
echo === Rate Limits (Advanced, press Enter to keep defaults) ===
set /p RL_COOLDOWN="Per-user cooldown seconds (default 30): "
if not defined RL_COOLDOWN set RL_COOLDOWN=30

set /p RL_DAILY="Per-guild daily limit (default 100): "
if not defined RL_DAILY set RL_DAILY=100

set /p RL_BUCKET="Token bucket capacity per user (default 5): "
if not defined RL_BUCKET set RL_BUCKET=5

set /p RL_REFILL="Token refill rate per second (default 1.0): "
if not defined RL_REFILL set RL_REFILL=1.0

set /p RL_QUEUE="Processing queue max size (default 50): "
if not defined RL_QUEUE set RL_QUEUE=50

rem Create directories
if not exist "config" mkdir config
if not exist "data" mkdir data

rem Check for existing config file
if exist "config\bot.yaml" (
    echo.
    echo Warning: config\bot.yaml already exists.
    set /p OVERWRITE="Overwrite existing config\bot.yaml? [y/N]: "
    if not defined OVERWRITE set OVERWRITE=N
    if /i not "%OVERWRITE%"=="Y" (
        echo Aborting without changes to config\bot.yaml.
        exit /b 0
    )
)

rem Generate YAML configuration file
(
    echo discord:
    echo   token: "%DISCORD_TOKEN%"
    echo   prefix: "%DISCORD_PREFIX%"
    echo   owner_id: %DISCORD_OWNER%
    echo.
    echo llm:
    echo   provider: "%LLM_PROVIDER%"
    echo   api_key: "%LLM_API_KEY%"
    echo   base_url: "%LLM_BASE_URL%"
    echo   model: "%LLM_MODEL%"
    echo   temperature: 0.0
    echo   max_tokens: 500
    echo.
    echo database:
    echo   url: "sqlite+aiosqlite:///data/ava.db"
    echo.
    echo rate_limits:
    echo   user_cooldown: %RL_COOLDOWN%
    echo   daily_guild_limit: %RL_DAILY%
    echo   bucket_tokens: %RL_BUCKET%
    echo   bucket_refill_rate: %RL_REFILL%
    echo   queue_max_size: %RL_QUEUE%
) > config\bot.yaml

echo.
echo config\bot.yaml has been created with your settings.
echo.
echo Next steps:
echo   1) Ensure config\system_prompt.txt contains the AVA system prompt.
echo   2) If you created a virtualenv:
echo        - Windows CMD: .venv\Scripts\activate.bat
echo        - Windows PowerShell: .venv\Scripts\Activate.ps1
echo   3) Run the bot from the project root:
echo        python -m src
echo.
echo Setup finished.
echo.
pause
endlocal