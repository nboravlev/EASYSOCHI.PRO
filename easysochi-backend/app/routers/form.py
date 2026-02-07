from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from app.db.db_async import get_async_session
from app.db.models.contact_form import ContactForm
import httpx, os, logging

router = APIRouter(tags=["form"])

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

logger = logging.getLogger(__name__)

@router.post("/")
async def receive_form(request: Request, db: AsyncSession = Depends(get_async_session)):
    # Получаем данные из запроса
    data = await request.json()
    print(f"DEBUG: received data = {data}")  # для проверки

    name = data.get("name")
    email = data.get("email")
    message = data.get("message")

    if not name or not email or not message:
        raise HTTPException(status_code=400, detail="Missing required fields")

    form_entry = ContactForm(name=name, email=email, message=message)

    try:
        db.add(form_entry)
        await db.commit()
        await db.refresh(form_entry)
        print(f"Inserted record with ID: {form_entry.id}")

    except SQLAlchemyError as e:
        await db.rollback()
        logger.exception("Failed to save form to DB")
        raise HTTPException(status_code=500, detail="DB error")

    # Отправка уведомления в Telegram
    text = f"📩 Новая заявка:\nИмя: {name}\nEmail: {email}\nСообщение:\n{message}"
    print(f"DEBUG: Sending to TG: {text} to chat {CHAT_ID}")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": CHAT_ID, "text": text}
            )
            print(f"DEBUG: TG API Response: {response.text}")
    except httpx.HTTPError as e:
        logger.warning(f"Telegram notification failed: {e}")

    return {"status": "ok"}
