"""merge restaurant subdivision head

Revision ID: 4a8ba5b0bdb7
Revises: 897587e0f2d8, 7e3b8af9d564
Create Date: 2025-11-13 01:26:52.245172

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a8ba5b0bdb7'
down_revision: Union[str, Sequence[str], None] = ('897587e0f2d8', '7e3b8af9d564')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
