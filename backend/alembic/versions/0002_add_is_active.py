"""Добавить колонку is_active в users.

Revision ID: 0002_add_is_active
Revises: 0001_create_users
Create Date: 2026-09-26

Новая миграция — старую 0001 не трогаем. Так и надо: каждое изменение схемы
= новый файл. server_default=true нужен, чтобы уже существующие строки
получили значение и колонка могла быть NOT NULL.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_add_is_active"
down_revision: Union[str, Sequence[str], None] = "0001_create_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "is_active")
