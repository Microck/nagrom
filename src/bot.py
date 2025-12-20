from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import dataclass
from typing import Literal, Optional, Tuple
from datetime import datetime

import discord
from discord.ext import commands

from .config_manager import BotConfig
from .llm.provider import LLMProvider
from .llm.search_provider import SearchManager
from .llm.openai_compatible import OpenRouterProvider
from .llm.openai_sdk_provider import OpenAISDKProvider
from .llm.google_ai_studio import GoogleAIStudioProvider
from .llm.anthropic import AnthropicProvider
from .models.database import DatabaseManager, FactCheck
from .models.verification import VerificationResult
from .utils.rate_limiter import RateLimiter
from .utils.webhook_manager import WebhookManager


logger = logging.getLogger(__name__)


def create_llm_provider(config: BotConfig, search_manager: Optional[SearchManager] = None) -> LLMProvider:
    """Factory function to create the appropriate LLM provider based on config."""
    provider_name = config.llm.provider.lower()
    
    print(f"[DEBUG] Provider factory called with: {provider_name}")
    print(f"[DEBUG] Base URL: {config.llm.base_url}")
    print(f"[DEBUG] Model: {config.llm.model}")
    
    if provider_name == "google_ai_studio" or provider_name == "google":
        print(f"[DEBUG] Creating GoogleAIStudioProvider")
        return GoogleAIStudioProvider(config.llm, "config/system_prompt.txt", search_manager)
    elif provider_name == "anthropic":
        print(f"[DEBUG] Creating AnthropicProvider")
        return AnthropicProvider(config.llm, "config/system_prompt.txt", search_manager)
    elif provider_name == "openai_compatible" or provider_name == "nvidia":
        print(f"[DEBUG] Creating OpenAISDKProvider for {provider_name}")
        return OpenAISDKProvider(config.llm, "config/system_prompt.txt", search_manager)
    elif provider_name == "custom" or provider_name == "openai" or provider_name == "openrouter":
        print(f"[DEBUG] Creating OpenRouterProvider (OpenAI-compatible)")
        return OpenRouterProvider(config.llm, "config/system_prompt.txt", search_manager)
    else:
        print(f"[DEBUG] Unknown provider '{provider_name}', falling back to OpenAI-compatible")
        logger.warning(f"Unknown provider '{provider_name}', falling back to OpenAI-compatible")
        return OpenRouterProvider(config.llm, "config/system_prompt.txt", search_manager)


@dataclass
class FactCheckJob:
    guild_id: Optional[int]
    channel_id: int
    source_message_id: Optional[int]
    requestor_id: int
    statement_author_id: int
    input_text: str
    trigger_type: Literal["reply", "mention", "slash", "context"]
    placeholder_message_id: Optional[int] = None


