from __future__ import annotations

from typing import Dict, Optional

import aiohttp
import discord
from discord import Webhook


class WebhookManager:
    def __init__(self) -> None:
        self.session: Optional[aiohttp.ClientSession] = None
        # Cache channel_id -> webhook
        self._channel_webhooks: Dict[int, Webhook] = {}

    async def start(self) -> None:
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def close(self) -> None:
        if self.session:
            await self.session.close()
            self.session = None

    async def send_log(self, url: str, content: str) -> None:
        if not self.session or not url:
            return
        try:
            webhook = Webhook.from_url(url, session=self.session)
            await webhook.send(content=content, wait=False)
        except Exception:
            # Logging-only; swallow exceptions
            return

    async def _get_or_create_channel_webhook(
        self, channel: discord.TextChannel
    ) -> Optional[Webhook]:
        cached = self._channel_webhooks.get(channel.id)
        if cached is not None:
            return cached

        try:
            existing = await channel.webhooks()
            for hook in existing:
                if hook.name == "AVA":
                    self._channel_webhooks[channel.id] = hook
                    return hook

            hook = await channel.create_webhook(name="AVA")
            self._channel_webhooks[channel.id] = hook
            return hook
        except Exception:
            return None

    async def send_fact_check(
        self,
        channel: discord.abc.Messageable,
        embed: discord.Embed,
        content: Optional[str] = None,
        file: Optional[discord.File] = None,
    ) -> Optional[discord.Message]:
        # Always send directly as the bot, per user request
        try:
            message = await channel.send(content=content or None, embed=embed, file=file)
            return message
        except Exception:
            return None