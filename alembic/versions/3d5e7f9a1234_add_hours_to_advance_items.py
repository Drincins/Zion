"""Add hours and rate fields to payroll advance items."""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "3d5e7f9a1234"
down_revision = "2c4d5e6f7a89"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("payroll_advance_items", sa.Column("fact_hours", sa.Numeric(10, 2), nullable=False, server_default="0"))
    op.add_column("payroll_advance_items", sa.Column("night_hours", sa.Numeric(10, 2), nullable=False, server_default="0"))
    op.add_column("payroll_advance_items", sa.Column("rate", sa.Numeric(12, 2), nullable=True))
    op.alter_column("payroll_advance_items", "fact_hours", server_default=None)
    op.alter_column("payroll_advance_items", "night_hours", server_default=None)


def downgrade():
    op.drop_column("payroll_advance_items", "rate")
    op.drop_column("payroll_advance_items", "night_hours")
    op.drop_column("payroll_advance_items", "fact_hours")
