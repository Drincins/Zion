"""Consolidate knowledge base permissions into a single section access right.

Revision ID: b4c5d6e7f8a9
Revises: 9f1a2b3c4d5e
Create Date: 2026-03-17 16:30:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b4c5d6e7f8a9"
down_revision: Union[str, Sequence[str], None] = "9f1a2b3c4d5e"
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
role_permissions_table = sa.Table(
    "role_permissions",
    metadata,
    sa.Column("id", sa.Integer),
    sa.Column("role_id", sa.Integer),
    sa.Column("permission_id", sa.Integer),
)
position_permissions_table = sa.Table(
    "position_permissions",
    metadata,
    sa.Column("id", sa.Integer),
    sa.Column("position_id", sa.Integer),
    sa.Column("permission_id", sa.Integer),
)
user_permissions_table = sa.Table(
    "user_permissions",
    metadata,
    sa.Column("id", sa.Integer),
    sa.Column("user_id", sa.Integer),
    sa.Column("permission_id", sa.Integer),
)

SECTION_PERMISSION_CODE = "knowledge_base.section"
LEGACY_PERMISSION_CODES = (
    "knowledge_base.view",
    "knowledge_base.manage",
    "knowledge_base.upload",
)
SECTION_PERMISSION_PAYLOAD = {
    "name": "\u0420\u0430\u0437\u0434\u0435\u043b \u0411\u0430\u0437\u0430 \u0437\u043d\u0430\u043d\u0438\u0439",
    "display_name": "\u0420\u0430\u0437\u0434\u0435\u043b \u0411\u0430\u0437\u0430 \u0437\u043d\u0430\u043d\u0438\u0439",
    "description": (
        "\u0414\u043e\u0441\u0442\u0443\u043f \u043a \u0440\u0430\u0437\u0434\u0435\u043b\u0443 "
        "\u00ab\u0411\u0430\u0437\u0430 \u0437\u043d\u0430\u043d\u0438\u0439\u00bb. "
        "\u041f\u0440\u0430\u0432\u0430 \u0432\u043d\u0443\u0442\u0440\u0438 \u0440\u0430\u0437\u0434\u0435\u043b\u0430 "
        "\u043e\u043f\u0440\u0435\u0434\u0435\u043b\u044f\u044e\u0442\u0441\u044f \u0434\u043e\u0441\u0442\u0443\u043f\u043e\u043c "
        "\u043a \u043f\u0430\u043f\u043a\u0430\u043c."
    ),
    "responsibility_zone": "\u0414\u043e\u0441\u0442\u0443\u043f \u043a \u0440\u0430\u0437\u0434\u0435\u043b\u0430\u043c",
}


def _permission_id(bind, code: str) -> int | None:
    value = bind.execute(
        sa.select(permissions_table.c.id).where(permissions_table.c.code == code)
    ).scalar()
    return int(value) if value is not None else None


def _upsert_section_permission(bind) -> int:
    permission_id = _permission_id(bind, SECTION_PERMISSION_CODE)
    if permission_id is None:
        bind.execute(
            permissions_table.insert().values(
                code=SECTION_PERMISSION_CODE,
                **SECTION_PERMISSION_PAYLOAD,
            )
        )
        permission_id = _permission_id(bind, SECTION_PERMISSION_CODE)
    else:
        bind.execute(
            sa.update(permissions_table)
            .where(permissions_table.c.id == permission_id)
            .values(**SECTION_PERMISSION_PAYLOAD)
        )
    if permission_id is None:
        raise RuntimeError("Failed to upsert knowledge base section permission")
    return permission_id


def _copy_links(bind, table, owner_column, source_permission_ids: list[int], target_permission_id: int) -> None:
    if not source_permission_ids:
        return
    owner_rows = bind.execute(
        sa.select(owner_column).where(table.c.permission_id.in_(source_permission_ids))
    ).all()
    owner_ids = sorted({int(owner_id) for (owner_id,) in owner_rows if owner_id is not None})
    for owner_id in owner_ids:
        exists = bind.execute(
            sa.select(table.c.id).where(
                owner_column == owner_id,
                table.c.permission_id == target_permission_id,
            )
        ).first()
        if exists:
            continue
        bind.execute(
            table.insert().values(
                **{
                    owner_column.key: owner_id,
                    "permission_id": target_permission_id,
                }
            )
        )


def _delete_permission(bind, permission_id: int) -> None:
    bind.execute(sa.delete(role_permissions_table).where(role_permissions_table.c.permission_id == permission_id))
    bind.execute(sa.delete(position_permissions_table).where(position_permissions_table.c.permission_id == permission_id))
    bind.execute(sa.delete(user_permissions_table).where(user_permissions_table.c.permission_id == permission_id))
    bind.execute(sa.delete(permissions_table).where(permissions_table.c.id == permission_id))


def upgrade() -> None:
    bind = op.get_bind()

    section_permission_id = _upsert_section_permission(bind)
    legacy_permission_ids = [
        permission_id
        for permission_id in (_permission_id(bind, code) for code in LEGACY_PERMISSION_CODES)
        if permission_id is not None
    ]

    _copy_links(
        bind,
        role_permissions_table,
        role_permissions_table.c.role_id,
        legacy_permission_ids,
        section_permission_id,
    )
    _copy_links(
        bind,
        position_permissions_table,
        position_permissions_table.c.position_id,
        legacy_permission_ids,
        section_permission_id,
    )
    _copy_links(
        bind,
        user_permissions_table,
        user_permissions_table.c.user_id,
        legacy_permission_ids,
        section_permission_id,
    )

    for legacy_permission_id in legacy_permission_ids:
        if legacy_permission_id == section_permission_id:
            continue
        _delete_permission(bind, legacy_permission_id)


def downgrade() -> None:
    # Irreversible consolidation migration.
    pass

