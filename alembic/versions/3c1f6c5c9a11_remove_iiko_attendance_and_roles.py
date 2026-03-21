"""remove obsolete iiko attendance and role tables

Revision ID: 3c1f6c5c9a11
Revises: 6f10e9232f0f
Create Date: 2025-10-03 09:03:44

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3c1f6c5c9a11'
down_revision: Union[str, Sequence[str], None] = '6f10e9232f0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop obsolete iiko attendance and role tables."""
    op.drop_table('iiko_attendances')
    op.drop_table('iiko_roles')


def downgrade() -> None:
    """Recreate iiko attendance and role tables."""
    op.create_table(
        'iiko_roles',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('deleted', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'iiko_attendances',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('employee_id', sa.String(), nullable=True),
        sa.Column('role_id', sa.String(), nullable=True),
        sa.Column('date_from', sa.DateTime(), nullable=True),
        sa.Column('date_to', sa.DateTime(), nullable=True),
        sa.Column('department_id', sa.String(), nullable=True),
        sa.Column('department_name', sa.String(), nullable=True),
        sa.Column('regular_minutes', sa.Integer(), nullable=True),
        sa.Column('regular_payment_sum', sa.Float(), nullable=True),
        sa.Column('overtime_minutes', sa.Integer(), nullable=True),
        sa.Column('overtime_payment_sum', sa.Float(), nullable=True),
        sa.Column('attendance_type', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['employee_id'], ['iiko_employees.id']),
        sa.ForeignKeyConstraint(['role_id'], ['iiko_roles.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('employee_id', 'date_from', name='uq_employee_date'),
    )
