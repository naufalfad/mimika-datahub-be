"""add spatial entities

Revision ID: [akan terisi otomatis oleh alembic]
Revises: [akan terisi otomatis oleh alembic]
Create Date: 2026-05-12 09:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

# revision identifiers, used by Alembic.
revision = 'add_spatial_entities'
down_revision = '17317ad032dc'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Buat Tabel districts
    op.create_table(
        'districts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_districts_id'), 'districts', ['id'], unique=False)
    op.create_index(op.f('ix_districts_name'), 'districts', ['name'], unique=True)

    # 2. Tambahkan kolom district_id ke tabel datasets
    op.add_column('datasets', sa.Column('district_id', sa.Integer(), nullable=True))
    
    # 3. Buat Foreign Key Constraint
    op.create_foreign_key(
        'fk_dataset_district',
        'datasets', 'districts',
        ['district_id'], ['id']
    )

    # 4. Seeder: Suntikkan 18 Nama Distrik Mimika
    # Mendefinisikan tabel untuk operasi bulk insert
    districts_table = table(
        'districts',
        column('name', sa.String)
    )

    op.bulk_insert(
        districts_table,
        [
            {"name": "Mimika Baru"},
            {"name": "Kuala Kencana"},
            {"name": "Tembagapura"},
            {"name": "Wania"},
            {"name": "Iwaka"},
            {"name": "Kwamki Narama"},
            {"name": "Mimika Timur"},
            {"name": "Mimika Tengah"},
            {"name": "Mimika Barat"},
            {"name": "Agimuga"},
            {"name": "Jila"},
            {"name": "Jita"},
            {"name": "Mimika Timur Jauh"},
            {"name": "Mimika Barat Jauh"},
            {"name": "Mimika Barat Tengah"},
            {"name": "Amar"},
            {"name": "Hoya"},
            {"name": "Alama"}
        ]
    )


def downgrade():
    # 1. Hapus Foreign Key Constraint
    op.drop_constraint('fk_dataset_district', 'datasets', type_='foreignkey')
    
    # 2. Hapus kolom district_id di tabel datasets
    op.drop_column('datasets', 'district_id')
    
    # 3. Hapus tabel districts dan index-nya
    op.drop_index(op.f('ix_districts_name'), table_name='districts')
    op.drop_index(op.f('ix_districts_id'), table_name='districts')
    op.drop_table('districts')