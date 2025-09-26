from __future__ import annotations

from fastapi import APIRouter, Request, Response, HTTPException
import asyncio

from app.config import WEBHOOK, get_settings


telegram_router = APIRouter(prefix="/telegram", tags=["telegram"])


@telegram_router.post("/webhook")
async def telegram_webhook(request: Request) -> Response:
    settings = get_settings()
    secret = request.headers.get(WEBHOOK.header_secret)
    if settings.TELEGRAM_WEBHOOK_SECRET and secret != settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="invalid secret")

    data = await request.json()
    update = Update.model_validate(data)
    # Обрабатываем апдейт асинхронно, чтобы мгновенно отвечать Telegram 200 OK
    asyncio.create_task(request.app.state.dp.feed_update(bot=request.app.state.bot, update=update))
    return Response(status_code=200)
