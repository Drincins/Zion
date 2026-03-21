"""Allow duplicate department_code for restaurants.

Revision ID: d0e1f2a3b4c6
Revises: c9f1b2d3e4f5
Create Date: 2026-01-04 19:30:00
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d0e1f2a3b4c6"
down_revision: Union[str, Sequence[str], None] = "c9f1b2d3e4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'restaurants_department_code_key'
            ) THEN
                ALTER TABLE restaurants DROP CONSTRAINT restaurants_department_code_key;
            END IF;
        END$$;
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_restaurants_department_code ON restaurants (department_code)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_restaurants_department_code")
    op.create_unique_constraint(
        "restaurants_department_code_key",
        "restaurants",
        ["department_code"],
    )
