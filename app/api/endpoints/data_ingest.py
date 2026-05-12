from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.models import models
from app.schemas import schemas
from app.services.cleaning_engine import CleaningEngine
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/upload-process", response_model=schemas.UploadResponse)
async def upload_and_process_form(
    title: str = Form(...),
    dataset_type: str = Form(...),
    source_id: int = Form(...),
    category_id: int = Form(...),
    source_type_id: int = Form(...),
    year: int = Form(...),
    period: str = Form(...),
    description: str = Form(None),
    district_id: Optional[int] = Form(None), # Tambahan parameter spasial dari form
    file: UploadFile = File(...), 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # 1. Ekstraksi File (Pindah ke awal sebelum menyentuh DB)
    contents = await file.read()
    
    try:
        # 2. Cleaning & Alignment Pipeline
        headers, cleaned_records, empty_rows_count = CleaningEngine.clean_and_align(contents)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # ==========================================
    # 3. INTERVENSI GIS: VALIDASI WILAYAH LOKAL
    # ==========================================
    # Ambil kamus absolut 18 Distrik dari DB untuk komparasi O(1)
    valid_districts = {d.name for d in db.query(models.District).all()}
    spatial_keywords = ['distrik', 'kecamatan', 'wilayah', 'daerah']
    
    for rec in cleaned_records:
        for key, val in rec["content"].items():
            if val and any(kw in str(key).lower() for kw in spatial_keywords):
                if val not in valid_districts:
                    # Pola Fail-Fast: Tolak file secara brutal jika wilayah tidak valid
                    raise HTTPException(
                        status_code=422, 
                        detail=f"Validation Error: Wilayah '{val}' pada kolom '{key}' tidak dikenali sebagai distrik administratif Kabupaten Mimika."
                    )
    # ==========================================

    initial_status = "approved" if current_user.role == "admin" else "pending"
    
    # 4. Simpan Metadata Dataset
    new_dataset = models.Dataset(
        title=title,
        dataset_type=dataset_type,
        source_id=source_id,
        category_id=category_id,
        source_type_id=source_type_id,
        district_id=district_id, # Injeksi Foreign Key Spasial (jika ada)
        year=year,
        period=period,
        description=description,
        status=initial_status,
        user_id=current_user.id,
        headers=headers
    )
    
    db.add(new_dataset)
    # Gunakan flush(), bukan commit(). Flush memberikan ID baru untuk foreign key
    # tetapi bisa di-rollback 100% jika insert record di bawah ini gagal.
    db.flush() 

    try:
        inserted_count = 0
        duplicate_count = 0

        # Optimization: Karena ini insert pertama untuk dataset baru, kita cukup
        # menggunakan Hash Set in-memory untuk mencegah duplikasi di dalam file yang sama.
        existing_hashes = set()

        # 5. Insert Data Rows (Bulk Preparation)
        for rec in cleaned_records:
            if rec["row_hash"] not in existing_hashes:
                db.add(models.DataRow(
                    dataset_id=new_dataset.id,
                    content=rec["content"],
                    row_hash=rec["row_hash"]
                ))
                inserted_count += 1
                existing_hashes.add(rec["row_hash"])
            else:
                duplicate_count += 1

        # 6. Hitung Statistik Evaluasi Kualitas
        total_rows = inserted_count + duplicate_count + empty_rows_count
        q_score = (inserted_count / total_rows * 100) if total_rows > 0 else 100.0

        new_dataset.total_rows = total_rows
        new_dataset.quality_score = round(q_score, 2)

        new_dataset.last_ingest_stats = {
            "inserted": inserted_count,
            "duplicates": duplicate_count,
            "empty": empty_rows_count,
            "total": total_rows
        }

        # 7. Finalisasi Transaksi
        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Terjadi kegagalan arsitektur saat merekam baris data: {str(e)}")

    # 8. Dispatch Response
    return {
        "status": "success",
        "dataset_id": new_dataset.id,
        "headers_found": headers,
        "message": f"Data berhasil diupload dan tervalidasi geografisnya dengan status {initial_status}",
        "stats": {
            "inserted": inserted_count,
            "duplicates": duplicate_count,
            "empty": empty_rows_count,
            "total": total_rows,
            "quality_score": round(q_score, 2)
        }
    }