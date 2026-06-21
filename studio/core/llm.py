from __future__ import annotations
from typing import Dict, List


MODELS: Dict[str, List[str]] = {
    "anthropic":  ["claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
    "openai":     ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
    "groq":       ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
    "openrouter": ["anthropic/claude-opus-4-8", "openai/gpt-4o", "meta-llama/llama-3.3-70b-instruct"],
}


class LLMClient:
    def __init__(self, provider: str, api_key: str, model: str):
        self.provider = provider
        self.api_key  = api_key
        self.model    = model

    async def complete(self, system: str, user: str, max_tokens: int = 4096) -> str:
        if self.provider == "anthropic":
            return await self._anthropic(system, user, max_tokens)
        if self.provider in ("openai", "groq", "openrouter"):
            return await self._openai_compat(system, user, max_tokens)
        raise ValueError(f"Unknown provider: {self.provider!r}")

    async def _anthropic(self, system: str, user: str, max_tokens: int) -> str:
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("Install anthropic: pip install anthropic")

        client = anthropic.AsyncAnthropic(api_key=self.api_key)
        msg = await client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return msg.content[0].text

    async def _openai_compat(self, system: str, user: str, max_tokens: int) -> str:
        try:
            import openai
        except ImportError:
            raise RuntimeError("Install openai: pip install openai")

        base_urls = {
            "groq":       "https://api.groq.com/openai/v1",
            "openrouter": "https://openrouter.ai/api/v1",
        }
        kwargs = {"api_key": self.api_key}
        if self.provider in base_urls:
            kwargs["base_url"] = base_urls[self.provider]

        client = openai.AsyncOpenAI(**kwargs)
        resp = await client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
        )
        return resp.choices[0].message.content
