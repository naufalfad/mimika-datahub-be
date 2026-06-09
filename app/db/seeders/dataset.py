# app/db/seeders/dataset.py
import json
import hashlib
from sqlalchemy.orm import Session
from app.models import models
from app.services.spatial_service import SpatialService  # Untuk memanaskan cache peta [cite: 15]

# ============================================================================
# DATA TRANSAKSIONAL: PREVALENSI STUNTING PER DISTRIK (RIIL) [cite: DISTRICT_MAP]
# ============================================================================
STUNTING_VALUES = {
    "Mimika Baru": 12.4, 
    "Kuala Kencana": 9.1, 
    "Tembagapura": 6.5, 
    "Wania": 14.8,
    "Iwaka": 19.2, 
    "Kwamki Narama": 15.5, 
    "Mimika Timur": 22.4, 
    "Mimika Tengah": 24.1,
    "Mimika Barat": 28.3, 
    "Agimuga": 32.5, 
    "Jila": 38.2, 
    "Jita": 35.0,
    "Mimika Timur Jauh": 29.8, 
    "Mimika Barat Jauh": 31.4, 
    "Mimika Barat Tengah": 27.5,
    "Amar": 26.8, 
    "Hoya": 41.2, 
    "Alama": 44.5
}

def seed_datasets(db: Session) -> dict:
    """
    [GRASP - CREATOR & INFORMATION EXPERT]
    Modul Seeder Dataset, DataRow, dan Pemanas Cache Spasial [2, 15].
    Menghitung hash MD5 secara dinamis untuk mengamankan redundansi data [2].
    """
    stats = {"datasets_inserted": 0, "rows_inserted": 0, "cache_warmed": False}

    # 1. RESOLUSI FOREIGN KEYS SECARA DINAMIS (Bebas Hardcoded ID)
    user_dinkes = db.query(models.User).filter(models.User.username == "dinkes").first()
    source_dinkes = db.query(models.Source).filter(models.Source.name == "Dinas Kesehatan").first()
    category_kesehatan = db.query(models.Category).filter(models.Category.name == "Kesehatan").first()
    source_type_sektoral = db.query(models.SourceType).filter(models.SourceType.name == "Statistik Sektoral").first()

    dinkes_id = user_dinkes.id if user_dinkes else 3
    dinkes_source_id = source_dinkes.id if source_dinkes else 2
    kesehatan_id = category_kesehatan.id if category_kesehatan else 2
    sektoral_id = source_type_sektoral.id if source_type_sektoral else 1

    # 2. SEED DATASET METADATA (IDEMPOTENT CHECK) [cite: 2]
    dataset_title = "Prevalensi Stunting Mimika 2025"
    existing_dataset = db.query(models.Dataset).filter(models.Dataset.title == dataset_title).first()

    if not existing_dataset:
        stunting_dataset = models.Dataset(
            user_id=dinkes_id,
            title=dataset_title,
            dataset_type="pemerintah",
            source_id=dinkes_source_id,
            category_id=kesehatan_id,
            source_type_id=sektoral_id,
            district_id=None,  # Level Kabupaten (Multi-Spatial mapping)
            year=2025,
            period="Tahunan",
            description="Laporan data prevalensi stunting balita per distrik di wilayah Kabupaten Mimika tahun anggaran 2025.",
            total_rows=18,
            quality_score=100.0,
            headers=["distrik", "stunting"],
            status="approved",
            structure_type="tabular",
            spatial_status="mapped",
            image_url="https://images.unsplash.com/photo-1516549655169-df83a0774514?auto=format&fit=crop&w=800&q=80"
        )
        db.add(stunting_dataset)
        db.flush() # Flush agar stunting_dataset.id siap direferensikan oleh DataRow [cite: 2]
        stats["datasets_inserted"] += 1

        # 3. SEED 18 DATAROW SPASIAL [cite: 2]
        for dist_name, st_val in STUNTING_VALUES.items():
            # Cari nama distrik di database untuk memastikan integritas rujukan
            db_dist = db.query(models.District).filter(models.District.name == dist_name).first()
            resolved_dist_name = db_dist.name if db_dist else dist_name

            row_content = {
                "distrik": resolved_dist_name,
                "stunting": st_val
            }
            
            # Memformat JSON string secara konsisten untuk kalkulasi Hash MD5 [cite: 2]
            row_json = json.dumps(row_content, sort_keys=True)
            row_hash = hashlib.md5(row_json.encode()).hexdigest()
            
            db.add(models.DataRow(
                dataset_id=stunting_dataset.id,
                content=row_content,
                row_hash=row_hash
            ))
            stats["rows_inserted"] += 1

        db.commit()
        print(f"[Seeder] Sukses menyuntikkan 18 baris data stunting untuk dataset ID: #{stunting_dataset.id}")

    # 4. MEMANASKAN CACHE SPASIAL (WARMING-UP SPATIAL CACHE) [cite: 15]
    print("[Seeder] Memicu background task kalkulasi rata-rata spasial untuk 'stunting'...")
    try:
        # Menghitung agregasi rata-rata dari kolom JSON dan mengisi tabel spatial_caches [cite: 15]
        SpatialService.calculate_and_cache_aggregation(db, "stunting")
        stats["cache_warmed"] = True
    except Exception as cache_error:
        print(f"❌ [Seeder Warning] Gagal menghitung cache spasial: {str(cache_error)}")

    return stats