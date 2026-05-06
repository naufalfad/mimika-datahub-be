from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.models import models
from app.schemas import schemas
from app.core import security
from app.api import deps

router = APIRouter()

# 1. CREATE USER
@router.post("/", response_model=schemas.UserOut)
def create_user(
    user_in: schemas.UserCreate, 
    db: Session = Depends(get_db),
    admin: models.User = Depends(deps.get_admin_user) # Proteksi Admin
):
    # Cek apakah username/email sudah ada
    user = db.query(models.User).filter(
        (models.User.username == user_in.username) | (models.User.email == user_in.email)
    ).first()
    if user:
        raise HTTPException(status_code=400, detail="Username atau Email sudah terdaftar")
    
    new_user = models.User(
        username=user_in.username,
        email=user_in.email,
        full_name=user_in.full_name,
        role=user_in.role,
        hashed_password=security.get_password_hash(user_in.password), # Hash password
        is_active=user_in.is_active
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# 2. READ ALL USERS
@router.get("/", response_model=List[schemas.UserOut])
def read_users(
    db: Session = Depends(get_db),
    admin: models.User = Depends(deps.get_admin_user)
):
    return db.query(models.User).all()

# 3. READ USER BY ID
@router.get("/{user_id}", response_model=schemas.UserOut)
def read_user_by_id(
    user_id: int, 
    db: Session = Depends(get_db),
    admin: models.User = Depends(deps.get_admin_user)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    return user

# 4. UPDATE USER
@router.put("/{user_id}", response_model=schemas.UserOut)
def update_user(
    user_id: int,
    user_in: schemas.UserUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(deps.get_admin_user)
):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    
    update_data = user_in.dict(exclude_unset=True)
    
    # Jika admin mengupdate password
    if "password" in update_data:
        db_user.hashed_password = security.get_password_hash(update_data["password"])
        del update_data["password"]
    
    # Update field lainnya secara dinamis
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user

# 5. DELETE USER
@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(deps.get_admin_user)
):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    
    # Proteksi: Admin tidak bisa menghapus dirinya sendiri agar tidak terkunci
    if db_user.id == admin.id:
        raise HTTPException(status_code=400, detail="Admin tidak bisa menghapus akunnya sendiri")
        
    db.delete(db_user)
    db.commit()
    return {"message": f"User '{db_user.username}' berhasil dihapus"}