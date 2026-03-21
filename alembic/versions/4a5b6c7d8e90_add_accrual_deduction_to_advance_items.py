"""Add accrual and deduction columns to payroll advance items."""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "4a5b6c7d8e90"
down_revision = "3d5e7f9a1234"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("payroll_advance_items", sa.Column("accrual_amount", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.add_column("payroll_advance_items", sa.Column("deduction_amount", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.alter_column("payroll_advance_items", "accrual_amount", server_default=None)
    op.alter_column("payroll_advance_items", "deduction_amount", server_default=None)


def downgrade():
    op.drop_column("payroll_advance_items", "deduction_amount")
    op.drop_column("payroll_advance_items", "accrual_amount")
