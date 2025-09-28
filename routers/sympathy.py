from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Body

from config import get_settings
from storage.match_store import MatchStore

sympathy_router = APIRouter(prefix="/webhook", tags=["sympathy"])

@sympathy_router.post("/sympathy")
async def sympathy_event(
    authorization: str | None = Header(default=None, alias="Authorization"),
    payload: dict | None = Body(default=None),
) -> dict[str, str]:
    settings = get_settings()
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]

    if not token or token != settings.MAIN_BOT_AUTH_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")

    if payload is None:
        raise HTTPException(status_code=400, detail="payload required")

    male_id = str(payload.get("male_id", "")).strip()
    female_id = str(payload.get("female_id", "")).strip()
    mutual = bool(payload.get("mutual", False))
    male_username = payload.get("male_username")
    female_username = payload.get("female_username")

    if not male_id or not female_id:
        raise HTTPException(status_code=400, detail="male_id and female_id required")

    store: MatchStore = sympathy_router.router.app.state.match_store  # type: ignore[attr-defined]
    match_id = await store.create_match(
        male_id=male_id,
        female_id=female_id,
        mutual=mutual,
        male_username=male_username,
        female_username=female_username,
    )

    return {"status": "received", "match_id": str(match_id)}
