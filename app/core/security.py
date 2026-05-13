# app/core/security.py
from datetime import datetime, timedelta
from typing import Any, Union, List
from jose import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status

# PENTING: Ganti SECRET_KEY dengan string acak yang kuat
SECRET_KEY = "MIMIKA_DATAHUB_SUPER_SECRET_KEY_123"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 1 hari

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(subject: Union[str, Any]) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# ==========================================
# INTERVENS: ROLE-BASED ACCESS CONTROL (RBAC)
# ==========================================
class RoleChecker:
    """
    Kelas Dependency Otorisasi RBAC.
    Digunakan untuk memproteksi endpoint berdasarkan 'role' pengguna.
    Sangat esensial untuk membedakan hak akses 'admin' dan 'user' (OPD).
    """
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: Any):
        # Asumsi: current_user adalah instansiasi model User hasil injeksi get_current_user
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sesi tidak valid atau telah berakhir."
            )
            
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Pelanggaran Otorisasi: Role '{current_user.role}' tidak memiliki izin untuk mengakses resource ini."
            )
            
        return current_user