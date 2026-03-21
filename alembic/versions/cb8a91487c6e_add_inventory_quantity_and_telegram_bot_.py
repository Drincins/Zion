"""Add inventory quantity and telegram bot access.

Revision ID: cb8a91487c6e
Revises: f9a0b1c2d3e4
Create Date: 2026-01-09 19:43:02.628033

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cb8a91487c6e'
down_revision: Union[str, Sequence[str], None] = 'f9a0b1c2d3e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("inv_item_records") as batch_op:
        batch_op.add_column(
            sa.Column(
                "quantity",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("1"),
            )
        )

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("telegram_id", sa.BigInteger(), nullable=True))
        batch_op.create_index("ix_users_telegram_id", ["telegram_id"], unique=False)
        batch_op.create_unique_constraint("uq_users_telegram_id", ["telegram_id"])

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

    permission_definitions = [
        {
            "code": "inventory.bot.access",
            "display_name": "Склад: доступ к Telegram-боту",
            "description": "Разрешает использовать Telegram-бота для складского учёта.",
            "responsibility_zone": "Склад",
        },
    ]

    bind = op.get_bind()
    existing_codes = {row.code for row in bind.execute(sa.select(permissions_table.c.code))}
    for item in permission_definitions:
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
            bind.execute(permissions_table.insert().values(code=item["code"], **values))


def downgrade() -> None:
    """Downgrade schema."""
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

    bind = op.get_bind()
    bind.execute(
        permissions_table.delete().where(permissions_table.c.code == "inventory.bot.access")
    )

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("uq_users_telegram_id", type_="unique")
        batch_op.drop_index("ix_users_telegram_id")
        batch_op.drop_column("telegram_id")

    with op.batch_alter_table("inv_item_records") as batch_op:
        batch_op.drop_column("quantity")
