from typing import List, Literal
from pydantic import BaseModel, Field

class VerificationResult(BaseModel):
    verdict: Literal["TRUE", "FALSE", "MIXED", "UNVERIFIABLE"]
    confidence: int = Field(ge=0, le=100)
    reasoning: str
    sources: List[str]