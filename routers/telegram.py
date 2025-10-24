from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
import httpx
from typing import Optional

from storage.dialogue_store import DialogueStore
from client import AIClient
from services.business_rules import BusinessRules
from storage.match_store import MatchStore
from storage.profile_store import ProfileStore
from config import get_settings


class ProfileForm(StatesGroup):
    ask_gender = State()
    ask_bio = State()
    ask_age = State()
    ask_city = State()
    ask_hobbies = State()
    # Расширенная анкета для знакомств по исламу
    ask_country = State()
    ask_citizenship = State()
    ask_ethnicity = State()
    ask_languages = State()
    ask_marital_status = State()
    ask_children = State()
    ask_religiosity = State()
    ask_prayer = State()
    ask_dress_code = State()  # хиджаб/ниqab для женщин; борода для мужчин
    ask_education = State()
    ask_occupation = State()
    ask_income = State()
    ask_height = State()
    ask_body_type = State()
    ask_smoking = State()
    ask_alcohol = State()
    ask_halal_practice = State()
    ask_family_consent = State()
    ask_contact_pref = State()
    ask_expectations = State()


def _format_profile_context(profile: dict) -> str:
    items = []
    username = profile.get("username")
    gender = profile.get("gender")
    bio = profile.get("bio")
    number = profile.get("profile_number")
    attrs = profile.get("attributes") or {}
    if username:
        items.append(f"username=@{username}")
    if gender:
        items.append(f"gender={gender}")
    if number:
        items.append(f"profile_number={number}")
    if bio:
        items.append(f"bio={bio}")
    if attrs:
        items.append(f"attributes={attrs}")
    return "\n".join(items) if items else "нет данных"


def _format_match_context(match: dict) -> str:
    parts = [
        f"match_id={match.get('id')}",
        f"male_id={match.get('male_id')}",
        f"female_id={match.get('female_id')}",
        f"mutual={match.get('mutual')}",
        f"paid={match.get('paid')}",
    ]
    if match.get("female_username"):
        parts.append(f"female_username=@{match.get('female_username')}")
    if match.get("male_username"):
        parts.append(f"male_username=@{match.get('male_username')}")
    if match.get("invoice_url"):
        parts.append(f"invoice={match.get('invoice_url')}")
    return ", ".join(parts)


