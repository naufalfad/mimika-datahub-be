from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import models
from app.schemas import schemas
from app.services.cleaning_engine import CleaningEngine
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/upload-process", response_model=schemas.UploadResponse)
async def upload_and_process_form(
    title: str = Form(...),
    source_id: int = Form(...),
    category_id: int = Form(...),
    year: int = Form(...),
    period: str = Form(...),
    description: str = Form(None),
    file: UploadFile = File(...), 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):

    initial_status = "approved" if current_user.role == "admin" else "pending"
    # 1. Simpan metadata dataset
    new_dataset = models.Dataset(
        title=title,
        source_id=source_id,
        category_id=category_id,
        year=year,
        period=period,
        description=description,
        status=initial_status
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