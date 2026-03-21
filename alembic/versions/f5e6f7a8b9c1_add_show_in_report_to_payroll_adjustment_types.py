"""Add show_in_report flag to payroll adjustment types.

Revision ID: f5e6f7a8b9c1
Revises: f2e3d4c5b6a7
Create Date: 2026-02-24 02:10:00
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f5e6f7a8b9c1"
down_revision: Union[str, Sequence[str], None] = "f2e3d4c5b6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("payroll_adjustment_types")}
    if "show_in_report" not in columns:
        op.add_column(
            "payroll_adjustment_types",
            sa.Column("show_in_report", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("payroll_adjustment_types")}
    if "show_in_report" in columns:
        op.drop_column("payroll_adjustment_types", "show_in_report")
