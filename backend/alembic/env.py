"""
alembic/env.py — как Alembic подключается к нашей базе.

Alembic — это «история изменений» схемы БД. Каждое изменение (добавили колонку,
создали таблицу) лежит отдельным файлом в alembic/versions/.
Команда `alembic upgrade head` применяет все ещё не применённые изменения.

Почему не create_all?
create_all умеет только «создать таблицу, если её нет». Он НЕ умеет
аккуратно ДОБАВИТЬ колонку в уже существующую таблицу. Alembic умеет.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config

# Импортируем Base вместе с моделями: пакет src.models в своём __init__
# подтягивает все таблицы, поэтому Base.metadata здесь заведомо полная.
from src.core.config import settings
from src.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# DSN берём из настроек приложения (.env), а не из alembic.ini.
config.set_main_option("sqlalchemy.url", settings.postgres_dsn)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Офлайн-режим: Alembic печатает SQL, не подключаясь к базе.
    Нужен редко, для генерации скриптов.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Онлайн-режим: подключаемся к базе асинхронно и накатываем миграции."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
