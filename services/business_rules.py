from __future__ import annotations

import pathlib


class BusinessRules:
    def __init__(self) -> None:
        # промпт лежит в корне в папке system_prompts
        self._base = pathlib.Path(__file__).parent.parent / "system_prompts"
        self._prompt_file = self._base / "dating_ru.txt"

    async def build_system_prompt(self, user_id: str) -> str:
        try:
            return self._prompt_file.read_text(encoding="utf-8")
        except FileNotFoundError:
            return (
                "Ты — виртуальный собеседник, помогающий знакомиться. Пиши естественно, дружелюбно, "
                "поддерживай диалог, задавай уместные вопросы, соблюдай безопасность и уважение."
            )
