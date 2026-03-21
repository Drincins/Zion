"""add checklist scope fields

Revision ID: c1a2b3c4d5e6
Revises: b9c1d2e3f4a5
Create Date: 2026-01-30 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c1a2b3c4d5e6"
down_revision = "b9c1d2e3f4a5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("checklists", sa.Column("scope_type", sa.String(), nullable=True))
    op.add_column("checklists", sa.Column("all_restaurants", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("checklists", sa.Column("restaurant_id", sa.Integer(), nullable=True))
    op.add_column(
        "checklists",
        sa.Column("restaurant_subdivision_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_checklists_restaurant_id",
        "checklists",
        "restaurants",
        ["restaurant_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_checklists_restaurant_subdivision_id",
        "checklists",
        "restaurant_subdivisions",
        ["restaurant_subdivision_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_checklists_restaurant_subdivision_id", "checklists", type_="foreignkey")
    op.drop_constraint("fk_checklists_restaurant_id", "checklists", type_="foreignkey")
    op.drop_column("checklists", "restaurant_subdivision_id")
    op.drop_column("checklists", "restaurant_id")
    op.drop_column("checklists", "all_restaurants")
    op.drop_column("checklists", "scope_type")
