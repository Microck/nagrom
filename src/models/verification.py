from __future__ import annotations

import re
from typing import List, Literal, Optional, Set
from pydantic import BaseModel, Field


class Source(BaseModel):
    name: str
    url: Optional[str] = None
    tier: Optional[int] = None
    snippet: Optional[str] = None
    raw_content: Optional[str] = None


class VerificationResult(BaseModel):
    statement: Optional[str] = None
    verdict: Literal["TRUE", "FALSE", "MIXED", "UNVERIFIABLE"] = "UNVERIFIABLE"
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    reasoning: str = ""
    sources: List[Source] = Field(default_factory=list)
    model_name: Optional[str] = None
    usage: Optional[dict] = None
    
    validation_passed: bool = True
    validation_errors: List[str] = Field(default_factory=list)


class ResponseValidator:
    """
    Validates LLM response against source-locked constraints.
    
    Rules:
    1. JSON must parse correctly
    2. Reasoning must contain citation tags [N] referencing provided sources
    3. If validation fails, return UNVERIFIABLE with low confidence
    """
    
    CITATION_PATTERN = re.compile(r'\[(\d+)\]')
    
    def __init__(self, provided_sources: List[Source]):
        self.provided_sources = provided_sources
        self.valid_urls: Set[str] = {s.url for s in provided_sources if s.url}
        self.source_count = len(provided_sources)
    
    def validate(self, result: VerificationResult) -> VerificationResult:
        errors: List[str] = []
        
        if self.source_count == 0:
            if result.verdict.upper() not in ("UNVERIFIABLE", "MIXED"):
                errors.append("No sources provided but verdict claims certainty")
        
        if result.reasoning:
            citations_found = self.CITATION_PATTERN.findall(result.reasoning)
            
            if self.source_count > 0 and not citations_found:
                errors.append("Reasoning contains no citation tags [N]")
            
            for cite_idx in citations_found:
                idx = int(cite_idx)
                if idx < 1 or idx > self.source_count:
                    errors.append(f"Citation [{cite_idx}] out of range (have {self.source_count} sources)")
        
        if errors:
            return VerificationResult(
                statement=result.statement,
                verdict="UNVERIFIABLE",
                confidence=0.15,
                reasoning=f"Validation failed: {'; '.join(errors)}. Original: {result.reasoning[:200]}",
                sources=result.sources,
                model_name=result.model_name,
                validation_passed=False,
                validation_errors=errors,
            )
        
        result.validation_passed = True
        result.validation_errors = []
        return result
