# app/services/spatial_service.py
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case, cast, Float
from app.models.models import District, Dataset, Category, DistrictProfile, SpatialCache, DataRow
from typing import Dict, Any, List

class SpatialService:
    """
    Pure Fabrication Service yang didedikasikan untuk kalkulasi dan agregasi
    data spasial GIS tanpa mengotori domain logic dari dataset maupun core CRUD.
    """

    @staticmethod
    def update_district_profile(db: Session, district_id: int, payload: dict) -> DistrictProfile:
        """
        [Fase 1] Engine Upsert (Update/Insert) untuk Manajemen Profil Wilayah.
        Jika relasi profil untuk distrik ini belum ada, buat baru.
        Jika sudah ada, timpa dengan data payload dari form Admin.
        Mendukung pemrosesan data list foto wilayah (images) secara dinamis [1].
        """
        district = db.query(District).filter(District.id == district_id).first()
        if not district:
            raise ValueError(f"Distrik dengan ID {district_id} tidak ditemukan.")

        profile = db.query(DistrictProfile).filter(DistrictProfile.district_id == district_id).first()

        if not profile:
            profile = DistrictProfile(
                district_id=district_id,
                luas_wilayah=payload.get("luas_wilayah"),
                jumlah_penduduk=payload.get("jumlah_penduduk"),
                deskripsi=payload.get("deskripsi"),
                batas_wilayah=payload.get("batas_wilayah"),
                images=payload.get("images")  # [1] Menyimpan array URL foto wilayah baru
            )
            db.add(profile)
        else:
            if "luas_wilayah" in payload:
                profile.luas_wilayah = payload["luas_wilayah"]
            if "jumlah_penduduk" in payload:
                profile.jumlah_penduduk = payload["jumlah_penduduk"]
            if "deskripsi" in payload:
                profile.deskripsi = payload["deskripsi"]
            if "batas_wilayah" in payload:
                profile.batas_wilayah = payload["batas_wilayah"]
            if "images" in payload:
                profile.images = payload["images"]  # [1] Memperbarui array URL foto wilayah

        db.commit()
        db.refresh(profile)
        return profile

    @staticmethod
    def get_district_stats(db: Session, category_id: int = None, year: int = None) -> List[Dict[str, Any]]:
        """
        Melakukan komputasi agregasi total dataset per distrik.
        Menggunakan OUTER JOIN agar distrik dengan 0 dataset tetap ter-render di peta.
        """
        dataset_filters = [Dataset.status == 'approved']
        
        if category_id is not None:
            dataset_filters.append(Dataset.category_id == category_id)
        if year is not None:
            dataset_filters.append(Dataset.year == year)
            
        aggregation_expr = func.count(
            case(
                (and_(*dataset_filters), Dataset.id), 
                else_=None
            )
        ).label("total_data")

        query_results = (
            db.query(
                District.name.label("district_name"),
                aggregation_expr
            )
            .outerjoin(Dataset, District.id == Dataset.district_id)
            .group_by(District.name)
            .all()
        )

        formatted_response = [
            {
                "district_name": row.district_name,
                "total_dataset": row.total_data or 0
            }
            for row in query_results
        ]

        return formatted_response

    @staticmethod
    def get_detailed_district_stats(db: Session, category_id: int = None) -> Dict[str, Any]:
        """
        Endpoint ekspansi spasial untuk Tooltip Interaktif di peta.
        """
        filters = [Dataset.status == 'approved']
        if category_id is not None:
            filters.append(Dataset.category_id == category_id)

        join_condition = and_(District.id == Dataset.district_id, *filters)

        query_results = (
            db.query(
                District.name.label("district_name"),
                func.count(Dataset.id).label("total_datasets"),
                func.sum(Dataset.total_rows).label("total_rows"),
                func.avg(Dataset.quality_score).label("avg_quality")
            )
            .outerjoin(Dataset, join_condition)
            .group_by(District.name)
            .all()
        )

        formatted_response = {}
        for row in query_results:
            formatted_response[row.district_name] = {
                "total_datasets": row.total_datasets or 0,
                "total_rows": row.total_rows or 0,
                "avg_quality": round(row.avg_quality or 0.0, 2)
            }
            
        return formatted_response

    @staticmethod
    def get_district_drilldown_stats(db: Session, district_id: int) -> Dict[str, Any]:
        """
        Engine untuk Pop-up Peta: Menarik Narasi Statis (Profile) dan 
        Agregasi Kepadatan per Kategori (Dinamis).
        """
        district = db.query(District).filter(District.id == district_id).first()
        if not district:
            return None

        profile_data = {
            "luas_wilayah": None,
            "jumlah_penduduk": None,
            "deskripsi": "Data profil wilayah belum diatur oleh administrator.",
            "batas_wilayah": None,
            "images": [] # Pastikan mengembalikan array kosong jika belum ada gambar
        }
        
        if district.profile:
            profile_data = {
                "luas_wilayah": district.profile.luas_wilayah,
                "jumlah_penduduk": district.profile.jumlah_penduduk,
                "deskripsi": district.profile.deskripsi,
                "batas_wilayah": district.profile.batas_wilayah,
                "images": district.profile.images or []
            }

        category_stats = (
            db.query(
                Category.id.label("category_id"),
                Category.name.label("name"),
                func.count(Dataset.id).label("total")
            )
            .join(Dataset, and_(
                Dataset.category_id == Category.id, 
                Dataset.district_id == district_id,
                Dataset.status == 'approved'
            ))
            .group_by(Category.id, Category.name)
            .all()
        )

        categories_data = [
            {
                "category_id": row.category_id,
                "name": row.name,
                "total": row.total
            }
            for row in category_stats if row.total > 0
        ]

        return {
            "district_id": district.id,
            "district_name": district.name,
            "profile": profile_data,
            "categories": categories_data
        }

    # ============================================================================
    # [REFACTOR] FASE 3: CHOROPLETH ENGINE MENGGUNAKAN REDIS/DB CACHING
    # ============================================================================
    
    @staticmethod
    def get_indicator_data(db: Session, indicator_key: str) -> Dict[str, float]:
        """
        [PROTECTED VARIATIONS] Membaca data aggregasi dari tabel Cache, 
        BUKAN melakukan parsing JSON secara langsung (O(1) Access Time).
        Sangat krusial untuk performa Choropleth di WebGIS Publik.
        """
        cached_results = (
            db.query(SpatialCache, District.name.label("district_name"))
            .join(District, District.id == SpatialCache.district_id)
            .filter(SpatialCache.indicator_key == indicator_key)
            .all()
        )

        formatted_data = {}
        for row, district_name in cached_results:
            clean_key = district_name.lower().replace(" ", "")
            formatted_data[clean_key] = round(row.value, 2) if row.value else 0

        return formatted_data

    @staticmethod
    def calculate_and_cache_aggregation(db: Session, indicator_key: str):
        """
        [BACKGROUND TASK ENGINE] Menghitung agregasi rata-rata nilai dari kolom JSON 
        di tabel DataRow, kemudian menyimpannya/menimpanya ke tabel SpatialCache.
        Fungsi ini harus dipicu (Triggered) oleh Event (contoh: Saat Dataset di-Approve Admin).
        """
        print(f"[Engine] Memulai kalkulasi agregasi spasial untuk indikator: {indicator_key}...")
        
        # 1. Eksekusi Heavy Query (Parsing JSONB ke Float)
        query = (
            db.query(
                District.id.label("district_id"),
                func.avg(
                    cast(
                        DataRow.content[indicator_key].astext,
                        Float
                    )
                ).label("average_value")
            )
            .join(Dataset, Dataset.id == DataRow.dataset_id)
            .join(District, District.id == Dataset.district_id)
            .filter(Dataset.status == "approved")
            .filter(DataRow.content[indicator_key].astext.isnot(None))
            .group_by(District.id)
        )

        results = query.all()

        # 2. Hapus Cache Lama untuk Indikator ini (Clear & Rebuild)
        db.query(SpatialCache).filter(SpatialCache.indicator_key == indicator_key).delete()
        db.commit()

        # 3. Simpan Hasil Perhitungan ke Tabel Cache
        caches_to_insert = []
        for row in results:
            if row.average_value is not None:
                new_cache = SpatialCache(
                    indicator_key=indicator_key,
                    district_id=row.district_id,
                    value=row.average_value
                )
                caches_to_insert.append(new_cache)
                
        if caches_to_insert:
            db.bulk_save_objects(caches_to_insert)
            db.commit()
            
        print(f"[Engine] Kalkulasi selesai. {len(caches_to_insert)} baris cache disimpan.")