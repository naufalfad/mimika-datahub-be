from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import models
from app.schemas import schemas
from typing import List
import shutil
import os
import uuid

router = APIRouter()

UPLOAD_DIR = "static/categories"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/", response_model=schemas.CategoryOut)
async def create_category(
    name: str = Form(...), 
    image: UploadFile = File(None), 
    db: Session = Depends(get_db)
):
    # 1. Cek apakah kategori sudah ada
    existing = db.query(models.Category).filter(models.Category.name == name).first()
    if existing:
        return existing

    # 2. Proses Upload Gambar jika ada
    image_path = None
    if image:
        # Buat nama file unik untuk menghindari bentrok nama
        file_extension = image.filename.split(".")[-1]
        file_name = f"{uuid.uuid4()}.{file_extension}"
        image_path = f"{UPLOAD_DIR}/{file_name}"
        
        with open(image_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)

    # 3. Simpan ke Database
    new_cat = models.Category(
        name=name,
        image_url=image_path # Simpan path gambar
    )
    db.add(new_cat)
    db.commit()
    db.refresh(new_cat)
    return new_cat

@router.get("/", response_model=List[schemas.CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.query(models.Category).all()