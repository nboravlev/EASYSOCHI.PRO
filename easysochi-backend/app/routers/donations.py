import logging
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, desc, select

from app.db.db_async import get_async_session
from app.db.models.payments import Payment, PaymentStatus
from app.db.models.users import User
from app.services.robokassa_service import RobokassaService
from app.services.notification_service import NotificationService
from app.schemas.payment_schemas import (
    DonationRequest, DonationResponse, 
    StatsResponse, DonorInfo
)
from app.core.config import settings

# 🔄 УЛУЧШЕНО: Роутер стал тонким и чистым

logger = logging.getLogger(__name__)
router = APIRouter(tags=["donations"])

# Инициализируем сервис
payment_service = RobokassaService()


async def get_or_create_user(db: AsyncSession, email: str, name: str) -> User | None:
    """Хелпер для работы с пользователями"""
    if not email:
        return None
    
    # Поиск пользователя
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    
    if not user:
        user = User(email=email, full_name=name)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    elif name and user.full_name != name:
        user.full_name = name
        await db.commit()
    
    return user


@router.post("/create", response_model=DonationResponse)
async def create_donation(
    data: DonationRequest, 
    db: AsyncSession = Depends(get_async_session)
):
    """
    🔄 ИЗМЕНЕНО: Создание платежа через Robokassa
    
    Создает донат и возвращает URL для перенаправления на Robokassa
    """
    # Находим/создаем пользователя
    user = None

    if data.email:
        user = await get_or_create_user(db, data.email, data.name)
    
    try:
        # 🔄 Вызов сервиса Robokassa
        confirmation_url = await payment_service.create_payment(
            amount=data.amount,
            name=data.name,
            email=data.email,
            user_id=user.id if user else None,
            db=db
        )
        
        return DonationResponse(confirmation_url=confirmation_url)
        
    except Exception as e:
        logger.error(f"Error creating payment: {e}")
        raise HTTPException(status_code=500, detail="Payment creation failed")


@router.post("/webhook", response_class=PlainTextResponse)
async def payment_webhook(
    request: Request, 
    db: AsyncSession = Depends(get_async_session)
):
    """
    Вебхук от Robokassa (ResultURL).

    Тело ответа должно быть ровно "OK<номер счёта>" открытым текстом — так
    описан ResultURL в документации Robokassa. Любой другой ответ, включая
    JSON с той же строкой внутри поля, она считает неуспехом и повторяет
    уведомление, пока не получит ожидаемый текст.

    IP проверяется на уровне Nginx (geo $is_payment_service), подпись —
    в RobokassaService по паролю #2.
    """
    logger.info("=== Входящий вебхук от Robokassa ===")
    
    try:
        # Robokassa отправляет form-data, а не JSON
        form_data = await request.form()
        data = dict(form_data)
        
        logger.info(f"Webhook data: {data}")
        
        result = await payment_service.process_webhook(data, db)
        
        if "error" in result:
            # Неверная подпись или нехватка параметров: подтверждать нечего.
            # 400 не даёт подделанному уведомлению выглядеть принятым и
            # отличим в логах от нормальной обработки.
            logger.warning(f"Webhook rejected: {result['error']}")
            return PlainTextResponse(result["error"], status_code=400)
        
        return PlainTextResponse(result["detail"])
        
    except Exception:
        # 500 — сигнал Robokassa повторить уведомление позже: ошибка на нашей
        # стороне, платёж при этом мог быть успешным
        logger.exception("Webhook error")
        return PlainTextResponse("Internal error", status_code=500)


@router.get("/stats", response_model=StatsResponse)
async def get_donation_stats(
    db: AsyncSession = Depends(get_async_session)
):
    """Статистика донатов для отображения на сайте"""
    
    # Общая сумма успешных платежей
    result_sum = await db.execute(
        select(func.sum(Payment.amount))
        .where(Payment.status == PaymentStatus.succeeded)
    )
    total_cents = result_sum.scalar() or 0
    total_rub = int(total_cents / 100)
    
    # Последние 10 донатов
    result_list = await db.execute(
        select(Payment, User)
        .outerjoin(User, Payment.user_id == User.id)
        .where(Payment.status == PaymentStatus.succeeded)
        .order_by(desc(Payment.created_at))
        .limit(10)
    )
    
    donors_data = []
    for payment, user in result_list:
        name_display = "Аноним"
        if user and user.full_name:
            name_display = user.full_name
        elif payment.metadata and payment.metadata.get("name"):
            name_display = payment.metadata["name"]
        
        donors_data.append(DonorInfo(
            name=name_display,
            amount=int(payment.amount / 100)
        ))
    
    return StatsResponse(
        raised=total_rub,
        goal=settings.GOAL_AMOUNT,
        donors=donors_data
    )
