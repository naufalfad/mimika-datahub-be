"""Add Asset & SpatialCache

Revision ID: c5995657278f
Revises: 9384f31db261
Create Date: 2026-06-02 15:06:43.675465

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5995657278f'
down_revision: Union[str, Sequence[str], None] = '9384f31db261'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Pembuatan Tabel Cache Spasial
    op.create_table('spatial_caches',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('indicator_key', sa.String(), nullable=False),
    sa.Column('district_id', sa.Integer(), nullable=False),
    sa.Column('value', sa.Float(), nullable=False),
    sa.Column('last_calculated', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['district_id'], ['districts.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_spatial_caches_id'), 'spatial_caches', ['id'], unique=False)
    op.create_index(op.f('ix_spatial_caches_indicator_key'), 'spatial_caches', ['indicator_key'], unique=False)
    
    # 2. [REFACTOR SAFE MIGRATION] Penambahan Kolom user_id di Tabel Aset
    # a. Tambahkan kolom secara dinamis (Izinkan NULL sementara)
    op.add_column('assets', sa.Column('user_id', sa.Integer(), nullable=True))
    
    # b. Injeksi data default (ID 1) ke baris aset yang sudah ada sebelumnya
    op.execute("UPDATE assets SET user_id = 1 WHERE user_id IS NULL")
    
    # c. Kunci kolom menjadi NOT NULL (Enforce Schema)
    op.alter_column('assets', 'user_id', nullable=False)
    
    # d. Tambahkan Foreign Key
    op.create_foreign_key('fk_assets_user_id', 'assets', 'users', ['user_id'], ['id'])

    # 3. Penambahan Kolom Array Gambar dan Status Moderasi
    op.add_column('assets', sa.Column('images', sa.JSON(), nullable=True))
    op.add_column('assets', sa.Column('status', sa.String(), nullable=True))
    
    # 4. Update District Profile
    op.add_column('district_profiles', sa.Column('images', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('district_profiles', 'images')
    
    # Harus hapus Foreign Key dengan nama spesifik sebelum hapus kolom
    op.drop_constraint('fk_assets_user_id', 'assets', type_='foreignkey')
    op.drop_column('assets', 'status')
    op.drop_column('assets', 'images')
    op.drop_column('assets', 'user_id')
    
    op.drop_index(op.f('ix_spatial_caches_indicator_key'), table_name='spatial_caches')
    op.drop_index(op.f('ix_spatial_caches_id'), table_name='spatial_caches')
    op.drop_table('spatial_caches')