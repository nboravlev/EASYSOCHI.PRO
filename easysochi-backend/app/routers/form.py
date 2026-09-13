import logging
import os
from typing import List

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.db_async import get_async_session
from app.db.models.contact_form import ContactForm
from app.schemas.form_schemas import (
    ContactFormAccepted,
    ContactFormCreate,
    ContactTopic,
    ContactType,
)

router = APIRouter(tags=["form"])

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

logger = logging.getLogger(__name__)

# Значки в уведомлении, чтобы способ связи считывался с первого взгляда.
CONTACT_ICONS = {
    ContactType.email: "📧",
    ContactType.phone: "📞",
    ContactType.telegram: "✈️",
}


@router.get("/topics", response_model=List[str])
async def get_topics():
    """Список тем обращения для выпадающего списка на фронте.

    Отдаётся из enum, справочника в базе нет — см. комментарий к ContactTopic.
    """
    return [topic.value for topic in ContactTopic]


@router.post("/", response_model=ContactFormAccepted)
async def receive_form(
    form_data: ContactFormCreate,
    db: AsyncSession = Depends(get_async_session),
):
    """Приём заявки с формы обратной связи.

    Валидацию целиком делает ContactFormCreate, поэтому невалидный ввод
    возвращает 422 с описанием проблемного поля, а не 400 без подробностей
    и не 500 из-за упёршегося в длину колонки текста.
    """
    entry = ContactForm(
        name=form_data.name,
        contact_type=form_data.contact_type.value,
        contact_value=form_data.contact_value,
        topic=form_data.topic.value,
        source=form_data.source,
        message=form_data.message,
    )

    try:
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
    except SQLAlchemyError:
        await db.rollback()
        logger.exception("Failed to save contact form")
        raise HTTPException(status_code=500, detail="DB error")

    # В лог — только идентификатор и тема. Имя, контакт и текст сообщения
    # это персональные данные, в docker logs им не место.
    logger.info("Contact form saved, id=%s topic=%s", entry.id, entry.topic)

    icon = CONTACT_ICONS.get(form_data.contact_type, "👤")
    text = (
        f"📩 Новая заявка\n\n"
        f"👤 Имя: {form_data.name}\n"
        f"{icon} {form_data.contact_type.value.capitalize()}: {form_data.contact_value}\n"
        f"📂 Тема: {form_data.topic.value}\n"
        f"🔗 Источник: {form_data.source or 'не указан'}\n"
        f"📝 Сообщение:\n{form_data.message}"
    )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": CHAT_ID, "text": text},
            )
        # Тело ответа Telegram содержит эхо отправленного сообщения,
        # то есть саму заявку — логируем только статус.
        logger.info("Telegram notification sent, status=%s", response.status_code)
    except httpx.HTTPError as exc:
        # Заявка уже в базе, так что неудача уведомления не повод
        # возвращать ошибку отправителю.
        logger.warning("Telegram notification failed: %s", exc)

    return ContactFormAccepted(id=entry.id)
