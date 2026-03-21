"""Add labor summary dashboard permission.

Revision ID: f8d9e0f1a2b3
Revises: f3d4e5f6a7b8
Create Date: 2026-01-10 00:00:00
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f8d9e0f1a2b3"
down_revision: Union[str, Sequence[str], None] = "f3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


metadata = sa.MetaData()
permissions_table = sa.Table(
    "permissions",
    metadata,
    sa.Column("id", sa.Integer),
    sa.Column("code", sa.String),
    sa.Column("name", sa.String),
    sa.Column("description", sa.String),
    sa.Column("display_name", sa.String),
    sa.Column("responsibility_zone", sa.String),
)

PERMISSION_DEFINITIONS = [
    {
        "code": "labor.summary.dashboard.view",
        "display_name": "Labor summary dashboard: view",
        "description": "View labor summary dashboard (hours and totals).",
        "responsibility_zone": "Labor summary",
    },
]


def upgrade() -> None:
    bind = op.get_bind()
    existing_codes = {
        row.code for row in bind.execute(sa.select(permissions_table.c.code))
    }

    for item in PERMISSION_DEFINITIONS:
        values = {
            "name": item["display_name"],
            "description": item["description"],
            "display_name": item["display_name"],
            "responsibility_zone": item["responsibility_zone"],
        }
        if item["code"] in existing_codes:
            bind.execute(
                sa.update(permissions_table)
                .where(permissions_table.c.code == item["code"])
                .values(**values)
            )
        else:
            bind.execute(
                permissions_table.insert().values(code=item["code"], **values)
            )


def downgrade() -> None:
    bind = op.get_bind()
    for item in PERMISSION_DEFINITIONS:
        bind.execute(
            permissions_table.delete().where(permissions_table.c.code == item["code"])
        )
