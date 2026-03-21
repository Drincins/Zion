"""Add role permissions and position hierarchy metadata.

Revision ID: a4d6d0b2f1e2
Revises: 8c3fc204a544
Create Date: 2025-10-29 18:30:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a4d6d0b2f1e2"
down_revision: Union[str, Sequence[str], None] = "8c3fc204a544"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PERMISSIONS_TABLE = sa.table(
    "permissions",
    sa.column("id", sa.Integer),
    sa.column("code", sa.String),
    sa.column("name", sa.String),
    sa.column("description", sa.String),
)


ROLES_TABLE = sa.table(
    "roles",
    sa.column("id", sa.Integer),
    sa.column("name", sa.String),
)


ROLE_PERMISSIONS_TABLE = sa.table(
    "role_permissions",
    sa.column("role_id", sa.Integer),
    sa.column("permission_id", sa.Integer),
)


ADMIN_PERMISSION_CODE = "system.admin"
ADMIN_PERMISSION_NAME = "System administrator"
ADMIN_PERMISSION_DESCRIPTION = "Full administrative access across the application."
LEGACY_ADMIN_ROLE_NAMES = {"admin", "administrator"}


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )

    op.add_column("employee_positions", sa.Column("parent_id", sa.Integer(), nullable=True))
    op.add_column(
        "employee_positions",
        sa.Column("hierarchy_level", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_foreign_key(
        "fk_employee_positions_parent_id_employee_positions",
        "employee_positions",
        "employee_positions",
        ["parent_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_employee_positions_parent_id",
        "employee_positions",
        ["parent_id"],
        unique=False,
    )
    op.alter_column("employee_positions", "hierarchy_level", server_default=None)

    bind = op.get_bind()

    existing_permission_id = bind.execute(
        sa.select(PERMISSIONS_TABLE.c.id).where(PERMISSIONS_TABLE.c.code == ADMIN_PERMISSION_CODE)
    ).scalar()

    if existing_permission_id is None:
        bind.execute(
            sa.insert(PERMISSIONS_TABLE).values(
                code=ADMIN_PERMISSION_CODE,
                name=ADMIN_PERMISSION_NAME,
                description=ADMIN_PERMISSION_DESCRIPTION,
            )
        )
        existing_permission_id = bind.execute(
            sa.select(PERMISSIONS_TABLE.c.id).where(PERMISSIONS_TABLE.c.code == ADMIN_PERMISSION_CODE)
        ).scalar()

    if existing_permission_id is not None:
        legacy_admin_roles = bind.execute(
            sa.select(ROLES_TABLE.c.id).where(ROLES_TABLE.c.name.in_(LEGACY_ADMIN_ROLE_NAMES))
        ).scalars()

        for role_id in legacy_admin_roles:
            already_linked = bind.execute(
                sa.select(ROLE_PERMISSIONS_TABLE.c.role_id).where(
                    sa.and_(
                        ROLE_PERMISSIONS_TABLE.c.role_id == role_id,
                        ROLE_PERMISSIONS_TABLE.c.permission_id == existing_permission_id,
                    )
                )
            ).first()
            if not already_linked:
                bind.execute(
                    sa.insert(ROLE_PERMISSIONS_TABLE).values(
                        role_id=role_id,
                        permission_id=existing_permission_id,
                    )
                )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_employee_positions_parent_id", table_name="employee_positions")
    op.drop_constraint(
        "fk_employee_positions_parent_id_employee_positions",
        "employee_positions",
        type_="foreignkey",
    )
    op.drop_column("employee_positions", "hierarchy_level")
    op.drop_column("employee_positions", "parent_id")

    op.drop_table("role_permissions")
    op.drop_table("permissions")
