from __future__ import annotations

from fastapi import APIRouter, Query, Request


test_ai_router = APIRouter(prefix="/test", tags=["test"])


@test_ai_router.get("/ai")
async def test_ai(request: Request, message: str = Query("Привет! Давай познакомимся?")) -> dict[str, str]:
    history = [{"role": "user", "content": message}]
    system_prompt = await request.app.state.rules.build_system_prompt(user_id="test")
    reply = await request.app.state.ai_client.generate_reply(system_prompt=system_prompt, history=history)
    return {"reply": reply}
