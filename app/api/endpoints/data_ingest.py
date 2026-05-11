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

    category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not category or not category.template_url:
        raise HTTPException(status_code=400, detail="Kategori tidak ditemukan atau belum memiliki template gambar")

    # 2. PROSES UPLOAD GAMBAR USER
    try:
        image_bytes = await image.read()
        # Folder akan otomatis terbuat di Cloudinary: mimika_datahub/user_uploads
        photo_url, photo_public_id = upload_image_to_cloudinary(
            image_bytes, 
            folder_name="mimika_datahub/user_uploads"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal upload gambar: {str(e)}")

    # try:
    #     # Teknik extract public_id dari URL (mengambil path folder + nama file)
    #     parts = category.template_url.split('/upload/')[-1].split('/')
    #     # Gabungkan folder dan nama file, ganti '/' menjadi ':' sesuai aturan Cloudinary overlay
    #     template_id_raw = "/".join(parts[1:]) # menghilangkan versi 'v12345/'
    #     template_public_id = template_id_raw.split('.')[0].replace('/', ':')

    #     # Generate Merged URL: Bingkai (u_...) diletakkan di atas Foto User
    #     cloud_name = "drcgddki1"
    #     merged_url = f"https://res.cloudinary.com/{cloud_name}/image/upload/u_{template_public_id},fl_relative,w_1.0,h_1.0/{photo_public_id}.png"
    # except:
    #     merged_url = photo_url # Fallback jika gagal generate

    initial_status = "approved" if current_user.role == "admin" else "pending"
    # 1. Simpan metadata dataset
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
        image_url=photo_url,
        # merged_image_url=merged_url
    )
    db.add(new_dataset)
    db.commit()
    db.refresh(new_dataset)

    contents = await file.read()

    try:
        # 2. Cleaning
        headers, cleaned_records, empty_rows_count = CleaningEngine.clean_and_align(contents)

        new_dataset.headers = headers

        inserted_count = 0
        duplicate_count = 0

        # ambil hash yang sudah ada
        existing_hashes = set(
            r[0] for r in db.query(models.DataRow.row_hash)
            .filter(models.DataRow.dataset_id == new_dataset.id)
            .all()
        )

        # 3. Insert data
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

        # 4. Hitung statistik
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

        # 5. Commit
        db.commit()

    except Exception as e:
        db.rollback()

        # optional: hapus dataset kalau gagal total
        db.delete(new_dataset)
        db.commit()

        raise HTTPException(status_code=400, detail=str(e))

    # 6. Response (DI LUAR try)
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