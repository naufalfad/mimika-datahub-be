# app/db/seeders/aset.py
from sqlalchemy.orm import Session
from app.models import models

# ============================================================================
# DATA MASTER: KATEGORI ASET GEOTAGGING [cite: ASSET_TAXONOMY_CONFIG]
# ============================================================================
ASSET_CATEGORIES_DATA = [
    {"id": 1, "name": "Rumah Sakit", "icon_url": "/icons/markers/hospital.svg", "color": "#EF4444"},
    {"id": 2, "name": "Puskesmas", "icon_url": "/icons/markers/clinic.svg", "color": "#F97316"},
    {"id": 3, "name": "Puskesmas Pembantu", "icon_url": "/icons/markers/aid.svg", "color": "#EAB308"},
    {"id": 4, "name": "Gedung Sekolah", "icon_url": "/icons/markers/school.svg", "color": "#10B981"},
    {"id": 5, "name": "Infrastruktur Jembatan", "icon_url": "/icons/markers/bridge.svg", "color": "#64748B"}
]

def seed_assets(db: Session) -> dict:
    """
    [GRASP - INFORMATION EXPERT & CREATOR]
    Modul Seeder Aset Fisik (Geotagging).
    Menarik rujukan foreign keys secara dinamis untuk mengeliminasi hardcoding rujukan data [1, 10].
    """
    stats = {"categories_inserted": 0, "assets_inserted": 0}

    # 1. SEED KATEGORI ASET [cite: ASSET_TAXONOMY_CONFIG]
    for ac in ASSET_CATEGORIES_DATA:
        existing_cat = db.query(models.AssetCategory).filter(models.AssetCategory.id == ac["id"]).first()
        if not existing_cat:
            name_check = db.query(models.AssetCategory).filter(models.AssetCategory.name == ac["name"]).first()
            if not name_check:
                db.add(models.AssetCategory(
                    id=ac["id"],
                    name=ac["name"],
                    icon_url=ac["icon_url"],
                    color=ac["color"]
                ))
                stats["categories_inserted"] += 1
    db.commit() # Commit agar ID kategori terbaca oleh inisialisasi tabel aset di bawahnya

    # 2. RESOLUSI RELASI PENGGUNA (USERS) SECARA DINAMIS [cite: 830]
    user_admin = db.query(models.User).filter(models.User.username == "admin").first()
    user_dinkes = db.query(models.User).filter(models.User.username == "dinkes").first()

    # Fallback aman jika akun belum dimasukkan oleh seeder user
    admin_id = user_admin.id if user_admin else 1
    dinkes_id = user_dinkes.id if user_dinkes else 1

    # 3. RESOLUSI RELASI INSTANSI (OPD) SECARA DINAMIS [cite: ASSET_TAXONOMY_CONFIG]
    source_dinkes = db.query(models.Source).filter(models.Source.name == "Dinas Kesehatan").first()
    source_disdik = db.query(models.Source).filter(models.Source.name == "Dinas Pendidikan").first()
    source_pupr = db.query(models.Source).filter(models.Source.name == "Dinas PUPR").first()

    dinkes_source_id = source_dinkes.id if source_dinkes else 2
    disdik_source_id = source_disdik.id if source_disdik else 3
    pupr_source_id = source_pupr.id if source_pupr else 4

    # 4. RESOLUSI RELASI WILAYAH (DISTRICTS) SECARA DINAMIS [cite: DISTRICT_MAP]
    dist_mimika_baru = db.query(models.District).filter(models.District.name == "Mimika Baru").first()
    dist_wania = db.query(models.District).filter(models.District.name == "Wania").first()

    mimika_baru_id = dist_mimika_baru.id if dist_mimika_baru else 1
    wania_id = dist_wania.id if dist_wania else 4

    # 5. STRUKTUR DATA TITIK ASET FISIK REKAYASA (REAL-COORDINATE MIMIKA) [cite: 10]
    assets_sample = [
        {
            "name": "RSUD Kabupaten Mimika",
            "user_id": dinkes_id, 
            "source_id": dinkes_source_id, 
            "district_id": mimika_baru_id, 
            "category_id": 1, # Rumah Sakit
            "lat": -4.5450, 
            "lng": 136.8900, 
            "description": "Gedung RSUD Utama Kabupaten Mimika, menyajikan pelayanan kesehatan rujukan tingkat pertama, IGD 24 Jam, dan klinik spesialis terpadu.",
            "details": {
                "Kapasitas Bed": "150 Tempat Tidur", 
                "Status Akreditasi": "Paripurna", 
                "Tahun Operasional": "2008",
                "Status Lahan": "Sertifikat Hak Pakai Pemda"
            },
            "images": [
                "https://images.unsplash.com/photo-1587351021355-a479a299d2f9?auto=format&fit=crop&w=800&q=80",
                "https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?auto=format&fit=crop&w=800&q=80"
            ]
        },
        {
            "name": "Puskesmas Timika Baru",
            "user_id": dinkes_id, 
            "source_id": dinkes_source_id, 
            "district_id": mimika_baru_id, 
            "category_id": 2, # Puskesmas
            "lat": -4.5300, 
            "lng": 136.8850, 
            "description": "Puskesmas induk Distrik Mimika Baru, berfokus pada upaya preventif-promotif kependudukan, imunisasi wajib anak, dan KIA.",
            "details": {
                "Status Operasional": "Aktif Penuh", 
                "Layanan Rawat Inap": "Tersedia (Terbatas)", 
                "Rata-rata Pasien/Hari": "85 Pasien"
            },
            "images": [
                "https://images.unsplash.com/photo-1516549655169-df83a0774514?auto=format&fit=crop&w=800&q=80"
            ]
        },
        {
            "name": "SMP Negeri 2 Mimika Baru",
            "user_id": admin_id, 
            "source_id": disdik_source_id, 
            "district_id": mimika_baru_id, 
            "category_id": 4, # Gedung Sekolah
            "lat": -4.5350, 
            "lng": 136.8950, 
            "description": "Fasilitas sarana pendidikan dasar menengah tingkat pertama, di bawah naungan Dinas Pendidikan Kabupaten Mimika.",
            "details": {
                "Jumlah Siswa": "450 Siswa", 
                "Jumlah Guru Aktif": "32 Guru", 
                "Status Bangunan": "Milik Pemda",
                "Jumlah Ruang Kelas": "12 Kelas"
            },
            "images": [
                "https://images.unsplash.com/photo-1580582932707-520aed937b7b?auto=format&fit=crop&w=800&q=80"
            ]
        },
        {
            "name": "Jembatan Poros Sungai Wania",
            "user_id": admin_id, 
            "source_id": pupr_source_id, 
            "district_id": wania_id, 
            "category_id": 5, # Infrastruktur Jembatan
            "lat": -4.5650, 
            "lng": 136.9150, 
            "description": "Infrastruktur penyeberangan vital yang mengintegrasikan jalan poros utama Distrik Wania dengan pusat kota Timika.",
            "details": {
                "Panjang Bentang": "120 Meter", 
                "Tahun Selesai": "2024",
                "Konstruksi Utama": "Rangka Baja Kelas A",
                "Kontraktor Pelaksana": "PT. Papua Karya Abadi"
            },
            "images": [
                "https://images.unsplash.com/photo-1545569341-9eb8b30979d9?auto=format&fit=crop&w=800&q=80"
            ]
        }
    ]

    # 6. SEED PHYSICAL ASSETS (IDEMPOTENT CHECK) [cite: 10]
    for a in assets_sample:
        existing_asset = db.query(models.Asset).filter(models.Asset.name == a["name"]).first()
        if not existing_asset:
            db.add(models.Asset(
                name=a["name"],
                user_id=a["user_id"],
                source_id=a["source_id"],
                district_id=a["district_id"],
                category_id=a["category_id"],
                lat=a["lat"],
                lng=a["lng"],
                description=a["description"],
                details=a["details"],
                image_url=a["images"][0],
                images=a["images"],
                status="approved"  # Otomatis langsung lulus karantina agar langsung tampil di peta publik
            ))
            stats["assets_inserted"] += 1
            
    db.commit()
    return stats