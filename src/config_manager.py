from __future__ import annotations

import os
from typing import Optional

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class DiscordConfig(BaseModel):
    token: str
    prefix: str = "!"
    owner_id: int = 0


class LLMConfig(BaseModel):
    provider: str
    api_key: str
    base_url: str
    model: str
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


class BotConfig(BaseSettings):
    discord: DiscordConfig
    llm: LLMConfig
    database: DatabaseConfig
    rate_limits: RateLimitConfig

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

        llm_section = yaml_data.setdefault("llm", {})

        if env_openrouter:
            llm_section["api_key"] = env_openrouter
        elif env_openai:
            llm_section["api_key"] = env_openai
        elif env_anthropic:
            llm_section["api_key"] = env_anthropic
        elif env_llm_generic:
            llm_section["api_key"] = env_llm_generic

        return cls(**yaml_data)