"""Sync position permissions from role templates.

Revision ID: db69c0bb6edb
Revises: 5b7c8d9e0f12
Create Date: 2026-01-28 00:00:00
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "db69c0bb6edb"
down_revision: Union[str, Sequence[str], None] = "5b7c8d9e0f12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO position_permissions (position_id, permission_id)
        SELECT p.id, rp.permission_id
        FROM positions p
        JOIN role_permissions rp ON rp.role_id = p.role_id
        LEFT JOIN position_permissions pp
          ON pp.position_id = p.id AND pp.permission_id = rp.permission_id
        WHERE pp.id IS NULL;
        """
    )


def downgrade() -> None:
    # Data sync is irreversible; leave as no-op.
    pass
