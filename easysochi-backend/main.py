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

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.include_router(form.router, prefix="/api/v2/form", tags=["Form"])
app.include_router(donations.router, prefix="/api/v2/donations", tags=["Donations"])
