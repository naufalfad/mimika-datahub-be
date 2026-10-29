# clean_and_seed_demo.py
"""
Mimika DataHub - Master Testing Seeder Engine
Menyuntikkan data testing bersih, komprehensif, dan realistis untuk demonstrasi klien Pemkab Mimika.
Mencakup:
1. Akun Master OPD (password seragam: password123)
2. Kategori Aset Fisik & Geotagging Aset (Approved, Pending, Rejected - min 3 per status)
3. Dataset Sektoral (Approved 18 Distrik, Pending Review - min 3 per status)
4. Survei Publik BRIDA (3 Kuesioner terstruktur + respons warga)
5. Pemanasan Cache Spasial (Choropleth Peta Atlas)
"""

import os
import sys
import json
import hashlib
import random
import warnings
from datetime import datetime, timedelta

warnings.filterwarnings("ignore", category=DeprecationWarning)

# Pastikan UTF-8 untuk output console di Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Pastikan direktori backend masuk sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import func, text
from app.db.session import SessionLocal
from app.models import models
from app.core import security

def sync_sequences(db):
    """Sinkronisasi seluruh sequence auto-increment PostgreSQL agar terhindar dari duplicate key error."""
    tables = [
        'districts', 'district_profiles', 'sources', 'categories', 
        'source_type', 'users', 'asset_categories', 'assets', 
        'datasets', 'data_rows', 'surveys', 'survey_responses', 'spatial_caches'
    ]
    for table in tables:
        try:
            max_id = db.execute(text(f"SELECT MAX(id) FROM {table}")).scalar()
            seq_name = f"{table}_id_seq"
            if max_id is not None and max_id > 0:
                db.execute(text(f"SELECT setval('{seq_name}', :val, true)"), {"val": max_id})
            else:
                db.execute(text(f"SELECT setval('{seq_name}', 1, false)"))
            db.commit()
        except Exception:
            db.rollback()

# ============================================================================
# 1. DATA MASTER DISTRIK (18 Distrik Resmi Kabupaten Mimika)
# ============================================================================
DISTRICT_DATA = [
    {"id": 1, "name": "Mimika Baru", "luas": 2216.00, "penduduk": 142519, "batas": "Utara: Kuala Kencana, Selatan: Wania, Timur: Mimika Timur, Barat: Iwaka", "deskripsi": "Distrik Mimika Baru adalah pusat administrasi pemerintahan dan episentrum ekonomi utama Kabupaten Mimika."},
    {"id": 2, "name": "Kuala Kencana", "luas": 860.74, "penduduk": 29104, "batas": "Utara: Tembagapura, Selatan: Mimika Baru, Timur: Kwamki Narama, Barat: Iwaka", "deskripsi": "Kuala Kencana merupakan kota industri modern yang didesain secara asri dengan utilitas bawah tanah dan sistem ramah lingkungan."},
    {"id": 3, "name": "Tembagapura", "luas": 2586.88, "penduduk": 22120, "batas": "Utara: Kab. Puncak, Selatan: Kuala Kencana, Timur: Agimuga, Barat: Jila", "deskripsi": "Distrik dataran tinggi pegunungan Mimika yang menampung area pertambangan utama."},
    {"id": 4, "name": "Wania", "luas": 310.20, "penduduk": 55210, "batas": "Utara: Mimika Baru, Selatan: Laut Arafuru, Timur: Mimika Timur, Barat: Mimika Tengah", "deskripsi": "Wania berkembang pesat sebagai wilayah penyangga kota Timika dengan basis komoditas pertanian dan perdagangan lokal."},
    {"id": 5, "name": "Iwaka", "luas": 785.40, "penduduk": 11450, "batas": "Utara: Tembagapura, Selatan: Mimika Tengah, Timur: Kuala Kencana, Barat: Mimika Barat", "deskripsi": "Iwaka dilalui jalur poros Trans Papua, memiliki potensi perkebunan dan ekowisata alam."},
    {"id": 6, "name": "Kwamki Narama", "luas": 240.50, "penduduk": 14890, "batas": "Utara: Kuala Kencana, Selatan: Mimika Baru, Timur: Mimika Timur, Barat: Wania", "deskripsi": "Kwamki Narama berkembang menjadi pusat permukiman baru dengan fokus pemberdayaan ekonomi komunitas lokal."},
    {"id": 7, "name": "Mimika Timur", "luas": 1520.10, "penduduk": 9540, "batas": "Utara: Mimika Baru, Selatan: Laut Arafuru, Timur: Mimika Timur Jauh, Barat: Wania", "deskripsi": "Berpusat di kawasan pesisir muara sungai dan pelabuhan pendaratan ikan Poumako."},
    {"id": 8, "name": "Mimika Tengah", "luas": 2150.30, "penduduk": 6230, "batas": "Utara: Iwaka, Selatan: Laut Arafuru, Timur: Wania, Barat: Mimika Barat", "deskripsi": "Distrik pesisir dengan ekosistem mangrove dan transportasi perahu motor sungai."},
    {"id": 9, "name": "Mimika Barat", "luas": 2750.00, "penduduk": 4200, "batas": "Utara: Kab. Deiyai, Selatan: Laut Arafuru, Timur: Mimika Tengah, Barat: Mimika Barat Tengah", "deskripsi": "Distrik pesisir barat dengan pusat administrasi bersejarah di Kokonao."},
    {"id": 10, "name": "Agimuga", "luas": 3120.45, "penduduk": 3150, "batas": "Utara: Kab. Puncak, Selatan: Mimika Timur Jauh, Timur: Jita, Barat: Tembagapura", "deskripsi": "Agimuga merupakan dataran rendah pedalaman yang subur dengan komoditas sagu dan kopi alami."},
    {"id": 11, "name": "Jila", "luas": 1820.00, "penduduk": 2800, "batas": "Utara: Kab. Puncak, Selatan: Agimuga, Timur: Alama, Barat: Tembagapura", "deskripsi": "Jila terletak di pegunungan tengah dengan panorama tebing alam lereng pegunungan."},
    {"id": 12, "name": "Jita", "luas": 1350.00, "penduduk": 3400, "batas": "Utara: Agimuga, Selatan: Laut Arafuru, Timur: Kab. Asmat, Barat: Mimika Timur Jauh", "deskripsi": "Distrik perairan sungai timur Mimika yang berbatasan langsung dengan Kabupaten Asmat."},
    {"id": 13, "name": "Mimika Timur Jauh", "luas": 2100.00, "penduduk": 3250, "batas": "Utara: Agimuga, Selatan: Laut Arafuru, Timur: Jita, Barat: Mimika Timur", "deskripsi": "Wilayah pesisir perairan timur dengan kearifan lokal nelayan suku Kamoro dan Sempan."},
    {"id": 14, "name": "Mimika Barat Jauh", "luas": 2850.00, "penduduk": 2100, "batas": "Utara: Kab. Dogiyai, Selatan: Laut Arafuru, Timur: Mimika Barat Tengah, Barat: Kab. Kaimana", "deskripsi": "Distrik terluar bagian barat Mimika yang berbatasan dengan Provinsi Papua Barat."},
    {"id": 15, "name": "Mimika Barat Tengah", "luas": 2300.00, "penduduk": 2550, "batas": "Utara: Kab. Deiyai, Selatan: Laut Arafuru, Timur: Mimika Barat, Barat: Mimika Barat Jauh", "deskripsi": "Wilayah pesisir kaya hasil kepiting bakau dan ikan perairan muara."},
    {"id": 16, "name": "Amar", "luas": 1950.00, "penduduk": 2380, "batas": "Utara: Mimika Barat Tengah, Selatan: Laut Arafuru, Timur: Mimika Barat, Barat: Mimika Barat Jauh", "deskripsi": "Distrik pesisir dengan potensi kelapa rakyat dan konservasi penyu alami."},
    {"id": 17, "name": "Hoya", "luas": 1650.00, "penduduk": 1950, "batas": "Utara: Kab. Puncak, Selatan: Tembagapura, Timur: Jila, Barat: Tembagapura", "deskripsi": "Distrik dataran tinggi terisolir yang mengandalkan jalur penerbangan perintis."},
    {"id": 18, "name": "Alama", "luas": 1780.00, "penduduk": 2150, "batas": "Utara: Kab. Yahukimo, Selatan: Jita, Timur: Kab. Nduga, Barat: Jila", "deskripsi": "Distrik pedalaman pegunungan timur dengan iklim sejuk dan hasil palawija organik."}
]

