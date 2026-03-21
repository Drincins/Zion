"""add checklist access/control fields

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c9
Create Date: 2026-02-02 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e4f5a6b7c8d9"
down_revision = "d3e4f5a6b7c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("checklists", sa.Column("access_subdivision_ids", sa.JSON(), nullable=True))
    op.add_column("checklists", sa.Column("access_all_subdivisions", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("checklists", sa.Column("control_restaurant_ids", sa.JSON(), nullable=True))
    op.add_column("checklists", sa.Column("control_subdivision_ids", sa.JSON(), nullable=True))
    op.add_column("checklists", sa.Column("control_all_restaurants", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("checklists", sa.Column("control_all_subdivisions", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.alter_column("checklists", "access_all_subdivisions", server_default=None)
    op.alter_column("checklists", "control_all_restaurants", server_default=None)
    op.alter_column("checklists", "control_all_subdivisions", server_default=None)


def downgrade() -> None:
    op.drop_column("checklists", "control_all_subdivisions")
    op.drop_column("checklists", "control_all_restaurants")
    op.drop_column("checklists", "control_subdivision_ids")
    op.drop_column("checklists", "control_restaurant_ids")
    op.drop_column("checklists", "access_all_subdivisions")
    op.drop_column("checklists", "access_subdivision_ids")
