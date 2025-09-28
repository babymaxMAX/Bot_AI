from __future__ import annotations

from fastapi import APIRouter, HTTPException, Body

from storage.match_store import MatchStore

payments_router = APIRouter(prefix="/payments", tags=["payments"])

@payments_router.post("/create")
async def create_payment(payload: dict = Body(...)) -> dict[str, str]:
    match_id = int(payload.get("match_id", 0))
    if match_id <= 0:
        raise HTTPException(status_code=400, detail="match_id required")

    # TODO: интеграция реального провайдера — сейчас заглушка
    invoice_url = f"https://pay.example.com/invoice/{match_id}"

    store: MatchStore = payments_router.router.app.state.match_store  # type: ignore[attr-defined]
    await store.set_invoice_url(match_id, invoice_url)
    return {"invoice_url": invoice_url}

@payments_router.post("/webhook")
async def payment_webhook(payload: dict = Body(...)) -> dict[str, str]:
    match_id = int(payload.get("match_id", 0))
    status = str(payload.get("status", "")).lower()
    if status != "paid" or match_id <= 0:
        raise HTTPException(status_code=400, detail="invalid payload")

    store: MatchStore = payments_router.router.app.state.match_store  # type: ignore[attr-defined]
    await store.mark_paid(match_id)
    return {"status": "ok"}
