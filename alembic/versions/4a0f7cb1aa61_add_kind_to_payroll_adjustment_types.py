"""add kind column to payroll adjustment types

Revision ID: 4a0f7cb1aa61
Revises: 3c1f6c5c9a11
Create Date: 2025-10-03 09:28:44

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a0f7cb1aa61'
down_revision: Union[str, Sequence[str], None] = '3c1f6c5c9a11'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


KIND_ENUM = sa.Enum('accrual', 'deduction', name='payroll_adjustment_kind')


def upgrade() -> None:
    """Add kind column and backfill existing rows."""
    bind = op.get_bind()
    KIND_ENUM.create(bind, checkfirst=True)
    op.add_column(
        'payroll_adjustment_types',
        sa.Column('kind', KIND_ENUM, nullable=False, server_default='accrual'),
    )
    op.execute("UPDATE payroll_adjustment_types SET kind = 'accrual' WHERE kind IS NULL")
    op.alter_column('payroll_adjustment_types', 'kind', server_default=None)


def downgrade() -> None:
    """Remove kind column."""
    op.drop_column('payroll_adjustment_types', 'kind')
    bind = op.get_bind()
    KIND_ENUM.drop(bind, checkfirst=True)
