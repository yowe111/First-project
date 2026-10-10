"""
database.py — ПОДКЛЮЧЕНИЕ К БАЗЕ ДАННЫХ.

Здесь только соединение, ничего предметного:

- `engine`        — «двигатель», умеет соединяться с базой;
- `session_factory` — фабрика сессий (сессия = одно «общение» с базой);
- `get_session`   — зависимость FastAPI, выдающая сессию на время запроса.

Базовый класс моделей (`Base`) лежит НЕ здесь, а в `src/models/base.py`.
Причина: этот модуль ничего не должен знать о таблицах — иначе получится
круговой импорт, когда модели тянут соединение, а соединение тянет модели.

Таблицы создаёт Alembic (`alembic upgrade head`), а не `create_all`.
"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import settings

# Движок знает адрес базы и открывает соединения по требованию.
engine = create_async_engine(settings.postgres_dsn, echo=False)

# expire_on_commit=False — после commit объекты ещё можно читать,
# иначе SQLAlchemy сбросит их поля и полезет в базу повторно.
session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Зависимость FastAPI: открыть сессию на время запроса и закрыть после."""
    async with session_factory() as session:
        yield session
