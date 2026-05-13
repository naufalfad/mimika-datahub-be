from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.db.session import get_db
from app.services.atlas_service import AtlasService

router = APIRouter()

@router.get("/indicators/list", response_model=List[str])
def list_available_indicators(db: Session = Depends(get_db)):
    """
    Mengambil semua daftar kunci indikator (headers) yang tersedia 
    dari dataset yang sudah disetujui (Approved).
    """
    indicators = AtlasService.get_available_indicators(db)
    if not indicators:
        return []
    return indicators

@router.get("/indicators/{indicator_type}")
def get_atlas_data(indicator_type: str, db: Session = Depends(get_db)):
    """
    Endpoint utama untuk Atlas Scrollytelling:
    Mengembalikan metadata indikator dan data spasial per distrik 
    untuk di-render menjadi peta Choropleth.
    """
    
    # 1. Ambil data agregat spasial (ID Distrik -> Nilai)
    spatial_data = AtlasService.get_indicator_data(db, indicator_type)
    
    # Validasi: Jika tidak ada data sama sekali untuk indikator tersebut
    if not spatial_data:
        raise HTTPException(
            status_code=404, 
            detail=f"Indikator '{indicator_type}' tidak ditemukan atau belum memiliki data yang valid."
        )
    
    # 2. Ambil metadata (Judul, Satuan, Deskripsi, Warna)
    metadata = AtlasService.get_indicator_metadata(indicator_type)
    
    # 3. Kembalikan response terpadu
    return {
        "indicator": indicator_type,
        "metadata": metadata,
        "data": spatial_data
    }

@router.get("/indicators/meta/all")
def get_all_indicators_metadata(db: Session = Depends(get_db)):
    """
    Helper endpoint untuk mendapatkan metadata dari beberapa indikator utama sekaligus.
    Berguna untuk inisialisasi awal halaman Atlas.
    """
    main_indicators = ["stunting", "jumlah_penduduk", "pdrb"]
    results = []
    
    for key in main_indicators:
        results.append({
            "key": key,
            "metadata": AtlasService.get_indicator_metadata(key)
        })
        
    return results