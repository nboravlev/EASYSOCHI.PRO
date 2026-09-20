"""Уведомления менеджеру. Единственная точка, где решается, кому и что писать.

До этого уведомления жили в двух местах и по-разному: заявка с формы
отправлялась прямо из роутера функцией notify_telegram, платёж — отсюда же,
но статическим методом. Транспорт у обоих был один — Telegram, а он с этого
сервера недоступен: на соседнем проекте, который стоит на той же машине,
в логах был ConnectTimeout, и ни одно уведомление не доходило. Проверять
это здесь по одному нечем: отправка в фоне, и её неудача в ответ формы не
попадает — заявка сохраняется, посетитель видит «спасибо», а менеджер не
видит ничего.

Теперь один сервис и один транспорт — почта (app/services/email_sender.py).
Текст письма собирается здесь, отправка живёт там.

Правила, общие для всех методов:
  * ничего не бросают. Уведомление — побочный эффект, и его сбой не должен
    ронять заявку или ответ платёжной системе;
  * возвращают True, если письмо ушло;
  * в лог не попадают ни адреса, ни тексты обращений — только идентификаторы.
    Персональные данные из логов убирали отдельной задачей, возвращать их
    незачем.
"""

import logging
from typing import Optional, Sequence

from app.core.config import settings
from app.services.email_sender import send_email

logger = logging.getLogger(__name__)

CONTACT_LABELS = {
    "email": "Почта",
    "phone": "Телефон",
    "telegram": "Telegram",
}


class NotificationService:
    """Сбор текста уведомлений и отправка их почтой."""

    @property
    def manager_emails(self) -> Sequence[str]:
        return settings.MANAGER_EMAILS

    def _warn_no_managers(self, what: str) -> None:
        logger.warning(
            "Уведомление (%s) не отправлено: не задан MANAGER_EMAILS", what
        )

    async def notify_new_contact_form(
        self,
        *,
        form_id: int,
        name: str,
        contact_type: str,
        contact_value: str,
        topic: str,
        source: Optional[str],
        message: str,
    ) -> bool:
        """Заявка с формы обратной связи."""
        if not self.manager_emails:
            self._warn_no_managers("заявка с формы")
            return False

        contact_label = CONTACT_LABELS.get(contact_type, contact_type or "Контакт")

        body = "\n".join(
            [
                "Новая заявка с сайта.",
                "",
                f"Имя: {name}",
                f"{contact_label}: {contact_value}",
                f"Тема: {topic}",
                f"Источник: {source or 'не указан'}",
                "",
                "Сообщение:",
                message or "(пусто)",
            ]
        )

        sent = await send_email(
            self.manager_emails,
            f"Заявка с сайта #{form_id}",
            body,
        )
        logger.info("Уведомление о заявке id=%s: отправлено=%s", form_id, sent)
        return sent

    async def notify_callback_request(
        self,
        *,
        form_id: int,
        name: str,
        phone: str,
        source: Optional[str],
    ) -> bool:
        """Запрос обратного звонка.

        Отдельное письмо, а не заявка с пустым текстом: здесь от менеджера
        требуется действие — позвонить, — и тема письма должна говорить об
        этом сразу, не открывая.
        """
        if not self.manager_emails:
            self._warn_no_managers("запрос обратного звонка")
            return False

        body = "\n".join(
            [
                "Запрос обратного звонка.",
                "",
                f"Имя: {name}",
                f"Телефон: {phone}",
                f"Источник: {source or 'не указан'}",
            ]
        )

        sent = await send_email(
            self.manager_emails,
            f"Перезвонить: {name}",
            body,
        )
        logger.info("Уведомление о звонке id=%s: отправлено=%s", form_id, sent)
        return sent

    async def notify_successful_payment(
        self,
        *,
        payment_id: int,
        amount: float,
        method: Optional[str] = None,
    ) -> bool:
        """Успешный платёж.

        amount приходит уже в рублях: в базе сумма хранится в копейках, и
        перевод делает вызывающий код — он же знает, в каких единицах пришла
        сумма от платёжной системы.
        """
        if not self.manager_emails:
            self._warn_no_managers("успешный платёж")
            return False

        lines = [
            "Поступил платёж.",
            "",
            f"Сумма: {amount:,.2f} ₽".replace(",", " "),
            f"Платёж #{payment_id}",
            f"Платёжная система: {settings.PAYMENT_PROVIDER}",
        ]
        if method:
            lines.append(f"Способ оплаты: {method}")

        sent = await send_email(
            self.manager_emails,
            f"Платёж #{payment_id}",
            "\n".join(lines),
        )
        logger.info("Уведомление о платеже id=%s: отправлено=%s", payment_id, sent)
        return sent


# Один экземпляр на приложение. Состояния у сервиса нет, но обращаться к нему
# как к объекту, а не к классу, удобнее: вызовы читаются одинаково и в
# роутерах, и в платёжных сервисах.
notification_service = NotificationService()
