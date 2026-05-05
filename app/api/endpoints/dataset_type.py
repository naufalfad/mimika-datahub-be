from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import models
from app.schemas import schemas
from typing import List

router = APIRouter()

@router.post("/", response_model=schemas.DatasetTypeOut)
def create_dataset_type(cat_in: schemas.DatasetTypeCreate, db: Session = Depends(get_db)):
    existing = db.query(models.DatasetType).filter(models.DatasetType.name == cat_in.name).first()
    if existing:
        return existing # Jika sudah ada, kembalikan yang lama
    
    new_cat = models.DatasetType(name=cat_in.name)
    db.add(new_cat)
    db.commit()
    db.refresh(new_cat)
    return new_cat

@router.get("/", response_model=List[schemas.DatasetTypeOut])
def list_dataset_type(db: Session = Depends(get_db)):
    return db.query(models.DatasetType).all()