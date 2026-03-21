"""Optimize KPI and attendance indexes.

Revision ID: d9b1e7c4f2a0
Revises: b7f8c9d0e1f2, c4d5e6f7a8b9
Create Date: 2026-03-07 23:40:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d9b1e7c4f2a0"
down_revision: Union[str, Sequence[str], None] = ("b7f8c9d0e1f2", "c4d5e6f7a8b9")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_attendances_open_date_user",
        "attendances",
        ["open_date", "user_id"],
        unique=False,
    )
    op.create_index(
        "ix_attendances_open_date_position",
        "attendances",
        ["open_date", "position_id"],
        unique=False,
    )
    op.create_index(
        "ix_kpi_rules_metric_active_period",
        "kpi_rules",
        ["metric_id", "is_active", "period_start", "period_end"],
        unique=False,
    )
    op.create_index(
        "ix_kpi_results_metric_status_period",
        "kpi_results",
        ["metric_id", "status", "period_start", "period_end"],
        unique=False,
    )
    op.create_index(
        "ix_kpi_plan_facts_year_rest_metric_month",
        "kpi_plan_facts",
        ["year", "restaurant_id", "metric_id", "month"],
        unique=False,
    )
    op.create_index(
        "ix_kpi_payout_batches_status_created",
        "kpi_payout_batches",
        ["status", "created_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_kpi_payout_batches_created",
        "kpi_payout_batches",
        ["created_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_kpi_payout_batches_status_period",
        "kpi_payout_batches",
        ["status", "period_start", "period_end"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_kpi_payout_batches_status_period", table_name="kpi_payout_batches")
    op.drop_index("ix_kpi_payout_batches_created", table_name="kpi_payout_batches")
    op.drop_index("ix_kpi_payout_batches_status_created", table_name="kpi_payout_batches")
    op.drop_index("ix_kpi_plan_facts_year_rest_metric_month", table_name="kpi_plan_facts")
    op.drop_index("ix_kpi_results_metric_status_period", table_name="kpi_results")
    op.drop_index("ix_kpi_rules_metric_active_period", table_name="kpi_rules")
    op.drop_index("ix_attendances_open_date_position", table_name="attendances")
    op.drop_index("ix_attendances_open_date_user", table_name="attendances")
