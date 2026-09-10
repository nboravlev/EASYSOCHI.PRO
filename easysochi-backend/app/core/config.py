import os
from typing import List

# 🔄 ВЫНЕСЕНО: Все конфиги и константы

class Settings:
    # Robokassa
    ROBOKASSA_SHOP_ID: str = os.getenv("ROBOKASSA_SHOP_ID", "")
    ROBOKASSA_PASSWORD_1: str = os.getenv("ROBOKASSA_PASSWORD_1", "")  # Для SuccessURL
    ROBOKASSA_PASSWORD_2: str = os.getenv("ROBOKASSA_PASSWORD_2", "")  # Для ResultURL
    ROBOKASSA_TEST_MODE: bool = os.getenv("ROBOKASSA_TEST_MODE", "1") == "1"
    
    # Общие
    DOMAIN_URL: str = os.getenv("DOMAIN_URL", "http://localhost")
    GOAL_AMOUNT: int = 156000  # Цель сбора (рублей)
    
    # Telegram
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")
    CHAT_ID: str = os.getenv("CHAT_ID", "")
    

settings = Settings()