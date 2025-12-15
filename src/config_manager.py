from __future__ import annotations

import os
from typing import Optional

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings

try:
    from dotenv import load_dotenv
    if os.path.exists('.env'):
        load_dotenv(override=True)
except ImportError:
    pass


class DiscordConfig(BaseModel):
    token: str
    prefix: str = "!"
    owner_id: int = 0


class LLMConfig(BaseModel):
    provider: str
    api_key: str
    base_url: str
    model: str
    fallback_models: list[str] = []
    temperature: float = 0.0
    max_tokens: int = 500


class DatabaseConfig(BaseModel):
    url: str


class RateLimitConfig(BaseModel):
    user_cooldown: int = 30
    daily_guild_limit: int = 100
    bucket_tokens: int = 5
    bucket_refill_rate: float = 1.0
    queue_max_size: int = 50


class SearchConfig(BaseModel):
    enabled: bool = True
    provider: str = "auto"
    tavily_api_key: str = ""
    tavily_base_url: str = "https://api.tavily.com"
    tavily_max_results: int = 5
    tavily_search_depth: str = "basic"


class BotConfig(BaseSettings):
    discord: DiscordConfig
    llm: LLMConfig
    database: DatabaseConfig
    rate_limits: RateLimitConfig
    search: SearchConfig = SearchConfig()

    @classmethod
    def load(cls, path: str = "config/bot.yaml") -> "BotConfig":
        if not os.path.exists(path):
            raise FileNotFoundError(f"Config not found at {path}")

        with open(path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)

        # Discord token override
        env_token = os.getenv("DISCORD_TOKEN")
        if env_token:
            yaml_data.setdefault("discord", {})["token"] = env_token

        # Generic LLM key
        env_llm_generic = os.getenv("LLM_API_KEY")
        # Provider-specific keys (BYOK)
        env_openrouter = os.getenv("OPENROUTER_API_KEY")
        env_openai = os.getenv("OPENAI_API_KEY")
        env_anthropic = os.getenv("ANTHROPIC_API_KEY")
        env_google = os.getenv("GOOGLE_AI_STUDIO_API_KEY")
        
        # Custom provider support
        env_custom_provider = os.getenv("LLM_PROVIDER")
        env_custom_api_key = os.getenv("CUSTOM_API_KEY")
        env_custom_base_url = os.getenv("CUSTOM_BASE_URL")
        env_custom_model = os.getenv("CUSTOM_MODEL")
        env_custom_temperature = os.getenv("CUSTOM_TEMPERATURE")
        env_custom_max_tokens = os.getenv("CUSTOM_MAX_TOKENS")
        env_custom_fallback_models = os.getenv("CUSTOM_FALLBACK_MODELS")

        llm_section = yaml_data.setdefault("llm", {})
        
        # Handle custom provider configuration
        if env_custom_provider:
            llm_section["provider"] = env_custom_provider
            print(f"[DEBUG] Set provider from env: {env_custom_provider}")
            
        if env_custom_api_key:
            llm_section["api_key"] = env_custom_api_key
            print(f"[DEBUG] Set API key from env: {env_custom_api_key[:8]}...")
        if env_custom_base_url:
            llm_section["base_url"] = env_custom_base_url
            print(f"[DEBUG] Set base URL from env: {env_custom_base_url}")
        if env_custom_model:
            llm_section["model"] = env_custom_model
            print(f"[DEBUG] Set model from env: {env_custom_model}")
        if env_custom_fallback_models:
            fallbacks = [m.strip() for m in env_custom_fallback_models.split(",") if m.strip()]
            llm_section["fallback_models"] = fallbacks
            print(f"[DEBUG] Set fallback models from env: {fallbacks}")
        if env_custom_temperature:
            llm_section["temperature"] = float(env_custom_temperature)
            print(f"[DEBUG] Set temperature from env: {env_custom_temperature}")
        if env_custom_max_tokens:
            llm_section["max_tokens"] = int(env_custom_max_tokens)
            print(f"[DEBUG] Set max tokens from env: {env_custom_max_tokens}")

        # Provider-specific keys (fallback for compatibility)
        if env_openrouter:
            llm_section["api_key"] = env_openrouter
        elif env_openai:
            llm_section["api_key"] = env_openai
        elif env_anthropic:
            llm_section["api_key"] = env_anthropic
        elif env_google:
            llm_section["api_key"] = env_google
        elif env_llm_generic:
            llm_section["api_key"] = env_llm_generic

        # Search provider configuration from env
        search_section = yaml_data.setdefault("search", {})
        env_search_provider = os.getenv("SEARCH_PROVIDER")
        env_tavily_key = os.getenv("TAVILY_API_KEY")
        env_tavily_base = os.getenv("TAVILY_BASE_URL")
        env_tavily_results = os.getenv("TAVILY_MAX_RESULTS")
        env_tavily_depth = os.getenv("TAVILY_SEARCH_DEPTH")
        
        if env_search_provider:
            search_section["provider"] = env_search_provider
        if env_tavily_key:
            search_section["tavily_api_key"] = env_tavily_key
        if env_tavily_base:
            search_section["tavily_base_url"] = env_tavily_base
        if env_tavily_results:
            search_section["tavily_max_results"] = int(env_tavily_results)
        if env_tavily_depth:
            search_section["tavily_search_depth"] = env_tavily_depth

        return cls(**yaml_data)