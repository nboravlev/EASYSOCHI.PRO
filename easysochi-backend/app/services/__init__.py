"""Фабрика платёжного сервиса.

Активная система выбирается переменной PAYMENT_PROVIDER в .env. Одновременно
работает ровно один провайдер: два включённых потребовали бы двух вебхук-
эндпоинтов и двух схем проверки подписи без какого-либо выигрыша.
"""
from app.core.config import settings
from app.services.payment_service import (
    PaymentService,
    PROVIDER_ROBOKASSA,
    PROVIDER_YOOKASSA,
    SUPPORTED_PROVIDERS,
)


def get_payment_service() -> PaymentService:
    """Вернуть сервис активной платёжной системы.

    Падает на импорте роутера, если PAYMENT_PROVIDER задан неизвестным
    значением — лучше не подняться при старте, чем молча принимать платежи
    не туда.
    """
    provider = settings.PAYMENT_PROVIDER

    if provider == PROVIDER_ROBOKASSA:
        from app.services.robokassa_service import RobokassaService
        return RobokassaService()

    if provider == PROVIDER_YOOKASSA:
        from app.services.yookassa_service import YookassaService
        return YookassaService()

    raise ValueError(
        f"Неизвестный PAYMENT_PROVIDER={provider!r}. "
        f"Допустимые значения: {', '.join(SUPPORTED_PROVIDERS)}"
    )


__all__ = ["get_payment_service", "PaymentService", "SUPPORTED_PROVIDERS"]
