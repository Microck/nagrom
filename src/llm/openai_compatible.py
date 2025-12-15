from __future__ import annotations

import json
import logging
import time
import asyncio
from typing import Any, Dict, List, Optional

import aiohttp
from aiohttp import ClientTimeout

from .provider import LLMProvider, SourceLockedProviderMixin
from .search_provider import SearchManager, SearchResult
from ..config_manager import LLMConfig
from ..models.verification import VerificationResult, Source

logger = logging.getLogger(__name__)


class OpenRouterProvider(SourceLockedProviderMixin, LLMProvider):
    
    def __init__(self, config: LLMConfig, system_prompt_path: str, search_manager: Optional[SearchManager] = None):
        self.config = config
        self.search_manager = search_manager
        with open(system_prompt_path, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()

    async def _check_health(self) -> str:
        url = f"{self.config.base_url}/models"
        headers = {"Authorization": f"Bearer {self.config.api_key}"}
        try:
            async with aiohttp.ClientSession(timeout=ClientTimeout(total=5)) as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        return "Endpoint is reachable (GET /models 200 OK)."
                    elif resp.status == 404:
                        return "Endpoint reachable (404 on /models, server is up)."
                    else:
                        return f"Endpoint reachable but returned {resp.status}."
        except asyncio.TimeoutError:
            return "Endpoint check timed out (5s)."
        except Exception as e:
            return f"Endpoint check failed: {str(e)}"

    async def analyze_text(self, text: str) -> VerificationResult:
        logger.info(f"OpenRouterProvider analyzing: {text[:50]}...")
        
        search_results = await self._get_search_results(text)
        sources = self._build_sources_list(search_results)
        
        if not sources:
            logger.warning("No search results, returning UNVERIFIABLE")
            return self._create_no_sources_result(text)
        
        user_prompt = self._build_stateless_prompt(text, sources)
        
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        models_to_try = [self.config.model] + self.config.fallback_models
        models_to_try = list(dict.fromkeys(models_to_try))
        
        logger.debug(f"Models execution plan: {models_to_try}")

        start = time.perf_counter()
        timeout = ClientTimeout(total=120)
        
        last_error = None
        
        for model_name in models_to_try:
            logger.debug(f"Trying model: {model_name}")
            
            payload: Dict[str, Any] = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
            }

            if model_name.lower().startswith(("gpt-", "o1-")):
                payload["response_format"] = {"type": "json_object"}

            max_retries_per_model = 2
            
            for attempt in range(max_retries_per_model):
                try:
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        async with session.post(
                            f"{self.config.base_url}/chat/completions",
                            headers=headers,
                            json=payload,
                        ) as resp:
                            latency = time.perf_counter() - start

                            if resp.status != 200:
                                body = await resp.text()
                                logger.error(f"LLM HTTP error {resp.status} ({latency:.3f}s): {body[:200]}")
                                
                                if resp.status >= 500 or resp.status == 429:
                                    last_error = f"Provider Error {resp.status} ({model_name}): {body[:200]}"
                                    await asyncio.sleep(2)
                                    continue
                                else:
                                    last_error = f"Client Error {resp.status} ({model_name}): {body[:200]}"
                                    break

                            body_text = await resp.text()
                            try:
                                data = json.loads(body_text)
                            except json.JSONDecodeError:
                                logger.error(f"Invalid JSON from API: {body_text}")
                                last_error = f"API returned invalid JSON ({model_name}): {body_text[:100]}..."
                                await asyncio.sleep(2)
                                continue

                            if "choices" not in data or not data["choices"]:
                                last_error = f"API response missing 'choices' ({model_name}): {body_text[:100]}..."
                                await asyncio.sleep(2)
                                continue
                                 
                            content = data["choices"][0]["message"]["content"]
                            
                            if isinstance(content, dict):
                                parsed = content
                                if "statement" not in parsed:
                                    parsed["statement"] = text[:500]
                            else:
                                parsed = self._parse_llm_response(content, text)
                            
                            result = self._validate_and_finalize(parsed, text, sources)
                            result.model_name = model_name
                            
                            if "usage" in data:
                                result.usage = {
                                    "input_tokens": data["usage"].get("prompt_tokens", 0),
                                    "output_tokens": data["usage"].get("completion_tokens", 0)
                                }
                            
                            logger.info(
                                "LLM success with %s in %.3fs | verdict=%s conf=%.3f valid=%s",
                                model_name, latency, result.verdict, result.confidence, result.validation_passed
                            )
                            return result

                except Exception as exc:
                    latency = time.perf_counter() - start
                    logger.exception("LLM exception attempt %d for %s: %s", attempt+1, model_name, exc)
                    last_error = f"Internal error ({model_name}): {str(exc)}"
                    await asyncio.sleep(2)
        
        health_status = await self._check_health()
        
        return VerificationResult(
            statement=text[:500],
            verdict="UNVERIFIABLE",
            confidence=0.0,
            reasoning=f"Failed after trying models {models_to_try}. Last error: {last_error}\n\nDiagnostic: {health_status}",
            sources=sources,
            model_name=self.config.model,
        )
