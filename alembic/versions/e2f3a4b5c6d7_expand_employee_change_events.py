"""Expand employee change events with context and JSON fields.

Revision ID: e2f3a4b5c6d7
Revises: 3c9d5a27c2f1, 5e6f7a8b9c0d, aa12bb34cc56, c042bde2d1c0, c1a2b3c4d5e6
Create Date: 2026-02-02 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "e2f3a4b5c6d7"
down_revision = ("3c9d5a27c2f1", "5e6f7a8b9c0d", "aa12bb34cc56", "c042bde2d1c0", "c1a2b3c4d5e6")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE employee_change_events ADD COLUMN IF NOT EXISTS entity_type VARCHAR(64)")
    op.execute("ALTER TABLE employee_change_events ADD COLUMN IF NOT EXISTS entity_id INTEGER")
    op.execute("ALTER TABLE employee_change_events ADD COLUMN IF NOT EXISTS old_value_json JSONB")
    op.execute("ALTER TABLE employee_change_events ADD COLUMN IF NOT EXISTS new_value_json JSONB")
    op.execute("ALTER TABLE employee_change_events ADD COLUMN IF NOT EXISTS request_id VARCHAR(64)")
    op.execute("ALTER TABLE employee_change_events ADD COLUMN IF NOT EXISTS ip_address VARCHAR(64)")
    op.execute("ALTER TABLE employee_change_events ADD COLUMN IF NOT EXISTS user_agent TEXT")
    op.execute("ALTER TABLE employee_change_events ADD COLUMN IF NOT EXISTS endpoint VARCHAR(255)")
    op.execute("ALTER TABLE employee_change_events ADD COLUMN IF NOT EXISTS method VARCHAR(16)")
    op.execute("ALTER TABLE employee_change_events ADD COLUMN IF NOT EXISTS restaurant_id INTEGER")
    op.execute("ALTER TABLE employee_change_events ADD COLUMN IF NOT EXISTS position_id INTEGER")
    op.execute("ALTER TABLE employee_change_events ADD COLUMN IF NOT EXISTS role_id INTEGER")

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_employee_change_events_created_at ON employee_change_events (created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_employee_change_events_field ON employee_change_events (field)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_employee_change_events_entity_type ON employee_change_events (entity_type)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_employee_change_events_entity_id ON employee_change_events (entity_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_employee_change_events_request_id ON employee_change_events (request_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_employee_change_events_restaurant_id ON employee_change_events (restaurant_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_employee_change_events_position_id ON employee_change_events (position_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_employee_change_events_role_id ON employee_change_events (role_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_employee_change_events_role_id")
    op.execute("DROP INDEX IF EXISTS ix_employee_change_events_position_id")
    op.execute("DROP INDEX IF EXISTS ix_employee_change_events_restaurant_id")
    op.execute("DROP INDEX IF EXISTS ix_employee_change_events_request_id")
    op.execute("DROP INDEX IF EXISTS ix_employee_change_events_entity_id")
    op.execute("DROP INDEX IF EXISTS ix_employee_change_events_entity_type")
    op.execute("DROP INDEX IF EXISTS ix_employee_change_events_field")
    op.execute("DROP INDEX IF EXISTS ix_employee_change_events_created_at")

    op.execute("ALTER TABLE employee_change_events DROP COLUMN IF EXISTS role_id")
    op.execute("ALTER TABLE employee_change_events DROP COLUMN IF EXISTS position_id")
    op.execute("ALTER TABLE employee_change_events DROP COLUMN IF EXISTS restaurant_id")
    op.execute("ALTER TABLE employee_change_events DROP COLUMN IF EXISTS method")
    op.execute("ALTER TABLE employee_change_events DROP COLUMN IF EXISTS endpoint")
    op.execute("ALTER TABLE employee_change_events DROP COLUMN IF EXISTS user_agent")
    op.execute("ALTER TABLE employee_change_events DROP COLUMN IF EXISTS ip_address")
    op.execute("ALTER TABLE employee_change_events DROP COLUMN IF EXISTS request_id")
    op.execute("ALTER TABLE employee_change_events DROP COLUMN IF EXISTS new_value_json")
    op.execute("ALTER TABLE employee_change_events DROP COLUMN IF EXISTS old_value_json")
    op.execute("ALTER TABLE employee_change_events DROP COLUMN IF EXISTS entity_id")
    op.execute("ALTER TABLE employee_change_events DROP COLUMN IF EXISTS entity_type")
