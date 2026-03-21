"""Add KPI metric group rules and adjustment types.

Revision ID: d4e5f6a7b8c9
Revises: c2d3e4f5a6b7
Create Date: 2026-03-10 16:05:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d4e5f6a7b8c9"
down_revision = "c2d3e4f5a6b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "kpi_metric_groups",
        sa.Column("bonus_adjustment_type_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "kpi_metric_groups",
        sa.Column("penalty_adjustment_type_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_kpi_metric_groups_bonus_adjustment_type_id",
        "kpi_metric_groups",
        "payroll_adjustment_types",
        ["bonus_adjustment_type_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_kpi_metric_groups_penalty_adjustment_type_id",
        "kpi_metric_groups",
        "payroll_adjustment_types",
        ["penalty_adjustment_type_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "kpi_metric_group_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=True),
        sa.Column("department_code", sa.String(length=64), nullable=True),
        sa.Column("position_id", sa.Integer(), nullable=True),
        sa.Column("employee_id", sa.Integer(), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("threshold_type", sa.String(length=32), nullable=False),
        sa.Column("comparison_basis", sa.String(length=32), nullable=False),
        sa.Column("target_value", sa.Numeric(14, 4), nullable=False),
        sa.Column("warning_value", sa.Numeric(14, 4), nullable=True),
        sa.Column("bonus_condition", sa.String(length=16), nullable=False),
        sa.Column("bonus_type", sa.String(length=16), nullable=False),
        sa.Column("bonus_value", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("bonus_base", sa.String(length=32), nullable=False),
        sa.Column("penalty_condition", sa.String(length=16), nullable=False),
        sa.Column("penalty_type", sa.String(length=16), nullable=False),
        sa.Column("penalty_value", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("penalty_base", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["kpi_metric_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["position_id"], ["positions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "group_id",
            "restaurant_id",
            "department_code",
            "position_id",
            "employee_id",
            "period_start",
            "period_end",
            name="uq_kpi_group_rules_scope_period",
        ),
    )
    op.create_index("ix_kpi_metric_group_rules_group_id", "kpi_metric_group_rules", ["group_id"], unique=False)
    op.create_index("ix_kpi_metric_group_rules_restaurant_id", "kpi_metric_group_rules", ["restaurant_id"], unique=False)
    op.create_index("ix_kpi_metric_group_rules_position_id", "kpi_metric_group_rules", ["position_id"], unique=False)
    op.create_index("ix_kpi_metric_group_rules_employee_id", "kpi_metric_group_rules", ["employee_id"], unique=False)
    op.create_index(
        "ix_kpi_group_rules_scope",
        "kpi_metric_group_rules",
        ["group_id", "restaurant_id", "position_id", "employee_id"],
        unique=False,
    )
    op.create_index(
        "ix_kpi_group_rules_group_active_period",
        "kpi_metric_group_rules",
        ["group_id", "is_active", "period_start", "period_end"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_kpi_group_rules_group_active_period", table_name="kpi_metric_group_rules")
    op.drop_index("ix_kpi_group_rules_scope", table_name="kpi_metric_group_rules")
    op.drop_index("ix_kpi_metric_group_rules_employee_id", table_name="kpi_metric_group_rules")
    op.drop_index("ix_kpi_metric_group_rules_position_id", table_name="kpi_metric_group_rules")
    op.drop_index("ix_kpi_metric_group_rules_restaurant_id", table_name="kpi_metric_group_rules")
    op.drop_index("ix_kpi_metric_group_rules_group_id", table_name="kpi_metric_group_rules")
    op.drop_table("kpi_metric_group_rules")
    op.drop_constraint("fk_kpi_metric_groups_penalty_adjustment_type_id", "kpi_metric_groups", type_="foreignkey")
    op.drop_constraint("fk_kpi_metric_groups_bonus_adjustment_type_id", "kpi_metric_groups", type_="foreignkey")
    op.drop_column("kpi_metric_groups", "penalty_adjustment_type_id")
    op.drop_column("kpi_metric_groups", "bonus_adjustment_type_id")
