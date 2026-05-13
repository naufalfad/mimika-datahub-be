from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case
from app.models.models import District, Dataset, Category, DistrictProfile
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
        """
        # 1. Validasi eksistensi Master District
        district = db.query(District).filter(District.id == district_id).first()
        if not district:
            raise ValueError(f"Distrik dengan ID {district_id} tidak ditemukan.")

        # 2. Ambil profil eksisting
        profile = db.query(DistrictProfile).filter(DistrictProfile.district_id == district_id).first()

        # 3. Logika Upsert
        if not profile:
            # Insert Baru
            profile = DistrictProfile(
                district_id=district_id,
                luas_wilayah=payload.get("luas_wilayah"),
                jumlah_penduduk=payload.get("jumlah_penduduk"),
                deskripsi=payload.get("deskripsi"),
                batas_wilayah=payload.get("batas_wilayah")
            )
            db.add(profile)
        else:
            # Update Eksisting
            if "luas_wilayah" in payload:
                profile.luas_wilayah = payload["luas_wilayah"]
            if "jumlah_penduduk" in payload:
                profile.jumlah_penduduk = payload["jumlah_penduduk"]
            if "deskripsi" in payload:
                profile.deskripsi = payload["deskripsi"]
            if "batas_wilayah" in payload:
                profile.batas_wilayah = payload["batas_wilayah"]

        # 4. Finalisasi Transaksi
        db.commit()
        db.refresh(profile)
        return profile

    @staticmethod
    def get_district_stats(db: Session, category_id: int = None, year: int = None) -> List[Dict[str, Any]]:
        """
        Melakukan komputasi agregasi total dataset per distrik.
        
        Logika Kritis:
        Kita menggunakan OUTER JOIN dan eksekusi filter di dalam argumen COUNT (case expression).
        Jika kita menggunakan `.filter(Dataset.category_id == X)` di level query utama, 
        Outer Join akan berubah menjadi Inner Join secara otomatis di level SQL, 
        sehingga distrik dengan 0 dataset akan hilang dari Payload Response.
        """
        
        # 1. PERBAIKAN: WAJIB filter status approved agar data hantu tidak muncul di peta
        dataset_filters = [Dataset.status == 'approved']
        
        if category_id is not None:
            dataset_filters.append(Dataset.category_id == category_id)
        if year is not None:
            dataset_filters.append(Dataset.year == year)
            
        # 2. PERBAIKAN SYNTAX SQLALCHEMY 2.0: 
        # Tanpa list [], langsung passing tuple posisional (condition, value)
        aggregation_expr = func.count(
            case(
                (and_(*dataset_filters), Dataset.id), 
                else_=None
            )
        ).label("total_data")

        # 3. Eksekusi ORM Query menggunakan Left Outer Join
        query_results = (
            db.query(
                District.name.label("district_name"),
                aggregation_expr
            )
            .outerjoin(Dataset, District.id == Dataset.district_id)
            .group_by(District.name)
            .all()
        )

        # 4. Restrukturisasi hasil ke format Array of Objects
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
        [Opsional/Ekspansi] Metode tambahan untuk menampilkan statistik multivariabel
        Misal: Mengirimkan total baris (rows) atau rata-rata skor kualitas per distrik.
        """
        # PERBAIKAN: Cegah perhitungan data pending
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
        # 1. Ambil Master Data & Profil Statis
        district = db.query(District).filter(District.id == district_id).first()
        if not district:
            return None

        # Fallback profile jika Bappeda belum mengisi data statisnya
        profile_data = {
            "luas_wilayah": None,
            "jumlah_penduduk": None,
            "deskripsi": "Data profil wilayah belum diatur oleh administrator.",
            "batas_wilayah": None
        }
        
        if district.profile:
            profile_data = {
                "luas_wilayah": district.profile.luas_wilayah,
                "jumlah_penduduk": district.profile.jumlah_penduduk,
                "deskripsi": district.profile.deskripsi,
                "batas_wilayah": district.profile.batas_wilayah
            }

        # 2. Agregasi Total Dataset per Kategori secara on-the-fly
        # PERBAIKAN: Tambahkan Dataset.status == 'approved' ke kondisi Join
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
            for row in category_stats if row.total > 0 # Hanya tampilkan kategori yang ada datanya
        ]

        # 3. Strukturisasi Response O(1)
        return {
            "district_id": district.id,
            "district_name": district.name,
            "profile": profile_data,
            "categories": categories_data
        }