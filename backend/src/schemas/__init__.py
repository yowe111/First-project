"""
schemas — ФОРМА ДАННЫХ НА ГРАНИЦЕ API.

Схемы Pydantic решают три задачи сразу:

1. проверяют входящие данные (не то прислали — FastAPI сам вернёт 422);
2. формируют ответ, отбрасывая лишние поля;
3. из них строится документация на `/docs`.
"""

from src.schemas.auth import Token
from src.schemas.common import Message, Page
from src.schemas.note import NoteCreate, NoteRead, NoteUpdate
from src.schemas.user import (
    PasswordChange,
    RoleUpdate,
    UserCreate,
    UserRead,
    UserUpdate,
)

__all__ = [
    "Message",
    "NoteCreate",
    "NoteRead",
    "NoteUpdate",
    "Page",
    "PasswordChange",
    "RoleUpdate",
    "Token",
    "UserCreate",
    "UserRead",
    "UserUpdate",
]
