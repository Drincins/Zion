"""add_staff_employees_export_permission

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7b8, f5e6f7a8b9c1
Create Date: 2026-03-06
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = ("b3c4d5e6f7b8", "f5e6f7a8b9c1")
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
            ON CONFLICT (code) DO UPDATE
            SET
                name = EXCLUDED.name,
                display_name = EXCLUDED.display_name,
                description = EXCLUDED.description,
                responsibility_zone = EXCLUDED.responsibility_zone
            """
        ),
        {
            "code": "staff_employees.export",
            "name": "Сотрудники: выгрузка списка",
            "display_name": "Сотрудники: выгрузка списка",
            "description": "Разрешает скачивать Excel-список сотрудников в разделе Сотрудники.",
            "zone": "Сотрудники",
        },
    )


def downgrade() -> None:
    # Keep seeded permissions on downgrade to avoid dropping assigned access rights.
    pass
