"""Add snapshot fields to payroll advance tables."""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "5b7c8d9e0f12"
down_revision = "4a5b6c7d8e90"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("payroll_advance_statements", sa.Column("adjustments_snapshot", sa.JSON(), nullable=True))
    op.add_column("payroll_advance_items", sa.Column("calc_snapshot", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("payroll_advance_items", "calc_snapshot")
    op.drop_column("payroll_advance_statements", "adjustments_snapshot")
