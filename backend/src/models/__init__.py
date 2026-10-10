"""
models — ТАБЛИЦЫ БАЗЫ ДАННЫХ.

Каждая таблица живёт в своём файле, а здесь они собираются вместе.

Почему все модели обязательно импортируются в этом файле: SQLAlchemy узнаёт
о таблице только в момент импорта её класса. Если модель нигде не
импортирована, `Base.metadata` окажется неполной — и Alembic при
`--autogenerate` решит, что таблицу нужно удалить. Поэтому новую модель
всегда добавляем в этот список.
"""

from src.models.base import Base, IntIdMixin, TimestampMixin
from src.models.note import Note
from src.models.user import User

__all__ = [
    "Base",
    "IntIdMixin",
    "Note",
    "TimestampMixin",
    "User",
]
