from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import models
from app.core import security
from app.api import deps
from app.schemas import schemas

router = APIRouter()

@router.post("/login")
def login(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Username atau password salah")
    
    return {
        "access_token": security.create_access_token(user.username),
        "token_type": "bearer",
        "role": user.role
    }

@router.get("/me", response_model=schemas.UserOut)
def get_user_profile(current_user: models.User = Depends(deps.get_current_user)):
    """Mengambil data profil user yang sedang login berdasarkan token"""
    return current_user

@router.post("/logout")
def logout(current_user: models.User = Depends(deps.get_current_user)):
    """
    Endpoint Logout.
    Karena menggunakan JWT, logout dilakukan dengan cara:
    1. Backend memberikan respon sukses.
    2. Frontend HARUS menghapus token dari local storage/cookies.
    """
    return {
        "status": "success", 
        "message": f"User {current_user.username} berhasil logout."
    }