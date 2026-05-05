from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import models
from app.schemas import schemas
from app.services.cleaning_engine import CleaningEngine

router = APIRouter()

@router.post("/upload-process", response_model=schemas.UploadResponse)
async def upload_and_process_form(
    # Informasi dari Form (dikirim sebagai form-data)
    title: str = Form(...),
    source_id: int = Form(...),
    category_id: int = Form(...),
    year: int = Form(...),
    period: str = Form(...),
    description: str = Form(None),
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    # 1. Simpan Metadata Dataset terlebih dahulu
    new_dataset = models.Dataset(
        title=title,
        source_id=source_id,
        category_id=category_id,
        year=year,
        period=period,
        description=description
    )
    db.add(new_dataset)
    db.commit()
    db.refresh(new_dataset)

    # 2. Proses File melalui Cleaning Engine
    contents = await file.read()
    try:
        headers, cleaned_records = CleaningEngine.clean_and_align(contents)
    except Exception as e:
        db.delete(new_dataset) # Rollback metadata jika file rusak
        db.commit()
        raise HTTPException(status_code=400, detail=str(e))

    # 3. Update headers
    new_dataset.headers = headers

    # 4. Simpan baris data & Cek Redundansi
    inserted_count = 0
    duplicate_count = 0

    for rec in cleaned_records:
        # Cek duplikasi baris dalam dataset ini
        exists = db.query(models.DataRow).filter(
            models.DataRow.dataset_id == new_dataset.id,
            models.DataRow.row_hash == rec["row_hash"]
        ).first()

        if not exists:
            new_row = models.DataRow(
                dataset_id=new_dataset.id,
                content=rec["content"],
                row_hash=rec["row_hash"]
            )
            db.add(new_row)
            inserted_count += 1
        else:
            duplicate_count += 1

    # 5. Hitung Skor Kualitas
    total_processed = inserted_count + duplicate_count
    q_score = (inserted_count / total_processed * 100) if total_processed > 0 else 100.0

    new_dataset.total_rows = inserted_count
    new_dataset.quality_score = round(q_score, 2)
    
    db.commit()

    return {
        "status": "success",
        "dataset_id": new_dataset.id,
        "headers_found": headers,
        "new_records": inserted_count,
        "duplicates_ignored": duplicate_count
    }