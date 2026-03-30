"""Add per-user theme preferences.

Revision ID: a7c9d2e4f6b1
Revises: e8a1f9d2b3c4
Create Date: 2026-03-28 03:40:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a7c9d2e4f6b1"
down_revision: Union[str, Sequence[str], None] = "e8a1f9d2b3c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_theme_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("theme_key", sa.String(length=32), nullable=False, server_default=sa.text("'light'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_user_theme_preferences_user_id"),
    )


def downgrade() -> None:
    op.drop_table("user_theme_preferences")
