from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from aiogram import Bot, Dispatcher

from app.config import get_settings, WEBHOOK
from app.storage.dialogue_store import DialogueStore
from app.storage.match_store import MatchStore
from app.ai.client import AIClient
from app.services.business_rules import BusinessRules
from app.routers.telegram import telegram_router
from app.routers.sympathy import sympathy_router
from app.routers.test_ai import test_ai_router
from app.routers.payments import payments_router


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

    # Attach router with dependencies
    from app.telegram.router import create_router

    dp.include_router(create_router(dialogue_store, ai_client, rules))

    # Provide stores to bot context for handlers
    bot["match_store"] = match_store

    app.state.bot = bot
    app.state.dp = dp
    app.state.dialogue_store = dialogue_store
    app.state.ai_client = ai_client
    app.state.rules = rules
    app.state.match_store = match_store

    # Setup webhook if URL provided
    if settings.TELEGRAM_WEBHOOK_URL:
        await bot.set_webhook(
            url=settings.TELEGRAM_WEBHOOK_URL + WEBHOOK.path,
            secret_token=settings.TELEGRAM_WEBHOOK_SECRET,
            drop_pending_updates=True,
        )

    try:
        yield
    finally:
        await bot.delete_webhook(drop_pending_updates=False)
        await bot.session.close()
        await dialogue_store.close()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# Routers
app.include_router(telegram_router)
app.include_router(sympathy_router)
app.include_router(test_ai_router)
app.include_router(payments_router)
