#!/usr/bin/env python3
"""Проверка подключения к БД из асинхронной сессии.

Скрипт, а не pytest-набор — имена намеренно не начинаются с test_.

ВНИМАНИЕ: вставляет НАСТОЯЩУЮ запись в таблицу contact_form. Раньше файл
назывался app/test_db_async.py с функцией test_db(), то есть pytest подобрал
бы его по имени и насорил бы в боевой базе при любом запуске в этом каталоге.

Запуск:
    docker exec -i easysochi_contact_api python3 - \n        < easysochi-backend/app/test/check_db_async.py
"""
import asyncio
from app.db.db_async import get_async_session
from app.db.models.contact_form import ContactForm
from sqlalchemy import text

async def check_db():
    # Получаем сессию через get_async_session()
    async for session in get_async_session():  # используем генератор
        result = await session.execute(text("SELECT NOW()"))
        print(result.scalar())

        # Вставка тестовой записи
        test_form = ContactForm(
            name="Test Ivan",
            email="test@mail.com",
            message="Text"
        )
        session.add(test_form)
        await session.commit()
        await session.refresh(test_form)
        print(f"Inserted test record with ID: {test_form.id}")

if __name__ == "__main__":
    asyncio.run(check_db())
