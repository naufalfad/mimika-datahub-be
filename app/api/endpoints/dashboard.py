from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.models import models

router = APIRouter()

@router.get("/stats")
def get_global_stats(db: Session = Depends(get_db)):
    """Memberikan ringkasan data untuk kartu statistik di Dashboard utama"""
    total_sources = db.query(models.Source).count()
    total_datasets = db.query(models.Dataset).count()
    total_rows = db.query(func.sum(models.Dataset.total_rows)).scalar() or 0
    avg_quality = db.query(func.avg(models.Dataset.quality_score)).scalar() or 0
    
    return {
        "summary": {
            "total_sources": total_sources,
            "total_datasets": total_datasets,
            "total_records": total_rows,
            "avg_system_quality": f"{round(avg_quality, 2)}%"
        }
    }

@router.get("/source-performance")
def get_source_performance(db: Session = Depends(get_db)):
    """Melihat performa upload per OPD (Sesuai mockup monitoring-opd.html)"""
    sources = db.query(models.Source).all()
    performance = []
    
    for s in sources:
        datasets_count = db.query(models.Dataset).filter(models.Dataset.source_id == s.id).count()
        avg_q = db.query(func.avg(models.Dataset.quality_score)).filter(models.Dataset.source_id == s.id).scalar() or 0
        
        performance.append({
            "source_name": s.name,
            "total_datasets": datasets_count,
            "average_quality": f"{round(avg_q, 2)}%",
            "status": "Aktif" if datasets_count > 0 else "Belum Upload"
        })
        
    return performance