# ============================================================================
# 2. MASTER OPD (SOURCES)
# ============================================================================
SOURCES_DATA = [
    {"id": 1, "name": "BAPPEDA", "type": "opd"},
    {"id": 2, "name": "Dinas Kesehatan", "type": "opd"},
    {"id": 3, "name": "Dinas Pendidikan", "type": "opd"},
    {"id": 4, "name": "Dinas PUPR", "type": "opd"},
    {"id": 5, "name": "Dinas Sosial", "type": "opd"},
    {"id": 6, "name": "BPS Mimika", "type": "bps"},
    {"id": 7, "name": "BRIDA Mimika", "type": "brida"}
]

# ============================================================================
# 3. KATEGORI DATASET & KATEGORI ASET
# ============================================================================
CATEGORIES_DATA = [
    {"id": 1, "name": "Kependudukan"},
    {"id": 2, "name": "Kesehatan"},
    {"id": 3, "name": "Pendidikan"},
    {"id": 4, "name": "Infrastruktur"},
    {"id": 5, "name": "Ekonomi & Keuangan"},
    {"id": 6, "name": "Sosial & Kemasyarakatan"}
]

ASSET_CATEGORIES_DATA = [
    {"id": 1, "name": "Rumah Sakit", "icon_url": "/icons/markers/hospital.svg", "color": "#EF4444"},
    {"id": 2, "name": "Puskesmas", "icon_url": "/icons/markers/clinic.svg", "color": "#F97316"},
    {"id": 3, "name": "Puskesmas Pembantu", "icon_url": "/icons/markers/aid.svg", "color": "#EAB308"},
    {"id": 4, "name": "Gedung Sekolah", "icon_url": "/icons/markers/school.svg", "color": "#10B981"},
    {"id": 5, "name": "Infrastruktur Jembatan", "icon_url": "/icons/markers/bridge.svg", "color": "#64748B"},
    {"id": 6, "name": "Kantor Pemerintahan", "icon_url": "/icons/markers/office.svg", "color": "#3B82F6"}
]

SOURCE_TYPES_DATA = [
    {"id": 1, "name": "Statistik Sektoral"},
    {"id": 2, "name": "Statistik Dasar"}
]

# ============================================================================
# 4. DATA USERS (PASSWORD SERAGAM: password123)
# ============================================================================
USERS_DATA = [
    {"username": "admin", "email": "admin@mimikakab.go.id", "full_name": "Bappeda Administrator", "role": "admin", "source_id": 1},
    {"username": "user", "email": "operator.dinkes@mimikakab.go.id", "full_name": "Operator Dinas Kesehatan", "role": "user", "source_id": 2},
    {"username": "dinkes", "email": "dinkes@mimikakab.go.id", "full_name": "Koordinator Dinkes Mimika", "role": "user", "source_id": 2},
    {"username": "disdik", "email": "disdik@mimikakab.go.id", "full_name": "Operator Dinas Pendidikan", "role": "user", "source_id": 3},
    {"username": "pupr", "email": "pupr@mimikakab.go.id", "full_name": "Operator Dinas PUPR", "role": "user", "source_id": 4},
    {"username": "dinsos", "email": "dinsos@mimikakab.go.id", "full_name": "Operator Dinas Sosial", "role": "user", "source_id": 5},
    {"username": "brida", "email": "operator.brida@mimikakab.go.id", "full_name": "Operator BRIDA Mimika", "role": "brida", "source_id": 7},
    {"username": "bps", "email": "bps9101@bps.go.id", "full_name": "Statistisi BPS Mimika", "role": "user", "source_id": 6},
    {"username": "test", "email": "testing@mimikakab.go.id", "full_name": "Akun Uji Coba OPD", "role": "user", "source_id": 2}
]

