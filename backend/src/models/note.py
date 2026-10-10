"""
note.py — таблица `notes`: заметка, принадлежащая одному пользователю.

Это первая связь «один ко многим» в проекте. Когда дойдём до продукта,
по этому же образцу будет устроен `Dataset`: владелец, права «только своё»,
каскадное удаление вместе с аккаунтом.
"""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, IntIdMixin, TimestampMixin
from src.models.user import User


class Note(IntIdMixin, TimestampMixin, Base):
    __tablename__ = "notes"

    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)

    # Внешний ключ: owner_id обязан существовать в users.id.
    # Индекс нужен, потому что по этой колонке идёт фильтр «только мои».
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    owner: Mapped[User] = relationship(back_populates="notes")
