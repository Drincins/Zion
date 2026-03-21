"""Add role permissions table and merge heads."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e0c1232d9eab"
down_revision: Union[str, Sequence[str], None] = ("3c9d5a27c2f1", "c042bde2d1c0")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "role_permissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("permission_id", sa.Integer(), sa.ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_permission"),
    )

    # Seed role permissions from existing position permissions to preserve current access patterns.
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT DISTINCT p.role_id, pp.permission_id
        FROM positions p
        JOIN position_permissions pp ON pp.position_id = p.id
        WHERE p.role_id IS NOT NULL
        ON CONFLICT ON CONSTRAINT uq_role_permissions_role_permission DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_table("role_permissions")
