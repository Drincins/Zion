"""Add interface theme key to user theme preferences.

Revision ID: b2e4f6a8c1d3
Revises: a7c9d2e4f6b1
Create Date: 2026-03-28 04:25:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2e4f6a8c1d3"
down_revision: Union[str, Sequence[str], None] = "a7c9d2e4f6b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_theme_preferences",
        sa.Column(
            "interface_theme_key",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'classic'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("user_theme_preferences", "interface_theme_key")
