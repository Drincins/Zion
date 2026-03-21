
"""drop iiko tables that depended on iiko employees data

Revision ID: b7bf2fa9d4f3
Revises: 4a0f7cb1aa61
Create Date: 2025-10-07 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7bf2fa9d4f3"
down_revision: Union[str, Sequence[str], None] = "4a0f7cb1aa61"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop obsolete iiko tables."""
    # Drop in dependency order to avoid FK violations; use IF EXISTS for idempotency.
    for table in ("iiko_attendances", "iiko_roles", "iiko_employees"):
        op.execute(sa.text(f"DROP TABLE IF EXISTS {table} CASCADE"))


def downgrade() -> None:
    """Recreate iiko tables as they existed before removal."""
    op.create_table(
        "iiko_employees",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("surname", sa.String(), nullable=True),
        sa.Column("patronymic", sa.String(), nullable=True),
        sa.Column("deleted", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "iiko_roles",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("deleted", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "iiko_attendances",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("employee_id", sa.String(), nullable=True),
        sa.Column("role_id", sa.String(), nullable=True),
        sa.Column("date_from", sa.DateTime(), nullable=True),
        sa.Column("date_to", sa.DateTime(), nullable=True),
        sa.Column("department_id", sa.String(), nullable=True),
        sa.Column("department_name", sa.String(), nullable=True),
        sa.Column("regular_minutes", sa.Integer(), nullable=True),
        sa.Column("regular_payment_sum", sa.Float(), nullable=True),
        sa.Column("overtime_minutes", sa.Integer(), nullable=True),
        sa.Column("overtime_payment_sum", sa.Float(), nullable=True),
        sa.Column("attendance_type", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["iiko_employees.id"]),
        sa.ForeignKeyConstraint(["role_id"], ["iiko_roles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_id", "date_from", name="uq_employee_date"),
    )
