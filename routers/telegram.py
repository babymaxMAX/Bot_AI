from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message
import httpx
from typing import Optional

from storage.dialogue_store import DialogueStore
from client import AIClient
from services.business_rules import BusinessRules
from storage.match_store import MatchStore
from config import get_settings


def create_router(dialogue_store: DialogueStore, ai_client: AIClient, rules: BusinessRules) -> Router:
    router = Router(name="chat")

    @router.message(F.text & F.chat.type == "private")
    async def on_message(message: Message) -> None:
        user_id = str(message.from_user.id) if message.from_user else str(message.chat.id)
        match_store: MatchStore = message.bot.get("match_store")  # type: ignore[assignment]
        latest = await match_store.get_latest_match_for_user(user_id)
        # если пишет мужчина, есть взаимная симпатия и нет оплаты — мягко подсказываем про оплату
        if latest and latest.get("male_id") == user_id and int(latest.get("mutual", 0)) == 1 and int(latest.get("paid", 0)) == 0:
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
        await message.answer("Привет! Я помогу начать диалог и поддерживать общение. Напиши первое сообщение.\nДоступные команды: /pay — получить ссылку на оплату (для мужчин при взаимной симпатии), /contact — получить контакт.")

    @router.message(F.text == "/pay")
    async def on_pay(message: Message) -> None:
        user_id = str(message.from_user.id) if message.from_user else str(message.chat.id)
        match_store: MatchStore = message.bot.get("match_store")  # type: ignore[assignment]
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
            settings = get_settings()
            base_url: Optional[str] = settings.APP_BASE_URL or settings.TELEGRAM_WEBHOOK_URL or "http://127.0.0.1:8000"
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(f"{base_url}/payments/create", json={"match_id": latest["id"]})
                    if resp.status_code == 200:
                        data = resp.json()
                        invoice_url = data.get("invoice_url")
                        if invoice_url:
                            await message.answer(f"Ссылка на оплату: {invoice_url}")
                            return
            except Exception:
                pass
            await message.answer("Ссылка на оплату скоро будет доступна. Обратитесь к поддержке.")

    @router.message(F.text == "/contact")
    async def on_contact(message: Message) -> None:
        user_id = str(message.from_user.id) if message.from_user else str(message.chat.id)
        match_store: MatchStore = message.bot.get("match_store")  # type: ignore[assignment]
        latest = await match_store.get_latest_match_for_user(user_id)
        if not latest or int(latest.get("mutual", 0)) != 1:
            await message.answer("Пока нет взаимной симпатии, контакт недоступен.")
            return
        # женщина — бесплатно получает контакт мужчины
        if latest.get("female_id") == user_id:
            male_username = latest.get("male_username")
            if male_username:
                await message.answer(f"Аккаунт собеседника: @{male_username}")
            else:
                await message.answer("Аккаунт собеседника пока недоступен. Попробуйте позже.")
            return
        # мужчина — после оплаты
        if latest.get("male_id") == user_id:
            if int(latest.get("paid", 0)) == 1:
                female_username = latest.get("female_username")
                if female_username:
                    await message.answer(f"Аккаунт собеседницы: @{female_username}")
                else:
                    await message.answer("Аккаунт собеседницы пока недоступен. Попробуйте позже.")
            else:
                await message.answer("Чтобы получить контакт собеседницы, необходимо оплатить 1000₽. Используйте команду /pay.")
            return

    return router
