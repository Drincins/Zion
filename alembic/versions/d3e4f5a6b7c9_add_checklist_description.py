"""add checklist description

Revision ID: d3e4f5a6b7c9
Revises: c1a2b3c4d5e6
Create Date: 2026-02-02 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d3e4f5a6b7c9"
down_revision = "c1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("checklists", sa.Column("description", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("checklists", "description")
