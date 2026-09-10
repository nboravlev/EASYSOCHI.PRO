import logging
import httpx
from app.core.config import settings

# 🔄 ВЫНЕСЕНО: Отдельный сервис для уведомлений

logger = logging.getLogger(__name__)

class NotificationService:
    """Сервис для отправки уведомлений"""
    
    @staticmethod
    async def send_telegram(text: str) -> bool:
        """Асинхронная отправка уведомления в Telegram"""
        if not settings.TELEGRAM_TOKEN or not settings.CHAT_ID:
            logger.warning("Telegram credentials missing")
            return False
        
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.post(
                    f"https://api.telegram.org/bot{settings.TELEGRAM_TOKEN}/sendMessage",
                    json={"chat_id": settings.CHAT_ID, "text": text}
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Telegram sending error: {e}")
            return False
    
    @staticmethod
    async def notify_successful_payment(amount: float, payment_id: int, method: str = None):
        """Уведомление об успешном платеже"""
        msg = f"💰 Успешный платеж!\nСумма: {amount} ₽\nID: {payment_id}"
        if method:
            msg += f"\nСпособ: {method}"
        await NotificationService.send_telegram(msg)