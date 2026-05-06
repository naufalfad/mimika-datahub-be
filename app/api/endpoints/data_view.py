from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import models
from typing import List, Optional
from fastapi.responses import StreamingResponse
from app.services.export_engine import ExportEngine

router = APIRouter()

@router.get("/preview/{dataset_id}")
def preview_clean_data(
    dataset_id: int, 
    page: int = Query(1, ge=1, description="Nomor halaman"),
    limit: int = Query(50, ge=1, le=100, description="Jumlah baris per halaman"),
    db: Session = Depends(get_db)
):
    """
    Mengambil data yang sudah bersih dari satu dataset tertentu.
    Sudah mendukung paginasi (pagination) agar tidak membebani browser.
    """
    # 1. Ambil Metadata Dataset
    dataset = db.query(models.Dataset).filter(models.Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset ID tidak ditemukan")

    dataset.view_count += 1
    db.commit()

    # 2. Ambil Nama Source (OPD) untuk info tambahan di dashboard
    source = db.query(models.Source).filter(models.Source.id == dataset.source_id).first()
    source_name = source.name if source else "Unknown"

    # 3. Ambil data baris dengan paginasi
    offset = (page - 1) * limit
    rows = db.query(models.DataRow).filter(
        models.DataRow.dataset_id == dataset_id
    ).offset(offset).limit(limit).all()

    # 4. Total Baris (untuk info paginasi di frontend)
    total_rows = db.query(models.DataRow).filter(models.DataRow.dataset_id == dataset_id).count()

    # 5. Ekstrak 'content' dari setiap baris
    clean_data = [r.content for r in rows]

    return {
        "dataset_id": dataset.id,
        "title": dataset.title,
        "source_name": source_name,
        "headers": dataset.headers,  # Daftar kolom yang sudah rapi
        "total_records": total_rows,
        "current_page": page,
        "total_pages": (total_rows + limit - 1) // limit,
        "data": clean_data  # Isi data baris per baris
    }

@router.get("/catalog")
def get_catalog(db: Session = Depends(get_db)):
    """
    Melihat daftar seluruh dataset yang sudah berhasil di-upload ke sistem.
    Ini untuk mengisi menu utama atau katalog data pemerintah.
    """
    datasets = db.query(models.Dataset).filter(models.Dataset.status == "approved").all()
    # datasets = db.query(models.Dataset).all()
    catalog = []
    
    for ds in datasets:
        source = db.query(models.Source).filter(models.Source.id == ds.source_id).first()
        row_count = db.query(models.DataRow).filter(models.DataRow.dataset_id == ds.id).count()
        
        catalog.append({
            "id": ds.id,
            "title": ds.title,
            "source_name": source.name if source else "Unknown",
            "source_type": source.type if source else "Unknown",
            "columns": ds.headers,
            "total_records": row_count,
            "created_at": ds.created_at.strftime("%Y-%m-%d %H:%M:%S") if ds.created_at else None
        })
        
    return catalog

@router.get("/export/{dataset_id}")
def export_dataset(dataset_id: int, db: Session = Depends(get_db)):
    rows = db.query(models.DataRow).filter(models.DataRow.dataset_id == dataset_id).all()
    if not rows:
        raise HTTPException(status_code=404, detail="Tidak ada data untuk di-export")
    
    clean_data = [r.content for r in rows]
    file_obj = ExportEngine.to_excel(clean_data, f"export_{dataset_id}")
    
    return StreamingResponse(
        file_obj,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=mimika_data_clean_{dataset_id}.xlsx"}
    )

@router.get("/my-datasets", response_model=List[schemas.DatasetOut])
def get_my_datasets(
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """Mengambil dataset yang diupload oleh user yang sedang login"""
    return db.query(models.Dataset).filter(models.Dataset.user_id == current_user.id).all()

@router.get("/export-list")
def export_dataset_list(
    dataset_type: str, # 'pemerintah' atau 'non-pemerintah'
    file_format: str = "excel", # 'excel' atau 'csv'
    db: Session = Depends(get_db)
):
    datasets = db.query(models.Dataset).filter(
        models.Dataset.dataset_type == dataset_type,
        models.Dataset.status == "approved"
    ).all()
    
    # Format data untuk excel
    data_to_export = []
    for d in datasets:
        data_to_export.append({
            "ID": d.id,
            "Judul Dataset": d.title,
            "Tahun": d.year,
            "Periode": d.period,
            "Total Baris": d.total_rows,
            "Skor Kualitas": f"{d.quality_score}%",
            "Uploader ID": d.user_id,
            "Tanggal Dibuat": d.created_at.strftime("%Y-%m-%d")
        })

    if file_format == "csv":
        csv_data = ExportEngine.list_to_csv(data_to_export)
        return StreamingResponse(io.BytesIO(csv_data), media_type="text/csv", 
                                headers={"Content-Disposition": f"attachment; filename=list_{dataset_type}.csv"})
    
    excel_file = ExportEngine.list_to_excel(data_to_export, "Datasets")
    return StreamingResponse(excel_file, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            headers={"Content-Disposition": f"attachment; filename=list_{dataset_type}.xlsx"})