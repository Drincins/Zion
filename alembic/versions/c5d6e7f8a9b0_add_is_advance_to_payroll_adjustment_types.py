"""Add is_advance flag to payroll adjustment types.

Revision ID: c5d6e7f8a9b0
Revises: 0f1e2d3c4b5a, b7f8c9d0e1f2
Create Date: 2026-03-12 18:40:00
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c5d6e7f8a9b0"
down_revision: Union[str, Sequence[str], None] = ("0f1e2d3c4b5a", "b7f8c9d0e1f2")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("payroll_adjustment_types")}
    if "is_advance" not in columns:
        op.add_column(
            "payroll_adjustment_types",
            sa.Column("is_advance", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )
        op.alter_column("payroll_adjustment_types", "is_advance", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("payroll_adjustment_types")}
    if "is_advance" in columns:
        op.drop_column("payroll_adjustment_types", "is_advance")
