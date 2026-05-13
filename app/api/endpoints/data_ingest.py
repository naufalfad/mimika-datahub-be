from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
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
    district_id: Optional[int] = Form(None), # Fallback jika ini file level kabupaten murni
    file: UploadFile = File(...),
    image: UploadFile = File(...), # Upload Cover Image dari Main
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # 1. Validasi Kategori
    category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=400, detail="Kategori tidak ditemukan")

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

    # 3. Baca Isi File Dataset (Excel/CSV) & Jalankan Cleaning Engine
    contents = await file.read()
    
    try:
        # PERBAIKAN: Menyertakan file.filename agar engine bisa mendeteksi ekstensi .xls/.xlsx/.csv
        clean_result = CleaningEngine.clean_and_align(
            contents,
            filename=file.filename
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Ekstraksi Hasil Cleaning (Struktur dari Main Branch)
    headers = clean_result["headers"]
    cleaned_records = clean_result["records"]
    empty_rows_count = clean_result["empty_rows"]
    empty_cells_count = clean_result["empty_cells"]
    structure_type = clean_result.get("structure_type", "structured")

    # ==========================================
    # 4. INTERVENSI GIS: GROUPING & ROW MELTING
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
                # Kolom wilayah terdeteksi, tapi namanya tidak valid/hancur. Masukkan ke zona karantina
                is_unmapped = True
                target_district_id = None
                
        group_key = (target_district_id, is_unmapped)
            
        if group_key not in grouped_records:
            grouped_records[group_key] = []
            
        grouped_records[group_key].append(rec)
    
    initial_status = "approved" if current_user.role == "admin" else "pending"
    
    # Variabel Kalkulasi Agregat Keseluruhan (Untuk Return Response)
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
                
            # 5. Buat Master Metadata (Tabel Dataset) untuk grup distrik ini
            # Injeksi status Fase 4 (Karantina) dan Foto Cloudinary ke dalam Master Dataset
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
                image_url=photo_url,           # [INJEK GAMBAR CLOUDINARY]
                headers=headers,
                structure_type=structure_type, # [INJEK TIPE STRUKTUR]
                spatial_status="unmapped" if is_unmapped else "mapped",
                needs_review=True if is_unmapped else False
            )
            db.add(new_dataset)
            db.flush() # Mendapatkan new_dataset.id tanpa menutup transaksi
            
            if first_dataset_id == 0:
                first_dataset_id = new_dataset.id
                
            # 6. Bulk Insert DataRow ke dalam Dataset yang bersangkutan
            rows_to_insert = [
                models.DataRow(
                    dataset_id=new_dataset.id, 
                    content=r["content"], 
                    row_hash=r["row_hash"]
                ) for r in unique_records
            ]
            db.bulk_save_objects(rows_to_insert)
            
            # 7. Kalkulasi Statistik Isolatif Presisi (Per Dataset - Standar Main Branch)
            inserted = len(rows_to_insert)
            total_inserted += inserted
            
            # Perhitungan Quality Score berdasarkan jumlah sel kosong
            if structure_type == "semi_structured":
                total_potential_cells = len(records) * 3
            else:
                total_potential_cells = len(records) * len(headers)
            
            # Empty cell dihitung proporsional per grup (estimasi kasar)
            group_empty_cells = (len(records) / len(cleaned_records)) * empty_cells_count
            
            if total_potential_cells > 0:
                filled_cells = total_potential_cells - group_empty_cells
                q_score = (filled_cells / total_potential_cells) * 100
            else:
                q_score = 100.0
            
            # Empty rows hanya dibebankan ke dataset pecahan pertama agar agregasi total akurat
            group_empty_rows = empty_rows_count if first_dataset_id == new_dataset.id else 0
            group_total_rows = inserted + (len(records) - inserted) + group_empty_rows
            
            new_dataset.total_rows = group_total_rows
            new_dataset.quality_score = round(q_score, 2)
            new_dataset.last_ingest_stats = {
                "inserted": inserted,
                "duplicates": len(records) - inserted,
                "empty_rows": group_empty_rows,
                "empty_cells": round(group_empty_cells),
                "total_rows": group_total_rows,
                "fill_rate": f"{round(q_score, 2)}%" 
            }
            
        # 8. Finalisasi seluruh transaksi dari multi-dataset
        db.commit()
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Terjadi kegagalan arsitektur Multi-Spatial Melting: {str(e)}")
        
    # 9. Return Agregasi ke Frontend
    # Kalkulasi skor kualitas rata-rata total
    total_potential = len(cleaned_records) * (3 if structure_type == "semi_structured" else len(headers))
    overall_q_score = ((total_potential - empty_cells_count) / total_potential * 100) if total_potential > 0 else 100.0

    return {
        "status": "success",
        "dataset_id": first_dataset_id, # Frontend schema mengharapkan 1 Integer ID
        "headers_found": headers,
        "stats": {
            "inserted": total_inserted,
            "duplicates": total_duplicates,
            "empty_rows": empty_rows_count,
            "empty_cells": empty_cells_count,
            "total": total_inserted + total_duplicates + empty_rows_count,
            "quality_score": round(overall_q_score, 2)
        }
    }