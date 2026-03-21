"""Add pay_amount to attendances

Revision ID: f1b7d13a1a2c
Revises: 7c2a5f3a1f24
Create Date: 2025-12-01 17:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f1b7d13a1a2c"
down_revision = "7c2a5f3a1f24"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "attendances",
        sa.Column("pay_amount", sa.Numeric(12, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("attendances", "pay_amount")

