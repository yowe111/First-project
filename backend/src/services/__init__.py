"""
services — БИЗНЕС-ЛОГИКА.

Слой, который знает правила продукта: кто что может, что считается
конфликтом, что происходит при регистрации.

Что сервису запрещено:

- писать SQL — для этого есть репозитории;
- бросать `HTTPException` и вообще знать про HTTP — для этого есть
  исключения из `src/core/exceptions.py` и роутеры.

Проверить, что слой получился чистым, легко: если в файле нет ни одного
импорта из `fastapi` и ни одного `select(...)` — всё в порядке.
"""

from src.services.auth import AuthService
from src.services.note import NoteService
from src.services.user import UserService

__all__ = [
    "AuthService",
    "NoteService",
    "UserService",
]
