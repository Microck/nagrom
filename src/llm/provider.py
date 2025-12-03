from abc import ABC, abstractmethod
from ..models.verification import VerificationResult

class LLMProvider(ABC):
    @abstractmethod
    async def analyze_text(self, text: str) -> VerificationResult:
        pass