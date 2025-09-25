from __future__ import annotations

import asyncio
from fastapi import APIRouter, Request, Response, HTTPException
from aiogram.types import Update

from config import WEBHOOK, get_settings

telegram_webhook_router = APIRouter(prefix="/telegram", tags=["telegram"])


@telegram_webhook_router.post("/webhook")
async def telegram_webhook(request: Request) -> Response:
    settings = get_settings()
    secret = request.headers.get(WEBHOOK.header_secret)
    if settings.TELEGRAM_WEBHOOK_SECRET and secret != settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="invalid secret")

    data = await request.json()
    update = Update.model_validate(data)

    # Отдаём 200 мгновенно, апдейт обрабатываем в фоне (чтобы не упираться в таймауты Telegram/OpenAI)
    asyncio.create_task(
        request.app.state.dp.feed_update(bot=request.app.state.bot, update=update)
    )
    return Response(status_code=200)
