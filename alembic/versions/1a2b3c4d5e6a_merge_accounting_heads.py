"""Merge accounting branch into main head.

Revision ID: 1a2b3c4d5e6a
Revises: fd4e5f6a7b8c, 0a1b2c3d4e5f
Create Date: 2025-01-16 00:00:00
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1a2b3c4d5e6a"
down_revision: Union[str, Sequence[str], None] = ("fd4e5f6a7b8c", "0a1b2c3d4e5f")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # merge point, no-op
    pass


def downgrade() -> None:
    # cannot automatically split merged heads
    pass
