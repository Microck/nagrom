from __future__ import annotations

import logging
import os
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
from dataclasses import dataclass

import aiohttp
from aiohttp import ClientTimeout

logger = logging.getLogger(__name__)

SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "auto").lower()
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
TAVILY_BASE_URL = os.getenv("TAVILY_BASE_URL", "https://api.tavily.com")
TAVILY_MAX_RESULTS = int(os.getenv("TAVILY_MAX_RESULTS", "5"))
TAVILY_SEARCH_DEPTH = os.getenv("TAVILY_SEARCH_DEPTH", "basic")


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    raw_content: Optional[str] = None
    score: float = 0.0


class SearchProvider(ABC):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
    
    @abstractmethod
    async def search(self, query: str) -> List[SearchResult]:
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        pass


class DuckDuckGoSearchProvider(SearchProvider):
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._available = None
    
    def _check_availability(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            from duckduckgo_search import DDGS
            self._available = True
        except ImportError:
            logger.warning(
                "DuckDuckGo search requested but 'duckduckgo-search' package not installed. "
                "Install with: pip install duckduckgo-search"
            )
            self._available = False
        return self._available
    
    async def search(self, query: str) -> List[SearchResult]:
        if not self._check_availability():
            return []
        
        try:
            from duckduckgo_search import DDGS
            import asyncio
            loop = asyncio.get_event_loop()
            
            def _sync_search():
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=5))
                    return [
                        SearchResult(
                            title=r.get("title", ""),
                            url=r.get("href", ""),
                            snippet=r.get("body", ""),
                        )
                        for r in results
                    ]
            
            return await loop.run_in_executor(None, _sync_search)
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            return []
    
    def is_configured(self) -> bool:
        return self._check_availability()


class TavilySearchProvider(SearchProvider):
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.api_key = self.config.get('api_key') or TAVILY_API_KEY
        self.base_url = self.config.get('base_url') or TAVILY_BASE_URL
        self.max_results = self.config.get('max_results') or TAVILY_MAX_RESULTS
        self.search_depth = self.config.get('search_depth') or TAVILY_SEARCH_DEPTH
    
    def _detect_time_sensitivity(self, query: str) -> tuple:
        time_keywords = [
            "today", "yesterday", "this week", "this month", "breaking",
            "latest", "recent", "just", "now", "current", "2024", "2025",
            "price", "stock", "market", "election", "announced"
        ]
        query_lower = query.lower()
        
        is_sensitive = any(kw in query_lower for kw in time_keywords)
        time_range = "day" if any(w in query_lower for w in ["today", "yesterday", "just", "breaking"]) \
                     else ("week" if is_sensitive else None)
        
        return is_sensitive, time_range
    
    async def _tavily_request(
        self,
        query: str,
        max_results: int,
        include_raw_content: bool = False,
        topic: Optional[str] = None,
        time_range: Optional[str] = None,
    ) -> List[SearchResult]:
        if not self.api_key:
            logger.error("Tavily API key not configured")
            return []
        
        payload: Dict[str, Any] = {
            "query": query,
            "search_depth": self.search_depth,
            "max_results": max_results,
            "include_answer": False,
            "include_raw_content": include_raw_content,
        }
        
        if topic:
            payload["topic"] = topic
        if time_range:
            payload["time_range"] = time_range
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        try:
            timeout = ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self.base_url}/search",
                    headers=headers,
                    json=payload,
                ) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        logger.error(f"Tavily API error {resp.status}: {body[:200]}")
                        return []
                    
                    data = await resp.json()
                    return [
                        SearchResult(
                            title=r.get("title", ""),
                            url=r.get("url", ""),
                            snippet=r.get("content", ""),
                            raw_content=r.get("raw_content"),
                            score=r.get("score", 0),
                        )
                        for r in data.get("results", [])
                    ]
        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
            return []
    
    async def search(self, query: str) -> List[SearchResult]:
        is_time_sensitive, time_range = self._detect_time_sensitivity(query)
        topic = "news" if is_time_sensitive else None
        return await self._tavily_request(
            query=query,
            max_results=self.max_results,
            include_raw_content=False,
            topic=topic,
            time_range=time_range,
        )
    
    def is_configured(self) -> bool:
        return bool(self.api_key)


def create_search_provider(config: Optional[Dict[str, Any]] = None) -> Optional[SearchProvider]:
    config = config or {}
    provider_type = config.get('provider') or SEARCH_PROVIDER
    api_key = config.get('api_key') or TAVILY_API_KEY
    
    if provider_type == "tavily":
        provider = TavilySearchProvider(config)
        if provider.is_configured():
            logger.info("Search provider: Tavily")
            return provider
        logger.error("SEARCH_PROVIDER=tavily but TAVILY_API_KEY not set")
        return None
    
    elif provider_type == "ddg":
        provider = DuckDuckGoSearchProvider(config)
        if provider.is_configured():
            logger.info("Search provider: DuckDuckGo")
            return provider
        if api_key:
            logger.info("DDG not available, falling back to Tavily")
            return TavilySearchProvider(config)
        logger.warning("DDG not available and no Tavily fallback configured")
        return None
    
    else:
        if api_key:
            logger.info("Search provider: Tavily (auto)")
            return TavilySearchProvider(config)
        ddg = DuckDuckGoSearchProvider(config)
        if ddg.is_configured():
            logger.info("Search provider: DuckDuckGo (auto)")
            return ddg
        logger.info("No search provider available")
        return None


class SearchManager:
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._provider: Optional[SearchProvider] = None
        self._initialize_provider()
    
    def _initialize_provider(self):
        search_config = self.config.get('search', self.config)
        
        provider_config = {
            'provider': search_config.get('provider') or SEARCH_PROVIDER,
            'api_key': search_config.get('tavily_api_key') or TAVILY_API_KEY,
            'base_url': TAVILY_BASE_URL,
            'max_results': search_config.get('tavily_max_results') or TAVILY_MAX_RESULTS,
            'search_depth': TAVILY_SEARCH_DEPTH,
        }
        
        self._provider = create_search_provider(provider_config)
    
    @property
    def provider(self) -> Optional[SearchProvider]:
        return self._provider
    
    async def search(self, query: str) -> List[SearchResult]:
        if not self._provider:
            logger.warning("No search provider available")
            return []
        
        if not self._provider.is_configured():
            logger.warning("Search provider not configured")
            return []
        
        return await self._provider.search(query)
    
    def get_available_providers(self) -> List[str]:
        providers = []
        if self._provider:
            if isinstance(self._provider, TavilySearchProvider):
                providers.append("tavily")
            elif isinstance(self._provider, DuckDuckGoSearchProvider):
                providers.append("duckduckgo")
        return providers
    
    def is_available(self) -> bool:
        return self._provider is not None and self._provider.is_configured()
