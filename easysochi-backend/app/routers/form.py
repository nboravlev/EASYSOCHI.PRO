import logging
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.db_async import get_async_session
from app.db.models.contact_form import ContactForm
from app.schemas.form_schemas import (
    CallbackRequest,
    ContactFormAccepted,
    ContactFormCreate,
    ContactTopic,
    ContactType,
)
from app.services.notification_service import notification_service

router = APIRouter(tags=["form"])

logger = logging.getLogger(__name__)


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

    # Уведомление уходит фоном: ответ клиенту отдаётся сразу после коммита,
    # не дожидаясь почтового сервера.
    #
    # В фон передаются обычные значения, а не entry: к моменту запуска задачи
    # сессия уже закрыта, и обращение к полям ORM-объекта дало бы
    # DetachedInstanceError.
    background_tasks.add_task(
        notification_service.notify_new_contact_form,
        form_id=entry.id,
        name=form_data.name,
        contact_type=form_data.contact_type.value,
        contact_value=form_data.contact_value,
        topic=form_data.topic.value,
        source=form_data.source,
        message=form_data.message,
    )

    return ContactFormAccepted(id=entry.id)


# Текст заявки для обратного звонка. Человек его не пишет — виджет спрашивает
# только имя и телефон, — но колонка message обязательная, и пустая строка в
# списке заявок читалась бы как потерянные данные.
CALLBACK_MESSAGE = "Запрос обратного звонка"


@router.post("/callback", response_model=ContactFormAccepted)
async def request_callback(
    callback_data: CallbackRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session),
):
    """Приём запроса обратного звонка.

    Ложится в ту же таблицу, что и обычная заявка: это тот же контакт, просто
    собранный короткой формой. Тема — "Другое": ContactTopic отдаётся фронту
    эндпоинтом /topics и строит выпадающий список, поэтому заводить в нём
    отдельное значение ради служебной пометки значило бы показать её человеку
    среди тем обращения.
    """
    entry = ContactForm(
        name=callback_data.name,
        contact_type=ContactType.phone.value,
        contact_value=callback_data.phone,
        topic=ContactTopic.other.value,
        source=callback_data.source,
        message=CALLBACK_MESSAGE,
    )

    try:
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
    except SQLAlchemyError:
        await db.rollback()
        logger.exception("Failed to save callback request")
        raise HTTPException(status_code=500, detail="DB error")

    # В лог — только идентификатор: имя и телефон это персональные данные.
    logger.info("Callback request saved, id=%s", entry.id)

    background_tasks.add_task(
        notification_service.notify_callback_request,
        form_id=entry.id,
        name=callback_data.name,
        phone=callback_data.phone,
        source=callback_data.source,
    )

    return ContactFormAccepted(id=entry.id)
