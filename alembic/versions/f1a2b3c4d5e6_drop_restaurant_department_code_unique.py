"""Drop unique constraint on restaurant department_code if present.

Revision ID: f1a2b3c4d5e6
Revises: e3f4a5b6c7d8
Create Date: 2026-01-04 21:10:00
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e3f4a5b6c7d8"
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
                WHERE conname = 'uq_restaurants_department_code'
            ) THEN
                ALTER TABLE restaurants DROP CONSTRAINT uq_restaurants_department_code;
            END IF;
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


def downgrade() -> None:
    op.create_unique_constraint(
        "uq_restaurants_department_code",
        "restaurants",
        ["department_code"],
    )