class NagromBot(commands.Bot):
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
        self.search_manager = SearchManager(config.search.model_dump())
        logger.info(f"Search manager available: {self.search_manager.is_available()}")
        if not self.search_manager.is_available():
            self.search_manager = None
            logger.warning("No search provider available - fact checks will return UNVERIFIABLE")

        self.llm: LLMProvider = create_llm_provider(self.config, self.search_manager)
        logger.info(f"LLM provider created with search_manager: {self.search_manager is not None}")
        self.start_time = datetime.utcnow()

        self.fact_check_queue: asyncio.Queue[FactCheckJob] = asyncio.Queue(
            maxsize=config.rate_limits.queue_max_size
        )
        self._worker_tasks: list[asyncio.Task[None]] = []

    async def setup_hook(self) -> None:
        logger.info("Initializing nagrom")

        await self.db.init_models()
        await self.webhook_manager.start()
        await self.load_active_config()

        initial_extensions = [
            "src.listeners.messages",
            "src.listeners.context_menu",
            "src.listeners.errors",
            "src.commands.general",
            "src.commands.config",
            "src.commands.admin",
            "src.commands.stats",
            "src.commands.help",
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
        
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="for facts to check",
            buttons=[{"label": "GitHub", "url": "https://github.com/Microck/nagrom"}]
        )
        await self.change_presence(activity=activity, status=discord.Status.online)
        
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
        logger.info("Shutting down nagrom")

        for task in self._worker_tasks:
            task.cancel()
        await self.webhook_manager.close()
        await self.db.engine.dispose()
        await super().close()

    async def reload_llm_provider(self) -> None:
        """Re-initializes the LLM provider with the current config."""
        for task in self._worker_tasks:
            task.cancel()
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks = []

        logger.info(f"Reloading LLM with search_manager: {self.search_manager is not None}")
        self.llm = create_llm_provider(self.config, self.search_manager)
        logger.info("LLM provider reloaded with new configuration.")

        # Restart worker tasks
        for _ in range(2):
            task = asyncio.create_task(self._fact_check_worker())
            self._worker_tasks.append(task)

    async def load_active_config(self) -> None:
        """Loads the active configuration preset from the database and updates self.config."""
        async with self.db.session_maker() as session:
            from sqlalchemy import select
            from .models.database import ConfigPreset
            from .utils.crypto import CryptoManager

            active_preset = await session.scalar(
                select(ConfigPreset).where(ConfigPreset.is_active == True)
            )

            if active_preset:
                logger.info(f"Loading active config preset: {active_preset.name}")
                # Update self.config.llm directly from the preset
                # This assumes LLMConfig can be updated from a ConfigPreset object.
                # Need to add a method to config_manager.py for this.
                from .config_manager import LLMConfig
                self.config.llm = LLMConfig(
                    provider=active_preset.provider,
                    api_key=CryptoManager.decrypt(active_preset.api_key),
                    base_url=active_preset.base_url,
                    model=active_preset.model,
                    fallback_models=[m.strip() for m in active_preset.fallback_models.split(',') if m.strip()],
                    temperature=active_preset.temperature,
                    max_tokens=active_preset.max_tokens,
                )
                logger.info(f"LLM configuration updated from DB preset '{active_preset.name}'.")
            else:
                logger.info("No active config preset found in DB. Using config from .env/.yaml.")

        # Always reload LLM provider after potentially changing config
        await self.reload_llm_provider()

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
        placeholder_message_id: Optional[int] = None,
    ) -> Tuple[bool, str]:
        job = FactCheckJob(
            guild_id=guild_id,
            channel_id=channel_id,
            source_message_id=source_message_id,
            requestor_id=requestor_id,
            statement_author_id=statement_author_id,
            input_text=input_text,
            trigger_type=trigger_type,
            placeholder_message_id=placeholder_message_id,
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
                try:
                    result = await self.llm.analyze_text(job.input_text)
                except Exception as llm_exc:
                    logger.exception("LLM analysis failed: %s", llm_exc)
                    result = VerificationResult(
                        statement=job.input_text[:500],
                        verdict="UNVERIFIABLE",
                        confidence=0.0,
                        reasoning=f"Analysis failed: {str(llm_exc)}",
                        sources=[],
                    )
                
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

        embed, file = await self._build_fact_check_embed(job, result)
        content = None  # no pings by default

        # Try to edit the placeholder message if it exists
        if job.placeholder_message_id:
            try:
                placeholder = await channel.fetch_message(job.placeholder_message_id)
                # Note: editing with a file that wasn't there before, or replacing one
                await placeholder.edit(embed=embed, attachments=[file] if file else [])
                return placeholder
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass  # Fallback to sending new message

        message = await self.webhook_manager.send_fact_check(channel, embed, content, file=file)
        return message

    async def _build_fact_check_embed(
        self, job: FactCheckJob, result: VerificationResult
    ) -> Tuple[discord.Embed, Optional[discord.File]]:
        statement_text = result.statement or job.input_text
        if len(statement_text) > 1024:
            statement_text = statement_text[:1021] + "..."

        # Color Logic & Thumbnail File
        verdict_title = result.verdict.title() # Title Case (True, False, etc.)
        verdict_upper = result.verdict.upper() # Keep upper for logic check
        file = None
        
        if verdict_upper == "FALSE":
            color = discord.Color(0xED4245)
            if os.path.exists("assets/false.png"):
                file = discord.File("assets/false.png", filename="false.png")
        elif verdict_upper == "TRUE":
            color = discord.Color(0x57F287)
            if os.path.exists("assets/true.png"):
                file = discord.File("assets/true.png", filename="true.png")
        elif verdict_upper == "MIXED":
            color = discord.Color(0xFEE75C)
        else:
            color = discord.Color(0x95A5A6)

        embed = discord.Embed(
            # title="Fact Check Result", 
            color=color,
        )

        # Thumbnail
        if file:
            embed.set_thumbnail(url=f"attachment://{file.filename}")

        # Field 1: Claim Checked:
        embed.add_field(name="Claim Checked:", value=statement_text, inline=False)

        # Field 2: Verdict
        embed.add_field(name="Verdict", value=verdict_title, inline=True)

        # Field 3: Confidence
        conf_val = result.confidence if isinstance(result.confidence, (int, float)) else 0.0
        embed.add_field(name="Confidence", value=f"{conf_val * 100:.1f}%", inline=True)

        # Field 4: Reasoning
        reasoning_val = result.reasoning if result.reasoning else "No reasoning provided."
        reasoning_val = re.sub(r'\s*\[\d+\]', '', reasoning_val)
        if len(reasoning_val) > 1024:
            reasoning_val = reasoning_val[:1021] + "..."
        embed.add_field(name="Reasoning", value=reasoning_val, inline=False)

        # Field 5: Sources
        if result.sources:
            source_lines = []
            for s in result.sources:
                tier_str = f" | Tier {s.tier}" if s.tier else ""
                if s.url:
                    source_lines.append(f"[{s.name}{tier_str}]({s.url})")
                else:
                    source_lines.append(f"{s.name}{tier_str}")
            
            sources_val = "\n".join(source_lines)
            if len(sources_val) > 1024:
                sources_val = sources_val[:1021] + "..."
            embed.add_field(name="Sources", value=sources_val, inline=False)
        else:
             embed.add_field(name="Sources", value="None provided", inline=False)

        # Fetch users for Author/Footer
        try:
            checker_user = await self.fetch_user(job.requestor_id)
            checker_name = checker_user.display_name
            checker_icon = checker_user.display_avatar.url
        except Exception:
            checker_name = f"User {job.requestor_id}"
            checker_icon = None

        # Footer: Checked by + Model
        # Clean model name: remove :online
        model_str = result.model_name or "Unknown Model"
        model_str = model_str.replace(":online", "")
        
        footer_text = f"Checked by {checker_name} | {model_str}"
        embed.set_footer(text=footer_text, icon_url=checker_icon)

        return embed, file

    async def _store_fact_check(
        self,
        job: FactCheckJob,
        result: VerificationResult,
        message: Optional[discord.Message],
    ) -> None:
        try:
            confidence_val = result.confidence
            if not isinstance(confidence_val, (int, float)):
                confidence_val = None
            elif confidence_val < 0 or confidence_val > 1:
                confidence_val = max(0.0, min(1.0, float(confidence_val)))
            else:
                confidence_val = float(confidence_val)
            
            async with self.db.session_maker() as session:
                input_tokens = None
                output_tokens = None
                cost = 0.0
                
                if hasattr(result, "usage") and result.usage:
                    input_tokens = result.usage.get("input_tokens")
                    output_tokens = result.usage.get("output_tokens")
                    # Naive cost calculation ($0.50 / 1M tokens blended average)
                    if input_tokens and output_tokens:
                        cost = (input_tokens + output_tokens) / 1_000_000 * 0.50

                fc = FactCheck(
                    user_id=job.requestor_id,
                    guild_id=job.guild_id,
                    channel_id=job.channel_id,
                    source_message_id=job.source_message_id,
                    response_message_id=message.id if message else None,
                    input_text=job.input_text,
                    statement=result.statement or job.input_text[:500],
                    verdict=result.verdict,
                    confidence=confidence_val,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost=cost,
                    raw_response=result.model_dump(),
                )
                session.add(fc)
                await session.commit()
        except Exception as db_exc:
            logger.exception("Failed to store fact-check: %s", db_exc)