from __future__ import annotations

from functools import lru_cache
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
import os
import re
import pathlib

# грузим .env до чтения настроек
load_dotenv(dotenv_path=".env")


def _normalize_env() -> None:
    env_path = pathlib.Path(".env")
    if not env_path.exists():
        return
    try:
        content = env_path.read_text(encoding="utf-8-sig")
    except Exception:
        return

    token_in_file: str | None = None
    webhook_url_in_file: str | None = None
    for line in content.splitlines():
        if line.startswith("TELEGRAM_BOT_TOKEN="):
            token_in_file = line.split("=", 1)[1].strip()
        elif line.startswith("TELEGRAM_WEBHOOK_URL="):
            webhook_url_in_file = line.split("=", 1)[1].strip()

    if not os.getenv("TELEGRAM_BOT_TOKEN") and token_in_file:
        os.environ["TELEGRAM_BOT_TOKEN"] = token_in_file

    token_like = webhook_url_in_file and re.match(r"^\d+:[A-Za-z0-9_\-]{20,}$", webhook_url_in_file)
    if not os.getenv("TELEGRAM_BOT_TOKEN") and token_like:
        os.environ["TELEGRAM_BOT_TOKEN"] = webhook_url_in_file  # type: ignore[arg-type]


__all__ = ["get_settings", "WEBHOOK"]

_normalize_env()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )
    # Telegram
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_WEBHOOK_URL: str | None = None
    TELEGRAM_WEBHOOK_SECRET: str | None = None

    # App
    APP_BASE_URL: str | None = None
    APP_PORT: int = 8000

    # AI
    AI_PROVIDER: str = "openai"
    OPENAI_API_KEY: str | None = None

    # Storage
    DIALOGUE_DB_PATH: str = "./data/dialogues.db"

    # Auth от основного бота
    MAIN_BOT_AUTH_TOKEN: str | None = None
    # URL вебхука основного бота для апсерта профиля (когда анкета создаётся в ИИ-боте)
    MAIN_BOT_PROFILE_UPSERT_URL: str | None = None


class WebhookConfig(BaseModel):
    path: str = "/telegram/webhook"
    header_secret: str = "X-Telegram-Bot-Api-Secret-Token"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]


WEBHOOK = WebhookConfig()
