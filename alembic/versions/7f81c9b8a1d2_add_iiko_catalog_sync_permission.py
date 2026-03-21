"""add_iiko_catalog_sync_permission

Revision ID: 7f81c9b8a1d2
Revises: 469769308d46
Create Date: 2026-02-11
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7f81c9b8a1d2"
down_revision: Union[str, Sequence[str], None] = "469769308d46"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO permissions (code, name, display_name, description, responsibility_zone)
            VALUES (
                :code,
                :name,
                :display_name,
                :description,
                :zone
            )
            ON CONFLICT (code) DO NOTHING
            """
        ),
        {
            "code": "iiko.catalog.sync",
            "name": "iiko.catalog.sync",
            "display_name": "iiko.catalog.sync",
            "description": "Permission to run iiko nomenclature network synchronization.",
            "zone": "IIKO",
        },
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            DELETE FROM permissions
            WHERE code = 'iiko.catalog.sync'
            """
        )
    )
