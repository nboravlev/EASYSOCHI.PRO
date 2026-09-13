import logging
import os
from typing import List

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
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


async def notify_telegram(text: str) -> None:
    """Уведомление о заявке. Запускается фоном, уже после ответа клиенту.

    Раньше отправка шла внутри обработчика, и при недоступном Telegram ответ
    формы задерживался на весь таймаут. Посетитель видел, что «ничего не
    происходит», жал кнопку ещё раз — в базе появлялись дубли заявки.
    Заявка уже сохранена, так что доставка уведомления не должна влиять
    ни на ответ, ни на его скорость.
    """
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": CHAT_ID, "text": text},
            )

        if response.status_code == 200:
            # Тело успешного ответа содержит эхо отправленного сообщения,
            # то есть саму заявку — его не логируем.
            logger.info("Telegram notification sent")
            return

        # А вот тело ОШИБКИ персональных данных не содержит: там
        # {"ok":false,"error_code":...,"description":"..."} — и без описания
        # причину не понять.
        description = ""
        try:
            description = response.json().get("description", "")
        except ValueError:
            pass
        logger.error(
            "Telegram rejected notification: status=%s description=%s",
            response.status_code,
            description,
        )
    except Exception as exc:
        # repr, а не str: у таймаутов httpx пустое строковое представление,
        # и в логах оставалось «Telegram notification failed:» без причины.
        logger.error("Telegram notification failed: %r", exc)


@router.get("/topics", response_model=List[str])
async def get_topics():
    """Список тем обращения для выпадающего списка на фронте.

    Отдаётся из enum, справочника в базе нет — см. комментарий к ContactTopic.
    """
    return [topic.value for topic in ContactTopic]


@router.post("/", response_model=ContactFormAccepted)
async def receive_form(
    form_data: ContactFormCreate,
    background_tasks: BackgroundTasks,
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
    # Уведомление уходит фоном: ответ клиенту отдаётся сразу после коммита,
    # не дожидаясь Telegram.
    background_tasks.add_task(notify_telegram, text)

    return ContactFormAccepted(id=entry.id)
