"""Создать таблицу notes.

Revision ID: 0003_create_notes
Revises: 0002_add_is_active
Create Date: 2026-09-26
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_create_notes"
down_revision: Union[str, Sequence[str], None] = "0002_add_is_active"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_notes_owner_id", "notes", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_notes_owner_id", table_name="notes")
    op.drop_table("notes")
