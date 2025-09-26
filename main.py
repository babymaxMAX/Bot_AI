from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from aiogram import Bot, Dispatcher

from config import get_settings, WEBHOOK
from storage.dialogue_store import DialogueStore
from storage.match_store import MatchStore
from client import AIClient
from services.business_rules import BusinessRules
import routers.telegram_webhook as telegram_webhook
from routers.sympathy import sympathy_router
from routers.test_ai import test_ai_router
from routers.payments import payments_router


class AppState:
    bot: Bot
    dp: Dispatcher
    dialogue_store: DialogueStore
    match_store: MatchStore
    ai_client: AIClient
    rules: BusinessRules


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()

    dialogue_store = DialogueStore(settings.DIALOGUE_DB_PATH)
    await dialogue_store.init()

    match_store = MatchStore(settings.DIALOGUE_DB_PATH)
    await match_store.init()

    ai_client = AIClient(provider=settings.AI_PROVIDER, openai_api_key=settings.OPENAI_API_KEY)
    rules = BusinessRules()

    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()

    # aiogram-обработчики (чат-логика)
    from routers.telegram import create_router
    dp.include_router(create_router(dialogue_store, ai_client, rules))

    # контекст для обработчиков
    bot["match_store"] = match_store

    app.state.bot = bot
    app.state.dp = dp
    app.state.dialogue_store = dialogue_store
    app.state.ai_client = ai_client
    app.state.rules = rules
    app.state.match_store = match_store

    if settings.TELEGRAM_WEBHOOK_URL:
        await bot.set_webhook(
            url=settings.TELEGRAM_WEBHOOK_URL + WEBHOOK.path,
            secret_token
