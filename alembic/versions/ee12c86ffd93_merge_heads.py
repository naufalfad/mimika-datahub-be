"""merge heads

Revision ID: ee12c86ffd93
Revises: df4e62abe04e, e07ddef9c19f
Create Date: 2026-05-13 13:19:10.170260

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ee12c86ffd93'
down_revision: Union[str, Sequence[str], None] = ('df4e62abe04e', 'e07ddef9c19f')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
