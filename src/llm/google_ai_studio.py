from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict

import aiohttp
import google.generativeai as genai

from .provider import LLMProvider
from ..config_manager import LLMConfig
from ..models.verification import VerificationResult

logger = logging.getLogger(__name__)


class GoogleAIStudioProvider(LLMProvider):
    def __init__(self, config: LLMConfig, system_prompt_path: str):
        self.config = config
        with open(system_prompt_path, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()
        
        # Initialize Google AI Studio
        genai.configure(api_key=config.api_key)
        
        # Use the model specified in config
        self.model = genai.GenerativeModel(
            model_name=config.model,
            generation_config={
                "temperature": config.temperature,
                "max_output_tokens": config.max_tokens,
                "response_mime_type": "application/json",
            }
        )

    async def analyze_text(self, text: str) -> VerificationResult:
        start = time.perf_counter()
        
        try:
            # Combine system prompt with user input
            full_prompt = f"{self.system_prompt}\n\nUser input: {text}"
            
            # Generate response
            response = await self.model.generate_content_async(full_prompt)
            content = response.text
            
            # Parse JSON response
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON from response if there's extra text
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    parsed = json.loads(content[start_idx:end_idx])
                else:
                    raise ValueError("Could not parse JSON from response")
            
            result = VerificationResult(**parsed)
            latency = time.perf_counter() - start
            
            logger.info(
                "Google AI Studio success in %.3fs | verdict=%s conf=%.3f",
                latency,
                result.verdict,
                result.confidence,
            )
            return result
            
        except Exception as exc:
            latency = time.perf_counter() - start
            logger.exception("Google AI Studio exception after %.3fs: %s", latency, exc)
            return VerificationResult(
                statement=text[:500],
                verdict="unverifiable",
                confidence=0.0,
                reasoning="Internal error while contacting the Google AI Studio verification engine.",
                sources=[],
            )