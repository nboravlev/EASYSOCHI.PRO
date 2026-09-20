import os
from typing import List

# 🔄 ВЫНЕСЕНО: Все конфиги и константы

class Settings:
    # Активная платёжная система. Допустимые значения перечислены в
    # app.services.payment_service.SUPPORTED_PROVIDERS; фабрика
    # get_payment_service() падает на старте, если значение неизвестное.
    PAYMENT_PROVIDER: str = os.getenv("PAYMENT_PROVIDER", "robokassa").strip().lower()

    # Robokassa
    ROBOKASSA_SHOP_ID: str = os.getenv("ROBOKASSA_SHOP_ID", "")
    ROBOKASSA_PASSWORD_1: str = os.getenv("ROBOKASSA_PASSWORD_1", "")  # Для SuccessURL
    ROBOKASSA_PASSWORD_2: str = os.getenv("ROBOKASSA_PASSWORD_2", "")  # Для ResultURL
    ROBOKASSA_TEST_MODE: bool = os.getenv("ROBOKASSA_TEST_MODE", "1") == "1"

    # ЮKassa
    YOOKASSA_SHOP_ID: str = os.getenv("YOOKASSA_SHOP_ID", "")
    YOOKASSA_SECRET_KEY: str = os.getenv("YOOKASSA_SECRET_KEY", "")

    # Общие
    DOMAIN_URL: str = os.getenv("DOMAIN_URL", "http://localhost")
    GOAL_AMOUNT: int = 156000  # Цель сбора (рублей)
    
    # Telegram
    #
    # Переменные остались, но уведомления через Telegram больше не уходят:
    # с этого сервера api.telegram.org недоступен. Транспорт уведомлений —
    # почта, см. ниже и app/services/notification_service.py.
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")
    CHAT_ID: str = os.getenv("CHAT_ID", "")

    # Почта: транспорт уведомлений
    #
    # Если SMTP_HOST пуст, отправка не делается вовсе — сервис пишет в лог
    # предупреждение и возвращает управление. Так стек поднимается на машине
    # разработчика без почтового сервера.
    SMTP_HOST: str = os.getenv("SMTP_HOST", "").strip()
    SMTP_PORT: int = int(os.getenv("SMTP_PORT") or 587)
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")

    # Два разных способа шифрования, путать нельзя:
    #   SMTP_SSL=1      — соединение сразу в TLS, обычный порт 465
    #   SMTP_STARTTLS=1 — открытое соединение, потом команда STARTTLS, порт 587
    SMTP_SSL: bool = os.getenv("SMTP_SSL", "0") == "1"
    SMTP_STARTTLS: bool = os.getenv("SMTP_STARTTLS", "1") == "1"
    SMTP_TIMEOUT: int = int(os.getenv("SMTP_TIMEOUT") or 20)

    # Адрес в поле From. По умолчанию совпадает с логином: почти у всех
    # провайдеров отправка от чужого адреса отклоняется.
    EMAIL_FROM: str = os.getenv("EMAIL_FROM") or os.getenv("SMTP_USER", "")
    EMAIL_FROM_NAME: str = os.getenv("EMAIL_FROM_NAME", "EASYSOCHI")

    # Кому уходят уведомления о заявках, звонках и платежах.
    # Несколько адресов — через запятую.
    MANAGER_EMAILS: List[str] = [
        address.strip()
        for address in os.getenv("MANAGER_EMAILS", "").split(",")
        if address.strip()
    ]


settings = Settings()
