"""Add invoice_date to accounting_invoices."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3c4d5e6f7a8b"
down_revision: Union[str, Sequence[str], None] = "2b3c4d5e6f7a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("accounting_invoices", sa.Column("invoice_date", sa.Date(), nullable=True))
    op.create_index(
        op.f("ix_accounting_invoices_invoice_date"),
        "accounting_invoices",
        ["invoice_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_accounting_invoices_invoice_date"), table_name="accounting_invoices")
    op.drop_column("accounting_invoices", "invoice_date")
