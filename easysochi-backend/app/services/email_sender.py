"""Отправка почты. Единственное место в проекте, которое знает про SMTP.

Транспорт намеренно на стандартной библиотеке: smtplib синхронный, поэтому
вызов уводится в поток через anyio. Новая зависимость ради нескольких писем
в день не нужна, а поток на время отправки дешевле, чем ещё один пакет в
requirements.

Функция никогда не бросает исключений. Уведомление — побочный эффект, и его
сбой не должен ронять ни заявку, ни бронирование, ни ответ платёжной системе.
Вызывающий код о неудаче узнаёт по возвращённому False и по логу.
"""

import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr
from typing import Sequence

import anyio.to_thread

from app.core.config import settings

logger = logging.getLogger(__name__)


def describe_configuration() -> str:
    """Одна строка про то, как настроена почта. Пишется при старте.

    Нужна потому, что переменную мало завести в .env: её надо ещё добавить
    в environment контейнера в deploy/docker-compose.yml, иначе приложение
    её не увидит. Без этой строки о промахе узнаёшь по первой пропавшей
    заявке, а не по логу запуска.
    """
    if not settings.SMTP_HOST:
        return "не настроена, SMTP_HOST пуст — письма отправляться не будут"

    if settings.SMTP_SSL:
        mode = "SSL"
    elif settings.SMTP_STARTTLS:
        mode = "STARTTLS"
    else:
        mode = "без шифрования"

    return (
        f"{settings.SMTP_HOST}:{settings.SMTP_PORT} ({mode}), "
        f"отправитель {settings.EMAIL_FROM or 'НЕ ЗАДАН'}, "
        f"адресатов уведомлений: {len(settings.MANAGER_EMAILS)}"
    )


def _build_message(to: Sequence[str], subject: str, body: str) -> EmailMessage:
    message = EmailMessage()
    message["From"] = formataddr((settings.EMAIL_FROM_NAME, settings.EMAIL_FROM))
    message["To"] = ", ".join(to)
    message["Subject"] = subject
    message.set_content(body)
    return message


def _send_sync(to: Sequence[str], subject: str, body: str) -> None:
    """Синхронная отправка. Вызывается только из потока."""
    message = _build_message(to, subject, body)

    if settings.SMTP_SSL:
        smtp = smtplib.SMTP_SSL(
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            timeout=settings.SMTP_TIMEOUT,
            context=ssl.create_default_context(),
        )
    else:
        smtp = smtplib.SMTP(
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            timeout=settings.SMTP_TIMEOUT,
        )

    with smtp:
        if settings.SMTP_STARTTLS and not settings.SMTP_SSL:
            smtp.starttls(context=ssl.create_default_context())
        if settings.SMTP_USER:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        smtp.send_message(message)


async def send_email(to: Sequence[str], subject: str, body: str) -> bool:
    """Отправляет письмо. True, если ушло.

    Адреса получателей в лог не пишем: это персональные данные. В логе
    остаётся количество адресатов и тема — по ним письмо и ищут.
    """
    recipients = [address for address in to if address]

    if not recipients:
        logger.warning("Письмо «%s» не отправлено: некому", subject)
        return False

    if not settings.SMTP_HOST:
        logger.warning(
            "Письмо «%s» не отправлено: SMTP_HOST не задан, почта не настроена",
            subject,
        )
        return False

    if not settings.EMAIL_FROM:
        logger.warning(
            "Письмо «%s» не отправлено: не задан EMAIL_FROM и нечем его заменить",
            subject,
        )
        return False

    try:
        await anyio.to_thread.run_sync(_send_sync, recipients, subject, body)
    except smtplib.SMTPAuthenticationError:
        # Отдельной веткой: самая частая ошибка настройки, и по общему
        # сообщению её не отличить от недоступного сервера.
        logger.error(
            "Письмо «%s» не отправлено: сервер отверг логин и пароль SMTP",
            subject,
        )
        return False
    except Exception as exc:
        # repr, а не str: у таймаутов пустое строковое представление.
        logger.error(
            "Письмо «%s» не отправлено (%s адресатов): %r",
            subject,
            len(recipients),
            exc,
        )
        return False

    logger.info("Отправлено письмо «%s», адресатов: %s", subject, len(recipients))
    return True
