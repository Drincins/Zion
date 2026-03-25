"""Add trigram index for staff employee search.

Revision ID: e8a1f9d2b3c4
Revises: c1d2e3f4a5b6
Create Date: 2026-03-25 23:10:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e8a1f9d2b3c4"
down_revision: Union[str, Sequence[str], None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SEARCH_EXPR = (
    "lower("
    "coalesce(username, '') || ' ' || "
    "coalesce(first_name, '') || ' ' || "
    "coalesce(last_name, '') || ' ' || "
    "coalesce(middle_name, '') || ' ' || "
    "coalesce(staff_code, '') || ' ' || "
    "coalesce(phone_number, '')"
    ")"
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_users_staff_search_trgm "
        f"ON users USING gin ({SEARCH_EXPR} gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_staff_search_trgm")

