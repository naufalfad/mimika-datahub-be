from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from app.db.session import get_db
from app.schemas import schemas
from app.services.spatial_service import SpatialService

router = APIRouter()

@router.get("/stats", response_model=List[schemas.SpatialStatResponse])
def get_gis_statistics(
    category_id: Optional[int] = Query(None, description="Filter berdasarkan ID Kategori untuk pemetaan sektoral"),
    year: Optional[int] = Query(None, description="Filter berdasarkan Tahun rilis dataset"),
    db: Session = Depends(get_db)
):
    """
    Endpoint agregasi spasial (GIS).
    Mengembalikan array dictionary dengan kompleksitas O(1) untuk rendering peta GeoJSON di frontend.
    Telah diarsiteki dengan Left Outer Join untuk menjamin 18 Distrik selalu dirender.
    """
    # Mendelegasikan logika kalkulasi murni ke layer Service (Pure Fabrication)
    return SpatialService.get_district_stats(db=db, category_id=category_id, year=year)

@router.get("/stats/detail", response_model=Dict[str, Any])
def get_detailed_gis_statistics(
    category_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Endpoint ekspansi spasial.
    Mengembalikan data multivariabel (jumlah row, rata-rata kualitas) untuk kebutuhan Tooltip Interaktif di peta.
    """
    return SpatialService.get_detailed_district_stats(db=db, category_id=category_id)

@router.get("/district/{district_id}/drilldown", response_model=Dict[str, Any])
def get_district_drilldown(
    district_id: int,
    db: Session = Depends(get_db)
):
    """
    Endpoint Drill-Down Spasial (Pop-up Peta).
    Menyajikan narasi statis profil distrik dipadukan dengan agregasi kepadatan dataset per kategori.
    """
    drilldown_data = SpatialService.get_district_drilldown_stats(db=db, district_id=district_id)
    
    if not drilldown_data:
        raise HTTPException(status_code=404, detail="Data Distrik tidak ditemukan di database.")
        
    return drilldown_data