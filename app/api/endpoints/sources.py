from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import models
from app.schemas import schemas
from typing import List

router = APIRouter()

# Menambah Sumber Data Baru (OPD/BPS/dll)
@router.post("/", response_model=schemas.SourceOut)
def create_source(source_in: schemas.SourceCreate, db: Session = Depends(get_db)):
    # Cek apakah nama sudah ada
    existing = db.query(models.Source).filter(models.Source.name == source_in.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Nama Sumber Data sudah terdaftar")
    
    new_source = models.Source(
        name=source_in.name,
        type=source_in.type,
        icon=source_in.icon
    )
    db.add(new_source)
    db.commit()
    db.refresh(new_source)
    return new_source

# Mengambil daftar semua Sumber Data
@router.get("/", response_model=List[schemas.SourceOut])
def list_sources(db: Session = Depends(get_db)):
    return db.query(models.Source).all()