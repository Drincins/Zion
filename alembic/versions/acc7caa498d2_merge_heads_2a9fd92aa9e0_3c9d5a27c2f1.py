"""merge heads 2a9fd92aa9e0 + 3c9d5a27c2f1

Revision ID: acc7caa498d2
Revises: 2a9fd92aa9e0, 3c9d5a27c2f1
Create Date: 2025-11-13 00:18:02.910332

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'acc7caa498d2'
down_revision: Union[str, Sequence[str], None] = ('2a9fd92aa9e0', '3c9d5a27c2f1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
