"""add_district_profiles

Revision ID: 715b4b37b750
Revises: 05d3021b552a
Create Date: 2026-05-12 16:07:24.708183

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '715b4b37b750'
down_revision: Union[str, Sequence[str], None] = 'add_spatial_entities'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'district_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('district_id', sa.Integer(), nullable=False),
        sa.Column('luas_wilayah', sa.Float(), nullable=True),
        sa.Column('jumlah_penduduk', sa.Integer(), nullable=True),
        sa.Column('deskripsi', sa.Text(), nullable=True),
        sa.Column('batas_wilayah', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['district_id'], ['districts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('district_id')
    )
    op.create_index(op.f('ix_district_profiles_id'), 'district_profiles', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_district_profiles_id'), table_name='district_profiles')
    op.drop_table('district_profiles')