"""Add tables for KPI metrics, rules, and results.

Revision ID: 2a9fd92aa9e0
Revises: a3bc1c2d4e55
Create Date: 2025-11-10 17:00:36.561631

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg


# revision identifiers, used by Alembic.
revision: str = "2a9fd92aa9e0"
down_revision: Union[str, Sequence[str], None] = "a3bc1c2d4e55"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

kpi_calculation_base = pg.ENUM("none", "salary", "hours_sum", "rate", name="kpi_calculation_base")
kpi_threshold_type = pg.ENUM("single", "dual", name="kpi_threshold_type")
kpi_effect_type = pg.ENUM("none", "fixed", "percent", name="kpi_effect_type")
kpi_value_base = pg.ENUM("none", "salary", "hours_sum", "rate", name="kpi_value_base")
kpi_result_status = pg.ENUM("draft", "confirmed", name="kpi_result_status")
kpi_result_source = pg.ENUM("manual", "import", "calculated", name="kpi_result_source")
permissions_table = sa.table(
    "permissions",
    sa.column("code", sa.String()),
    sa.column("name", sa.String()),
    sa.column("description", sa.String()),
    sa.column("display_name", sa.String()),
)
NEW_PERMISSIONS = [
    {
        "code": "kpi.view",
        "name": "Просмотр KPI",
        "description": "Просмотр KPI-метрик, правил и зафиксированных результатов",
        "display_name": "Просмотр KPI",
    },
    {
        "code": "kpi.manage",
        "name": "Управление KPI",
        "description": "Управление KPI-метриками, правилами и результатами",
        "display_name": "Управление KPI",
    },
]


def _enum_for_column(enum_type: pg.ENUM) -> pg.ENUM:
    return pg.ENUM(*enum_type.enums, name=enum_type.name, create_type=False)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    kpi_calculation_base.create(bind, checkfirst=True)
    kpi_threshold_type.create(bind, checkfirst=True)
    kpi_effect_type.create(bind, checkfirst=True)
    kpi_value_base.create(bind, checkfirst=True)
    kpi_result_status.create(bind, checkfirst=True)
    kpi_result_source.create(bind, checkfirst=True)

    op.create_table(
        "kpi_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("calculation_base", _enum_for_column(kpi_calculation_base), nullable=False, server_default="none"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
    )
    op.create_index("ix_kpi_metrics_code", "kpi_metrics", ["code"], unique=True)
    op.alter_column("kpi_metrics", "calculation_base", server_default=None)
    op.alter_column("kpi_metrics", "is_active", server_default=None)

    op.create_table(
        "kpi_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("metric_id", sa.Integer(), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=True),
        sa.Column("department_code", sa.String(length=64), nullable=True),
        sa.Column("position_id", sa.Integer(), nullable=True),
        sa.Column("employee_id", sa.Integer(), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("threshold_type", _enum_for_column(kpi_threshold_type), nullable=False, server_default="single"),
        sa.Column("target_value", sa.Numeric(14, 4), nullable=False),
        sa.Column("warning_value", sa.Numeric(14, 4), nullable=True),
        sa.Column("bonus_type", _enum_for_column(kpi_effect_type), nullable=False, server_default="none"),
        sa.Column("bonus_value", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("bonus_base", _enum_for_column(kpi_value_base), nullable=False, server_default="none"),
        sa.Column("penalty_type", _enum_for_column(kpi_effect_type), nullable=False, server_default="none"),
        sa.Column("penalty_value", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("penalty_base", _enum_for_column(kpi_value_base), nullable=False, server_default="none"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["metric_id"], ["kpi_metrics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["position_id"], ["positions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["employee_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "metric_id",
            "restaurant_id",
            "department_code",
            "position_id",
            "employee_id",
            "period_start",
            "period_end",
            name="uq_kpi_rules_scope_period",
        ),
    )
    op.create_index(
        "ix_kpi_rules_scope",
        "kpi_rules",
        ["metric_id", "restaurant_id", "position_id", "employee_id"],
        unique=False,
    )
    op.alter_column("kpi_rules", "threshold_type", server_default=None)
    op.alter_column("kpi_rules", "bonus_type", server_default=None)
    op.alter_column("kpi_rules", "bonus_value", server_default=None)
    op.alter_column("kpi_rules", "bonus_base", server_default=None)
    op.alter_column("kpi_rules", "penalty_type", server_default=None)
    op.alter_column("kpi_rules", "penalty_value", server_default=None)
    op.alter_column("kpi_rules", "penalty_base", server_default=None)
    op.alter_column("kpi_rules", "is_active", server_default=None)

    op.create_table(
        "kpi_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("metric_id", sa.Integer(), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=True),
        sa.Column("department_code", sa.String(length=64), nullable=True),
        sa.Column("position_id", sa.Integer(), nullable=True),
        sa.Column("employee_id", sa.Integer(), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("fact_value", sa.Numeric(14, 4), nullable=False),
        sa.Column("status", _enum_for_column(kpi_result_status), nullable=False, server_default="draft"),
        sa.Column("source", _enum_for_column(kpi_result_source), nullable=False, server_default="manual"),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("recorded_by_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["metric_id"], ["kpi_metrics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["position_id"], ["positions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["employee_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recorded_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "metric_id",
            "restaurant_id",
            "department_code",
            "position_id",
            "employee_id",
            "period_start",
            "period_end",
            name="uq_kpi_results_scope_period",
        ),
    )
    op.create_index(
        "ix_kpi_results_scope",
        "kpi_results",
        ["metric_id", "restaurant_id", "position_id", "employee_id"],
        unique=False,
    )
    op.alter_column("kpi_results", "status", server_default=None)
    op.alter_column("kpi_results", "source", server_default=None)

    op.bulk_insert(permissions_table, NEW_PERMISSIONS)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()

    op.drop_index("ix_kpi_results_scope", table_name="kpi_results")
    op.drop_table("kpi_results")

    op.drop_index("ix_kpi_rules_scope", table_name="kpi_rules")
    op.drop_table("kpi_rules")

    op.drop_index("ix_kpi_metrics_code", table_name="kpi_metrics")
    op.drop_table("kpi_metrics")

    op.execute(
        sa.delete(permissions_table).where(permissions_table.c.code.in_([item["code"] for item in NEW_PERMISSIONS]))
    )

    kpi_result_source.drop(bind, checkfirst=True)
    kpi_result_status.drop(bind, checkfirst=True)
    kpi_value_base.drop(bind, checkfirst=True)
    kpi_effect_type.drop(bind, checkfirst=True)
    kpi_threshold_type.drop(bind, checkfirst=True)
    kpi_calculation_base.drop(bind, checkfirst=True)
