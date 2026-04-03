"""Add attendances user/date/time index.

Revision ID: b9c8d7e6f5a4
Revises: e8f7a6b5c4d3
Create Date: 2026-04-03 22:20:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b9c8d7e6f5a4"
down_revision: Union[str, Sequence[str], None] = "e8f7a6b5c4d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_attendances_user_open_date_time",
        "attendances",
        ["user_id", "open_date", "open_time"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_attendances_user_open_date_time", table_name="attendances")
