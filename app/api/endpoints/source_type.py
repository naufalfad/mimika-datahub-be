from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import models
from app.schemas import schemas
from typing import List

router = APIRouter()

@router.post("/", response_model=schemas.SourceTypeOut)
def create_source_type(cat_in: schemas.SourceTypeCreate, db: Session = Depends(get_db)):
    existing = db.query(models.SourceType).filter(models.SourceType.name == cat_in.name).first()
    if existing:
        return existing # Jika sudah ada, kembalikan yang lama
    
    new_cat = models.SourceType(name=cat_in.name)
    db.add(new_cat)
    db.commit()
    db.refresh(new_cat)
    return new_cat

@router.get("/", response_model=List[schemas.SourceTypeOut])
def list_source_type(db: Session = Depends(get_db)):
    return db.query(models.SourceType).all()