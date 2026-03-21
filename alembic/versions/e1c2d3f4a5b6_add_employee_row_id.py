"""Add employee row id for duplicate checks.

Revision ID: e1c2d3f4a5b6
Revises: d8f9a0b1c2d3
Create Date: 2025-01-15 12:00:00.000000
"""
from __future__ import annotations

import hashlib
import re
from datetime import date as date_cls
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e1c2d3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "d8f9a0b1c2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SPACE_RE = re.compile(r"\s+")


def _normalize_name(value: object) -> str:
    if not value:
        return ""
    return _SPACE_RE.sub(" ", str(value).strip().lower())


def _build_row_id(
    last_name: object,
    first_name: object,
    middle_name: object,
    birth_date: object,
) -> str | None:
    if not last_name or not first_name or not birth_date:
        return None
    if isinstance(birth_date, date_cls):
        birth_value = birth_date.isoformat()
    else:
        birth_value = str(birth_date)[:10]
    base = "|".join(
        [
            _normalize_name(last_name),
            _normalize_name(first_name),
            _normalize_name(middle_name),
            birth_value,
        ]
    )
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def upgrade() -> None:
    op.add_column("users", sa.Column("employee_row_id", sa.String(), nullable=True))
    op.create_index("ix_users_employee_row_id", "users", ["employee_row_id"], unique=False)

    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "select id, first_name, last_name, middle_name, birth_date from users"
        )
    ).fetchall()
    for row in rows:
        data = row._mapping
        row_id = _build_row_id(
            data.get("last_name"),
            data.get("first_name"),
            data.get("middle_name"),
            data.get("birth_date"),
        )
        conn.execute(
            sa.text("update users set employee_row_id = :row_id where id = :id"),
            {"row_id": row_id, "id": data.get("id")},
        )


def downgrade() -> None:
    op.drop_index("ix_users_employee_row_id", table_name="users")
    op.drop_column("users", "employee_row_id")
