from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message

from storage.dialogue_store import DialogueStore
from ai.client import AIClient
from services.business_rules import BusinessRules
from storage.match_store import MatchStore


def create_router(
    dialogue_store: DialogueStore,
    ai_client: AIClient,
    rules: BusinessRules,
    match_store: MatchStore,
) -> Router:
    router = Router(name="chat")

    @router.message(F.text & F.chat.type == "private")
    async def on_message(message: Message) -> None:
        user_id = str(message.from_user.id) if message.from_user else str(message.chat.id)

        # Гейтинг для мужчины при взаимной симпатии без оплаты
        latest = await match_store.get_latest_match_for_user(user_id)
        if latest and latest["male_id"] == user_id and int(latest.get("mutual", 0)) == 1 and int(
            latest.get("paid", 0)
        ) == 0:
            invoice_url = latest.get("invoice_url")
            pay_hint = "Для доступа к странице собеседницы требуется оплата 1000₽."
            if invoice_url:
                pay_hint += f" Ссылка на оплату: {invoice_url}"
            else:
                pay_hint += " Запросите ссылку командой /pay"
            await message.answer(pay_hint)

        await dialogue_store.add_message(user_id=user_id, role="user", content=message.text or "")

        system_prompt = await rules.build_system_prompt(user_id=user_id)
        history = await dialogue_store.get_recent_messages(user_id=user_id, limit=12)
        reply_text = await ai_client.generate_reply(system_prompt=system_prompt, history=history)

        await message.answer(reply_text)
        await dialogue_store.add_message(user_id=user_id, role="assistant", content=reply_text)

    @router.message(F.text == "/start")
    async def on_start(message: Message) -> None:
        await message.answer("Привет! Я помогу начать диалог и поддерживать общение. Напиши первое сообщение.")

    @router.message(F.text == "/pay")
    async def on_pay(message: Message) -> None:
        user_id = str(message.from_user.id) if message.from_user else str(message.chat.id)
        latest = await match_store.get_latest_match_for_user(user_id)
        if not latest or latest["male_id"] != user_id or int(latest.get("mutual", 0)) != 1:
            await message.answer("Пока нет активной взаимной симпатии, оплата не требуется.")
            return
        if int(latest.get("paid", 0)) == 1:
            await message.answer("Оплата уже подтверждена. Можете общаться свободно.")
            return
        invoice = latest.get("invoice_url")
        if invoice:
            await message.answer(f"Ссылка на оплату: {invoice}")
        else:
            await message.answer("Ссылка на оплату скоро будет доступна. Обратитесь к поддержке.")

    return router
