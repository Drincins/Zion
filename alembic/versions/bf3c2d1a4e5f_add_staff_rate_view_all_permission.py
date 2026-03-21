"""Add staff.rate.view_all permission to view all rates

Revision ID: bf3c2d1a4e5f
Revises: 5e6f7a8b9c0d
Create Date: 2026-01-23 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "bf3c2d1a4e5f"
down_revision: Union[str, Sequence[str], None] = "5e6f7a8b9c0d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


metadata = sa.MetaData()
permissions = sa.Table(
    "permissions",
    metadata,
    sa.Column("id", sa.Integer),
    sa.Column("code", sa.String),
    sa.Column("name", sa.String),
    sa.Column("description", sa.String),
    sa.Column("display_name", sa.String),
    sa.Column("responsibility_zone", sa.String),
)

NEW_PERMISSION = {
    "code": "staff.rate.view_all",
    "name": "Просмотр всех ставок",
    "display_name": "Просмотр всех ставок",
    "description": "Дает право видеть ставки всех сотрудников без ограничений по уровню роли.",
    "responsibility_zone": "HR",
}

CIS_DOCUMENT_TYPES = [
    {"code": "passport", "name": "Паспорт", "validity_months": None, "notice_days": 30, "is_active": True},
    {"code": "patent", "name": "Патент", "validity_months": 12, "notice_days": 30, "is_active": True},
    {"code": "stay_period", "name": "Срок пребывания", "validity_months": 6, "notice_days": 30, "is_active": True},
    {"code": "registration", "name": "Регистрация", "validity_months": None, "notice_days": 30, "is_active": True},
]


def upgrade():
    conn = op.get_bind()
    existing = conn.execute(
        sa.select(permissions.c.id).where(permissions.c.code == NEW_PERMISSION["code"])
    ).fetchone()
    if existing:
        conn.execute(
            permissions.update()
            .where(permissions.c.code == NEW_PERMISSION["code"])
            .values(
                name=NEW_PERMISSION["name"],
                display_name=NEW_PERMISSION["display_name"],
                description=NEW_PERMISSION["description"],
                responsibility_zone=NEW_PERMISSION["responsibility_zone"],
            )
        )
    else:
        conn.execute(permissions.insert().values(**NEW_PERMISSION))

    cis_table = sa.table(
        "cis_document_types",
        sa.column("id", sa.Integer),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("validity_months", sa.Integer),
        sa.column("notice_days", sa.Integer),
        sa.column("is_active", sa.Boolean),
    )

    existing_codes = {
        row.code for row in conn.execute(sa.select(cis_table.c.code).where(cis_table.c.code.in_([c["code"] for c in CIS_DOCUMENT_TYPES])))
    }
    to_insert = [item for item in CIS_DOCUMENT_TYPES if item["code"] not in existing_codes]
    for item in to_insert:
        conn.execute(cis_table.insert().values(**item))


def downgrade():
    conn = op.get_bind()
    conn.execute(permissions.delete().where(permissions.c.code == NEW_PERMISSION["code"]))
    conn.execute(sa.text("DELETE FROM cis_document_types WHERE code IN (:c1, :c2, :c3, :c4)"), {"c1": "passport", "c2": "patent", "c3": "stay_period", "c4": "registration"})
