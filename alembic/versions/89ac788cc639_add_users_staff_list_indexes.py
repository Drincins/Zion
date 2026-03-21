"""add_users_staff_list_indexes

Revision ID: 89ac788cc639
Revises: e1f2a3b4c5d6
Create Date: 2026-02-06 18:42:07.984000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '89ac788cc639'
down_revision: Union[str, Sequence[str], None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index("ix_users_fired", "users", ["fired"], unique=False)
    op.create_index(
        "ix_users_workplace_fired",
        "users",
        ["workplace_restaurant_id", "fired"],
        unique=False,
    )
    # Helps ORDER BY lower(last_name), lower(first_name), id used in staff employees list.
    op.create_index(
        "ix_users_name_order",
        "users",
        [sa.text("lower(last_name)"), sa.text("lower(first_name)"), "id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_users_name_order", table_name="users")
    op.drop_index("ix_users_workplace_fired", table_name="users")
    op.drop_index("ix_users_fired", table_name="users")
