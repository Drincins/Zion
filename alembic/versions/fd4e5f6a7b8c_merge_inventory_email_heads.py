"""Merge inventory and email heads.

Revision ID: fd4e5f6a7b8c
Revises: aa12bb34cc56, fc3c4d5e6f7a
Create Date: 2026-01-12 02:00:00
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "fd4e5f6a7b8c"
down_revision: Union[str, Sequence[str], None] = ("aa12bb34cc56", "fc3c4d5e6f7a")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
