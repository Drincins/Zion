"""Add KPI metric result aggregation mode.

Revision ID: 0c1d2e3f4a5b
Revises: b9c8d7e6f5a4
Create Date: 2026-04-04 16:10:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0c1d2e3f4a5b"
down_revision: Union[str, Sequence[str], None] = "b9c8d7e6f5a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


kpi_metric_aggregation_mode = sa.Enum(
    "average",
    "sum",
    name="kpi_metric_aggregation_mode",
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    enum_names = {enum.get("name") for enum in inspector.get_enums()}
    if "kpi_metric_aggregation_mode" not in enum_names:
        kpi_metric_aggregation_mode.create(bind, checkfirst=True)

    existing_columns = {column.get("name") for column in inspector.get_columns("kpi_metrics")}
    if "result_aggregation_mode" not in existing_columns:
        op.add_column(
            "kpi_metrics",
            sa.Column(
                "result_aggregation_mode",
                kpi_metric_aggregation_mode,
                nullable=False,
                server_default="average",
            ),
        )

    op.execute(
        sa.text(
            "UPDATE kpi_metrics "
            "SET result_aggregation_mode = 'average' "
            "WHERE result_aggregation_mode IS NULL"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE kpi_metrics "
            "ALTER COLUMN result_aggregation_mode SET DEFAULT 'average'"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE kpi_metrics "
            "ALTER COLUMN result_aggregation_mode SET NOT NULL"
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_columns = {column.get("name") for column in inspector.get_columns("kpi_metrics")}
    if "result_aggregation_mode" in existing_columns:
        op.drop_column("kpi_metrics", "result_aggregation_mode")

    enum_names = {enum.get("name") for enum in inspector.get_enums()}
    if "kpi_metric_aggregation_mode" in enum_names:
        kpi_metric_aggregation_mode.drop(bind, checkfirst=True)
