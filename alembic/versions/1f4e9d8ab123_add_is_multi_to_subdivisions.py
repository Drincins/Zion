"""Add is_multi flag to restaurant_subdivisions."""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "1f4e9d8ab123"
down_revision = "bf3c2d1a4e5f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "restaurant_subdivisions",
        sa.Column("is_multi", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.alter_column("restaurant_subdivisions", "is_multi", server_default=None)


def downgrade():
    op.drop_column("restaurant_subdivisions", "is_multi")

