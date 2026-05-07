"""create_users_table_and_seed

Revision ID: 892527d5c154
Revises: fe395a9d2545
Create Date: 2026-05-05 11:20:44.459064

"""
from typing import Sequence, Union

from alembic import op
from app.core.security import get_password_hash
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '892527d5c154'
down_revision: Union[str, Sequence[str], None] = 'fe395a9d2545'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Buat Tabel Users (Biasanya terisi otomatis jika pakai --autogenerate, 
    # jika tidak, pastikan tabel dibuat dulu)
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('role', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=True, unique=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 2. SEEDER: Masukkan User Awal
    # Password admin: admin123
    # Password user: user123
    op.execute(
        f"INSERT INTO users (username, hashed_password, full_name, role, email, is_active) VALUES "
        f"('admin', '{get_password_hash('password123')}', 'Admin', 'admin', 'admin@gmail.com', true),"
        f"('user', '{get_password_hash('password123')}', 'Operator OPD', 'user', 'user@gmail.com', true)"
    )

def downgrade() -> None:
    op.drop_table('users')