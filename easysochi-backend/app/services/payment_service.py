from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

# 🔄 ВЫНЕСЕНО: Абстракция для разных платежных систем

class PaymentService(ABC):
    """Абстрактный класс для платежных систем"""
    
    @abstractmethod
    async def create_payment(
        self,
        amount: int,
        name: Optional[str],
        email: Optional[str],
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
        """Обработать вебхук от платежной системы"""
        pass