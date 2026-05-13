from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import models
from app.schemas import schemas
from typing import List, Optional
from fastapi.responses import StreamingResponse
from app.services.export_engine import ExportEngine
from app.api import deps
from sqlalchemy import or_

import csv
import io

router = APIRouter()

@router.get("/content/{dataset_id}")
def get_dataset_content(
    dataset_id: int, 
    limit: int = 100, # Batasi 100 baris untuk preview agar ringan
    db: Session = Depends(get_db)
):
    """
    Mengambil isi data bersih (data_rows) untuk preview tabel seperti Excel.
    """
    # 1. Ambil info dataset untuk dapetin headernya
    dataset = db.query(models.Dataset).filter(models.Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan")

    # 2. Ambil baris datanya
    rows = db.query(models.DataRow).filter(models.DataRow.dataset_id == dataset_id).limit(limit).all()
    
    # 3. Increment view count (karena data sedang diakses/dilihat)
    dataset.view_count += 1
    db.commit()

    # 4. Susun respon agar frontend tinggal render <thead> dan <tbody>
    return {
        "title": dataset.title,
        "type": dataset.dataset_type,
        "headers": dataset.headers,  # Contoh: ["nama_distrik", "jumlah_penduduk"]
        "rows": [r.content for r in rows] # Contoh: [{"nama_distrik": "Mimika Baru", "jumlah_penduduk": 1000}, ...]
    }

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
    current_user: models.User = Depends(deps.get_current_user)
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

@router.get("/export-monitoring-csv")
def export_monitoring_csv(db: Session = Depends(get_db), admin: models.User = Depends(deps.get_admin_user)):
    # Re-use logika dari summary (atau panggil fungsi internal)
    # Untuk singkatnya, kita ambil data user role 'user'
    users_opd = db.query(models.User).filter(models.User.role == "user").all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Nama OPD", "Email", "Progress", "Status", "Rerata Kualitas"])

    now = datetime.now()
    for u in users_opd:
        count = db.query(models.Dataset).filter(
            models.Dataset.user_id == u.id,
            extract('month', models.Dataset.created_at) == now.month,
            extract('year', models.Dataset.created_at) == now.year,
            models.Dataset.status == "approved"
        ).count()
        
        status = "Lengkap" if count >= 12 else "Kurang" if count > 0 else "Belum Kirim"
        avg_q = db.query(func.avg(models.Dataset.quality_score)).filter(models.Dataset.user_id == u.id).scalar() or 0
        
        writer.writerow([u.full_name, u.email, f"{count}/12", status, f"{round(float(avg_q), 2)}%"])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=monitoring_opd.csv"}
    )

@router.get("/search-suggestions")
def get_search_suggestions(
    q: str = Query(..., min_length=1), 
    db: Session = Depends(get_db)
):
    """
    Fitur pencarian untuk landing page:
    1. Mencari kategori yang namanya mirip 'q'
    2. Mencari dataset yang judulnya mirip 'q'
    """
    # Mencari kategori yang relevan
    categories = db.query(models.Category).filter(
        models.Category.name.ilike(f"%{q}%")
    ).limit(5).all()

    # Mencari dataset yang relevan (hanya yang sudah approved)
    datasets = db.query(models.Dataset).filter(
        models.Dataset.status == "approved",
        or_(
            models.Dataset.title.ilike(f"%{q}%"),
            models.Dataset.description.ilike(f"%{q}%")
        )
    ).limit(10).all()

    return {
        "suggestions": {
            "categories": [{"id": c.id, "name": c.name} for c in categories],
            "datasets": [
                {
                    "id": d.id, 
                    "title": d.title, 
                    "category_id": d.category_id,
                    "dataset_type": d.dataset_type
                } for d in datasets
            ]
        }
    }

@router.get("/search-by-category")
def search_by_category(
    category_id: int, 
    q: Optional[str] = None, 
    db: Session = Depends(get_db)
):
    """
    Mencari dataset spesifik di dalam satu kategori
    """
    query = db.query(models.Dataset).filter(
        models.Dataset.category_id == category_id,
        models.Dataset.status == "approved"
    ) 

    if q:
        query = query.filter(models.Dataset.title.ilike(f"%{q}%"))

    results = query.all()
    return results 