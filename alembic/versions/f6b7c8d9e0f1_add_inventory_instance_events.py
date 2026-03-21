"""add inventory instance events

Revision ID: f6b7c8d9e0f1
Revises: f5a6b7c8d9e0
Create Date: 2026-03-18 12:40:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f6b7c8d9e0f1"
down_revision = "f5a6b7c8d9e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inv_item_instance_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("instance_id", sa.Integer(), nullable=True),
        sa.Column("sequence_no", sa.Integer(), nullable=True),
        sa.Column("instance_code_snapshot", sa.String(length=80), nullable=True),
        sa.Column("purchase_cost", sa.Numeric(12, 2), nullable=True),
        sa.Column("from_location_kind", sa.String(length=32), nullable=True),
        sa.Column("from_restaurant_id", sa.Integer(), nullable=True),
        sa.Column("from_subdivision_id", sa.Integer(), nullable=True),
        sa.Column("to_location_kind", sa.String(length=32), nullable=True),
        sa.Column("to_restaurant_id", sa.Integer(), nullable=True),
        sa.Column("to_subdivision_id", sa.Integer(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["from_restaurant_id"], ["restaurants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["from_subdivision_id"], ["restaurant_subdivisions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["instance_id"], ["inv_item_instances.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["item_id"], ["inv_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_restaurant_id"], ["restaurants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["to_subdivision_id"], ["restaurant_subdivisions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inv_item_instance_events_action_created", "inv_item_instance_events", ["action_type", "created_at"])
    op.create_index("ix_inv_item_instance_events_actor_id", "inv_item_instance_events", ["actor_id"])
    op.create_index("ix_inv_item_instance_events_code_created", "inv_item_instance_events", ["instance_code_snapshot", "created_at"])
    op.create_index("ix_inv_item_instance_events_from_rest", "inv_item_instance_events", ["from_location_kind", "from_restaurant_id"])
    op.create_index("ix_inv_item_instance_events_instance_id", "inv_item_instance_events", ["instance_id"])
    op.create_index("ix_inv_item_instance_events_item_created", "inv_item_instance_events", ["item_id", "created_at"])
    op.create_index("ix_inv_item_instance_events_item_id", "inv_item_instance_events", ["item_id"])
    op.create_index("ix_inv_item_instance_events_to_rest", "inv_item_instance_events", ["to_location_kind", "to_restaurant_id"])
    op.execute(
        """
        INSERT INTO inv_item_instance_events (
            created_at,
            action_type,
            item_id,
            instance_id,
            sequence_no,
            instance_code_snapshot,
            purchase_cost,
            to_location_kind,
            to_restaurant_id,
            to_subdivision_id,
            comment
        )
        SELECT
            COALESCE(arrived_at, created_at, now()),
            'quantity_increase',
            item_id,
            id,
            sequence_no,
            instance_code,
            purchase_cost,
            location_kind,
            restaurant_id,
            subdivision_id,
            'Начальная точка истории единицы'
        FROM inv_item_instances
        """
    )


def downgrade() -> None:
    op.drop_index("ix_inv_item_instance_events_to_rest", table_name="inv_item_instance_events")
    op.drop_index("ix_inv_item_instance_events_item_id", table_name="inv_item_instance_events")
    op.drop_index("ix_inv_item_instance_events_item_created", table_name="inv_item_instance_events")
    op.drop_index("ix_inv_item_instance_events_instance_id", table_name="inv_item_instance_events")
    op.drop_index("ix_inv_item_instance_events_from_rest", table_name="inv_item_instance_events")
    op.drop_index("ix_inv_item_instance_events_code_created", table_name="inv_item_instance_events")
    op.drop_index("ix_inv_item_instance_events_actor_id", table_name="inv_item_instance_events")
    op.drop_index("ix_inv_item_instance_events_action_created", table_name="inv_item_instance_events")
    op.drop_table("inv_item_instance_events")
