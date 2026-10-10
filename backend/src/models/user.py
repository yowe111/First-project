"""
user.py — таблица `users`: аккаунт человека в системе.
"""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum as SAEnum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.enums import UserRole
from src.models.base import Base, IntIdMixin, TimestampMixin

# Импорт только для подсказок типов: во время работы программы он не
# выполняется, поэтому круговой импорт User ↔ Note не возникает.
if TYPE_CHECKING:
    from src.models.note import Note


class User(IntIdMixin, TimestampMixin, Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))

    role: Mapped[UserRole] = mapped_column(
        # native_enum=False — роль хранится обычной строкой (VARCHAR).
        # Так проще менять список ролей: не нужен ALTER TYPE в PostgreSQL.
        SAEnum(UserRole, native_enum=False, length=16),
        default=UserRole.USER,
        server_default=UserRole.USER.value,
    )

    # Заблокированный не входит и не ходит по защищённым эндпоинтам.
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
    )

    # Один пользователь → много заметок.
    # cascade: удалили человека — удалились и его записи.
    notes: Mapped[list["Note"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )
