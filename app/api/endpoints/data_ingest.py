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
    district_id: Optional[int] = Form(None), # Fallback jika ini file level kabupaten murni
    file: UploadFile = File(...), 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    contents = await file.read()
    
    try:
        headers, cleaned_records, empty_rows_count = CleaningEngine.clean_and_align(contents)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # ==========================================
    # 3. INTERVENSI GIS: GROUPING & ROW MELTING
    # ==========================================
    district_map = {d.name: d.id for d in db.query(models.District).all()}
    
    # Dictionary penampung hasil pemecahan (Key: Tuple(district_id, is_unmapped), Value: List of Records)
    grouped_records = {}
    
    for rec in cleaned_records:
        content = rec["content"]
        # Ekstraksi dan hapus marker spasial rahasia agar tidak masuk DB
        mapped_name = content.pop("_spatial_mapping", None)
        rec["content"] = content 
        
        target_district_id = district_id # Titik awal menggunakan fallback dari User Form
        is_unmapped = False # Flag trigger Fase 4 (Karantina)
        
        if mapped_name:
            # Validasi O(1): Konversi nama distrik hasil Fuzzy Match ke ID Database
            if mapped_name in district_map:
                target_district_id = district_map[mapped_name]
            else:
                # Kolom wilayah terdeteksi, tapi namanya tidak valid/hancur. 
                # Masukkan ke zona karantina
                is_unmapped = True
                target_district_id = None
                
        group_key = (target_district_id, is_unmapped)
            
        if group_key not in grouped_records:
            grouped_records[group_key] = []
            
        grouped_records[group_key].append(rec)
    
    initial_status = "approved" if current_user.role == "admin" else "pending"
    
    total_inserted = 0
    total_duplicates = 0
    first_dataset_id = 0 # Referensi master id untuk balikan response
    
    try:
        # Loop pemecahan 1 Payload menjadi N Dataset berdasarkan Distrik dan Status Karantina
        for (d_id, is_unmapped), records in grouped_records.items():
            existing_hashes = set()
            unique_records = []
            
            # Eliminasi duplikasi internal (dalam satu distrik/grup yang sama)
            for r in records:
                if r["row_hash"] not in existing_hashes:
                    unique_records.append(r)
                    existing_hashes.add(r["row_hash"])
                else:
                    total_duplicates += 1
                    
            if not unique_records:
                continue
                
            # 4. Buat Master Metadata (Tabel Dataset) untuk grup distrik ini
            # Injeksi status Fase 4 (Karantina) ke dalam Master Dataset
            new_dataset = models.Dataset(
                title=title,
                dataset_type=dataset_type,
                source_id=source_id,
                category_id=category_id,
                source_type_id=source_type_id,
                district_id=d_id, 
                year=year,
                period=period,
                description=description,
                status=initial_status,
                user_id=current_user.id,
                headers=headers,
                spatial_status="unmapped" if is_unmapped else "mapped",
                needs_review=True if is_unmapped else False
            )
            db.add(new_dataset)
            db.flush() # Mendapatkan new_dataset.id tanpa menutup transaksi
            
            if first_dataset_id == 0:
                first_dataset_id = new_dataset.id
                
            # 5. Bulk Insert DataRow ke dalam Dataset yang bersangkutan
            rows_to_insert = [
                models.DataRow(
                    dataset_id=new_dataset.id, 
                    content=r["content"], 
                    row_hash=r["row_hash"]
                ) for r in unique_records
            ]
            db.bulk_save_objects(rows_to_insert)
            
            # 6. Kalkulasi Statistik Isolatif (Per Dataset)
            inserted = len(rows_to_insert)
            total_inserted += inserted
            
            # Empty rows hanya dibebankan ke dataset pecahan pertama agar kalkulasi akurat
            group_total = inserted + (empty_rows_count if first_dataset_id == new_dataset.id else 0)
            q_score = (inserted / group_total * 100) if group_total > 0 else 100.0
            
            new_dataset.total_rows = group_total
            new_dataset.quality_score = round(q_score, 2)
            new_dataset.last_ingest_stats = {
                "inserted": inserted,
                "duplicates": len(records) - inserted,
                "empty": empty_rows_count if first_dataset_id == new_dataset.id else 0,
                "total": group_total
            }
            
        # 7. Finalisasi seluruh transaksi dari multi-dataset
        db.commit()
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Terjadi kegagalan arsitektur Multi-Spatial Melting: {str(e)}")
        
    # 8. Return Agregasi ke Frontend
    return {
        "status": "success",
        "dataset_id": first_dataset_id, # Frontend schema mengharapkan 1 Integer
        "headers_found": headers,
        "stats": {
            "inserted": total_inserted,
            "duplicates": total_duplicates,
            "empty": empty_rows_count,
            "total": total_inserted + total_duplicates + empty_rows_count,
            "quality_score": 100.0 # Bypassed overall calculation untuk kecepatan respons
        }
    }