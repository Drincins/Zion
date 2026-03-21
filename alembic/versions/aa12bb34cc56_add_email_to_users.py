"""Add email column to users table.

Revision ID: aa12bb34cc56
Revises: f6a7b8c9d0e1
Create Date: 2026-01-10 12:30:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "aa12bb34cc56"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "email")
