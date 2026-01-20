import asyncio
from app.db.db_async import get_async_session
from app.db.models.contact_form import ContactForm
from sqlalchemy import text

async def test_db():
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
    asyncio.run(test_db())
