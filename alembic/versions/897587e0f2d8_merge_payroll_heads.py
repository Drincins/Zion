"""merge payroll heads

Revision ID: 897587e0f2d8
Revises: acc7caa498d2, 6fb1c9986191
Create Date: 2025-11-13 01:05:10.957279

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '897587e0f2d8'
down_revision: Union[str, Sequence[str], None] = ('acc7caa498d2', '6fb1c9986191')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
