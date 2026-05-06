from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import models
from app.schemas import schemas
from typing import List
from app.api.deps import get_admin_user

router = APIRouter()

# Mengambil daftar semua Dataset
@router.get("/", response_model=List[schemas.DatasetOut])
def list_datasets(db: Session = Depends(get_db)):
    return db.query(models.Dataset).all()

@router.patch("/{dataset_id}/approve")
def approve_dataset(
    dataset_id: int, 
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user) # Hanya admin yang bisa lewat
):
    dataset = db.query(models.Dataset).filter(models.Dataset.id == dataset_id).first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan")
    
    dataset.status = "approved"
    db.commit()
    
    return {"message": f"Dataset '{dataset.title}' berhasil disetujui (Approved)"}

# Endpoint Admin untuk melihat dataset yang masih pending
@router.get("/pending-list")
def get_pending_datasets(
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user)
):
    return db.query(models.Dataset).filter(models.Dataset.status == "pending").all()

# Endpoint Admin untuk melihat dataset approved
@router.get("/approved-list")
def get_approved_datasets(
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user)
):
    return db.query(models.Dataset).filter(models.Dataset.status == "approved").all()

@router.get("/pemerintah", response_model=List[schemas.DatasetOut])
def get_datasets_pemerintah(db: Session = Depends(get_db)):
    """Mengambil semua dataset tipe pemerintah yang sudah approved"""
    return db.query(models.Dataset).filter(
        models.Dataset.dataset_type == "pemerintah",
        models.Dataset.status == "approved"
    ).all()

@router.get("/non-pemerintah", response_model=List[schemas.DatasetOut])
def get_datasets_non_pemerintah(db: Session = Depends(get_db)):
    """Mengambil semua dataset tipe non-pemerintah yang sudah approved"""
    return db.query(models.Dataset).filter(
        models.Dataset.dataset_type == "non-pemerintah",
        models.Dataset.status == "approved"
    ).all()