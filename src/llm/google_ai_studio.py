from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict

import google.generativeai as genai
# Import types for safety and tools
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.ai.generativelanguage_v1beta.types import content as content_types

from .provider import LLMProvider
from ..config_manager import LLMConfig
from ..models.verification import VerificationResult

logger = logging.getLogger(__name__)

class GoogleAIStudioProvider(LLMProvider):
    def __init__(self, config: LLMConfig, system_prompt_path: str):
        self.config = config
        with open(system_prompt_path, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()
        
        genai.configure(api_key=config.api_key)
        
        # 1. Safety Settings (Permissive for fact-checking)
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

        # 2. ENABLE SEARCH (The Fix)
        # We use the explicit dictionary key 'google_search_retrieval'
        # which maps correctly in the Python SDK.
        tools = [
            {"google_search_retrieval": {}}
        ]

        self.model = genai.GenerativeModel(
            model_name=config.model,
            tools=tools,
            generation_config={
                "temperature": config.temperature,
                "max_output_tokens": config.max_tokens,
                "response_mime_type": "application/json",
            },
            safety_settings=self.safety_settings
        )

    async def analyze_text(self, text: str) -> VerificationResult:
        start = time.perf_counter()
        
        try:
            full_prompt = f"{self.system_prompt}\n\nUser input: {text}"
            
            # Generate content
            response = await self.model.generate_content_async(full_prompt)
            
            # Handle blocked/empty responses
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
                    sources=[]
                )

            # Extract text
            content = response.text
            
            # Parse JSON
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    parsed = json.loads(content[start_idx:end_idx])
                else:
                    raise ValueError("Could not parse JSON from response")
            
            # Data Normalization
            if "verdict" in parsed and isinstance(parsed["verdict"], str):
                parsed["verdict"] = parsed["verdict"].upper()
            if "statement" not in parsed:
                parsed["statement"] = text[:500]

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
                verdict="UNVERIFIABLE",
                confidence=0.0,
                reasoning=f"Internal error: {str(exc)}",
                sources=[],
            )