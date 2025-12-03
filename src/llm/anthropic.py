import aiohttp
import json
from .provider import LLMProvider
from ..models.verification import VerificationResult
from ..config_manager import LLMConfig

class AnthropicProvider(LLMProvider):
    def __init__(self, config: LLMConfig, system_prompt_path: str):
        self.config = config
        with open(system_prompt_path, "r") as f:
            self.system_prompt = f.read()

    async def analyze_text(self, text: str) -> VerificationResult:
        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        # Anthropic doesn't support JSON mode enforcement natively like OpenAI
        # We append instructions to the user prompt to ensure compliance
        prompt = f"{text}\n\nReturn strictly valid JSON."

        payload = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "system": self.system_prompt,
            "messages": [{"role": "user", "content": prompt}]
        }

        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload) as resp:
                data = await resp.json()
                content = data['content'][0]['text']
                # Simplistic parsing, in prod use a robust json repair tool
                start = content.find('{')
                end = content.rfind('}') + 1
                return VerificationResult(**json.loads(content[start:end]))