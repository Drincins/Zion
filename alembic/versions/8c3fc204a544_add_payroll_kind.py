"""add payroll kind

Revision ID: 8c3fc204a544
Revises: c6ac89c01f31
Create Date: 2025-10-13 14:34:28.170746

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '8c3fc204a544'
down_revision: Union[str, Sequence[str], None] = 'c6ac89c01f31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PAYROLL_KIND_ENUM = sa.Enum('accrual', 'deduction', name='payroll_adjustment_kind')


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("payroll_adjustment_types")}

    if "kind" not in columns:
        PAYROLL_KIND_ENUM.create(bind, checkfirst=True)
        op.add_column(
            "payroll_adjustment_types",
            sa.Column("kind", PAYROLL_KIND_ENUM, nullable=False, server_default="accrual"),
        )
        op.execute("UPDATE payroll_adjustment_types SET kind = 'accrual' WHERE kind IS NULL")
        op.alter_column("payroll_adjustment_types", "kind", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("payroll_adjustment_types")}

    if "kind" in columns:
        op.drop_column("payroll_adjustment_types", "kind")
        PAYROLL_KIND_ENUM.drop(bind, checkfirst=True)