def run_seeder():
    db = SessionLocal()
    print("\n" + "="*70)
    print("🚀 MEMULAI SEEDER MASTER DATA MIMIKA DATAHUB (DEMO READY)")
    print("="*70)

    try:
        # --------------------------------------------------------------------
        # TAHAP 1: PEMBERSIHAN DATA KOTOR/TESTING LAMA
        # --------------------------------------------------------------------
        print("\n[1/6] Membersihkan data lama & dirty mock records...")
        
        # Hapus data transaksional agar relasi bersih
        db.query(models.SpatialCache).delete()
        db.query(models.SurveyResponse).delete()
        db.query(models.Survey).delete()
        db.query(models.DataRow).delete()
        db.query(models.Dataset).delete()
        db.query(models.Asset).delete()
        db.commit()
        sync_sequences(db)
        print("  ✓ Tabel spatial_caches, survey_responses, surveys, data_rows, datasets, assets telah dibersihkan.")

        # --------------------------------------------------------------------
        # TAHAP 2: MASTER WILAYAH & PROFIL 18 DISTRIK
        # --------------------------------------------------------------------
        print("\n[2/6] Memverifikasi 18 Distrik Kabupaten Mimika...")
        district_map = {}
        for d in DISTRICT_DATA:
            existing_d = db.query(models.District).filter(
                (models.District.name == d["name"]) | (func.lower(models.District.name) == d["name"].lower())
            ).first()
            if not existing_d:
                existing_d = models.District(name=d["name"])
                db.add(existing_d)
                db.commit()
                db.refresh(existing_d)
                sync_sequences(db)
            
            district_map[d["name"]] = existing_d.id

            # Profil Distrik
            existing_prof = db.query(models.DistrictProfile).filter(models.DistrictProfile.district_id == existing_d.id).first()
            if not existing_prof:
                prof = models.DistrictProfile(
                    district_id=existing_d.id,
                    luas_wilayah=d["luas"],
                    jumlah_penduduk=d["penduduk"],
                    deskripsi=d["deskripsi"],
                    batas_wilayah=d["batas"],
                    images=[
                        "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=800&q=80",
                        "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?auto=format&fit=crop&w=800&q=80"
                    ]
                )
                db.add(prof)
                db.commit()
                sync_sequences(db)
            else:
                existing_prof.luas_wilayah = d["luas"]
                existing_prof.jumlah_penduduk = d["penduduk"]
                existing_prof.deskripsi = d["deskripsi"]
                existing_prof.batas_wilayah = d["batas"]
        db.commit()
        sync_sequences(db)
        print(f"  ✓ {len(district_map)} Distrik & Profil aktif terkonfigurasi.")

        # --------------------------------------------------------------------
        # TAHAP 3: MASTER SOURCES, CATEGORIES, SOURCE TYPES, USERS
        # --------------------------------------------------------------------
        print("\n[3/6] Memverifikasi Master OPD, Kategori, dan Akun Pengguna...")
        
        # Sources
        source_map = {}
        for s in SOURCES_DATA:
            src = db.query(models.Source).filter(models.Source.name == s["name"]).first()
            if not src:
                src = db.query(models.Source).filter(func.lower(models.Source.name) == s["name"].lower()).first()
                if src:
                    src.name = s["name"]
                    src.type = s["type"]
                    db.commit()
                else:
                    src = models.Source(name=s["name"], type=s["type"])
                    db.add(src)
                    db.commit()
                    db.refresh(src)
                    sync_sequences(db)
            else:
                src.type = s["type"]
                db.commit()
            source_map[s["name"]] = src.id
        
        # Categories
        cat_map = {}
        for c in CATEGORIES_DATA:
            cat = db.query(models.Category).filter(models.Category.name == c["name"]).first()
            if not cat:
                cat = db.query(models.Category).filter(func.lower(models.Category.name) == c["name"].lower()).first()
                if cat:
                    cat.name = c["name"]
                    db.commit()
                else:
                    cat = models.Category(name=c["name"])
                    db.add(cat)
                    db.commit()
                    db.refresh(cat)
                    sync_sequences(db)
            cat_map[c["name"]] = cat.id

        # Hapus duplikat lowercase puskesmas lama jika ada
        db.query(models.AssetCategory).filter(models.AssetCategory.name == "puskesmas").delete()
        db.commit()

        # Asset Categories
        asset_cat_map = {}
        for ac in ASSET_CATEGORIES_DATA:
            acat = db.query(models.AssetCategory).filter(models.AssetCategory.name == ac["name"]).first()
            if not acat:
                acat = db.query(models.AssetCategory).filter(func.lower(models.AssetCategory.name) == ac["name"].lower()).first()
                if acat:
                    acat.name = ac["name"]
                    acat.icon_url = ac["icon_url"]
                    acat.color = ac["color"]
                    db.commit()
                else:
                    acat = models.AssetCategory(name=ac["name"], icon_url=ac["icon_url"], color=ac["color"])
                    db.add(acat)
                    db.commit()
                    db.refresh(acat)
                    sync_sequences(db)
            else:
                acat.icon_url = ac["icon_url"]
                acat.color = ac["color"]
                db.commit()
            asset_cat_map[ac["name"]] = acat.id
        db.commit()

        # Source Types
        st_map = {}
        for st in SOURCE_TYPES_DATA:
            st_obj = db.query(models.SourceType).filter(models.SourceType.name == st["name"]).first()
            if not st_obj:
                st_obj = db.query(models.SourceType).filter(func.lower(models.SourceType.name) == st["name"].lower()).first()
                if st_obj:
                    st_obj.name = st["name"]
                    db.commit()
                else:
                    st_obj = models.SourceType(name=st["name"])
                    db.add(st_obj)
                    db.commit()
                    db.refresh(st_obj)
                    sync_sequences(db)
            st_map[st["name"]] = st_obj.id
        db.commit()

        # Users (Setiap user password = password123)
        user_map = {}
        hashed_default_pw = security.get_password_hash("password123")
        for u in USERS_DATA:
            user_obj = db.query(models.User).filter(models.User.username == u["username"]).first()
            target_source_id = source_map.get("BAPPEDA", 1)
            if u["source_id"] == 2:
                target_source_id = source_map.get("Dinas Kesehatan", 2)
            elif u["source_id"] == 3:
                target_source_id = source_map.get("Dinas Pendidikan", 3)
            elif u["source_id"] == 4:
                target_source_id = source_map.get("Dinas PUPR", 4)
            elif u["source_id"] == 5:
                target_source_id = source_map.get("Dinas Sosial", 5)
            elif u["source_id"] == 6:
                target_source_id = source_map.get("BPS Mimika", 6)
            elif u["source_id"] == 7:
                target_source_id = source_map.get("BRIDA Mimika", 7)

            if not user_obj:
                user_obj = models.User(
                    username=u["username"],
                    email=u["email"],
                    full_name=u["full_name"],
                    role=u["role"],
                    hashed_password=hashed_default_pw,
                    is_active=True,
                    source_id=target_source_id
                )
                db.add(user_obj)
                db.commit()
                db.refresh(user_obj)
                sync_sequences(db)
            else:
                user_obj.hashed_password = hashed_default_pw
                user_obj.role = u["role"]
                user_obj.source_id = target_source_id
                user_obj.is_active = True
                db.commit()
            user_map[u["username"]] = user_obj.id
        db.commit()
        sync_sequences(db)
        print(f"  ✓ {len(user_map)} Akun Pengguna siap (Password seragam: 'password123').")

        # --------------------------------------------------------------------
        # TAHAP 4: ASET FISIK GEOTAGGING (APPROVED, PENDING, REJECTED)
        # --------------------------------------------------------------------
        print("\n[4/6] Menyuntikkan Aset Fisik Geotagging dengan Siklus Lengkap...")
        
        assets_seed_data = [
            # --- APPROVED (Tampil di WebGIS Publik & Peta Atlas) ---
            {
                "name": "RSUD Kabupaten Mimika",
                "username": "dinkes",
                "source_name": "Dinas Kesehatan",
                "district_name": "Mimika Baru",
                "category_name": "Rumah Sakit",
                "lat": -4.5450,
                "lng": 136.8900,
                "status": "approved",
                "description": "Rumah Sakit Umum Daerah Tipe B milik Pemerintah Kabupaten Mimika, pusat rujukan medis utama wilayah Papua Tengah.",
                "details": {"Kapasitas Bed": "180 Tempat Tidur", "Akreditasi": "Paripurna", "IGD 24 Jam": "Tersedia", "Tahun Berdiri": "2008"},
                "images": [
                    "https://images.unsplash.com/photo-1587351021355-a479a299d2f9?auto=format&fit=crop&w=800&q=80",
                    "https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?auto=format&fit=crop&w=800&q=80"
                ]
            },
            {
                "name": "Puskesmas Timika Baru",
                "username": "dinkes",
                "source_name": "Dinas Kesehatan",
                "district_name": "Mimika Baru",
                "category_name": "Puskesmas",
                "lat": -4.5300,
                "lng": 136.8850,
                "status": "approved",
                "description": "Puskesmas induk pelayanan primer perkotaan Timika, melayani rawat jalan, KIA, posyandu terintegrasi, dan imunisasi.",
                "details": {"Status Operasional": "Aktif Penuh", "Layanan Rawat Inap": "Tersedia (12 Bed)", "Rata-rata Pasien": "110 Pasien/Hari"},
                "images": [
                    "https://images.unsplash.com/photo-1516549655169-df83a0774514?auto=format&fit=crop&w=800&q=80"
                ]
            },
            {
                "name": "Puskesmas Kuala Kencana",
                "username": "dinkes",
                "source_name": "Dinas Kesehatan",
                "district_name": "Kuala Kencana",
                "category_name": "Puskesmas",
                "lat": -4.4320,
                "lng": 136.8650,
                "status": "approved",
                "description": "Fasilitas kesehatan primer melayani masyarakat Distrik Kuala Kencana dan sekitarnya dengan fasilitas laboratorium lengkap.",
                "details": {"Status Operasional": "Aktif", "Layanan Laboratorium": "Lengkap", "Ambulans Siaga": "2 Unit"},
                "images": [
                    "https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?auto=format&fit=crop&w=800&q=80"
                ]
            },
            {
                "name": "SMP Negeri 2 Mimika Baru",
                "username": "disdik",
                "source_name": "Dinas Pendidikan",
                "district_name": "Mimika Baru",
                "category_name": "Gedung Sekolah",
                "lat": -4.5350,
                "lng": 136.8950,
                "status": "approved",
                "description": "Gedung sekolah menengah pertama negeri dengan 18 ruang kelas, laboratorium komputer, dan lapangan olahraga serbaguna.",
                "details": {"Jumlah Siswa": "580 Siswa", "Tenaga Pendidik": "36 Guru", "Akreditasi": "A", "Luas Lahan": "4.200 m²"},
                "images": [
                    "https://images.unsplash.com/photo-1580582932707-520aed937b7b?auto=format&fit=crop&w=800&q=80"
                ]
            },
            {
                "name": "SMA Negeri 1 Mimika",
                "username": "disdik",
                "source_name": "Dinas Pendidikan",
                "district_name": "Mimika Baru",
                "category_name": "Gedung Sekolah",
                "lat": -4.5400,
                "lng": 136.8800,
                "status": "approved",
                "description": "Sekolah menengah atas rujukan di Timika, dilengkapi perpustakaan digital dan laboratorium sains terpadu.",
                "details": {"Jumlah Siswa": "720 Siswa", "Tenaga Pendidik": "48 Guru", "Kondisi Bangunan": "Sangat Baik"},
                "images": [
                    "https://images.unsplash.com/photo-1509062522246-3755977927d7?auto=format&fit=crop&w=800&q=80"
                ]
            },
            {
                "name": "Jembatan Poros Sungai Wania",
                "username": "pupr",
                "source_name": "Dinas PUPR",
                "district_name": "Wania",
                "category_name": "Infrastruktur Jembatan",
                "lat": -4.5650,
                "lng": 136.9150,
                "status": "approved",
                "description": "Jembatan rangka baja kelas A yang menghubungkan poros transportasi utama Distrik Wania dengan Pelabuhan Poumako.",
                "details": {"Panjang Bentang": "120 Meter", "Konstruksi": "Rangka Baja Kelas A", "Beban Maksimal": "40 Ton", "Tahun Selesai": "2023"},
                "images": [
                    "https://images.unsplash.com/photo-1545569341-9eb8b30979d9?auto=format&fit=crop&w=800&q=80"
                ]
            },
            {
                "name": "Puskesmas Pembantu (Pustu) Limau Asri",
                "username": "dinkes",
                "source_name": "Dinas Kesehatan",
                "district_name": "Iwaka",
                "category_name": "Puskesmas Pembantu",
                "lat": -4.5200,
                "lng": 136.8100,
                "status": "approved",
                "description": "Pos pelayanan kesehatan pembantu untuk warga pemukiman SP 5 Limau Asri, melayani pertolongan pertama dan posyandu lansia.",
                "details": {"Tenaga Medis": "1 Bidan, 1 Perawat", "Jadwal Layanan": "Senin - Sabtu", "Status Lahan": "Hibah Desa"},
                "images": [
                    "https://images.unsplash.com/photo-1516549655169-df83a0774514?auto=format&fit=crop&w=800&q=80"
                ]
            },
            {
                "name": "Kantor Distrik Kuala Kencana",
                "username": "admin",
                "source_name": "BAPPEDA",
                "district_name": "Kuala Kencana",
                "category_name": "Kantor Pemerintahan",
                "lat": -4.4350,
                "lng": 136.8620,
                "status": "approved",
                "description": "Pusat pelayanan administrasi kependudukan dan koordinasi kewilayahan Distrik Kuala Kencana.",
                "details": {"Luas Bangunan": "650 m²", "Layanan Terpadu": "Perekaman e-KTP, Izin Domisili", "Konektivitas": "Internet Fiber"},
                "images": [
                    "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=800&q=80"
                ]
            },

            # --- PENDING (Antrean Uji Moderasi di /admin/admin-manajemen-aset) ---
            {
                "name": "Usulan Pembangunan Pustu Kampung Tipuka",
                "username": "dinkes",
                "source_name": "Dinas Kesehatan",
                "district_name": "Mimika Timur",
                "category_name": "Puskesmas Pembantu",
                "lat": -4.6500,
                "lng": 136.9500,
                "status": "pending",
                "description": "Pengajuan titik lokasi pembangunan Pustu baru guna menjangkau 450 KK di pesisir Kampung Tipuka yang terisolir muara sungai.",
                "details": {"Kebutuhan Anggaran": "Rp 750.000.000", "Luas Lahan Diusulkan": "800 m²", "Status Tanah": "Pelepasan Adat"},
                "images": [
                    "https://images.unsplash.com/photo-1516549655169-df83a0774514?auto=format&fit=crop&w=800&q=80"
                ]
            },
            {
                "name": "Pengadaan Fasilitas Laboratorium SMPN 7 Wania",
                "username": "disdik",
                "source_name": "Dinas Pendidikan",
                "district_name": "Wania",
                "category_name": "Gedung Sekolah",
                "lat": -4.5720,
                "lng": 136.9200,
                "status": "pending",
                "description": "Rencana pembangunan gedung laboratorium komputer dan perpustakaan digital untuk mendukung asesmen nasional siswa.",
                "details": {"Sasaran Pengguna": "320 Siswa", "Kebutuhan Unit PC": "35 Unit", "Target Realisasi": "Semester Ganjil 2025/2026"},
                "images": [
                    "https://images.unsplash.com/photo-1580582932707-520aed937b7b?auto=format&fit=crop&w=800&q=80"
                ]
            },
            {
                "name": "Pembangunan Jembatan Gantung Nayaro",
                "username": "pupr",
                "source_name": "Dinas PUPR",
                "district_name": "Mimika Baru",
                "category_name": "Infrastruktur Jembatan",
                "lat": -4.5900,
                "lng": 136.8700,
                "status": "pending",
                "description": "Usulan jembatan gantung pejalan kaki dan kendaraan roda dua melintasi sungai pemisah Kampung Nayaro menuju jalan poros.",
                "details": {"Panjang": "85 Meter", "Estimasi Biaya": "Rp 1.200.000.000", "Kondisi Eksisting": "Hanya Perahu Dayung"},
                "images": [
                    "https://images.unsplash.com/photo-1545569341-9eb8b30979d9?auto=format&fit=crop&w=800&q=80"
                ]
            },

            # --- REJECTED (Contoh Histori Aset Ditolak untuk Demonstrasi) ---
            {
                "name": "Pengajuan Poskesdes Kampung Pigapu (Ditolak)",
                "username": "dinkes",
                "source_name": "Dinas Kesehatan",
                "district_name": "Iwaka",
                "category_name": "Puskesmas Pembantu",
                "lat": -4.5800,
                "lng": 136.7900,
                "status": "rejected",
                "description": "Pengajuan titik fasilitas kesehatan ditolak oleh verifikator karena koordinat GPS berada di luar batas administrasi polygon wilayah kerja.",
                "details": {"Alasan Penolakan": "Titik koordinat berada di luar batas distrik Iwaka (irisan hutan lindung). Harap validasi ulang titik koordinat GPS fisik.", "Tanggal Verifikasi": "2025-02-14"},
                "images": [
                    "https://images.unsplash.com/photo-1516549655169-df83a0774514?auto=format&fit=crop&w=800&q=80"
                ]
            },
            {
                "name": "Renovasi Balai Warga Limau Asri (Ditolak)",
                "username": "admin",
                "source_name": "BAPPEDA",
                "district_name": "Wania",
                "category_name": "Kantor Pemerintahan",
                "lat": -4.5550,
                "lng": 136.9050,
                "status": "rejected",
                "description": "Pengajuan bantuan renovasi balai pertemuan warga dikembalikan karena berkas legalitas kepemilikan tanah belum terlampir.",
                "details": {"Alasan Penolakan": "Dokumen kepemilikan lahan hak pakai desa belum diunggah. Foto eksisting buram dan tidak memperlihatkan kerusakan struktur.", "Tanggal Verifikasi": "2025-01-28"},
                "images": [
                    "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=800&q=80"
                ]
            },
            {
                "name": "Pembangunan Dermaga Kayu Muara Pomako (Ditolak)",
                "username": "pupr",
                "source_name": "Dinas PUPR",
                "district_name": "Mimika Timur",
                "category_name": "Infrastruktur Jembatan",
                "lat": -4.7100,
                "lng": 136.9800,
                "status": "rejected",
                "description": "Usulan pembuatan dermaga sandar kapal kayu kecil ditolak karena tumpang tindih dengan proyek revitalisasi pelabuhan Kemenhub.",
                "details": {"Alasan Penolakan": "Duplikasi rencana kegiatan dengan proyek Pelabuhan Perikanan Nasional Kementerian Kelautan dan Perikanan 2025.", "Tanggal Verifikasi": "2025-02-02"},
                "images": [
                    "https://images.unsplash.com/photo-1545569341-9eb8b30979d9?auto=format&fit=crop&w=800&q=80"
                ]
            }
        ]

        inserted_assets = 0
        for item in assets_seed_data:
            new_asset = models.Asset(
                name=item["name"],
                user_id=user_map[item["username"]],
                source_id=source_map[item["source_name"]],
                district_id=district_map[item["district_name"]],
                category_id=asset_cat_map[item["category_name"]],
                lat=item["lat"],
                lng=item["lng"],
                description=item["description"],
                details=item["details"],
                image_url=item["images"][0],
                images=item["images"],
                status=item["status"]
            )
            db.add(new_asset)
            inserted_assets += 1
        db.commit()
        print(f"  ✓ Berhasil menyuntikkan {inserted_assets} Aset Geotagging:")
        print(f"    - Approved: 8 aset (tampil di peta publik)")
        print(f"    - Pending:  3 aset (siap dites di panel moderasi admin)")
        print(f"    - Rejected: 3 aset (histori penolakan terdokumentasi)")

        # --------------------------------------------------------------------
        # TAHAP 5: DATASET SEKTORAL & DATA ROWS (APPROVED & PENDING)
        # --------------------------------------------------------------------
        print("\n[5/6] Menyuntikkan Dataset Sektoral & 18 Baris Data Distrik...")

        # Data Nilai Riil per Distrik untuk Dataset
        dist_names = [d["name"] for d in DISTRICT_DATA]
        
        # Generator nilai konsisten per distrik
        stunting_dict = {
            "Mimika Baru": 12.4, "Kuala Kencana": 9.1, "Tembagapura": 6.5, "Wania": 14.8,
            "Iwaka": 19.2, "Kwamki Narama": 15.5, "Mimika Timur": 22.4, "Mimika Tengah": 24.1,
            "Mimika Barat": 28.3, "Agimuga": 32.5, "Jila": 38.2, "Jita": 35.0,
            "Mimika Timur Jauh": 29.8, "Mimika Barat Jauh": 31.4, "Mimika Barat Tengah": 27.5,
            "Amar": 26.8, "Hoya": 41.2, "Alama": 44.5
        }

        imunisasi_dict = {
            "Mimika Baru": 92.5, "Kuala Kencana": 95.0, "Tembagapura": 94.2, "Wania": 88.4,
            "Iwaka": 79.1, "Kwamki Narama": 84.6, "Mimika Timur": 75.3, "Mimika Tengah": 71.0,
            "Mimika Barat": 68.4, "Agimuga": 62.0, "Jila": 58.5, "Jita": 64.2,
            "Mimika Timur Jauh": 69.1, "Mimika Barat Jauh": 61.3, "Mimika Barat Tengah": 67.8,
            "Amar": 70.2, "Hoya": 54.0, "Alama": 51.5
        }

        apm_sd_dict = {
            "Mimika Baru": 96.2, "Kuala Kencana": 98.4, "Tembagapura": 97.1, "Wania": 94.5,
            "Iwaka": 89.2, "Kwamki Narama": 91.0, "Mimika Timur": 87.3, "Mimika Tengah": 82.5,
            "Mimika Barat": 84.1, "Agimuga": 76.5, "Jila": 69.4, "Jita": 74.0,
            "Mimika Timur Jauh": 80.2, "Mimika Barat Jauh": 73.1, "Mimika Barat Tengah": 78.6,
            "Amar": 81.0, "Hoya": 62.5, "Alama": 59.8
        }

        jalan_mantap_dict = {
            "Mimika Baru": 88.5, "Kuala Kencana": 96.0, "Tembagapura": 84.2, "Wania": 79.4,
            "Iwaka": 72.1, "Kwamki Narama": 76.5, "Mimika Timur": 68.2, "Mimika Tengah": 48.0,
            "Mimika Barat": 52.4, "Agimuga": 36.0, "Jila": 28.5, "Jita": 32.0,
            "Mimika Timur Jauh": 44.1, "Mimika Barat Jauh": 35.2, "Mimika Barat Tengah": 41.5,
            "Amar": 39.0, "Hoya": 21.0, "Alama": 18.5
        }

        kemiskinan_dict = {
            "Mimika Baru": 8.5, "Kuala Kencana": 5.2, "Tembagapura": 7.1, "Wania": 11.2,
            "Iwaka": 16.4, "Kwamki Narama": 14.0, "Mimika Timur": 19.8, "Mimika Tengah": 22.5,
            "Mimika Barat": 24.1, "Agimuga": 28.6, "Jila": 33.2, "Jita": 29.5,
            "Mimika Timur Jauh": 26.4, "Mimika Barat Jauh": 28.0, "Mimika Barat Tengah": 25.2,
            "Amar": 24.0, "Hoya": 36.5, "Alama": 39.1
        }

        pdrb_dict = {
            "Mimika Baru": 4850.5, "Kuala Kencana": 3920.0, "Tembagapura": 12800.0, "Wania": 2150.0,
            "Iwaka": 980.0, "Kwamki Narama": 890.0, "Mimika Timur": 1250.0, "Mimika Tengah": 640.0,
            "Mimika Barat": 580.0, "Agimuga": 420.0, "Jila": 380.0, "Jita": 450.0,
            "Mimika Timur Jauh": 510.0, "Mimika Barat Jauh": 410.0, "Mimika Barat Tengah": 480.0,
            "Amar": 440.0, "Hoya": 310.0, "Alama": 290.0
        }

        datasets_meta = [
            # 1. APPROVED DATASETS
            {
                "title": "Prevalensi Stunting Balita per Distrik 2025",
                "username": "dinkes",
                "source_name": "Dinas Kesehatan",
                "category_name": "Kesehatan",
                "source_type_name": "Statistik Sektoral",
                "year": 2025,
                "period": "Tahunan",
                "status": "approved",
                "description": "Laporan resmi pemantauan status gizi dan angka prevalensi stunting pada balita per distrik di wilayah Kabupaten Mimika tahun anggaran 2025.",
                "quality_score": 100.0,
                "headers": ["distrik", "stunting", "target_nasional", "status_zona"],
                "data_builder": lambda d: {
                    "distrik": d,
                    "stunting": stunting_dict.get(d, 20.0),
                    "target_nasional": 14.0,
                    "status_zona": "Zona Hijau" if stunting_dict.get(d, 20.0) <= 14.0 else ("Zona Kuning" if stunting_dict.get(d, 20.0) <= 25.0 else "Zona Merah")
                }
            },
            {
                "title": "Cakupan Imunisasi Dasar Lengkap (IDL) Balita 2024",
                "username": "dinkes",
                "source_name": "Dinas Kesehatan",
                "category_name": "Kesehatan",
                "source_type_name": "Statistik Sektoral",
                "year": 2024,
                "period": "Tahunan",
                "status": "approved",
                "description": "Persentase pencapaian imunisasi dasar lengkap balita (HB0, BCG, DPT-HB-Hib, Polio, Campak) pada 18 distrik Kabupaten Mimika.",
                "quality_score": 98.8,
                "headers": ["distrik", "cakupan_imunisasi", "target_renstra", "capaian"],
                "data_builder": lambda d: {
                    "distrik": d,
                    "cakupan_imunisasi": imunisasi_dict.get(d, 70.0),
                    "target_renstra": 90.0,
                    "capaian": "Tercapai" if imunisasi_dict.get(d, 70.0) >= 90.0 else "Perlu Penguatan"
                }
            },
            {
                "title": "Angka Partisipasi Murni (APM) Jenjang SD Menurut Distrik 2024",
                "username": "disdik",
                "source_name": "Dinas Pendidikan",
                "category_name": "Pendidikan",
                "source_type_name": "Statistik Sektoral",
                "year": 2024,
                "period": "Tahunan",
                "status": "approved",
                "description": "Indikator persentase siswa kelompok usia 7-12 tahun yang bersekolah tepat di jenjang sekolah dasar pada masing-masing distrik.",
                "quality_score": 99.2,
                "headers": ["distrik", "apm_sd", "jumlah_sekolah_sd", "kategori_partisipasi"],
                "data_builder": lambda d: {
                    "distrik": d,
                    "apm_sd": apm_sd_dict.get(d, 80.0),
                    "jumlah_sekolah_sd": random.randint(4, 18),
                    "kategori_partisipasi": "Tinggi" if apm_sd_dict.get(d, 80.0) >= 90.0 else ("Sedang" if apm_sd_dict.get(d, 80.0) >= 75.0 else "Rendah")
                }
            },
            {
                "title": "Kemantapan Infrastruktur Jalan Kabupaten per Distrik 2024",
                "username": "pupr",
                "source_name": "Dinas PUPR",
                "category_name": "Infrastruktur",
                "source_type_name": "Statistik Sektoral",
                "year": 2024,
                "period": "Tahunan",
                "status": "approved",
                "description": "Kondisi jalan kewenangan Pemerintah Daerah Kabupaten Mimika (Kondisi Mantap vs Rusak Ringan/Berat) dalam satuan persentase.",
                "quality_score": 100.0,
                "headers": ["distrik", "kemantapan_jalan", "panjang_ruas_km", "klasifikasi"],
                "data_builder": lambda d: {
                    "distrik": d,
                    "kemantapan_jalan": jalan_mantap_dict.get(d, 50.0),
                    "panjang_ruas_km": round(random.uniform(15.0, 110.0), 1),
                    "klasifikasi": "Baik / Sangat Baik" if jalan_mantap_dict.get(d, 50.0) >= 75.0 else "Prioritas Pemeliharaan"
                }
            },
            {
                "title": "Tingkat Kemiskinan Makro dan Sebaran Bantuan Sosial 2024",
                "username": "dinsos",
                "source_name": "Dinas Sosial",
                "category_name": "Sosial & Kemasyarakatan",
                "source_type_name": "Statistik Sektoral",
                "year": 2024,
                "period": "Tahunan",
                "status": "approved",
                "description": "Persentase penduduk miskin dan estimasi alokasi kuota bantuan Program Keluarga Harapan (PKH) per wilayah distrik.",
                "quality_score": 97.5,
                "headers": ["distrik", "kemiskinan", "kuota_pkh", "indeks_kerentanan"],
                "data_builder": lambda d: {
                    "distrik": d,
                    "kemiskinan": kemiskinan_dict.get(d, 20.0),
                    "kuota_pkh": random.randint(250, 2400),
                    "indeks_kerentanan": "Tinggi" if kemiskinan_dict.get(d, 20.0) >= 25.0 else ("Sedang" if kemiskinan_dict.get(d, 20.0) >= 15.0 else "Rendah")
                }
            },
            {
                "title": "Produk Domestik Regional Bruto (PDRB) Non-Tambang Sektor Riil 2024",
                "username": "bps",
                "source_name": "BPS Mimika",
                "category_name": "Ekonomi & Keuangan",
                "source_type_name": "Statistik Dasar",
                "year": 2024,
                "period": "Tahunan",
                "status": "approved",
                "description": "Distribusi nilai tambah ekonomi riil (PDRB ADHK) menurut distrik di luar sektor pertambangan ekstraktif tembaga/emas.",
                "quality_score": 100.0,
                "headers": ["distrik", "pdrb_miliar", "sektor_utama", "tren_pertumbuhan"],
                "data_builder": lambda d: {
                    "distrik": d,
                    "pdrb_miliar": pdrb_dict.get(d, 500.0),
                    "sektor_utama": "Perdagangan & Jasa" if d in ["Mimika Baru", "Wania", "Kuala Kencana"] else ("Perikanan & Kelautan" if "Timur" in d or "Barat" in d or d in ["Amar", "Jita"] else "Pertanian Rakyat"),
                    "tren_pertumbuhan": "+5.4%" if pdrb_dict.get(d, 500.0) > 1000 else "+3.8%"
                }
            },

            # 2. PENDING DATASETS (Untuk uji validasi Data Quality di Portal Admin)
            {
                "title": "Surveilans Kasus Malaria Positif dan Distribusi Kelambu Q1 2025",
                "username": "dinkes",
                "source_name": "Dinas Kesehatan",
                "category_name": "Kesehatan",
                "source_type_name": "Statistik Sektoral",
                "year": 2025,
                "period": "Triwulan I",
                "status": "pending",
                "description": "Data laporan kasus malaria terkonfirmasi laboratorium serta rekapitulasi pembagian kelambu berinsektisida triwulan pertama.",
                "quality_score": 96.0,
                "headers": ["distrik", "kasus_positif", "kelambu_dibagikan"],
                "data_builder": lambda d: {
                    "distrik": d,
                    "kasus_positif": random.randint(12, 145),
                    "kelambu_dibagikan": random.randint(50, 600)
                }
            },
            {
                "title": "Pendataan Akses Sarana Air Bersih Perpipaan dan Non-Perpipaan 2025",
                "username": "pupr",
                "source_name": "Dinas PUPR",
                "category_name": "Infrastruktur",
                "source_type_name": "Statistik Sektoral",
                "year": 2025,
                "period": "Tahunan",
                "status": "pending",
                "description": "Monitoring cakupan akses air minum aman dan sanitasi layak rumah tangga perkotaan dan perdesaan Mimika.",
                "quality_score": 94.5,
                "headers": ["distrik", "akses_air_bersih_persen", "sanitasi_layak_persen"],
                "data_builder": lambda d: {
                    "distrik": d,
                    "akses_air_bersih_persen": round(random.uniform(35.0, 92.0), 1),
                    "sanitasi_layak_persen": round(random.uniform(40.0, 88.0), 1)
                }
            },
            {
                "title": "Rekapitulasi Angka Putus Sekolah (APS) Siswa Usia 7-18 Tahun 2024/2025",
                "username": "disdik",
                "source_name": "Dinas Pendidikan",
                "category_name": "Pendidikan",
                "source_type_name": "Statistik Sektoral",
                "year": 2025,
                "period": "Semester I",
                "status": "pending",
                "description": "Pendataan siswa putus sekolah jenjang SD, SMP, dan SMA/SMK untuk dasar alokasi beasiswa afirmasi Pemda Mimika.",
                "quality_score": 95.0,
                "headers": ["distrik", "aps_sd", "aps_smp", "aps_sma"],
                "data_builder": lambda d: {
                    "distrik": d,
                    "aps_sd": round(random.uniform(0.5, 4.2), 1),
                    "aps_smp": round(random.uniform(1.2, 7.5), 1),
                    "aps_sma": round(random.uniform(2.0, 9.8), 1)
                }
            }
        ]

        total_datasets_inserted = 0
        total_rows_inserted = 0

        for meta in datasets_meta:
            ds = models.Dataset(
                user_id=user_map[meta["username"]],
                title=meta["title"],
                dataset_type="pemerintah" if meta["source_name"] != "BPS Mimika" else "non-pemerintah",
                source_id=source_map[meta["source_name"]],
                category_id=cat_map[meta["category_name"]],
                source_type_id=st_map[meta["source_type_name"]],
                district_id=None, # Multi-distrik (Kabupaten level)
                year=meta["year"],
                period=meta["period"],
                description=meta["description"],
                total_rows=len(dist_names),
                quality_score=meta["quality_score"],
                headers=meta["headers"],
                status=meta["status"],
                structure_type="tabular",
                spatial_status="mapped",
                needs_review=(meta["status"] == "pending"),
                image_url="https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=800&q=80"
            )
            db.add(ds)
            db.flush()
            total_datasets_inserted += 1

            # Masukkan 18 Baris Data Distrik
            for d_name in dist_names:
                row_content = meta["data_builder"](d_name)
                row_json = json.dumps(row_content, sort_keys=True)
                row_hash = hashlib.md5(row_json.encode()).hexdigest()

                drow = models.DataRow(
                    dataset_id=ds.id,
                    content=row_content,
                    row_hash=row_hash
                )
                db.add(drow)
                total_rows_inserted += 1

        db.commit()
        print(f"  ✓ Berhasil menyuntikkan {total_datasets_inserted} Dataset ({total_rows_inserted} baris DataRow):")
        print(f"    - Approved: 6 dataset (tampil di Explorer dan siap diekspor)")
        print(f"    - Pending:  3 dataset (menunggu review di Data Quality admin)")

        # --------------------------------------------------------------------
        # TAHAP 6: SURVEI PUBLIK BRIDA & RESPONS SINTETIS
        # --------------------------------------------------------------------
        print("\n[6/6] Menyuntikkan 3 Kuesioner Survei BRIDA & Data Respons Warga...")

        surveys_data = [
            {
                "title": "Survei Kepuasan Pasien Terhadap Layanan Puskesmas di Kabupaten Mimika",
                "description": "Kajian kepuasan masyarakat terhadap mutu pelayanan dokter, paramedis, ketepatan waktu, dan ketersediaan obat di Puskesmas se-Kabupaten Mimika.",
                "location": "Kabupaten Mimika (18 Distrik)",
                "start_date": datetime.utcnow() - timedelta(days=30),
                "end_date": datetime.utcnow() + timedelta(days=60),
                "status": "active",
                "questions": [
                    {
                        "id": "q1",
                        "title": "Fasilitas Puskesmas mana yang paling sering Anda kunjungi?",
                        "type": "choice",
                        "options": ["Puskesmas Timika Baru", "Puskesmas Wania", "Puskesmas Kuala Kencana", "Puskesmas Pesisir / Pedalaman"]
                    },
                    {
                        "id": "q2",
                        "title": "Bagaimana penilaian Anda terhadap keramahan dan kejelasan komunikasi petugas medis?",
                        "type": "rating",
                        "scale": 5
                    },
                    {
                        "id": "q3",
                        "title": "Berapa rata-rata waktu tunggu antrean dari pendaftaran hingga dipanggil dokter?",
                        "type": "choice",
                        "options": ["Kurang dari 30 Menit", "30 - 60 Menit", "Lebih dari 1 Jam"]
                    },
                    {
                        "id": "q4",
                        "title": "Ketersediaan obat-obatan yang diresepkan oleh dokter:",
                        "type": "choice",
                        "options": ["Sangat Lengkap (Langsung dapat di apotek puskesmas)", "Sebagian Tersedia", "Sering Kosong (Harus beli di apotek luar)"]
                    }
                ],
                "response_count": 26
            },
            {
                "title": "Kajian Kebutuhan Transportasi Publik dan Rute Trayek Perintis Timika",
                "description": "Pengumpulan data aspirasi masyarakat untuk perencanaan rute bus DAMRI perintis dan perahu motor penyeberangan distrik pesisir.",
                "location": "Wilayah Perkotaan dan Pesisir Mimika",
                "start_date": datetime.utcnow() - timedelta(days=15),
                "end_date": datetime.utcnow() + timedelta(days=75),
                "status": "active",
                "questions": [
                    {
                        "id": "q1",
                        "title": "Moda transportasi utama harian yang Anda gunakan:",
                        "type": "choice",
                        "options": ["Sepeda Motor Pribadi", "Taksi / Angkutan Kota (Angkot)", "Perahu Motor / Belang", "Kendaraan Sewa / Ojek"]
                    },
                    {
                        "id": "q2",
                        "title": "Rute yang paling mendesak memerlukan penambahan armada bus bersubsidi:",
                        "type": "choice",
                        "options": ["Timika - Pelabuhan Poumako", "Timika - Kuala Kencana / SP 3", "Timika - Iwaka / Limau Asri", "Jalur Angkutan Sungai Mimika Timur"]
                    },
                    {
                        "id": "q3",
                        "title": "Keterjangkauan tarif angkutan umum yang berlaku saat ini:",
                        "type": "rating",
                        "scale": 5
                    }
                ],
                "response_count": 22
            },
            {
                "title": "Evaluasi Efektivitas Program Ketahanan Pangan & Pembagian PMT Balita",
                "description": "Evaluasi dampak langsung program Pemberian Makanan Tambahan (PMT) lokal dalam upaya penurunan angka stunting di kampung prioritas.",
                "location": "Distrik Lokus Stunting Kabupaten Mimika",
                "start_date": datetime.utcnow() - timedelta(days=20),
                "end_date": datetime.utcnow() + timedelta(days=45),
                "status": "active",
                "questions": [
                    {
                        "id": "q1",
                        "title": "Apakah balita Anda rutin ditimbang dan diukur tinggi badannya di Posyandu setiap bulan?",
                        "type": "choice",
                        "options": ["Ya, Rutin Setiap Bulan", "Hanya Saat Sempat", "Jarang / Belum Pernah"]
                    },
                    {
                        "id": "q2",
                        "title": "Apakah keluarga Anda pernah menerima paket makanan bergizi (telur, susu, pangan lokal) dari kader Posyandu?",
                        "type": "choice",
                        "options": ["Rutin Setiap Bulan", "Pernah 1-2 Kali", "Belum Pernah Menerima"]
                    },
                    {
                        "id": "q3",
                        "title": "Tingkat kepuasan terhadap pendampingan petugas gizi puskesmas:",
                        "type": "rating",
                        "scale": 5
                    }
                ],
                "response_count": 20
            }
        ]

        total_surveys = 0
        total_responses = 0

        for sv in surveys_data:
            new_sv = models.Survey(
                title=sv["title"],
                description=sv["description"],
                location=sv["location"],
                start_date=sv["start_date"],
                end_date=sv["end_date"],
                status=sv["status"],
                questions=sv["questions"]
            )
            db.add(new_sv)
            db.flush()
            total_surveys += 1

            # Suntikkan respons bervariasi
            for i in range(sv["response_count"]):
                answers = {}
                for q in sv["questions"]:
                    if q["type"] == "choice":
                        answers[q["id"]] = random.choice(q["options"])
                    elif q["type"] == "rating":
                        answers[q["id"]] = random.choices([3, 4, 5], weights=[20, 50, 30])[0]

                submitted_time = datetime.utcnow() - timedelta(days=random.randint(1, 14), hours=random.randint(1, 12))
                resp = models.SurveyResponse(
                    survey_id=new_sv.id,
                    answers=answers,
                    email=f"warga{i+1}@gmail.com",
                    submitted_at=submitted_time
                )
                db.add(resp)
                total_responses += 1

        db.commit()
        print(f"  ✓ {total_surveys} Survei Publik BRIDA aktif dibuat dengan {total_responses} data respons warga.")

        # --------------------------------------------------------------------
        # TAHAP 7: PEMANASAN SPATIAL CACHE (CHOROPLETH ATLAS)
        # --------------------------------------------------------------------
        print("\n[7/7] Memanaskan Cache Spasial (Choropleth Peta Atlas)...")

        indicators = {
            "stunting": stunting_dict,
            "kemiskinan": kemiskinan_dict,
            "imunisasi": imunisasi_dict,
            "jalan_mantap": jalan_mantap_dict,
            "pdrb": pdrb_dict
        }

        total_caches = 0
        for ind_key, values in indicators.items():
            for d_name, val in values.items():
                d_id = district_map.get(d_name)
                if d_id:
                    cache_item = models.SpatialCache(
                        indicator_key=ind_key,
                        district_id=d_id,
                        value=float(val),
                        last_calculated=datetime.utcnow()
                    )
                    db.add(cache_item)
                    total_caches += 1
        db.commit()
        sync_sequences(db)
        print(f"  ✓ {total_caches} Titik Agregasi SpatialCache dipanaskan (Indikator: stunting, kemiskinan, imunisasi, jalan_mantap, pdrb).")

        print("\n" + "="*70)
        print("🎉 SELURUH SEEDER MASTER DATA BERHASIL DISELESAIKAN DENGAN SEMPURNA!")
        print("="*70)
        print("\nRingkasan Kredensial Pengujian (Password: password123):")
        print("  • Super Admin:  admin   (Portal: /admin-dashboard)")
        print("  • Dinkes:       user    atau dinkes  (Portal: /dashboard & /user-manajemen-aset)")
        print("  • Disdik:       disdik  (Portal: /dashboard)")
        print("  • PUPR:         pupr    (Portal: /dashboard)")
        print("  • Dinsos:       dinsos  (Portal: /dashboard)")
        print("  • BRIDA:        brida   (Portal: /brida-dashboard & /survey)")
        print("  • BPS:          bps     (Portal: /dashboard)")
        print("="*70 + "\n")

    except Exception as e:
        db.rollback()
        print(f"\n❌ [ERROR SEEDER] Terjadi kesalahan: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    run_seeder()
