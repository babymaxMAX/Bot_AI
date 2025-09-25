from __future__ import annotations

import os
import random
import asyncio
from typing import List, Dict

from openai import AsyncOpenAI
from openai import RateLimitError, APIError, APITimeoutError


# Глобальный лимит одновременных запросов к OpenAI (по умолчанию 1)
_CONCURRENCY = int(os.getenv("OPENAI_CONCURRENCY", "1"))
_semaphore = asyncio.Semaphore(max(1, _CONCURRENCY))


class AIClient:
    def __init__(self, provider: str = "openai", openai_api_key: str | None = None) -> None:
        self._provider = provider
        self._openai = None
        if provider == "openai":
            # таймауты, чтобы не зависать
            self._openai = AsyncOpenAI(api_key=openai_api_key, timeout=25.0)

    async def _call_openai(self, messages: List[Dict[str, str]]) -> str:
        assert self._openai is not None
        # до 3 попыток с экспоненциальным бэкофом
        for attempt in range(3):
            try:
                async with _semaphore:
                    resp = await self._openai.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=messages,
                        temperature=0.7,
                        max_tokens=400,
                    )
                return resp.choices[0].message.content or ""
            except RateLimitError as e:
                # ждём и пробуем снова
                wait = 2 * (2 ** attempt) + random.uniform(0, 1.0)
                await asyncio.sleep(wait)
                continue
            except (APITimeoutError, APIError) as e:
                # краткий бэкоф и повтор
                wait = 1.5 * (2 ** attempt) + random.uniform(0, 0.5)
                await asyncio.sleep(wait)
                continue
            except Exception:
                break
        return "Немного перегружен запросами, давай продолжим через пару секунд?"

    async def generate_reply(self, system_prompt: str, history: List[Dict[str, str]]) -> str:
        if self._provider != "openai" or self._openai is None:
            return "Извините, ИИ временно недоступен."
        messages = [{"role": "system", "content": system_prompt}] + history
        try:
            return await self._call_openai(messages)
        except Exception:
            return "Короткая пауза на моей стороне. Напиши ещё раз, пожалуйста."
