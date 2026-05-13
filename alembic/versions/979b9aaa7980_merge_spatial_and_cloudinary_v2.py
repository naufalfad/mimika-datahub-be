"""merge_spatial_and_cloudinary_v2

Revision ID: 979b9aaa7980
Revises: 72a6b426750b, df4e62abe04e, e07ddef9c19f
Create Date: 2026-05-13 12:22:47.899481

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '979b9aaa7980'
down_revision: Union[str, Sequence[str], None] = ('72a6b426750b', 'df4e62abe04e', 'e07ddef9c19f')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
