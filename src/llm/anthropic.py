from __future__ import annotations

import logging
from typing import List, Optional

import aiohttp

from .provider import LLMProvider, SourceLockedProviderMixin
from .search_provider import SearchManager, SearchResult
from ..config_manager import LLMConfig
from ..models.verification import VerificationResult, Source

logger = logging.getLogger(__name__)


class AnthropicProvider(SourceLockedProviderMixin, LLMProvider):
    
    def __init__(self, config: LLMConfig, system_prompt_path: str, search_manager: Optional[SearchManager] = None):
        self.config = config
        self.search_manager = search_manager
        with open(system_prompt_path, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()

    async def analyze_text(self, text: str) -> VerificationResult:
        logger.info(f"AnthropicProvider analyzing: {text[:50]}...")
        
        search_results = await self._get_search_results(text)
        sources = self._build_sources_list(search_results)
        
        if not sources:
            logger.warning("No search results, returning UNVERIFIABLE")
            return self._create_no_sources_result(text)
        
        user_prompt = self._build_stateless_prompt(text, sources)
        
        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        payload = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "system": self.system_prompt,
            "messages": [{"role": "user", "content": user_prompt}]
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=payload
                ) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        logger.error(f"Anthropic API error {resp.status}: {body[:200]}")
                        return self._create_error_result(text, f"API error {resp.status}", sources)
                    
                    data = await resp.json()
                    content = data['content'][0]['text']
                    
                    parsed = self._parse_llm_response(content, text)
                    result = self._validate_and_finalize(parsed, text, sources)
                    
                    logger.info(
                        "Anthropic success | verdict=%s conf=%.3f valid=%s",
                        result.verdict, result.confidence, result.validation_passed
                    )
                    return result
                    
        except Exception as exc:
            logger.exception(f"Anthropic call failed: {exc}")
            return self._create_error_result(text, str(exc), sources)
