"""Expand KPI metric groups with plans and scale settings.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-03-10 16:55:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("kpi_metric_groups", sa.Column("unit", sa.String(length=32), nullable=True))
    op.add_column("kpi_metric_groups", sa.Column("use_max_scale", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("kpi_metric_groups", sa.Column("max_scale_value", sa.Numeric(14, 4), nullable=True))
    op.alter_column("kpi_metric_groups", "use_max_scale", server_default=None)

    op.create_table(
        "kpi_metric_group_plan_facts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("plan_value", sa.Numeric(14, 4), nullable=True),
        sa.Column("fact_value", sa.Numeric(14, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["kpi_metric_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "restaurant_id", "year", "month", name="uq_kpi_metric_group_plan_facts_group_period"),
    )
    op.create_index(
        "ix_kpi_metric_group_plan_facts_group_period",
        "kpi_metric_group_plan_facts",
        ["group_id", "restaurant_id", "year", "month"],
        unique=False,
    )

    op.create_table(
        "kpi_metric_group_plan_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("plan_mode", sa.String(length=32), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=True),
        sa.Column("is_dynamic", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("selected_month", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["kpi_metric_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id"),
    )
    op.create_index(
        "ix_kpi_metric_group_plan_preferences_restaurant_id",
        "kpi_metric_group_plan_preferences",
        ["restaurant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_kpi_metric_group_plan_preferences_restaurant_id", table_name="kpi_metric_group_plan_preferences")
    op.drop_table("kpi_metric_group_plan_preferences")
    op.drop_index("ix_kpi_metric_group_plan_facts_group_period", table_name="kpi_metric_group_plan_facts")
    op.drop_table("kpi_metric_group_plan_facts")
    op.drop_column("kpi_metric_groups", "max_scale_value")
    op.drop_column("kpi_metric_groups", "use_max_scale")
    op.drop_column("kpi_metric_groups", "unit")
