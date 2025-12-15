from __future__ import annotations

import asyncio
import logging
from typing import List, Optional

from .provider import LLMProvider, SourceLockedProviderMixin
from .search_provider import SearchManager, SearchResult
from ..config_manager import LLMConfig
from ..models.verification import VerificationResult, Source

logger = logging.getLogger(__name__)


class OpenAISDKProvider(SourceLockedProviderMixin, LLMProvider):
    
    def __init__(self, config: LLMConfig, system_prompt_path: str, search_manager: Optional[SearchManager] = None):
        self.config = config
        self.search_manager = search_manager
        self._client = None
        with open(system_prompt_path, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()
    
    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
            )
        return self._client
    
    async def analyze_text(self, text: str) -> VerificationResult:
        logger.info(f"OpenAISDKProvider analyzing: {text[:50]}...")
        logger.info(f"Base URL: {self.config.base_url}")
        logger.info(f"Model: {self.config.model}")
        
        search_results = await self._get_search_results(text)
        sources = self._build_sources_list(search_results)
        
        if not sources:
            logger.warning("No search results, returning UNVERIFIABLE")
            return self._create_no_sources_result(text)
        
        user_prompt = self._build_stateless_prompt(text, sources)
        
        def _sync_completion():
            return self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, _sync_completion)
            
            content = response.choices[0].message.content
            parsed = self._parse_llm_response(content, text)
            result = self._validate_and_finalize(parsed, text, sources)
            
            logger.info(f"LLM success: verdict={result.verdict} conf={result.confidence} valid={result.validation_passed}")
            return result
            
        except Exception as exc:
            logger.exception(f"OpenAI SDK call failed: {exc}")
            return self._create_error_result(text, str(exc), sources)