def create_router(
    dialogue_store: DialogueStore,
    match_store: MatchStore,
    profile_store: ProfileStore,
    ai_client: AIClient,
    rules: BusinessRules,
) -> Router:
    router = Router(name="chat")

    @router.message(F.text == "/help")
    async def on_help(message: Message) -> None:
        await message.answer(
            "Команды:\n"
            "/start — начать\n"
            "/my_matches — список взаимных совпадений\n"
            "/create_profile — создать/обновить анкету\n"
            "/profile — показать мою анкету\n"
            "/match — статус моего матча\n"
            "/pay — получить ссылку на оплату (для мужчин при взаимной симпатии)\n"
            "/contact — получить контакт\n"
            "/cancel — отменить заполнение анкеты"
        )

    # Естественные фразы-триггеры на создание анкеты
    @router.message(F.text.lower().contains("создать анкет") | F.text.lower().contains("завести анкет") | F.text.lower().contains("добавить анкет"))
    async def create_profile_trigger(message: Message, state: FSMContext) -> None:
        await create_profile_start(message, state)

    @router.message(F.text == "/create_profile")
    async def create_profile_start(message: Message, state: FSMContext) -> None:
        await state.clear()
        await state.set_state(ProfileForm.ask_gender)
        await message.answer("Создадим анкету. Укажите ваш пол (male/female):")

    @router.message(ProfileForm.ask_gender, F.text.lower().in_("male", "female", "мужчина", "женщина"))
    async def create_profile_gender(message: Message, state: FSMContext) -> None:
        txt = (message.text or "").strip().lower()
        gender = "male" if txt in {"male", "мужчина"} else "female"
        await state.update_data(gender=gender)
        await state.set_state(ProfileForm.ask_bio)
        await message.answer("Коротко о себе (био):")

    @router.message(ProfileForm.ask_bio, F.text)
    async def create_profile_bio(message: Message, state: FSMContext) -> None:
        await state.update_data(bio=(message.text or "").strip())
        await state.set_state(ProfileForm.ask_age)
        await message.answer("Возраст (число):")

    @router.message(ProfileForm.ask_age, F.text.regexp(r"^(1[0-1][0-9]|[1-9]?[0-9])$"))
    async def create_profile_age(message: Message, state: FSMContext) -> None:
        await state.update_data(age=int(message.text))  # type: ignore[arg-type]
        await state.set_state(ProfileForm.ask_country)
        await message.answer("Страна проживания:")

    @router.message(ProfileForm.ask_age)
    async def create_profile_age_invalid(message: Message) -> None:
        await message.answer("Укажите возраст числом, пример: 29")

    @router.message(ProfileForm.ask_country, F.text)
    async def create_profile_country(message: Message, state: FSMContext) -> None:
        await state.update_data(country=(message.text or "").strip())
        await state.set_state(ProfileForm.ask_city)
        await message.answer("Город проживания:")

    @router.message(ProfileForm.ask_city, F.text)
    async def create_profile_city(message: Message, state: FSMContext) -> None:
        await state.update_data(city=(message.text or "").strip())
        await state.set_state(ProfileForm.ask_citizenship)
        await message.answer("Гражданство (если несколько — через запятую, можно 'пропустить'):")

    @router.message(ProfileForm.ask_citizenship, F.text)
    async def create_profile_citizenship(message: Message, state: FSMContext) -> None:
        txt = (message.text or "").strip()
        if txt.lower() != "пропустить":
            await state.update_data(citizenship=txt)
        await state.set_state(ProfileForm.ask_ethnicity)
        await message.answer("Этническое происхождение (например: татарин, дагестанец; можно 'пропустить'):")

    @router.message(ProfileForm.ask_ethnicity, F.text)
    async def create_profile_ethnicity(message: Message, state: FSMContext) -> None:
        txt = (message.text or "").strip()
        if txt.lower() != "пропустить":
            await state.update_data(ethnicity=txt)
        await state.set_state(ProfileForm.ask_languages)
        await message.answer("Языки (через запятую):")

    @router.message(ProfileForm.ask_languages, F.text)
    async def create_profile_languages(message: Message, state: FSMContext) -> None:
        langs = [x.strip() for x in (message.text or "").split(",") if x.strip()]
        await state.update_data(languages=langs)
        await state.set_state(ProfileForm.ask_marital_status)
        await message.answer("Семейное положение (холост/незамужем, разведен(а), вдовец/вдова):")

    @router.message(ProfileForm.ask_marital_status, F.text)
    async def create_profile_marital(message: Message, state: FSMContext) -> None:
        await state.update_data(marital_status=(message.text or "").strip())
        await state.set_state(ProfileForm.ask_children)
        await message.answer("Дети (нет / есть, сколько и возраст):")

    @router.message(ProfileForm.ask_children, F.text)
    async def create_profile_children(message: Message, state: FSMContext) -> None:
        await state.update_data(children=(message.text or "").strip())
        await state.set_state(ProfileForm.ask_religiosity)
        await message.answer("Уровень религиозной практики (начальный/средний/высокий):")

    @router.message(ProfileForm.ask_religiosity, F.text)
    async def create_profile_religiosity(message: Message, state: FSMContext) -> None:
        await state.update_data(religiosity=(message.text or "").strip())
        await state.set_state(ProfileForm.ask_prayer)
        await message.answer("Намаз (совершаю регулярно/иногда/нет):")

    @router.message(ProfileForm.ask_prayer, F.text)
    async def create_profile_prayer(message: Message, state: FSMContext) -> None:
        await state.update_data(prayer=(message.text or "").strip())
        await state.set_state(ProfileForm.ask_dress_code)
        await message.answer("Для женщин: хиджаб/ниqab (ношение) — ответ; для мужчин: борода — ответ. Если не применимо — 'пропустить':")

    @router.message(ProfileForm.ask_dress_code, F.text)
    async def create_profile_dress(message: Message, state: FSMContext) -> None:
        txt = (message.text or "").strip()
        if txt.lower() != "пропустить":
            await state.update_data(dress_code=txt)
        await state.set_state(ProfileForm.ask_education)
        await message.answer("Образование (уровень, специальность):")

    @router.message(ProfileForm.ask_education, F.text)
    async def create_profile_education(message: Message, state: FSMContext) -> None:
        await state.update_data(education=(message.text or "").strip())
        await state.set_state(ProfileForm.ask_occupation)
        await message.answer("Род занятий/работа:")

    @router.message(ProfileForm.ask_occupation, F.text)
    async def create_profile_occupation(message: Message, state: FSMContext) -> None:
        await state.update_data(occupation=(message.text or "").strip())
        await state.set_state(ProfileForm.ask_income)
        await message.answer("Доход (диапазон, можно 'пропустить'):")

    @router.message(ProfileForm.ask_income, F.text)
    async def create_profile_income(message: Message, state: FSMContext) -> None:
        txt = (message.text or "").strip()
        if txt.lower() != "пропустить":
            await state.update_data(income=txt)
        await state.set_state(ProfileForm.ask_height)
        await message.answer("Рост (см, число, можно 'пропустить'):")

    @router.message(ProfileForm.ask_height, F.text)
    async def create_profile_height(message: Message, state: FSMContext) -> None:
        txt = (message.text or "").strip()
        if txt.lower() != "пропустить":
            await state.update_data(height=txt)
        await state.set_state(ProfileForm.ask_body_type)
        await message.answer("Телосложение (стройное/среднее/крепкое и т.п., можно 'пропустить'):")

    @router.message(ProfileForm.ask_body_type, F.text)
    async def create_profile_body(message: Message, state: FSMContext) -> None:
        txt = (message.text or "").strip()
        if txt.lower() != "пропустить":
            await state.update_data(body_type=txt)
        await state.set_state(ProfileForm.ask_smoking)
        await message.answer("Курение (нет/иногда/да):")

    @router.message(ProfileForm.ask_smoking, F.text)
    async def create_profile_smoking(message: Message, state: FSMContext) -> None:
        await state.update_data(smoking=(message.text or "").strip())
        await state.set_state(ProfileForm.ask_alcohol)
        await message.answer("Алкоголь (нет/иногда/да):")

    @router.message(ProfileForm.ask_alcohol, F.text)
    async def create_profile_alcohol(message: Message, state: FSMContext) -> None:
        await state.update_data(alcohol=(message.text or "").strip())
        await state.set_state(ProfileForm.ask_halal_practice)
        await message.answer("Соблюдение халяль (строго/в основном/стараюсь):")

    @router.message(ProfileForm.ask_halal_practice, F.text)
    async def create_profile_halal(message: Message, state: FSMContext) -> None:
        await state.update_data(halal=(message.text or "").strip())
        await state.set_state(ProfileForm.ask_family_consent)
        await message.answer("Согласие семьи/вали известно? (да/нет/обсуждается):")

    @router.message(ProfileForm.ask_family_consent, F.text)
    async def create_profile_consent(message: Message, state: FSMContext) -> None:
        await state.update_data(family_consent=(message.text or "").strip())
        await state.set_state(ProfileForm.ask_contact_pref)
        await message.answer("Предпочтительный способ связи (чат/звонок/через вали/опекуна):")

    @router.message(ProfileForm.ask_contact_pref, F.text)
    async def create_profile_contactpref(message: Message, state: FSMContext) -> None:
        await state.update_data(contact_pref=(message.text or "").strip())
        await state.set_state(ProfileForm.ask_hobbies)
        await message.answer("Хобби и интересы (через запятую):")

    @router.message(ProfileForm.ask_hobbies, F.text)
    async def create_profile_finish(message: Message, state: FSMContext) -> None:
        user_id = str(message.from_user.id) if message.from_user else str(message.chat.id)
        data = await state.get_data()
        hobbies = [h.strip() for h in (message.text or "").split(",") if h.strip()]
        attrs = {
            "age": data.get("age"),
            "country": data.get("country"),
            "city": data.get("city"),
            "citizenship": data.get("citizenship"),
            "ethnicity": data.get("ethnicity"),
            "languages": data.get("languages"),
            "marital_status": data.get("marital_status"),
            "children": data.get("children"),
            "religiosity": data.get("religiosity"),
            "prayer": data.get("prayer"),
            "dress_code": data.get("dress_code"),
            "education": data.get("education"),
            "occupation": data.get("occupation"),
            "income": data.get("income"),
            "height": data.get("height"),
            "body_type": data.get("body_type"),
            "smoking": data.get("smoking"),
            "alcohol": data.get("alcohol"),
            "halal": data.get("halal"),
            "family_consent": data.get("family_consent"),
            "contact_pref": data.get("contact_pref"),
            "hobbies": hobbies,
        }

        await profile_store.upsert_profile(
            user_id=user_id,
            username=message.from_user.username if message.from_user else None,
            gender=data.get("gender"),
            bio=data.get("bio"),
            attributes=attrs,
            profile_number=None,
        )
        # Отправим апдейт в основной бот, если настроен URL
        settings = get_settings()
        if settings.MAIN_BOT_PROFILE_UPSERT_URL and settings.MAIN_BOT_AUTH_TOKEN:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    await client.post(
                        settings.MAIN_BOT_PROFILE_UPSERT_URL,
                        headers={"Authorization": f"Bearer {settings.MAIN_BOT_AUTH_TOKEN}"},
                        json={
                            "user_id": user_id,
                            "username": message.from_user.username if message.from_user else None,
                            "gender": data.get("gender"),
                            "bio": data.get("bio"),
                            "attributes": attrs,
                            "profile_number": None,
                        },
                    )
            except Exception:
                pass

        preview = [
            "Анкета сохранена:",
            f"Пол: {'Мужчина' if data.get('gender')=='male' else 'Женщина'}",
            f"О себе: {data.get('bio')}",
            f"Возраст: {attrs.get('age')}",
            f"Страна/Город: {attrs.get('country')} / {attrs.get('city')}",
            f"Гражданство: {attrs.get('citizenship')}",
            f"Этнос: {attrs.get('ethnicity')}",
            f"Языки: {', '.join(attrs.get('languages') or [])}",
            f"Сем. положение: {attrs.get('marital_status')} | Дети: {attrs.get('children')}",
            f"Религиозность: {attrs.get('religiosity')} | Намаз: {attrs.get('prayer')}",
            f"Одежда/борода: {attrs.get('dress_code')}",
            f"Образование: {attrs.get('education')}",
            f"Занятость: {attrs.get('occupation')} | Доход: {attrs.get('income')}",
            f"Рост/телосложение: {attrs.get('height')} / {attrs.get('body_type')}",
            f"Курение/алкоголь: {attrs.get('smoking')} / {attrs.get('alcohol')}",
            f"Халяль: {attrs.get('halal')} | Согласие семьи: {attrs.get('family_consent')}",
            f"Связь: {attrs.get('contact_pref')}",
            f"Хобби: {', '.join(attrs.get('hobbies') or [])}",
        ]
        await message.answer("\n".join(preview) + "\nИспользуйте /profile для просмотра или /my_matches для статуса совпадений.")
        await state.clear()

    @router.message(F.text == "/cancel")
    async def on_cancel(message: Message, state: FSMContext) -> None:
        await state.clear()
        await message.answer("Ок, отменил. Используйте /create_profile, чтобы начать заново.")

    @router.message(F.text == "/profile")
    async def on_profile(message: Message) -> None:
        user_id = str(message.from_user.id) if message.from_user else str(message.chat.id)
        profile = await profile_store.get_profile(user_id)
        if not profile:
            await message.answer("Анкета не найдена. Попросите основной бот отправить/обновить анкету.")
            return
        ctx = _format_profile_context(profile)
        await message.answer(f"Профиль:\n{ctx}")

    @router.message(F.text == "/match")
    async def on_match(message: Message) -> None:
        user_id = str(message.from_user.id) if message.from_user else str(message.chat.id)
        latest = await match_store.get_latest_match_for_user(user_id)
        if not latest:
            await message.answer("Активных совпадений пока нет.")
            return
        await message.answer("Статус: " + _format_match_context(latest))

    @router.message(F.text == "/my_matches")
    async def on_my_matches(message: Message) -> None:
        user_id = str(message.from_user.id) if message.from_user else str(message.chat.id)
        rows = await match_store.list_matches_for_user(user_id, only_mutual=True)
        if not rows:
            await message.answer("Взаимных совпадений пока нет.")
            return
        lines = ["Ваши взаимные совпадения:"]
        for m in rows[:10]:
            lines.append(_format_match_context(m))
        await message.answer("\n".join(lines))

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
        latest = await match_store.get_latest_match_for_user(user_id)
        if not latest or int(latest.get("mutual", 0)) != 1:
            await message.answer("Пока нет взаимной симпатии, контакт недоступен.")
            return
        if latest.get("female_id") == user_id:
            male_username = latest.get("male_username")
            if male_username:
                await message.answer(f"Аккаунт собеседника: @{male_username}")
            else:
                await message.answer("Аккаунт собеседника пока недоступен. Попробуйте позже.")
            return
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

    @router.message(F.text & F.chat.type == "private")
    async def on_message(message: Message) -> None:
        user_id = str(message.from_user.id) if message.from_user else str(message.chat.id)

        latest = await match_store.get_latest_match_for_user(user_id)
        if latest and latest.get("male_id") == user_id and int(latest.get("mutual", 0)) == 1 and int(latest.get("paid", 0)) == 0:
            invoice_url = latest.get("invoice_url")
            pay_hint = "Для доступа к странице собеседницы требуется оплата 1000₽."
            if invoice_url:
                pay_hint += f" Ссылка на оплату: {invoice_url}"
            else:
                pay_hint += " Запросите ссылку командой /pay"
            await message.answer(pay_hint)

        await dialogue_store.add_message(user_id=user_id, role="user", content=message.text or "")

        profile = await profile_store.get_profile(user_id)
        profile_ctx = _format_profile_context(profile) if profile else None
        match_ctx = _format_match_context(latest) if latest else None
        system_prompt = await rules.build_system_prompt(user_id=user_id, profile_context=profile_ctx, match_context=match_ctx)

        history = await dialogue_store.get_recent_messages(user_id=user_id, limit=12)
        reply_text = await ai_client.generate_reply(system_prompt=system_prompt, history=history)

        await message.answer(reply_text)
        await dialogue_store.add_message(user_id=user_id, role="assistant", content=reply_text)

    return router
