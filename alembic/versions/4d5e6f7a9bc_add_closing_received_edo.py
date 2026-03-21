"""add closing_received_edo flag

Revision ID: 4d5e6f7a9bc
Revises: 3c4d5e6f7a8b_add_invoice_date
Create Date: 2026-01-16 12:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "4d5e6f7a9bc"
down_revision = "3c4d5e6f7a8b"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "accounting_invoices",
        sa.Column("closing_received_edo", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade():
    op.drop_column("accounting_invoices", "closing_received_edo")

