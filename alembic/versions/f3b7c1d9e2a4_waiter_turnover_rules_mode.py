"""waiter_turnover_rules_mode

Revision ID: f3b7c1d9e2a4
Revises: d4f8a1c2b7e9
Create Date: 2026-02-13 18:15:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f3b7c1d9e2a4"
down_revision: Union[str, Sequence[str], None] = "d4f8a1c2b7e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "iiko_waiter_turnover_settings",
        sa.Column("rule_name", sa.String(), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE iiko_waiter_turnover_settings "
            "SET rule_name = 'Основное правило' "
            "WHERE rule_name IS NULL OR btrim(rule_name) = ''"
        )
    )
    op.alter_column("iiko_waiter_turnover_settings", "rule_name", nullable=False)

    op.drop_constraint(
        "uq_iiko_waiter_turnover_settings_company",
        "iiko_waiter_turnover_settings",
        type_="unique",
    )
    op.create_index(
        "ix_iiko_waiter_turnover_settings_company_active_updated",
        "iiko_waiter_turnover_settings",
        ["company_id", "is_active", "updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_iiko_waiter_turnover_settings_company_active_updated",
        table_name="iiko_waiter_turnover_settings",
    )
    op.create_unique_constraint(
        "uq_iiko_waiter_turnover_settings_company",
        "iiko_waiter_turnover_settings",
        ["company_id"],
    )
    op.drop_column("iiko_waiter_turnover_settings", "rule_name")

