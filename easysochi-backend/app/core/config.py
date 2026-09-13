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
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")
    CHAT_ID: str = os.getenv("CHAT_ID", "")
    

settings = Settings()
