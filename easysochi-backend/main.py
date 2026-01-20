from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
from app.routers import form, donations
from app.db.db_async import engine, Base

app = FastAPI(redirect_slashes=False)

# Настройка CORS — разрешаем отправку с Hugo-домена
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://easysochi.pro", "http://localhost:1313"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
"""
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

@app.post("/form")
async def receive_form(request: Request):
    data = await request.json()
    name = data.get("name")
    email = data.get("email")
    message = data.get("message")

    text = f"📩 Новая заявка с сайта:\n\nИмя: {name}\nEmail: {email}\nСообщение:\n{message}"

    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text}
        )

    return {"status": "ok"}
"""
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.include_router(form.router)
app.include_router(donations.router)
