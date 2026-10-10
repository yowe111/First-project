"""
base.py — ОСНОВА ВСЕХ ТАБЛИЦ.

Напоминание о том, что такое модель:

    класс   = таблица
    атрибут = колонка
    объект  = одна строка

Кроме базового класса здесь лежат **миксины** — маленькие классы с набором
готовых колонок. Миксин сам по себе таблицей не является; его «подмешивают»
к модели, чтобы не переписывать одни и те же поля в каждой из них.

Когда в проекте появятся датасеты, задачи и результаты анализов, каждая из
этих таблиц тоже получит `id` и `created_at` — и не придётся копировать
объявления колонок пять раз.
"""

from datetime import datetime

from sqlalchemy import TIMESTAMP, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Общий предок всех моделей.

    В `Base.metadata` SQLAlchemy собирает описание всех таблиц проекта.
    Именно оттуда Alembic узнаёт, какой должна быть схема базы.
    """


class IntIdMixin:
    """Целочисленный первичный ключ с автонумерацией."""

    id: Mapped[int] = mapped_column(primary_key=True)


class TimestampMixin:
    """Момент создания строки.

    `server_default=func.now()` означает, что время проставит сама база,
    а не Python. Так значение будет корректным даже для строк, вставленных
    в обход приложения — например, из миграции или psql.
    """

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.now(),
    )
