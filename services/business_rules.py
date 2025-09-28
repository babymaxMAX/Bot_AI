from __future__ import annotations

import pathlib
from typing import Optional


class BusinessRules:
    def __init__(self) -> None:
        self._base = pathlib.Path(__file__).parent.parent / "system_prompts"
        self._prompt_file = self._base / "dating_ru.txt"

    async def build_system_prompt(self, user_id: str, *, profile_context: Optional[str] = None, match_context: Optional[str] = None) -> str:
        try:
            base = self._prompt_file.read_text(encoding="utf-8")
        except FileNotFoundError:
            base = (
                "Ты — виртуальный собеседник, помогающий знакомиться. Пиши естественно, дружелюбно, "
                "поддерживай диалог, задавай уместные вопросы, соблюдай безопасность и уважение."
            )
        extra = []
        if profile_context:
            extra.append("Контекст профиля пользователя:\n" + profile_context.strip())
        if match_context:
            extra.append("Контекст активного матча:\n" + match_context.strip())
        if extra:
            base = base.rstrip() + "\n\n" + "\n\n".join(extra)
        return base
