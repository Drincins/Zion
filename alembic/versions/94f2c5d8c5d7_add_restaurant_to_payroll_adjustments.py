"""Add restaurant to payroll adjustments."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "94f2c5d8c5d7"
down_revision: Union[str, Sequence[str], None] = "e0c1232d9eab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "payroll_adjustments",
        sa.Column("restaurant_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_payroll_adjustments_restaurant_id",
        "payroll_adjustments",
        ["restaurant_id"],
    )
    op.create_foreign_key(
        "fk_payroll_adjustments_restaurant_id_restaurants",
        "payroll_adjustments",
        "restaurants",
        ["restaurant_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_payroll_adjustments_restaurant_id_restaurants",
        "payroll_adjustments",
        type_="foreignkey",
    )
    op.drop_index("ix_payroll_adjustments_restaurant_id", table_name="payroll_adjustments")
    op.drop_column("payroll_adjustments", "restaurant_id")
