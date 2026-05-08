from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import models
from app.schemas import schemas
from typing import List
from app.api.deps import get_admin_user
from sqlalchemy import func, String

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
def get_datasets_pemerintah(
    category_id: int = None,
    source_id: int = None,
    source_type_id: int = None,
    year: int = None,
    db: Session = Depends(get_db)
    ):
    query = db.query(models.Dataset).filter(
        models.Dataset.dataset_type == "pemerintah",
        models.Dataset.status == "approved"
    )
    
    # Logic Filtering
    if category_id:
        query = query.filter(models.Dataset.category_id == category_id)
    if source_id:
        query = query.filter(models.Dataset.source_id == source_id)
    if source_type_id:
        query = query.filter(models.Dataset.source_type_id == source_type_id)
    if year: # Tambahkan logika filtering year
        query = query.filter(models.Dataset.year == year)
        
    return query.all()

@router.get("/non-pemerintah", response_model=List[schemas.DatasetOut])
def get_datasets_non_pemerintah(
    category_id: int = None,
    source_id: int = None,
    source_type_id: int = None,
    year: int = None,
    db: Session = Depends(get_db)
    ):
    query = db.query(models.Dataset).filter(
        models.Dataset.dataset_type == "non-pemerintah",
        models.Dataset.status == "approved"
    )
    
    # Logic Filtering
    if category_id:
        query = query.filter(models.Dataset.category_id == category_id)
    if source_id:
        query = query.filter(models.Dataset.source_id == source_id)
    if source_type_id:
        query = query.filter(models.Dataset.source_type_id == source_type_id)
    if year: # Tambahkan logika filtering year
        query = query.filter(models.Dataset.year == year)
        
    return query.all()

@router.get("/sidebar-stats", response_model=schemas.SidebarStats)
def get_sidebar_stats(dataset_type: str = "pemerintah", db: Session = Depends(get_db)):
    """
    Mengambil daftar filter beserta jumlah dataset yang terkait 
    berdasarkan dataset_type (pemerintah/non-pemerintah)
    """
    
    # 1. Hitung berdasarkan Kategori
    categories = db.query(
        models.Category.id,
        models.Category.name,
        func.count(models.Dataset.id).label("count")
    ).join(models.Dataset, models.Dataset.category_id == models.Category.id)\
     .filter(models.Dataset.dataset_type == dataset_type, models.Dataset.status == "approved")\
     .group_by(models.Category.id).all()

    # 2. Hitung berdasarkan Source (OPD)
    sources = db.query(
        models.Source.id,
        models.Source.name,
        func.count(models.Dataset.id).label("count")
    ).join(models.Dataset, models.Dataset.source_id == models.Source.id)\
     .filter(models.Dataset.dataset_type == dataset_type, models.Dataset.status == "approved")\
     .group_by(models.Source.id).all()

    # 3. Hitung berdasarkan Source Type (Internal/Eksternal)
    source_types = db.query(
        models.SourceType.id,
        models.SourceType.name,
        func.count(models.Dataset.id).label("count")
    ).join(models.Dataset, models.Dataset.source_type_id == models.SourceType.id)\
     .filter(models.Dataset.dataset_type == dataset_type, models.Dataset.status == "approved")\
     .group_by(models.SourceType.id).all()
    
    years = db.query(
        models.Dataset.year.label("id"), # Menggunakan value tahun sebagai ID
        models.Dataset.year.cast(String).label("name"), # Mengconvert tahun ke string untuk Nama
        func.count(models.Dataset.id).label("count")
    ).filter(
        models.Dataset.dataset_type == dataset_type, 
        models.Dataset.status == "approved"
    ).group_by(models.Dataset.year)\
     .order_by(models.Dataset.year.desc()).all()

    return {
        "categories": categories,
        "sources": sources,
        "source_types": source_types,
        "years": years
    }