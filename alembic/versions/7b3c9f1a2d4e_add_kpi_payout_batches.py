"""Add KPI payout batches and comparison operators."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "7b3c9f1a2d4e"
down_revision = ("e4f5a6b7c8d9", "91562de72a95")
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DROP TYPE IF EXISTS kpi_comparison_operator")
    comparison_enum = postgresql.ENUM(
        "gte",
        "gt",
        "lte",
        "lt",
        name="kpi_comparison_operator",
        create_type=False,
    )
    comparison_enum.create(op.get_bind(), checkfirst=True)

    op.execute("DROP TYPE IF EXISTS kpi_payout_status")
    payout_status_enum = postgresql.ENUM(
        "draft",
        "posted",
        name="kpi_payout_status",
        create_type=False,
    )
    payout_status_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "kpi_rules",
        sa.Column(
            "bonus_condition",
            comparison_enum,
            nullable=False,
            server_default="gte",
        ),
    )
    op.add_column(
        "kpi_rules",
        sa.Column(
            "penalty_condition",
            comparison_enum,
            nullable=False,
            server_default="lte",
        ),
    )
    op.alter_column("kpi_rules", "bonus_condition", server_default=None)
    op.alter_column("kpi_rules", "penalty_condition", server_default=None)

    op.create_table(
        "kpi_payout_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("rule_id", sa.Integer(), sa.ForeignKey("kpi_rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("result_id", sa.Integer(), sa.ForeignKey("kpi_results.id", ondelete="SET NULL"), nullable=True),
        sa.Column("restaurant_id", sa.Integer(), sa.ForeignKey("restaurants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("position_id", sa.Integer(), sa.ForeignKey("positions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("status", payout_status_enum, nullable=False, server_default="draft"),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("posted_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index(
        "ix_kpi_payout_batches_scope_period",
        "kpi_payout_batches",
        ["restaurant_id", "position_id", "period_start", "period_end"],
    )
    op.create_index(
        "ix_kpi_payout_batches_rule_id",
        "kpi_payout_batches",
        ["rule_id"],
    )
    op.create_index(
        "ix_kpi_payout_batches_result_id",
        "kpi_payout_batches",
        ["result_id"],
    )

    op.create_table(
        "kpi_payout_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("kpi_payout_batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), sa.ForeignKey("restaurants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("base_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("bonus_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("penalty_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("bonus_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("penalty_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("manual", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("calc_snapshot", sa.JSON(), nullable=True),
        sa.Column("bonus_adjustment_id", sa.Integer(), sa.ForeignKey("payroll_adjustments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("penalty_adjustment_id", sa.Integer(), sa.ForeignKey("payroll_adjustments.id", ondelete="SET NULL"), nullable=True),
        sa.UniqueConstraint("batch_id", "user_id", name="uq_kpi_payout_items_batch_user"),
    )
    op.create_index(
        "ix_kpi_payout_items_batch_id",
        "kpi_payout_items",
        ["batch_id"],
    )
    op.create_index(
        "ix_kpi_payout_items_user_id",
        "kpi_payout_items",
        ["user_id"],
    )
    op.create_index(
        "ix_kpi_payout_items_restaurant_id",
        "kpi_payout_items",
        ["restaurant_id"],
    )

    op.alter_column("kpi_payout_batches", "status", server_default=None)
    op.alter_column("kpi_payout_items", "base_amount", server_default=None)
    op.alter_column("kpi_payout_items", "bonus_amount", server_default=None)
    op.alter_column("kpi_payout_items", "penalty_amount", server_default=None)
    op.alter_column("kpi_payout_items", "bonus_enabled", server_default=None)
    op.alter_column("kpi_payout_items", "penalty_enabled", server_default=None)
    op.alter_column("kpi_payout_items", "manual", server_default=None)

    op.execute(
        """
        INSERT INTO payroll_adjustment_types (name, kind)
        SELECT 'KPI бонус', 'accrual'
        WHERE NOT EXISTS (
            SELECT 1 FROM payroll_adjustment_types WHERE lower(name) = lower('KPI бонус')
        )
        """
    )
    op.execute(
        """
        INSERT INTO payroll_adjustment_types (name, kind)
        SELECT 'KPI штраф', 'deduction'
        WHERE NOT EXISTS (
            SELECT 1 FROM payroll_adjustment_types WHERE lower(name) = lower('KPI штраф')
        )
        """
    )


def downgrade():
    op.drop_index("ix_kpi_payout_items_restaurant_id", table_name="kpi_payout_items")
    op.drop_index("ix_kpi_payout_items_user_id", table_name="kpi_payout_items")
    op.drop_index("ix_kpi_payout_items_batch_id", table_name="kpi_payout_items")
    op.drop_table("kpi_payout_items")

    op.drop_index("ix_kpi_payout_batches_result_id", table_name="kpi_payout_batches")
    op.drop_index("ix_kpi_payout_batches_rule_id", table_name="kpi_payout_batches")
    op.drop_index("ix_kpi_payout_batches_scope_period", table_name="kpi_payout_batches")
    op.drop_table("kpi_payout_batches")

    op.drop_column("kpi_rules", "penalty_condition")
    op.drop_column("kpi_rules", "bonus_condition")

    op.execute("DELETE FROM payroll_adjustment_types WHERE lower(name) IN (lower('KPI бонус'), lower('KPI штраф'))")

    op.execute("DROP TYPE IF EXISTS kpi_payout_status")
    op.execute("DROP TYPE IF EXISTS kpi_comparison_operator")
