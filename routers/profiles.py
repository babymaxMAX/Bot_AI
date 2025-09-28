from __future__ import annotations

from fastapi import APIRouter, HTTPException, Header, Body, Query

from config import get_settings
from storage.profile_store import ProfileStore

profiles_router = APIRouter(prefix="/profiles", tags=["profiles"])

@profiles_router.get("/{user_id}")
async def get_profile(user_id: str) -> dict:
    store: ProfileStore = profiles_router.router.app.state.profile_store  # type: ignore[attr-defined]
    profile = await store.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="profile not found")
    return profile

@profiles_router.get("/by_number/{number}")
async def get_profile_by_number(number: int) -> dict:
    store: ProfileStore = profiles_router.router.app.state.profile_store  # type: ignore[attr-defined]
    profile = await store.find_by_number(number)
    if not profile:
        raise HTTPException(status_code=404, detail="profile not found")
    return profile

@profiles_router.get("")
async def list_profiles(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)) -> list[dict]:
    store: ProfileStore = profiles_router.router.app.state.profile_store  # type: ignore[attr-defined]
    return await store.list_profiles(limit=limit, offset=offset)

@profiles_router.post("/webhook/profile_upsert")
async def profile_upsert(
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

    user_id = str(payload.get("user_id", "")).strip()
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")

    store: ProfileStore = profiles_router.router.app.state.profile_store  # type: ignore[attr-defined]
    await store.upsert_profile(
        user_id=user_id,
        username=payload.get("username"),
        gender=payload.get("gender"),
        bio=payload.get("bio"),
        attributes=payload.get("attributes"),
        profile_number=payload.get("profile_number"),
    )
    return {"status": "ok"}
