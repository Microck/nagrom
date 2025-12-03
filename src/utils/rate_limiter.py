from __future__ import annotations

import time
from typing import Dict, Tuple

from cachetools import TTLCache

from ..config_manager import RateLimitConfig


class RateLimiter:
    def __init__(self, config: RateLimitConfig):
        self.config = config

        # User cooldown: key=user_id, value=timestamp (value unused; TTLCache handles expiry)
        self.user_cooldowns: TTLCache[int, float] = TTLCache(
            maxsize=10000, ttl=config.user_cooldown
        )

        # Token buckets: key=user_id, value=(tokens, last_update_ts)
        self.token_buckets: Dict[int, Tuple[float, float]] = {}

        # Guild daily usage (in-memory, soft enforcement)
        self.guild_usage: Dict[int, int] = {}
        self.guild_usage_reset_ts: float = time.time()

    def _reset_guild_usage_if_needed(self, now: float) -> None:
        # Simple 24h rolling window reset
        if now - self.guild_usage_reset_ts >= 86400:
            self.guild_usage.clear()
            self.guild_usage_reset_ts = now

    def check(self, user_id: int, guild_id: int | None) -> Tuple[bool, str]:
        now = time.time()

        # Daily guild usage reset
        self._reset_guild_usage_if_needed(now)

        # 1. Hard cooldown
        if user_id in self.user_cooldowns:
            return False, "Per-user cooldown is active."

        # 2. Token bucket
        bucket_tokens = float(self.config.bucket_tokens)
        bucket = self.token_buckets.get(user_id, (bucket_tokens, now))
        tokens, last_update = bucket
        elapsed = max(0.0, now - last_update)
        tokens = min(bucket_tokens, tokens + elapsed * float(self.config.bucket_refill_rate))

        if tokens < 1.0:
            return False, "Per-user burst limit reached. Please wait a moment."

        # 3. Guild limit
        if guild_id is not None:
            current_guild_usage = self.guild_usage.get(guild_id, 0)
            if current_guild_usage >= self.config.daily_guild_limit:
                return False, "Daily fact-check limit for this server has been reached."

        # Commit usage
        self.token_buckets[user_id] = (tokens - 1.0, now)
        self.user_cooldowns[user_id] = now

        if guild_id is not None:
            self.guild_usage[guild_id] = self.guild_usage.get(guild_id, 0) + 1

        return True, ""