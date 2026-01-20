import os
import uuid
import logging
import httpx
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc

from yookassa import Configuration, Payment as YookassaPayment
from app.db.db_async import get_async_session

from app.db.models.users import User
from app.db.models.payments import Payment, PaymentStatus
from app.db.models.payment_events import PaymentEvent

# --- Настройка ---
router = APIRouter(prefix="/donation", tags=["donation"])
logger = logging.getLogger(__name__)

YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")
DOMAIN_URL = os.getenv("DOMAIN_URL", "http://localhost")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GOAL_AMOUNT = 156000  # Цель сбора (рублей)
# Список IP-адресов ЮKassa для проверки (рекомендуется)
YOOKASSA_IPS = [
    "185.71.76.0/27",
    "185.71.77.0/27",
    "77.75.153.0/25",
    "77.75.156.11",
    "77.75.156.35",
    "77.75.154.128/25",
    "2a02:5180::/32"
]

# Инициализация ЮКассы
if YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY:
    Configuration.account_id = YOOKASSA_SHOP_ID
    Configuration.secret_key = YOOKASSA_SECRET_KEY
else:
    logger.warning("Yookassa keys are missing in env!")

# --- Pydantic схемы ---

class DonationRequest(BaseModel):
    amount: int = Field(..., ge=50, description="Сумма в рублях")
    name: Optional[str] = Field(None, max_length=150)
    email: Optional[str] = Field(None, max_length=150)

class DonationResponse(BaseModel):
    confirmation_url: str

class DonorInfo(BaseModel):
    name: str
    amount: int
    
class StatsResponse(BaseModel):
    raised: int
    goal: int
    donors: List[DonorInfo]


# --- Хелперы ---

async def send_telegram_notification(text: str):
    """Асинхронная отправка уведомления в Telegram"""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": CHAT_ID, "text": text}
            )
    except Exception as e:
        logger.error(f"Telegram sending error: {e}")

async def get_or_create_user(db: AsyncSession, email: str, name: str) -> User:
    """Ищет пользователя по email или создает нового"""
    if not email:
        return None
    
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    
    if not user:
        user = User(email=email, full_name=name)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    elif name and user.full_name != name:
        # Обновим имя, если оно изменилось
        user.full_name = name
        await db.commit()
    
    return user

# --- Эндпоинты ---

@router.post("/create", response_model=DonationResponse)
async def create_donation(data: DonationRequest, db: AsyncSession = Depends(get_async_session)):
    """1. Создание платежа"""
    
    # Находим/создаем юзера (если введен email)
    user = None
    if data.email:
        user = await get_or_create_user(db, data.email, data.name)

    idempotence_key = str(uuid.uuid4())
    amount_rub = data.amount
    
    # Формируем объект для ЮКассы
    payment_data = {
        "amount": {
            "value": f"{amount_rub}.00",
            "currency": "RUB"
        },
        "capture": True,
        "confirmation": {
            "type": "redirect",
            # После оплаты вернем пользователя на главную (можно сделать отдельную страницу "спасибо")
            "return_url": f"{DOMAIN_URL}/" 
        },
        "description": f"Платеж от {data.name or 'анонима'}",
        "metadata": {
            "email": data.email,
            "name": data.name
        }
    }

    try:
        # Запрос к API Юкассы (синхронный вызов)
        yk_payment = YookassaPayment.create(payment_data, idempotence_key)
        
        # Сохраняем в БД
        new_payment = Payment(
            user_id=user.id if user else None,
            yk_payment_id=yk_payment.id,
            amount=amount_rub * 100,  # Конвертируем в копейки для хранения в Integer
            currency="RUB",
            description=payment_data["description"],
            status=PaymentStatus.pending,
            confirmation_url=yk_payment.confirmation.confirmation_url,
            paid=False
        )
        db.add(new_payment)
        await db.commit()
        
        return {"confirmation_url": yk_payment.confirmation.confirmation_url}

    except Exception as e:
        logger.error(f"Error creating payment: {e}")
        raise HTTPException(status_code=500, detail="Payment creation failed")


@router.post("/webhook")
async def yookassa_webhook(request: Request, db: AsyncSession = Depends(get_async_session)):
    """ 1. Логируем сам факт прихода запроса (для отладки в docker logs)"""
    logger.info("=== Входящий вебхук от ЮKassa ===")
    """2. Прием уведомлений от ЮКассы (Webhook)"""
    try:
        data = await request.json()
        event = data.get("event")
        obj = data.get("object", {})
        yk_id = obj.get("id")
        status = obj.get("status")

        logger.info(f"Событие: {event}, ID: {yk_id}, Статус: {status}")
        
        if not yk_id:
            return {"status": "error", "detail": "No ID"}

        # Ищем платеж в БД
        result = await db.execute(select(Payment).where(Payment.yk_payment_id == yk_id))
        payment = result.scalars().first()

        if not payment:
            # Платеж не найден (странно, но бывает)
            return {"status": "ok"}

        # Логируем событие
        new_event = PaymentEvent(
            payment_id=payment.id,
            event_type=event,
            raw_data=data
        )
        db.add(new_event)

        # Обновляем статус платежа
        if status == "succeeded":
            payment.status = PaymentStatus.succeeded
            payment.paid = True
            # Уведомляем админа в телегу
            amount_rub = payment.amount / 100
            msg = f"💰 Успешный платеж!\nСумма: {amount_rub} ₽\nID: {payment.id}"
            await send_telegram_notification(msg)
            
        elif status == "canceled":
            payment.status = PaymentStatus.canceled
        
        await db.commit()
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        # ЮКасса ждет 200 OK, иначе будет слать повторы. 
        # Если ошибка критичная, можно вернуть 500, но лучше логировать и возвращать 200.
        return {"status": "error"}

    return {"status": "ok"}


@router.get("/stats", response_model=StatsResponse)
async def get_donation_stats(db: AsyncSession = Depends(get_async_session)):
    """3. Получение статистики для сайта"""
    
    # 1. Считаем общую сумму успешных платежей
    # amount хранится в копейках, поэтому делим на 100
    query_sum = select(func.sum(Payment.amount)).where(Payment.status == PaymentStatus.succeeded)
    result_sum = await db.execute(query_sum)
    total_cents = result_sum.scalar() or 0
    total_rub = int(total_cents / 100)

    # 2. Получаем последние 10 донатов
    # Делаем join с Users, чтобы получить имя, если оно есть
    query_list = (
        select(Payment, User)
        .outerjoin(User, Payment.user_id == User.id)
        .where(Payment.status == PaymentStatus.succeeded)
        .order_by(desc(Payment.created_at))
        .limit(10)
    )
    result_list = await db.execute(query_list)
    
    donors_data = []
    for payment, user in result_list:
        # Если есть user.full_name берем его, иначе fallback, иначе Аноним
        name_display = "Аноним"
        if user and user.full_name:
            name_display = user.full_name
        # Иногда имя может прийти в метаданных платежа, но для простоты берем из User
        
        donors_data.append(DonorInfo(
            name=name_display,
            amount=int(payment.amount / 100)
        ))

    return {
        "raised": total_rub,
        "goal": GOAL_AMOUNT,
        "donors": donors_data
    }