from __future__ import annotations

from openai import AsyncOpenAI


class AIClient:
    def __init__(self, provider: str = "openai", openai_api_key: str | None = None) -> None:
        self._provider = provider
        self._openai = None
        if provider == "openai":
            self._openai = AsyncOpenAI(api_key=openai_api_key)

    async def generate_reply(self, system_prompt: str, history: list[dict[str, str]]) -> str:
        if self._provider == "openai" and self._openai:
            messages = [{"role": "system", "content": system_prompt}] + history
            resp = await self._openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                max_tokens=400,
            )
            return resp.choices[0].message.content or ""
        return "Извините, ИИ временно недоступен."
