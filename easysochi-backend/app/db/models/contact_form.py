from sqlalchemy import Column, Integer, String, DateTime
from app.db.db import Base
from datetime import datetime

class ContactForm(Base):
    __tablename__ = "contact_form"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)

    # Способ связи, выбранный отправителем: email, phone или telegram.
    # Хранится строкой, а не PG-типом enum: набор значений задан в
    # app/schemas/form_schemas.py и меняется без миграции типа в базе.
    contact_type = Column(String(20), nullable=False, default="email")

    # Сам контакт в выбранном формате. Раньше колонка называлась email и
    # хранила только почту.
    contact_value = Column(String(255), nullable=False)

    # Тема обращения — одно из значений ContactTopic. Текстом, а не ссылкой
    # на справочник: тем шесть, отдельная таблица тут была бы тяжелее задачи.
    topic = Column(String(100), nullable=False, default="Другое")

    # Страница, с которой отправлена форма (RelPermalink). Нужна, чтобы
    # видеть, откуда приходят заявки.
    source = Column(String(200), nullable=True)

    message = Column(String(2000), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
