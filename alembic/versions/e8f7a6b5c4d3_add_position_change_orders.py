"""Add position change orders and permission.

Revision ID: e8f7a6b5c4d3
Revises: d7e6f5a4b3c2
Create Date: 2026-04-03 15:20:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "e8f7a6b5c4d3"
down_revision: Union[str, Sequence[str], None] = "d7e6f5a4b3c2"
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

position_change_order_status = postgresql.ENUM(
    "pending",
    "applied",
    "cancelled",
    "failed",
    name="position_change_order_status",
    create_type=False,
)

PERMISSION_DEFINITION = {
    "code": "positions.change_orders.manage",
    "display_name": "Кадровые изменения должностей",
    "description": "Создание, отмена и применение отложенных изменений ставок должностей с датой вступления в силу.",
    "responsibility_zone": "Доступ",
}


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(
        "pending",
        "applied",
        "cancelled",
        "failed",
        name="position_change_order_status",
    ).create(bind, checkfirst=True)

    op.create_table(
        "position_change_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("position_id", sa.Integer(), sa.ForeignKey("positions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            position_change_order_status,
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("rate_new", sa.Numeric(10, 2), nullable=False),
        sa.Column("apply_to_attendances", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("cancelled_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_position_change_orders_status_effective",
        "position_change_orders",
        ["status", "effective_date"],
    )
    op.create_index(
        "ix_position_change_orders_position_status_effective",
        "position_change_orders",
        ["position_id", "status", "effective_date"],
    )
    op.create_index(
        "ix_position_change_orders_created_at_id",
        "position_change_orders",
        ["created_at", "id"],
    )
    op.create_index(
        "uq_position_change_orders_position_pending_effective",
        "position_change_orders",
        ["position_id", "effective_date"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'::position_change_order_status"),
    )

    existing = bind.execute(
        sa.select(permissions_table.c.code).where(
            permissions_table.c.code == PERMISSION_DEFINITION["code"]
        )
    ).first()
    values = {
        "name": PERMISSION_DEFINITION["display_name"],
        "description": PERMISSION_DEFINITION["description"],
        "display_name": PERMISSION_DEFINITION["display_name"],
        "responsibility_zone": PERMISSION_DEFINITION["responsibility_zone"],
    }
    if existing:
        bind.execute(
            sa.update(permissions_table)
            .where(permissions_table.c.code == PERMISSION_DEFINITION["code"])
            .values(**values)
        )
    else:
        bind.execute(
            permissions_table.insert().values(code=PERMISSION_DEFINITION["code"], **values)
        )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.delete(permissions_table).where(
            permissions_table.c.code == PERMISSION_DEFINITION["code"]
        )
    )
    op.drop_index("uq_position_change_orders_position_pending_effective", table_name="position_change_orders")
    op.drop_index("ix_position_change_orders_created_at_id", table_name="position_change_orders")
    op.drop_index("ix_position_change_orders_position_status_effective", table_name="position_change_orders")
    op.drop_index("ix_position_change_orders_status_effective", table_name="position_change_orders")
    op.drop_table("position_change_orders")
    position_change_order_status.drop(bind, checkfirst=True)
