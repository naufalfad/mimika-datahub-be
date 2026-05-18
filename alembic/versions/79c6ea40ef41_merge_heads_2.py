"""merge heads 2

Revision ID: 79c6ea40ef41
Revises: 7acfe5ecb3e2, 979b9aaa7980
Create Date: 2026-05-13 14:12:06.456554

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '79c6ea40ef41'
down_revision: Union[str, Sequence[str], None] = ('7acfe5ecb3e2', '979b9aaa7980')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
