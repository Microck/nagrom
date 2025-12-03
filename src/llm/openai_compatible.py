from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict

import aiohttp

from .provider import LLMProvider
from ..config_manager import LLMConfig
from ..models.verification import VerificationResult

logger = logging.getLogger(__name__)


class OpenRouterProvider(LLMProvider):
    def __init__(self, config: LLMConfig, system_prompt_path: str):
        self.config = config
        with open(system_prompt_path, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()

    async def analyze_text(self, text: str) -> VerificationResult:
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": text},
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "response_format": {"type": "json_object"},
        }

        start = time.perf_counter()

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.config.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                ) as resp:
                    latency = time.perf_counter() - start

                    if resp.status != 200:
                        body = await resp.text()
                        logger.error(
                            "LLM HTTP error %s (%.3fs): %s",
                            resp.status,
                            latency,
                            body,
                        )
                        raise RuntimeError(f"LLM Provider Error: {resp.status}")

                    data = await resp.json()
                    content = data["choices"][0]["message"]["content"]

                    if isinstance(content, dict):
                        parsed = content
                    else:
                        parsed = json.loads(content)

                    result = VerificationResult(**parsed)
                    logger.info(
                        "LLM success in %.3fs | verdict=%s conf=%.3f",
                        latency,
                        result.verdict,
                        result.confidence,
                    )
                    return result
            except Exception as exc:
                latency = time.perf_counter() - start
                logger.exception("LLM exception after %.3fs: %s", latency, exc)
                return VerificationResult(
                    statement=text[:500],
                    verdict="unverifiable",
                    confidence=0.0,
                    reasoning="Internal error while contacting the verification engine.",
                    sources=[],
                )