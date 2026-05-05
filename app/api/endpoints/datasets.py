from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import models
from app.schemas import schemas
from typing import List
from app.api.deps import get_admin_user

router = APIRouter()

# Membuat Judul Dataset Baru
@router.post("/", response_model=schemas.DatasetOut)
def create_dataset(dataset_in: schemas.DatasetCreate, db: Session = Depends(get_db)):
    # 1. Pastikan Source ID-nya ada (Cek apakah OPD-nya terdaftar)
    source = db.query(models.Source).filter(models.Source.id == dataset_in.source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source ID tidak ditemukan. Buat Source dulu.")
    
    new_dataset = models.Dataset(
        title=dataset_in.title,
        source_id=dataset_in.source_id
    )
    db.add(new_dataset)
    db.commit()
    db.refresh(new_dataset)
    return new_dataset

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