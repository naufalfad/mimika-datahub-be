from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import json
import hashlib
from datetime import datetime

import json
import hashlib
from datetime import datetime

from app.db.session import get_db
from app.models import models
from app.schemas import schemas
from app.services.cleaning_engine import CleaningEngine
from app.api.deps import get_current_user
from app.core.cloudinary_config import upload_image_to_cloudinary

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
    district_id: Optional[int] = Form(None),
    district_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
    image: UploadFile = File(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # --- 1. INISIALISASI VARIABEL AWAL (Agar tidak UnboundLocalError) ---
    headers = []
    total_inserted = 0
    total_duplicates = 0
    empty_rows_count = 0
    empty_cells_count = 0
    overall_q_score = 0.0
    first_dataset_id = 0
    structure_type = "tabular" # default

    # 2. Validasi Kategori
    # --- 1. INISIALISASI VARIABEL AWAL (Agar tidak UnboundLocalError) ---
    headers = []
    total_inserted = 0
    total_duplicates = 0
    empty_rows_count = 0
    empty_cells_count = 0
    overall_q_score = 0.0
    first_dataset_id = 0
    structure_type = "tabular" # default

    # 2. Validasi Kategori
    category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=400, detail="Kategori tidak ditemukan")

    # 3. Upload Gambar Cover ke Cloudinary
    # 3. Upload Gambar Cover ke Cloudinary
    try:
        image_bytes = await image.read()
        photo_url, photo_public_id = upload_image_to_cloudinary(
            image_bytes, 
            folder_name="mimika_datahub/user_uploads"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal upload gambar: {str(e)}")

    initial_status = "approved" if current_user.role == "admin" else "pending"
    filename = file.filename.lower()
    is_tabular = filename.endswith(('.xlsx', '.xls', '.csv'))
    is_document = filename.endswith(('.pdf', '.doc', '.docx'))

    if not is_tabular and not is_document:
        raise HTTPException(status_code=400, detail="Format file tidak didukung.")

    initial_status = "approved" if current_user.role == "admin" else "pending"
    filename = file.filename.lower()
    is_tabular = filename.endswith(('.xlsx', '.xls', '.csv'))
    is_document = filename.endswith(('.pdf', '.doc', '.docx'))

    if not is_tabular and not is_document:
        raise HTTPException(status_code=400, detail="Format file tidak didukung.")

    contents = await file.read()

    # --- 4. LOGIKA PERCABANGAN FILE ---

    if is_tabular:
        try:
            # A. Jalankan Cleaning Engine
            clean_result = CleaningEngine.clean_and_align(contents, filename=file.filename)
            
            headers = clean_result["headers"]
            cleaned_records = clean_result["records"]
            empty_rows_count = clean_result["empty_rows"]
            empty_cells_count = clean_result["empty_cells"]
            structure_type = clean_result.get("structure_type", "structured")

    # --- 4. LOGIKA PERCABANGAN FILE ---

    if is_tabular:
        try:
            # A. Jalankan Cleaning Engine
            clean_result = CleaningEngine.clean_and_align(contents, filename=file.filename)
            
            headers = clean_result["headers"]
            cleaned_records = clean_result["records"]
            empty_rows_count = clean_result["empty_rows"]
            empty_cells_count = clean_result["empty_cells"]
            structure_type = clean_result.get("structure_type", "structured")

            # B. INTERVENSI GIS: GROUPING & ROW MELTING
            district_map = {d.name.lower().strip(): d.id for d in db.query(models.District).all()}
            grouped_records = {}

            for rec in cleaned_records:
                content = rec["content"]
                
                # 1. Coba ambil mapping dari cleaning engine jika ada
                mapped_name = content.pop("_spatial_mapping", None)
                
                # 2. LOGIKA TAMBAHAN: Jika _spatial_mapping kosong, cari di dalam cell content
                target_district_id = district_id # Default ke input form jika ada
                
                if mapped_name:
                    # Jika engine menemukan kolom spesifik (misal kolom 'district')
                    target_district_id = district_map.get(mapped_name.lower().strip(), target_district_id)
                else:
                    # Jika tidak ada kolom spesifik, scan SEMUA isi cell di baris ini
                    for cell_value in content.values():
                        if isinstance(cell_value, str):
                            val_clean = cell_value.lower().strip()
                            if val_clean in district_map:
                                target_district_id = district_map[val_clean]
                                break

                is_unmapped = (target_district_id is None)
                group_key = (target_district_id, is_unmapped)
                if group_key not in grouped_records:
                    grouped_records[group_key] = []
                
                # Simpan record ke grupnya
                rec["content"] = content 
                grouped_records[group_key].append(rec)

            # C. Loop Pemecahan Dataset (Multi-Spatial)
            for (d_id, is_unmapped), records in grouped_records.items():
                existing_hashes = set()
                unique_records = []
                
                for r in records:
                    if r["row_hash"] not in existing_hashes:
                        unique_records.append(r)
                        existing_hashes.add(r["row_hash"])
                    else:
                        total_duplicates += 1
                        
                if not unique_records:
                    continue
                    
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
                    image_url=photo_url,
                    headers=headers,
                    structure_type=structure_type,
                    spatial_status="unmapped" if is_unmapped else "mapped",
                    needs_review=True if is_unmapped else False
                )
                db.add(new_dataset)
                db.flush() 
                
                if first_dataset_id == 0:
                    first_dataset_id = new_dataset.id
                    
                rows_to_insert = [
                    models.DataRow(
                        dataset_id=new_dataset.id, 
                        content=r["content"], 
                        row_hash=r["row_hash"]
                    ) for r in unique_records
                ]
                db.bulk_save_objects(rows_to_insert)
                
                # Statistik Per Dataset
                inserted = len(rows_to_insert)
                total_inserted += inserted
                
                if structure_type == "semi_structured":
                    total_potential_cells = len(records) * 3
                else:
                    total_potential_cells = len(records) * len(headers)
                
                group_empty_cells = (len(records) / len(cleaned_records)) * empty_cells_count
                
                if total_potential_cells > 0:
                    filled_cells = total_potential_cells - group_empty_cells
                    q_score_local = (filled_cells / total_potential_cells) * 100
                else:
                    q_score_local = 100.0
                
                group_empty_rows = empty_rows_count if first_dataset_id == new_dataset.id else 0
                group_total_rows = inserted + (len(records) - inserted) + group_empty_rows
                
                new_dataset.total_rows = group_total_rows
                new_dataset.quality_score = round(q_score_local, 2)
                new_dataset.last_ingest_stats = {
                    "inserted": inserted,
                    "duplicates": len(records) - inserted,
                    "empty_rows": group_empty_rows,
                    "empty_cells": round(group_empty_cells),
                    "total_rows": group_total_rows,
                    "fill_rate": f"{round(q_score_local, 2)}%" 
                }
            
            db.commit()

            # Kalkulasi skor kualitas rata-rata total untuk return
            total_potential = len(cleaned_records) * (3 if structure_type == "semi_structured" else len(headers))
            overall_q_score = ((total_potential - empty_cells_count) / total_potential * 100) if total_potential > 0 else 100.0
            db.commit()

            # Kalkulasi skor kualitas rata-rata total untuk return
            total_potential = len(cleaned_records) * (3 if structure_type == "semi_structured" else len(headers))
            overall_q_score = ((total_potential - empty_cells_count) / total_potential * 100) if total_potential > 0 else 100.0

        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Gagal memproses data tabular: {str(e)}")

    elif is_document:
        try:
            # Proses Upload Dokumen (PDF/Word) ke Cloudinary
            file_url, file_public_id = upload_image_to_cloudinary(
                contents, 
                folder_name="mimika_datahub/documents",
                resource_type="raw"
            )
            
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
                file_url=file_url, # Simpan URL dokumen
                headers=["Dokumen"],
                structure_type="document",
                total_rows=1,
                quality_score=100.0
            )
            db.add(new_dataset)
            db.commit()
            db.refresh(new_dataset)

            # Set variabel untuk return response
            first_dataset_id = new_dataset.id
            headers = ["Dokumen"]
            total_inserted = 1
            overall_q_score = 100.0
            structure_type = "document"

        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Gagal upload dokumen: {str(e)}")

    # 5. Return Agregasi ke Frontend
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Gagal memproses data tabular: {str(e)}")

    elif is_document:
        try:
            # Proses Upload Dokumen (PDF/Word) ke Cloudinary
            file_url, file_public_id = upload_image_to_cloudinary(
                contents, 
                folder_name="mimika_datahub/documents",
                resource_type="raw"
            )
            
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
                file_url=file_url, # Simpan URL dokumen
                headers=["Dokumen"],
                structure_type="document",
                total_rows=1,
                quality_score=100.0
            )
            db.add(new_dataset)
            db.commit()
            db.refresh(new_dataset)

            # Set variabel untuk return response
            first_dataset_id = new_dataset.id
            headers = ["Dokumen"]
            total_inserted = 1
            overall_q_score = 100.0
            structure_type = "document"

        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Gagal upload dokumen: {str(e)}")

    # 5. Return Agregasi ke Frontend
    return {
        "status": "success",
        "dataset_id": first_dataset_id,
        "dataset_id": first_dataset_id,
        "headers_found": headers,
        "message": f"File {filename} berhasil diproses sebagai {structure_type}",
        "message": f"File {filename} berhasil diproses sebagai {structure_type}",
        "stats": {
            "inserted": total_inserted,
            "duplicates": total_duplicates,
            "empty_rows": empty_rows_count,
            "empty_cells": empty_cells_count,
            "total": total_inserted + total_duplicates + empty_rows_count,
            "quality_score": round(overall_q_score, 2)
        }
    }