from __future__ import annotations

from fastapi import APIRouter, HTTPException, Body, Request, Header

from storage.match_store import MatchStore
from services.payment_provider import load_provider

payments_router = APIRouter(prefix="/payments", tags=["payments"])

@payments_router.post("/create")
async def create_payment(payload: dict = Body(...)) -> dict[str, str]:
    match_id = int(payload.get("match_id", 0))
    if match_id <= 0:
        raise HTTPException(status_code=400, detail="match_id required")

    provider = load_provider()
    invoice_url = await provider.create_invoice(
        match_id=match_id,
        amount_rub=1000,
        description=f"Access to contact for match {match_id}",
    )

    store: MatchStore = payments_router.router.app.state.match_store  # type: ignore[attr-defined]
    await store.set_invoice_url(match_id, invoice_url)
    return {"invoice_url": invoice_url}

@payments_router.post("/webhook")
async def payment_webhook(request: Request, signature: str | None = Header(default=None, alias="X-Signature")) -> dict[str, str]:
    raw = await request.body()
    provider = load_provider()
    if not provider.verify_webhook(raw, signature or ""):
        raise HTTPException(status_code=401, detail="invalid signature")

    payload = await request.json()
    match_id = int(payload.get("match_id", 0))
    status = str(payload.get("status", "")).lower()
    if status != "paid" or match_id <= 0:
        raise HTTPException(status_code=400, detail="invalid payload")

    store: MatchStore = payments_router.router.app.state.match_store  # type: ignore[attr-defined]
    await store.mark_paid(match_id)
    return {"status": "ok"}
