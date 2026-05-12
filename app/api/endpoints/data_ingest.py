from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import models
from app.schemas import schemas
from app.services.cleaning_engine import CleaningEngine
from app.api.deps import get_current_user
from app.core.cloudinary_config import upload_image_to_cloudinary
import json
import hashlib

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
    file: UploadFile = File(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # 1. Validasi Kategori
    category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not category or not category.template_url:
        raise HTTPException(status_code=400, detail="Kategori tidak ditemukan atau belum memiliki template gambar")

    # 2. PROSES UPLOAD GAMBAR USER KE CLOUDINARY
    try:
        image_bytes = await image.read()
        # Folder akan otomatis terbuat di Cloudinary: mimika_datahub/user_uploads
        photo_url, photo_public_id = upload_image_to_cloudinary(
            image_bytes, 
            folder_name="mimika_datahub/user_uploads"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal upload gambar: {str(e)}")

    # 3. Tentukan Status Awal (Admin langsung approved, User pending)
    initial_status = "approved" if current_user.role == "admin" else "pending"

    # 4. Simpan Metadata Dataset
    new_dataset = models.Dataset(
        title=title,
        dataset_type=dataset_type,
        source_id=source_id,
        category_id=category_id,
        source_type_id=source_type_id,
        year=year,
        period=period,
        description=description,
        status=initial_status,
        user_id=current_user.id,
        image_url=photo_url
    )
    db.add(new_dataset)
    db.commit()
    db.refresh(new_dataset)

    # 5. Baca Isi File Dataset
    contents = await file.read()

    try:
        # 6. Jalankan Cleaning Engine
        # PERBAIKAN: Menyertakan file.filename agar engine bisa mendeteksi ekstensi .xls/.xlsx/.csv
        headers, cleaned_records, empty_rows_count = CleaningEngine.clean_and_align(
            contents, 
            filename=file.filename
        )

        new_dataset.headers = headers

        inserted_count = 0
        duplicate_count = 0

        # Ambil hash yang sudah ada (untuk pencegahan duplikasi dalam satu dataset)
        existing_hashes = set(
            r[0] for r in db.query(models.DataRow.row_hash)
            .filter(models.DataRow.dataset_id == new_dataset.id)
            .all()
        )

        # 7. Insert Baris Data yang Sudah Bersih
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

        # 8. Hitung Statistik Ingest
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

        # 9. Final Commit untuk DataRows dan Update Stats Dataset
        db.commit()

    except Exception as e:
        db.rollback()
        # Hapus metadata dataset jika proses cleaning/insert gagal total
        db.delete(new_dataset)
        db.commit()
        raise HTTPException(status_code=400, detail=f"Gagal memproses isi file: {str(e)}")

    # 10. Kembalikan Response Sukses
    return {
        "status": "success",
        "dataset_id": new_dataset.id,
        "headers_found": headers,
        "message": f"Data berhasil diupload dengan status {initial_status}",
        "stats": {
            "inserted": inserted_count,
            "duplicates": duplicate_count,
            "empty": empty_rows_count,
            "total": total_rows,
            "quality_score": round(q_score, 2)
        }
    }