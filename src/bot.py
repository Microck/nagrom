from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Literal, Optional, Tuple

import discord
from discord.ext import commands

from .config_manager import BotConfig
from .llm.provider import LLMProvider
from .llm.openai_compatible import OpenRouterProvider
from .llm.google_ai_studio import GoogleAIStudioProvider
from .llm.anthropic import AnthropicProvider
from .models.database import DatabaseManager, FactCheck
from .models.verification import VerificationResult
from .utils.rate_limiter import RateLimiter
from .utils.webhook_manager import WebhookManager


logger = logging.getLogger(__name__)


def create_llm_provider(config: BotConfig) -> LLMProvider:
    """Factory function to create the appropriate LLM provider based on config."""
    provider_name = config.llm.provider.lower()
    
    if provider_name == "google_ai_studio" or provider_name == "google":
        return GoogleAIStudioProvider(config.llm, "config/system_prompt.txt")
    elif provider_name == "anthropic":
        return AnthropicProvider(config.llm, "config/system_prompt.txt")
    else:  # Default to OpenAI-compatible (openai, openrouter, custom)
        return OpenRouterProvider(config.llm, "config/system_prompt.txt")


@dataclass
class FactCheckJob:
    guild_id: Optional[int]
    channel_id: int
    source_message_id: Optional[int]
    requestor_id: int
    statement_author_id: int
    input_text: str
    trigger_type: Literal["reply", "mention", "slash", "context"]


class AVABot(commands.Bot):
    def __init__(self, config: BotConfig):
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix=config.discord.prefix,
            intents=intents,
            help_command=None,
            owner_id=config.discord.owner_id,
        )

        self.config = config
        self.db = DatabaseManager(config.database.url)
        self.rate_limiter = RateLimiter(config.rate_limits)
        self.webhook_manager = WebhookManager()

        self.llm = create_llm_provider(config)

        self.fact_check_queue: asyncio.Queue[FactCheckJob] = asyncio.Queue(
            maxsize=config.rate_limits.queue_max_size
        )
        self._worker_tasks: list[asyncio.Task[None]] = []

    async def setup_hook(self) -> None:
        logger.info("Initializing AVA")

        await self.db.init_models()
        await self.webhook_manager.start()

        initial_extensions = [
            "src.listeners.messages",
            "src.listeners.context_menu",
            "src.listeners.errors",
            "src.commands.setup",
            "src.commands.config",
            "src.commands.admin",
        ]

        for ext in initial_extensions:
            try:
                await self.load_extension(ext)
                logger.info("Loaded extension: %s", ext)
            except Exception as exc:
                logger.error("Failed to load extension %s: %s", ext, exc)

        # Start worker tasks
        for _ in range(2):
            task = asyncio.create_task(self._fact_check_worker())
            self._worker_tasks.append(task)

        await self.tree.sync()
        logger.info("Application commands synced.")

    async def on_ready(self) -> None:
        logger.info("Logged in as %s (ID: %s)", self.user, self.user.id if self.user else "N/A")
        
        # Set bot avatar to default logo if not already set
        try:
            if self.user and self.user.avatar is None:
                logo_path = "assets/logo/logo.png"
                if os.path.exists(logo_path):
                    with open(logo_path, "rb") as f:
                        avatar_data = f.read()
                    await self.user.edit(avatar=avatar_data)
                    logger.info("Bot avatar set to default logo")
                else:
                    logger.warning("Logo file not found at %s", logo_path)
        except Exception as exc:
            logger.warning("Could not set bot avatar: %s", exc)

    async def close(self) -> None:
        logger.info("Shutting down AVA")

        for task in self._worker_tasks:
            task.cancel()
        await self.webhook_manager.close()
        await self.db.engine.dispose()
        await super().close()

    async def submit_fact_check(
        self,
        *,
        guild_id: Optional[int],
        channel_id: int,
        source_message_id: Optional[int],
        requestor_id: int,
        statement_author_id: int,
        input_text: str,
        trigger_type: Literal["reply", "mention", "slash", "context"],
    ) -> Tuple[bool, str]:
        job = FactCheckJob(
            guild_id=guild_id,
            channel_id=channel_id,
            source_message_id=source_message_id,
            requestor_id=requestor_id,
            statement_author_id=statement_author_id,
            input_text=input_text,
            trigger_type=trigger_type,
        )
        try:
            self.fact_check_queue.put_nowait(job)
            return True, ""
        except asyncio.QueueFull:
            return False, "The fact-check queue is full. Please try again shortly."

    async def _fact_check_worker(self) -> None:
        while True:
            job = await self.fact_check_queue.get()
            try:
                result = await self.llm.analyze_text(job.input_text)
                message = await self._deliver_fact_check(job, result)
                await self._store_fact_check(job, result, message)
            except Exception as exc:
                logger.exception("Error processing fact-check job: %s", exc)
            finally:
                self.fact_check_queue.task_done()

    async def _deliver_fact_check(
        self, job: FactCheckJob, result: VerificationResult
    ) -> Optional[discord.Message]:
        channel = self.get_channel(job.channel_id)
        if channel is None:
            try:
                channel = await self.fetch_channel(job.channel_id)  # type: ignore[assignment]
            except Exception:
                logger.warning("Could not resolve channel_id=%s", job.channel_id)
                return None

        if not isinstance(
            channel, (discord.TextChannel, discord.Thread, discord.DMChannel, discord.GroupChannel)
        ):
            return None

        embed = self._build_fact_check_embed(job, result)
        content = None  # no pings by default

        message = await self.webhook_manager.send_fact_check(channel, embed, content)
        return message

    def _build_fact_check_embed(
        self, job: FactCheckJob, result: VerificationResult
    ) -> discord.Embed:
        statement_text = result.statement or job.input_text[:500]

        color_map = {
            "true": discord.Color.green(),
            "false": discord.Color.red(),
            "mixed": discord.Color.orange(),
            "unverifiable": discord.Color.light_grey(),
        }
        embed = discord.Embed(
            title="Fact Check Result",
            description=statement_text,
            color=color_map.get(result.verdict, discord.Color.default()),
        )

        embed.add_field(name="Verdict", value=result.verdict.upper(), inline=True)
        embed.add_field(
            name="Confidence",
            value=f"{result.confidence * 100:.1f}%",
            inline=True,
        )
        embed.add_field(name="Reasoning", value=result.reasoning, inline=False)

        if result.sources:
            lines: list[str] = []
            for s in result.sources:
                base = s.name
                if s.url:
                    base = f"[{s.name}]({s.url})"
                lines.append(f"{base} (Tier {s.tier})")
            embed.add_field(name="Sources", value="\n".join(lines), inline=False)

        footer = (
            f"Checked by <@{job.requestor_id}>, "
            f"Statement by <@{job.statement_author_id}>"
        )
        embed.set_footer(text=footer)

        return embed

    async def _store_fact_check(
        self,
        job: FactCheckJob,
        result: VerificationResult,
        message: Optional[discord.Message],
    ) -> None:
        async with self.db.session_maker() as session:
            fc = FactCheck(
                user_id=job.requestor_id,
                guild_id=job.guild_id,
                channel_id=job.channel_id,
                source_message_id=job.source_message_id,
                response_message_id=message.id if message else None,
                input_text=job.input_text,
                statement=result.statement,
                verdict=result.verdict,
                confidence=result.confidence,
                raw_response=result.model_dump(),
            )
            session.add(fc)
            await session.commit()