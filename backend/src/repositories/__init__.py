"""
repositories — ДОСТУП К ДАННЫМ.

Единственный слой, которому разрешено писать запросы к базе.
Ни роутеры, ни сервисы не должны содержать `select(...)`.

Иерархия: `BaseRepository` знает общие операции, наследники добавляют
запросы, специфичные для своей таблицы.
"""

from src.repositories.base import BaseRepository
from src.repositories.note import NoteRepository
from src.repositories.user import UserRepository

__all__ = [
    "BaseRepository",
    "NoteRepository",
    "UserRepository",
]
