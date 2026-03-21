"""Add employee change history events and permissions.

Revision ID: f2c3d4e5f6a7
Revises: f1a2b3c4d5e6
Create Date: 2026-01-05 12:00:00
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
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
        "code": "employee_changes.view",
        "display_name": "Employee changes: view",
        "description": "View employee change history.",
        "responsibility_zone": "Employees",
    },
    {
        "code": "employee_changes.manage",
        "display_name": "Employee changes: edit",
        "description": "Edit employee change history entries.",
        "responsibility_zone": "Employees",
    },
    {
        "code": "employee_changes.delete",
        "display_name": "Employee changes: delete",
        "description": "Delete employee change history entries.",
        "responsibility_zone": "Employees",
    },
]


def upgrade() -> None:
    op.create_table(
        "employee_change_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("changed_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("field", sa.String(), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_employee_change_events_user_id",
        "employee_change_events",
        ["user_id"],
    )
    op.create_index(
        "ix_employee_change_events_changed_by_id",
        "employee_change_events",
        ["changed_by_id"],
    )
    op.create_index(
        "ix_employee_change_events_created_at",
        "employee_change_events",
        ["created_at"],
    )

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
    op.drop_index("ix_employee_change_events_created_at", table_name="employee_change_events")
    op.drop_index("ix_employee_change_events_changed_by_id", table_name="employee_change_events")
    op.drop_index("ix_employee_change_events_user_id", table_name="employee_change_events")
    op.drop_table("employee_change_events")
