"""Add iiko ids for users/positions/restaurants."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "94f2c5d8c5d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("iiko_id", sa.String(), nullable=True))
    op.create_unique_constraint("uq_users_iiko_id", "users", ["iiko_id"])

    op.add_column("positions", sa.Column("code", sa.String(), nullable=True))
    op.create_unique_constraint("uq_positions_code", "positions", ["code"])

    op.add_column("restaurants", sa.Column("department_code", sa.String(), nullable=True))
    op.create_unique_constraint("uq_restaurants_department_code", "restaurants", ["department_code"])
    op.create_index(
        "ix_restaurants_department_code",
        "restaurants",
        ["department_code"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_restaurants_department_code", table_name="restaurants")
    op.drop_constraint("uq_restaurants_department_code", "restaurants", type_="unique")
    op.drop_column("restaurants", "department_code")

    op.drop_constraint("uq_positions_code", "positions", type_="unique")
    op.drop_column("positions", "code")

    op.drop_constraint("uq_users_iiko_id", "users", type_="unique")
    op.drop_column("users", "iiko_id")
