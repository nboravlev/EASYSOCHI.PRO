import enum
import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator

# Схемы формы обратной связи.


class ContactType(str, enum.Enum):
    """Способ связи, выбранный отправителем."""

    email = "email"
    phone = "phone"
    telegram = "telegram"


class ContactTopic(str, enum.Enum):
    """Тема обращения.

    Единственный источник правды: фронт забирает список эндпоинтом
    /api/v2/form/topics и строит из него выпадающий список. Справочника в
    базе нет намеренно — тем шесть, а отдельная таблица потребовала бы
    миграций и join ради выпадающего списка.

    В базу попадает само значение, то есть читаемая строка. Если тему
    когда-нибудь переименуют, старые записи сохранят прежний текст — это
    честная история обращения, а не рассогласование.
    """

    web_app = "Сайты и веб-приложения"
    chatbot = "Чат-боты"
    data = "Сбор и хранение данных"
    analytics = "Аналитика и BI"
    ai = "AI-ассистенты и LLM"
    other = "Другое"


# Простая проверка структуры адреса. EmailStr из pydantic не используется
# намеренно: он тянет зависимость email-validator, а нам достаточно отсечь
# заведомо неадресные строки — существование ящика всё равно не проверить.
EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class ContactFormCreate(BaseModel):
    """Входящая заявка."""

    name: str = Field(..., min_length=2, max_length=255, description="Имя отправителя")
    contact_type: ContactType = Field(ContactType.email, description="Способ связи")
    contact_value: str = Field(..., min_length=3, max_length=255, description="Контакт в выбранном формате")
    topic: ContactTopic = Field(ContactTopic.other, description="Тема обращения")
    message: str = Field(..., min_length=5, max_length=2000, description="Текст сообщения")
    source: Optional[str] = Field(None, max_length=200, description="Страница, с которой отправлена форма")

    @field_validator("contact_value")
    @classmethod
    def validate_contact_value(cls, value: str, info):
        """Проверка контакта по выбранному способу связи.

        Значение соседнего поля в Pydantic V2 лежит в info.data, и оно есть
        только если contact_type объявлен ВЫШЕ по тексту класса и прошёл
        валидацию. Если он не прошёл, ключа не будет — тогда проверять
        нечего, ошибку по contact_type пользователь и так увидит.
        """
        contact_type = info.data.get("contact_type")
        if contact_type is None:
            return value

        value = value.strip()

        if contact_type == ContactType.email:
            if not EMAIL_RE.match(value):
                raise ValueError("Некорректный формат email адреса")

        elif contact_type == ContactType.phone:
            digits = re.sub(r"\D", "", value)
            if len(digits) < 7:
                raise ValueError("Номер телефона слишком короткий, нужно минимум 7 цифр")

        elif contact_type == ContactType.telegram:
            if not value.startswith("@"):
                raise ValueError("Ник в Telegram должен начинаться с символа @")
            if len(value) < 3:
                raise ValueError("Ник в Telegram слишком короткий")

        return value


class ContactFormAccepted(BaseModel):
    """Ответ на принятую заявку.

    Наружу отдаём только идентификатор: возвращать клиенту его же
    персональные данные незачем.
    """

    status: str = "ok"
    id: int
