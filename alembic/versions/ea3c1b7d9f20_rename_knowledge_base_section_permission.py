"""Rename knowledge base section permission label.

Revision ID: ea3c1b7d9f20
Revises: b4c5d6e7f8a9
Create Date: 2026-03-17 16:50:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ea3c1b7d9f20"
down_revision: Union[str, Sequence[str], None] = "b4c5d6e7f8a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


metadata = sa.MetaData()
permissions_table = sa.Table(
    "permissions",
    metadata,
    sa.Column("id", sa.Integer),
    sa.Column("code", sa.String),
    sa.Column("name", sa.String),
    sa.Column("display_name", sa.String),
)

PERMISSION_CODE = "knowledge_base.section"
NEW_LABEL = "\u0420\u0430\u0437\u0434\u0435\u043b\u044b: \u0411\u0430\u0437\u0430 \u0437\u043d\u0430\u043d\u0438\u0439"
OLD_LABEL = "\u0420\u0430\u0437\u0434\u0435\u043b \u0411\u0430\u0437\u0430 \u0437\u043d\u0430\u043d\u0438\u0439"


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.update(permissions_table)
        .where(permissions_table.c.code == PERMISSION_CODE)
        .values(
            name=NEW_LABEL,
            display_name=NEW_LABEL,
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.update(permissions_table)
        .where(permissions_table.c.code == PERMISSION_CODE)
        .values(
            name=OLD_LABEL,
            display_name=OLD_LABEL,
        )
    )

