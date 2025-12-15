from __future__ import annotations

import logging
import time
from typing import List, Optional

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from .provider import LLMProvider, SourceLockedProviderMixin
from .search_provider import SearchManager, SearchResult
from ..config_manager import LLMConfig
from ..models.verification import VerificationResult, Source

logger = logging.getLogger(__name__)


class GoogleAIStudioProvider(SourceLockedProviderMixin, LLMProvider):
    
    def __init__(self, config: LLMConfig, system_prompt_path: str, search_manager: Optional[SearchManager] = None):
        self.config = config
        self.search_manager = search_manager
        with open(system_prompt_path, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()
        
        configure_kwargs = {"api_key": config.api_key}
        if config.base_url:
            configure_kwargs["client_options"] = {"api_endpoint": config.base_url}
            configure_kwargs["transport"] = "rest"
            logger.info(f"Using custom Google AI Studio endpoint: {config.base_url}")
        
        genai.configure(**configure_kwargs)
        
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

        self.model = genai.GenerativeModel(
            model_name=config.model,
            generation_config={
                "temperature": config.temperature,
                "max_output_tokens": config.max_tokens,
                "response_mime_type": "application/json",
            },
            safety_settings=self.safety_settings
        )

    async def analyze_text(self, text: str) -> VerificationResult:
        logger.info(f"GoogleAIStudioProvider analyzing: {text[:50]}...")
        
        search_results = await self._get_search_results(text)
        sources = self._build_sources_list(search_results)
        
        if not sources:
            logger.warning("No search results, returning UNVERIFIABLE")
            return self._create_no_sources_result(text)
        
        user_prompt = self._build_stateless_prompt(text, sources)
        full_prompt = f"{self.system_prompt}\n\n{user_prompt}"
        
        start = time.perf_counter()
        
        try:
            response = await self.model.generate_content_async(full_prompt)
            
            if not response.parts:
                finish_reason = "UNKNOWN"
                if response.candidates:
                    finish_reason = str(response.candidates[0].finish_reason)
                
                logger.warning(f"Google blocked response. Finish Reason: {finish_reason}")
                return VerificationResult(
                    statement=text[:500],
                    verdict="UNVERIFIABLE",
                    confidence=0.0,
                    reasoning=f"Content blocked or empty (Reason: {finish_reason}).",
                    sources=sources,
                    model_name=self.config.model,
                )

            content = response.text
            parsed = self._parse_llm_response(content, text)
            result = self._validate_and_finalize(parsed, text, sources)
            
            if response.usage_metadata:
                result.usage = {
                    "input_tokens": response.usage_metadata.prompt_token_count,
                    "output_tokens": response.usage_metadata.candidates_token_count
                }
            
            latency = time.perf_counter() - start
            logger.info(
                "Google AI Studio success in %.3fs | verdict=%s conf=%.3f valid=%s",
                latency, result.verdict, result.confidence, result.validation_passed
            )
            return result
            
        except Exception as exc:
            latency = time.perf_counter() - start
            logger.exception("Google AI Studio exception after %.3fs: %s", latency, exc)
            return self._create_error_result(text, str(exc), sources)
