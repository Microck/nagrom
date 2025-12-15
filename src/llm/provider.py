from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .search_provider import SearchManager, SearchResult
    from ..config_manager import LLMConfig

from ..models.verification import (
    VerificationResult,
    Source,
    ResponseValidator,
)

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    @abstractmethod
    async def analyze_text(self, text: str) -> VerificationResult:
        pass


class SourceLockedProviderMixin:
    
    search_manager: Optional["SearchManager"]
    config: "LLMConfig"
    system_prompt: str
    
    TIER_1_DOMAINS = {
        # US IFCN-Certified
        "politifact.com", "factcheck.org", "reuters.com", "apnews.com",
        "leadstories.com", "washingtonpost.com", "checkyourfact.com", "snopes.com",
        "poynter.org", "wisconsinwatch.org", "univision.com", "telemundo.com",
        # International IFCN-Certified
        "factcheck.afp.com", "fullfact.org", "sciencefeedback.co", "africacheck.org",
        "dw.com", "correctiv.org", "maldita.es", "chequeado.com",
        "aosfatos.org", "lupa.news", "pesacheck.org", "stopfake.org",
        "voxukraine.org", "rappler.com", "thejournal.ie", "poligrafo.sapo.pt",
        "newtral.es", "faktisk.no", "ellinikahoaxes.gr", "teyit.org",
        "tfc-taiwan.org.tw", "factcheckcenter.jp",
    }
    TIER_2_DOMAINS = {
        "who.int", "arxiv.org", "nasa.gov", "cdc.gov", "nih.gov", "europa.eu",
        "whitehouse.gov", "congress.gov", "supremecourt.gov"
    }
    TIER_2_SUFFIXES = (".gov", ".edu", ".eu")
    TIER_3_DOMAINS = {
        "bbc.com", "bbc.co.uk", "nytimes.com", "wsj.com", "bloomberg.com",
        "aljazeera.com", "theguardian.com", "npr.org",
        # Source evaluators (not fact-checkers)
        "mediabiasfactcheck.com", "allsides.com", "adfontesmedia.com", "ground.news"
    }
    TIER_4_DOMAINS = {
        "wikipedia.org", "reddit.com", "twitter.com", "x.com", "medium.com",
        "quora.com", "facebook.com", "instagram.com", "tiktok.com", "youtube.com"
    }
    
    DOMAIN_TO_NAME = {
        # Tier 1 - US
        "snopes.com": "Snopes",
        "politifact.com": "PolitiFact",
        "factcheck.org": "FactCheck.org",
        "reuters.com": "Reuters",
        "apnews.com": "AP News",
        "leadstories.com": "Lead Stories",
        "washingtonpost.com": "Washington Post",
        "checkyourfact.com": "Check Your Fact",
        "poynter.org": "MediaWise",
        "wisconsinwatch.org": "Wisconsin Watch",
        "univision.com": "El Detector",
        "telemundo.com": "T Verifica",
        # Tier 1 - International
        "factcheck.afp.com": "AFP Fact Check",
        "fullfact.org": "Full Fact",
        "sciencefeedback.co": "Science Feedback",
        "africacheck.org": "Africa Check",
        "dw.com": "DW Fact Check",
        "correctiv.org": "Correctiv",
        "maldita.es": "Maldita.es",
        "chequeado.com": "Chequeado",
        "aosfatos.org": "Aos Fatos",
        "lupa.news": "Lupa",
        "pesacheck.org": "PesaCheck",
        "stopfake.org": "StopFake",
        "voxukraine.org": "VoxUkraine",
        "rappler.com": "Rappler",
        "thejournal.ie": "TheJournal FactCheck",
        "poligrafo.sapo.pt": "Poligrafo",
        "newtral.es": "Newtral",
        "faktisk.no": "Faktisk",
        "ellinikahoaxes.gr": "Ellinika Hoaxes",
        "teyit.org": "Teyit",
        "tfc-taiwan.org.tw": "Taiwan FactCheck",
        "factcheckcenter.jp": "Japan Fact-Check",
        # Tier 3
        "bbc.com": "BBC",
        "bbc.co.uk": "BBC",
        "nytimes.com": "NY Times",
        "wsj.com": "WSJ",
        "bloomberg.com": "Bloomberg",
        "aljazeera.com": "Al Jazeera",
        "theguardian.com": "The Guardian",
        "npr.org": "NPR",
        "mediabiasfactcheck.com": "MBFC",
        "allsides.com": "AllSides",
        "adfontesmedia.com": "Ad Fontes",
        "ground.news": "Ground News",
        # Tier 4
        "wikipedia.org": "Wikipedia",
        "reddit.com": "Reddit",
        "twitter.com": "Twitter",
        "x.com": "X",
        "medium.com": "Medium",
        "quora.com": "Quora",
        "youtube.com": "YouTube",
        # Tier 2
        "who.int": "WHO",
        "arxiv.org": "arXiv",
        "nasa.gov": "NASA",
        "cdc.gov": "CDC",
        "nih.gov": "NIH",
    }
    
    def _classify_tier(self, url: str) -> int:
        if not url:
            return 4
        
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.lower().replace("www.", "")
        except Exception:
            return 4
        
        for t1 in self.TIER_1_DOMAINS:
            if t1 in domain:
                return 1
        
        for t2 in self.TIER_2_DOMAINS:
            if t2 in domain:
                return 2
        if any(domain.endswith(suffix) for suffix in self.TIER_2_SUFFIXES):
            return 2
        
        for t3 in self.TIER_3_DOMAINS:
            if t3 in domain:
                return 3
        
        for t4 in self.TIER_4_DOMAINS:
            if t4 in domain:
                return 4
        
        return 3
    
    def _extract_source_name(self, url: str, title: str) -> str:
        if not url:
            return title or "Unknown"
        
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.lower().replace("www.", "")
        except Exception:
            return title or "Unknown"
        
        for key, name in self.DOMAIN_TO_NAME.items():
            if key in domain:
                return name
        
        parts = domain.split(".")
        if len(parts) >= 2:
            return parts[-2].capitalize()
        
        return domain.capitalize()
    
    def _build_sources_list(self, search_results: List["SearchResult"]) -> List[Source]:
        return [
            Source(
                name=self._extract_source_name(r.url, r.title),
                url=r.url,
                tier=self._classify_tier(r.url),
                snippet=r.snippet,
                raw_content=r.raw_content,
            )
            for r in search_results
        ]
    
    def _build_stateless_prompt(self, claim: str, sources: List[Source]) -> str:
        source_block = self._format_sources_for_prompt(sources)
        
        return f"""CLAIM TO VERIFY:
{claim}

SOURCES (use [N] citation tags to reference these):
<source_data>
{source_block}
</source_data>

Verify the claim using the sources above. Output valid JSON."""
    
    def _format_sources_for_prompt(self, sources: List[Source]) -> str:
        if not sources:
            return "No sources available. Mark as unverifiable."
        
        lines = []
        for i, src in enumerate(sources, 1):
            content = src.raw_content if src.raw_content else src.snippet
            content_preview = content[:1500] if content else "No content"
            # XML-escape content to prevent tag injection (basic)
            content_preview = content_preview.replace("<", "&lt;").replace(">", "&gt;")
            lines.append(f'<source id="{i}">\n<name>{src.name}</name>\n<url>{src.url}</url>\n<content>{content_preview}</content>\n</source>')
        
        return "\n".join(lines)
    
    async def _get_search_results(self, text: str) -> List["SearchResult"]:
        if not self.search_manager:
            logger.warning("No search_manager available")
            return []
        
        try:
            results = await self.search_manager.search(text[:200])
            logger.info(f"Search returned {len(results)} results")
            return results
        except Exception as e:
            logger.warning(f"Search failed: {e}")
            return []
    
    def _create_no_sources_result(self, text: str) -> VerificationResult:
        return VerificationResult(
            statement=text[:500],
            verdict="UNVERIFIABLE",
            confidence=0.1,
            reasoning="No sources available to verify this claim.",
            sources=[],
            model_name=getattr(self.config, 'model', 'unknown'),
        )
    
    def _create_error_result(self, text: str, error: str, sources: List[Source]) -> VerificationResult:
        return VerificationResult(
            statement=text[:500],
            verdict="UNVERIFIABLE",
            confidence=0.0,
            reasoning=f"Analysis failed: {error}",
            sources=sources,
            model_name=getattr(self.config, 'model', 'unknown'),
        )
    
    def _parse_llm_response(self, content: str, original_text: str) -> Dict[str, Any]:
        content_str = content.strip()
        
        if content_str.startswith("```json"):
            content_str = content_str[7:]
        elif content_str.startswith("```"):
            content_str = content_str[3:]
        
        if content_str.endswith("```"):
            content_str = content_str[:-3]
        
        content_str = content_str.strip()
        
        try:
            parsed = json.loads(content_str)
        except json.JSONDecodeError:
            start_idx = content_str.find('{')
            end_idx = content_str.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                json_candidate = content_str[start_idx:end_idx]
                try:
                    parsed = json.loads(json_candidate)
                except json.JSONDecodeError:
                    # Attempt to fix common JSON issues from LLM output
                    parsed = self._attempt_json_repair(json_candidate)
                    if parsed is None:
                        return self._fallback_parse_result()
            else:
                return self._fallback_parse_result()
        
        if "verdict" in parsed and isinstance(parsed["verdict"], str):
            v = parsed["verdict"].upper()
            if v not in ("TRUE", "FALSE", "MIXED", "UNVERIFIABLE"):
                v = "UNVERIFIABLE"
            parsed["verdict"] = v
        else:
            parsed["verdict"] = "UNVERIFIABLE"
        
        if "confidence" in parsed:
            conf = parsed["confidence"]
            if isinstance(conf, (int, float)):
                if isinstance(conf, int) and conf > 1:
                    conf = conf / 100.0
                parsed["confidence"] = max(0.0, min(1.0, float(conf)))
            else:
                parsed["confidence"] = 0.0
        else:
            parsed["confidence"] = 0.0
        
        if "reasoning" not in parsed or not isinstance(parsed["reasoning"], str):
            parsed["reasoning"] = "No reasoning provided."
        
        if "statement" not in parsed:
            parsed["statement"] = original_text[:500]
        
        if "sources" in parsed and isinstance(parsed["sources"], list):
            normalized = []
            for src in parsed["sources"]:
                if isinstance(src, str):
                    normalized.append({"name": src})
                elif isinstance(src, dict):
                    if "name" not in src:
                        src["name"] = "Unknown"
                    normalized.append(src)
            parsed["sources"] = normalized
        else:
            parsed["sources"] = []
        
        return parsed
    
    def _attempt_json_repair(self, json_str: str) -> Optional[Dict[str, Any]]:
        import re
        
        repaired = json_str
        
        repaired = re.sub(r'(?<!\\)"([^"]*?)(?<!\\)"(?=\s*[:,}\]])', 
                          lambda m: '"' + m.group(1).replace('"', '\\"') + '"', 
                          repaired)
        
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass
        
        try:
            repaired = re.sub(r',\s*}', '}', json_str)
            repaired = re.sub(r',\s*]', ']', repaired)
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass
        
        try:
            verdict_match = re.search(r'"verdict"\s*:\s*"([^"]*)"', json_str, re.IGNORECASE)
            conf_match = re.search(r'"confidence"\s*:\s*([0-9.]+)', json_str)
            reasoning_match = re.search(r'"reasoning"\s*:\s*"((?:[^"\\]|\\.)*)"', json_str)
            
            if verdict_match:
                return {
                    "verdict": verdict_match.group(1).upper(),
                    "confidence": float(conf_match.group(1)) if conf_match else 0.5,
                    "reasoning": reasoning_match.group(1) if reasoning_match else "Extracted from malformed response.",
                    "sources": [],
                }
        except Exception:
            pass
        
        return None
    
    def _fallback_parse_result(self) -> Dict[str, Any]:
        return {
            "verdict": "UNVERIFIABLE",
            "confidence": 0.1,
            "reasoning": "Failed to parse LLM response as JSON.",
            "sources": [],
        }
    
    def _validate_and_finalize(
        self,
        parsed: Dict[str, Any],
        text: str,
        sources: List[Source],
    ) -> VerificationResult:
        result = VerificationResult(
            statement=parsed.get("statement", text[:500]),
            verdict=parsed.get("verdict", "UNVERIFIABLE"),
            confidence=parsed.get("confidence", 0.0),
            reasoning=parsed.get("reasoning", ""),
            sources=sources,
            model_name=getattr(self.config, 'model', 'unknown'),
        )
        
        validator = ResponseValidator(sources)
        return validator.validate(result)
