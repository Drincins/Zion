"""Rename employee_positions table to positions.

Revision ID: 8f4a0b8b9a77
Revises: 5c7b2c4e3a26
Create Date: 2025-10-31 14:20:00
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8f4a0b8b9a77"
down_revision: Union[str, Sequence[str], None] = "5c7b2c4e3a26"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE employee_positions RENAME TO positions")
    op.execute("ALTER INDEX ix_employee_positions_role_id RENAME TO ix_positions_role_id")
    op.execute("ALTER INDEX ix_employee_positions_payment_format_id RENAME TO ix_positions_payment_format_id")
    op.execute("ALTER INDEX ix_employee_positions_parent_id RENAME TO ix_positions_parent_id")
    op.execute(
        "ALTER TABLE positions RENAME CONSTRAINT fk_employee_positions_parent_id_employee_positions "
        "TO fk_positions_parent_id_positions"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE positions RENAME CONSTRAINT fk_positions_parent_id_positions "
        "TO fk_employee_positions_parent_id_employee_positions"
    )
    op.execute("ALTER INDEX ix_positions_role_id RENAME TO ix_employee_positions_role_id")
    op.execute("ALTER INDEX ix_positions_payment_format_id RENAME TO ix_employee_positions_payment_format_id")
    op.execute("ALTER INDEX ix_positions_parent_id RENAME TO ix_employee_positions_parent_id")
    op.execute("ALTER TABLE positions RENAME TO employee_positions")
