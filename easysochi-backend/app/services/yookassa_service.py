import asyncio
import logging
import uuid
from typing import Dict, Any, Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from yookassa import Configuration, Payment as YookassaPayment

from app.services.payment_service import PaymentService, PROVIDER_YOOKASSA
from app.services.notification_service import NotificationService
from app.core.config import settings
from app.db.models.payments import Payment, PaymentStatus
from app.db.models.payment_events import PaymentEvent

# Реализация для ЮKassa. Логика перенесена из app/routers/_donations.py —
# старого роутера, который остался после перехода на Robokassa и никуда
# не подключался.

logger = logging.getLogger(__name__)


class YookassaService(PaymentService):
    """Реализация платежного сервиса ЮKassa"""

    provider = PROVIDER_YOOKASSA

    def __init__(self):
        if not settings.YOOKASSA_SHOP_ID or not settings.YOOKASSA_SECRET_KEY:
            # Не падаем на старте: ключи могут быть не заведены, пока провайдер
            # не активирован. Ошибка вылезет при первой попытке создать платёж.
            logger.warning("YOOKASSA_SHOP_ID / YOOKASSA_SECRET_KEY не заданы в .env")
        else:
            Configuration.account_id = settings.YOOKASSA_SHOP_ID
            Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

    async def parse_webhook(self, request: Request) -> Dict[str, Any]:
        """ЮKassa шлёт уведомление как JSON."""
        return await request.json()

    async def create_payment(
        self,
        amount: int,
        name: Optional[str],
        email: Optional[str],
        user_id: Optional[int],
        db: AsyncSession
    ) -> str:
        """Создание платежа в ЮKassa"""

        idempotence_key = str(uuid.uuid4())
        description = f"Платеж от {name or 'анонима'}"

        payment_data = {
            "amount": {
                "value": f"{amount}.00",
                "currency": "RUB",
            },
            "capture": True,
            "confirmation": {
                "type": "redirect",
                "return_url": f"{settings.DOMAIN_URL}/",
            },
            "description": description,
            "metadata": {
                "email": email,
                "name": name,
            },
        }

        # Клиент ЮKassa синхронный, а мы внутри событийного цикла — уводим
        # блокирующий HTTP-вызов в поток, иначе он тормозит весь воркер.
        yk_payment = await asyncio.to_thread(
            YookassaPayment.create, payment_data, idempotence_key
        )

        confirmation_url = yk_payment.confirmation.confirmation_url

        new_payment = Payment(
            user_id=user_id,
            provider=self.provider,
            provider_payment_id=yk_payment.id,
            amount=amount * 100,  # В копейки
            currency="RUB",
            description=description,
            status=PaymentStatus.pending,
            confirmation_url=confirmation_url,
            paid=False,
            extradata={"email": email, "name": name},
        )
        db.add(new_payment)
        await db.commit()
        await db.refresh(new_payment)

        return confirmation_url

    async def process_webhook(
        self,
        request_data: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Обработка вебхука от ЮKassa.

        Подпись ЮKassa не передаёт — подлинность уведомления обеспечивается
        фильтрацией по IP на уровне nginx (geo $is_payment_service в
        nginx/conf.d/payments_ids.geo) и тем, что идентификатор платежа должен
        найтись в нашей базе.
        """
        event = request_data.get("event")
        obj = request_data.get("object") or {}
        yk_id = obj.get("id")
        status = obj.get("status")

        logger.info(f"Processing webhook: event={event}, id={yk_id}, status={status}")

        if not yk_id:
            return {"error": "Missing payment id"}

        result = await db.execute(
            select(Payment).where(
                Payment.provider == self.provider,
                Payment.provider_payment_id == str(yk_id),
            )
        )
        payment = result.scalars().first()

        if not payment:
            # Подтверждаем приём, иначе ЮKassa будет слать повторы по платежу,
            # которого у нас всё равно нет.
            logger.warning(f"Payment not found for id {yk_id}")
            return {"status": "ok", "detail": "OK"}

        db.add(PaymentEvent(
            payment_id=payment.id,
            event_type=event or "unknown",
            raw_data=request_data,
        ))

        if status == "succeeded":
            payment.status = PaymentStatus.succeeded
            payment.paid = True
            await NotificationService.notify_successful_payment(
                amount=payment.amount / 100,
                payment_id=payment.id,
                method=(obj.get("payment_method") or {}).get("type"),
            )
        elif status == "canceled":
            payment.status = PaymentStatus.canceled

        await db.commit()

        # ЮKassa считает уведомление принятым по коду 200, тело ей безразлично.
        return {"status": "ok", "detail": "OK"}
