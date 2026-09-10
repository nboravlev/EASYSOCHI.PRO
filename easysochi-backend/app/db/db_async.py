import os
import logging

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# На уровне INFO SQLAlchemy пишет в лог каждый запрос вместе со значениями
# параметров — то есть email'ы, имена и SignatureValue платежей в открытом
# виде в docker logs. Держим WARNING по умолчанию; для отладки достаточно
# выставить SQL_ECHO=1 в .env.
#
# Уровень задаётся явно, а не наследуется от корневого логгера: SQLAlchemy
# проверяет isEnabledFor(INFO), поэтому при root=INFO запросы посыпались бы
# в лог обратно.
logging.getLogger("sqlalchemy.engine").setLevel(
    logging.INFO if os.getenv("SQL_ECHO") == "1" else logging.WARNING
)

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_async_session():
    async with async_session_maker() as session:
        yield session
