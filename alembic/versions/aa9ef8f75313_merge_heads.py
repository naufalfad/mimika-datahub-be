"""merge heads

Revision ID: aa9ef8f75313
Revises: add_spatial_entities, 45caa2a31f73
Create Date: 2026-05-12 12:43:23.244612

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aa9ef8f75313'
down_revision: Union[str, Sequence[str], None] = ('add_spatial_entities', '45caa2a31f73')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
