"""Set dark mode as default for user theme preferences.

Revision ID: c6d5e4f3a2b1
Revises: b2e4f6a8c1d3
Create Date: 2026-03-28 13:10:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c6d5e4f3a2b1"
down_revision: Union[str, Sequence[str], None] = "b2e4f6a8c1d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "user_theme_preferences",
        "theme_key",
        existing_type=sa.String(length=32),
        server_default=sa.text("'dark'"),
    )


def downgrade() -> None:
    op.alter_column(
        "user_theme_preferences",
        "theme_key",
        existing_type=sa.String(length=32),
        server_default=sa.text("'light'"),
    )
