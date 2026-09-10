import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx
from app.routers import form, donations

# Логи приложения: без явной настройки корневого логгера сообщения уровня
# INFO из наших модулей никуда не попадают — у root остаётся уровень WARNING.
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


class HealthcheckFilter(logging.Filter):
    """Убирает из access-лога проверки /health.

    Healthcheck контейнера ходит каждые 10 секунд — это около 8600 строк в
    сутки, которые вытесняют полезные записи из окна ротации docker-логов
    (max-size 10m, max-file 3). Формат аргументов uvicorn.access:
    (client_addr, method, full_path, http_version, status_code).
    """

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        return not (isinstance(args, tuple) and len(args) >= 3 and args[2] == "/health")


logging.getLogger("uvicorn.access").addFilter(HealthcheckFilter())

app = FastAPI(redirect_slashes=False)

# Настройка CORS — разрешаем отправку с Hugo-домена
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://easysochi.pro", "http://localhost:1313"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok"}

app.include_router(form.router, prefix="/api/v2/form", tags=["Form"])
app.include_router(donations.router, prefix="/api/v2/donations", tags=["Donations"])
