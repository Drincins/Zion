"""add_cost_and_tech_card_to_iiko_products

Revision ID: ab29c7e1f4d8
Revises: 5a2c4e7f1b90
Create Date: 2026-02-13

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "ab29c7e1f4d8"
down_revision: Union[str, Sequence[str], None] = "5a2c4e7f1b90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("iiko_products", sa.Column("default_sale_price", sa.Numeric(14, 2), nullable=True))
    op.add_column("iiko_products", sa.Column("estimated_cost", sa.Numeric(14, 4), nullable=True))
    op.add_column("iiko_products", sa.Column("tech_card_id", sa.String(), nullable=True))
    op.add_column("iiko_products", sa.Column("tech_card_date_from", sa.Date(), nullable=True))
    op.add_column("iiko_products", sa.Column("tech_card_date_to", sa.Date(), nullable=True))
    op.add_column(
        "iiko_products",
        sa.Column("tech_card_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "iiko_products",
        sa.Column("raw_v2_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("iiko_products", "raw_v2_payload")
    op.drop_column("iiko_products", "tech_card_payload")
    op.drop_column("iiko_products", "tech_card_date_to")
    op.drop_column("iiko_products", "tech_card_date_from")
    op.drop_column("iiko_products", "tech_card_id")
    op.drop_column("iiko_products", "estimated_cost")
    op.drop_column("iiko_products", "default_sale_price")

