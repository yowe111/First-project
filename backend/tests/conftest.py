"""
Общие фикстуры для тестов.

Идея: настоящее приложение ходит в PostgreSQL. В тестах мы подменяем
базу на SQLite в памяти — так тесты гоняются быстро и без Docker.

Порядок важен: сначала прописываем переменные окружения,
и только потом импортируем приложение (оно читает настройки при импорте).
"""

from collections.abc import AsyncIterator

import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

os.environ["POSTGRES_DSN"] = "sqlite+aiosqlite://"
os.environ["SECRET_KEY"] = "test-secret-key-do-not-use-in-prod"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"

from src.core.database import get_session  # noqa: E402
from src.main import app  # noqa: E402
from src.models import Base  # noqa: E402


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Живой HTTP-клиент, который бьёт в наше FastAPI-приложение.

    На каждый тест:
    1) создаём чистую базу в памяти;
    2) подменяем зависимость get_session;
    3) после теста всё выбрасываем — следующий тест стартует с нуля.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        follow_redirects=True,
    ) as http:
        yield http

    app.dependency_overrides.clear()
    await engine.dispose()
