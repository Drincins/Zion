"""Add employee change orders and permission.

Revision ID: d7e6f5a4b3c2
Revises: c6d5e4f3a2b1
Create Date: 2026-04-03 01:40:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "d7e6f5a4b3c2"
down_revision: Union[str, Sequence[str], None] = "c6d5e4f3a2b1"
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

employee_change_order_status = postgresql.ENUM(
    "pending",
    "applied",
    "cancelled",
    "failed",
    name="employee_change_order_status",
    create_type=False,
)

PERMISSION_DEFINITION = {
    "code": "staff.employee_orders.manage",
    "display_name": "Кадровые изменения сотрудников",
    "description": "Создание, отмена и применение кадровых изменений сотрудника с датой вступления в силу.",
    "responsibility_zone": "Сотрудники",
}


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(
        "pending",
        "applied",
        "cancelled",
        "failed",
        name="employee_change_order_status",
    ).create(bind, checkfirst=True)

    op.create_table(
        "employee_change_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            employee_change_order_status,
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("change_position", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("position_id_new", sa.Integer(), sa.ForeignKey("positions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("change_workplace_restaurant", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "workplace_restaurant_id_new",
            sa.Integer(),
            sa.ForeignKey("restaurants.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("change_rate", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("rate_new", sa.Numeric(10, 2), nullable=True),
        sa.Column("change_individual_rate", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("individual_rate_new", sa.Numeric(10, 2), nullable=True),
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
        "ix_employee_change_orders_status_effective",
        "employee_change_orders",
        ["status", "effective_date"],
    )
    op.create_index(
        "ix_employee_change_orders_user_status_effective",
        "employee_change_orders",
        ["user_id", "status", "effective_date"],
    )
    op.create_index(
        "ix_employee_change_orders_created_at_id",
        "employee_change_orders",
        ["created_at", "id"],
    )
    op.create_index(
        "uq_employee_change_orders_user_pending_effective",
        "employee_change_orders",
        ["user_id", "effective_date"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'::employee_change_order_status"),
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
    op.drop_index("uq_employee_change_orders_user_pending_effective", table_name="employee_change_orders")
    op.drop_index("ix_employee_change_orders_created_at_id", table_name="employee_change_orders")
    op.drop_index("ix_employee_change_orders_user_status_effective", table_name="employee_change_orders")
    op.drop_index("ix_employee_change_orders_status_effective", table_name="employee_change_orders")
    op.drop_table("employee_change_orders")
    employee_change_order_status.drop(bind, checkfirst=True)
