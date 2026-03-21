"""add_waiter_mode_to_waiter_turnover_settings

Revision ID: 5a2c4e7f1b90
Revises: f3b7c1d9e2a4
Create Date: 2026-02-13 21:35:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5a2c4e7f1b90"
down_revision: Union[str, Sequence[str], None] = "f3b7c1d9e2a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "iiko_waiter_turnover_settings",
        sa.Column("waiter_mode", sa.String(), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE iiko_waiter_turnover_settings "
            "SET waiter_mode = 'order_close' "
            "WHERE waiter_mode IS NULL OR btrim(waiter_mode) = ''"
        )
    )
    op.alter_column("iiko_waiter_turnover_settings", "waiter_mode", nullable=False)


def downgrade() -> None:
    op.drop_column("iiko_waiter_turnover_settings", "waiter_mode")
