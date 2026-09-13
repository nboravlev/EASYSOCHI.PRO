from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

# 🔄 ВЫНЕСЕНО: Абстракция для разных платежных систем

# Значения колонки payments.provider и переменной PAYMENT_PROVIDER в .env
PROVIDER_ROBOKASSA = "robokassa"
PROVIDER_YOOKASSA = "yookassa"
SUPPORTED_PROVIDERS = (PROVIDER_ROBOKASSA, PROVIDER_YOOKASSA)


class PaymentService(ABC):
    """Абстрактный класс для платежных систем"""

    #: Имя провайдера, попадает в payments.provider. Задаётся в наследнике.
    provider: str

    @abstractmethod
    async def parse_webhook(self, request: Request) -> Dict[str, Any]:
        """Разобрать тело вебхука.

        Вынесено в сервис, потому что системы шлют разное: Robokassa —
        form-data, ЮKassa — JSON. Роутер не должен об этом знать.
        """
        pass

    @abstractmethod
    async def create_payment(
        self,
        amount: int,
        name: Optional[str],
        email: Optional[str],
        user_id: Optional[int],
        db: AsyncSession
    ) -> str:
        """Создать платеж и вернуть URL для оплаты"""
        pass
    
    @abstractmethod
    async def process_webhook(
        self,
        request_data: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Обработать вебхук от платежной системы.

        Возвращает либо {"error": "..."} — тогда роутер отдаёт 400, либо
        {"status": "ok", "detail": "<тело ответа>"} — роутер отдаёт detail
        открытым текстом. Robokassa требует ровно "OK<InvId>", ЮKassa
        достаточно кода 200 с любым телом.
        """
        pass
