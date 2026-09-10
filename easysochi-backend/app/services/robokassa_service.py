import hashlib
import uuid
import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.payment_service import PaymentService
from app.services.notification_service import NotificationService
from app.core.config import settings
from app.db.models.payments import Payment, PaymentStatus
from app.db.models.payment_events import PaymentEvent
from app.db.models.users import User

# 🔄 НОВЫЙ: Полная реализация для Robokassa

logger = logging.getLogger(__name__)

class RobokassaService(PaymentService):
    """Реализация платежного сервиса Robokassa"""
    
    def __init__(self):
        self.shop_id = settings.ROBOKASSA_SHOP_ID
        self.password_1 = settings.ROBOKASSA_PASSWORD_1
        self.password_2 = settings.ROBOKASSA_PASSWORD_2
        self.test_mode = settings.ROBOKASSA_TEST_MODE
        
        # URL для запросов к Robokassa
        self.api_url = "https://auth.robokassa.ru/Merchant/Index.aspx"
    
    def _generate_signature(self, out_sum: str, inv_id: str, password: str, shp_params: dict = None) -> str:
        """Генерация MD5 подписи"""
        sign_str = f"{out_sum}:{inv_id}:{password}"
        
        if shp_params:
            for param_name in sorted(shp_params.keys()):
                sign_str += f":{param_name}={shp_params[param_name]}"
        
        return hashlib.md5(sign_str.encode('utf-8')).hexdigest().upper()
    
    async def create_payment(
        self,
        amount: int,
        name: Optional[str],
        email: Optional[str],
        user_id: Optional[int],
        db: AsyncSession
    ) -> str:
        """Создание платежа в Robokassa"""
        
        # Генерируем уникальный номер заказа (InvId)
        # Можно использовать ID в БД или отдельную последовательность
        inv_id = uuid.uuid4().int & 0xFFFFFFFF  # 32-битное число
        
        # Сумма с копейками
        out_sum = f"{amount:.2f}"
        
        # Формируем параметры для Robokassa
        # 🔄 С пользовательскими параметрами (Shp_)
        shp_params = {
            "Shp_email": email or "",
            "Shp_name": name or "",
            "Shp_user_id": str(user_id) if user_id else ""
        }
        
        # Генерируем подпись (используем пароль #1 для создания платежа)
        signature = self._generate_signature(out_sum, str(inv_id), self.password_1, shp_params)
        
        # Строим URL для редиректа пользователя
        redirect_url = (
            f"{self.api_url}?"
            f"MerchantLogin={self.shop_id}"
            f"&OutSum={out_sum}"
            f"&InvId={inv_id}"
            f"&SignatureValue={signature}"
            f"&Description=Donation from {name or 'anon'}"
            f"&Culture=ru"
        )
        
        # Добавляем пользовательские параметры
        for key, value in shp_params.items():
            if value:
                redirect_url += f"&{key}={value}"
        
        print(f"PAYMENT DEBUG: Final interpreted test_mode: {self.test_mode}, flush=True")
        # Добавляем тестовый режим
        if self.test_mode:
            redirect_url += "&IsTest=1"

        
        # Сохраняем платеж в БД
        new_payment = Payment(
            user_id=user_id,
            yk_payment_id=str(inv_id),
            amount=int(amount * 100),  # В копейки
            currency="RUB",
            description=f"Donation from {name or 'anon'}",
            status=PaymentStatus.pending,
            confirmation_url=redirect_url,
            paid=False,
            metadata={"email": email, "name": name}
        )
        db.add(new_payment)
        await db.commit()
        await db.refresh(new_payment)
        
        return redirect_url
    
    async def process_webhook(
        self,
        request_data: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Обработка вебхука от Robokassa (ResultURL)"""
        
        # Извлекаем параметры
        out_sum = request_data.get("OutSum")
        inv_id = request_data.get("InvId")
        signature = request_data.get("SignatureValue")
        
        logger.info(f"Processing webhook: InvId={inv_id}, OutSum={out_sum}")
        
        if not inv_id or not out_sum:
            return {"error": "Missing required parameters"}
        
        # Извлекаем пользовательские параметры
        shp_params = {k: v for k, v in request_data.items() if k.startswith("Shp_")}
        
        # Проверяем подпись (используем пароль #2 для вебхука)
        computed_sig = self._generate_signature(out_sum, inv_id, self.password_2, shp_params)
        
        if computed_sig != signature:
            logger.error(f"Invalid signature for InvId {inv_id}")
            return {"error": "Invalid signature"}
        
        # Ищем платеж в БД
        result = await db.execute(
            select(Payment).where(Payment.yk_payment_id == str(inv_id))
        )
        payment = result.scalars().first()
        
        if not payment:
            logger.warning(f"Payment not found for InvId {inv_id}")
            return {"status": "ok", "detail": f"OK{inv_id}"}
        
        # Логируем событие
        event = PaymentEvent(
            payment_id=payment.id,
            event_type="payment.succeeded",
            raw_data=request_data
        )
        db.add(event)
        
        # Обновляем статус
        payment.status = PaymentStatus.succeeded
        payment.paid = True
        
        # Уведомляем
        amount_rub = float(out_sum)
        await NotificationService.notify_successful_payment(
            amount=amount_rub,
            payment_id=payment.id,
            method=request_data.get("PaymentMethod")
        )
        
        await db.commit()
        
        # 🔄 Robokassa ожидает именно такой формат ответа
        return {"status": "ok", "detail": f"OK{inv_id}"}