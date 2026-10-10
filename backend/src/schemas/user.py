"""
user.py — СХЕМЫ ПОЛЬЗОВАТЕЛЯ.

Напоминание, почему схема и модель — разные вещи:

    модель  (`src/models/user.py`)  — как данные лежат в базе;
    схема   (этот файл)             — как данные ходят через HTTP.

Именно разделение не даёт хешу пароля случайно уехать наружу: в `UserRead`
такого поля просто нет.
"""

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from src.enums import UserRole


class UserCreate(BaseModel):
    """Тело запроса на регистрацию."""

    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(min_length=5, max_length=128)


class UserUpdate(BaseModel):
    """Частичное обновление профиля: поле не прислали — оно не меняется."""

    username: str | None = Field(default=None, min_length=3, max_length=64)
    email: EmailStr | None = None


class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(min_length=5, max_length=128)


class RoleUpdate(BaseModel):
    role: UserRole


class UserRead(BaseModel):
    """Что отдаём наружу. Пароля и его хеша здесь нет и быть не должно."""

    id: int
    username: str
    email: EmailStr
    role: UserRole
    is_active: bool

    # from_attributes разрешает собрать схему прямо из объекта SQLAlchemy,
    # а не только из словаря.
    model_config = ConfigDict(from_attributes=True)
