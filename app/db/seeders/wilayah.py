# app/db/seeders/wilayah.py
from sqlalchemy.orm import Session
from app.models import models

# ============================================================================
# DATA MASTER: 18 DISTRIK & PROFIL KEWILAYAHAN [cite: DISTRICT_MAP, MOCK_DISTRICT_DRILLDOWN]
# ============================================================================
WILAYAH_DATA = [
    {
        "id": 1, 
        "name": "Mimika Baru", 
        "luas": 2216.00, 
        "penduduk": 142519, 
        "batas": "Utara: Kuala Kencana, Selatan: Wania, Timur: Mimika Timur, Barat: Iwaka",
        "deskripsi": "Distrik Mimika Baru adalah pusat administrasi pemerintahan dan episentrum ekonomi utama Kabupaten Mimika. Menghadapi tantangan urbanisasi cepat, distrik ini menjadi wilayah terpadat."
    },
    {
        "id": 2, 
        "name": "Kuala Kencana", 
        "luas": 860.74, 
        "penduduk": 29104, 
        "batas": "Utara: Tembagapura, Selatan: Mimika Baru, Timur: Kwamki Narama, Barat: Iwaka",
        "deskripsi": "Kuala Kencana merupakan kota industri modern yang didesain secara asri dengan utilitas bawah tanah dan sistem pengolahan limbah berstandar internasional."
    },
    {
        "id": 3, 
        "name": "Tembagapura", 
        "luas": 2586.88, 
        "penduduk": 22120, 
        "batas": "Utara: Kabupaten Puncak, Selatan: Kuala Kencana, Timur: Agimuga, Barat: Jila",
        "deskripsi": "Distrik dataran tinggi pegunungan Mimika yang menampung area operasional pertambangan emas dan tembaga utama nasional."
    },
    {
        "id": 4, 
        "name": "Wania", 
        "luas": 310.20, 
        "penduduk": 55210, 
        "batas": "Utara: Mimika Baru, Selatan: Laut Arafuru, Timur: Mimika Timur, Barat: Mimika Tengah",
        "deskripsi": "Wania berkembang pesat sebagai wilayah penyangga kota Timika dengan basis komoditas pertanian dan peternakan lokal."
    },
    {
        "id": 5, 
        "name": "Iwaka", 
        "luas": 785.40, 
        "penduduk": 11450, 
        "batas": "Utara: Tembagapura, Selatan: Mimika Tengah, Timur: Kuala Kencana, Barat: Mimika Barat",
        "deskripsi": " iwaka dilalui oleh jalur poros Trans Papua, menyimpan potensi ekowisata alam dan perkebunan kelapa sawit yang subur."
    },
    {
        "id": 6, 
        "name": "Kwamki Narama", 
        "luas": 240.50, 
        "penduduk": 14890, 
        "batas": "Utara: Kuala Kencana, Selatan: Mimika Baru, Timur: Mimika Timur, Barat: Wania",
        "deskripsi": "Kwamki Narama kini berkembang menjadi pusat permukiman baru yang asri dengan fokus pemberdayaan ekonomi komunitas pemuda lokal."
    },
    {
        "id": 7, 
        "name": "Mimika Timur", 
        "luas": 1520.10, 
        "penduduk": 9540, 
        "batas": "Utara: Mimika Baru, Selatan: Laut Arafuru, Timur: Mimika Timur Jauh, Barat: Wania",
        "deskripsi": "Berpusat di kawasan pesisir muara sungai, Mimika Timur didominasi oleh kebudayaan Kamoro dan potensi perikanan laut di Pelabuhan Poumako."
    },
    {
        "id": 8, 
        "name": "Mimika Tengah", 
        "luas": 2150.30, 
        "penduduk": 6230, 
        "batas": "Utara: Iwaka, Selatan: Laut Arafuru, Timur: Wania, Barat: Mimika Barat",
        "deskripsi": "Distrik pesisir dengan hamparan hutan mangrove yang rimbun, mengandalkan transportasi perahu motor sungai sebagai urat nadi konektivitas."
    },
    {
        "id": 9, 
        "name": "Mimika Barat", 
        "luas": 2750.00, 
        "penduduk": 4200, 
        "batas": "Utara: Kabupaten Deiyai, Selatan: Laut Arafuru, Timur: Mimika Tengah, Barat: Mimika Barat Tengah",
        "deskripsi": "Distrik pesisir bagian barat dengan pusat administrasi bersejarah di Kokonao, kaya akan potensi laut dan kelapa."
    },
    {
        "id": 10, 
        "name": "Agimuga", 
        "luas": 3120.45, 
        "penduduk": 3150, 
        "batas": "Utara: Kabupaten Puncak, Selatan: Mimika Timur Jauh, Timur: Jita, Barat: Tembagapura",
        "deskripsi": "Agimuga merupakan dataran rendah pedalaman yang subur dengan potensi perkebunan sagu dan kopi robusta alami."
    },
    {
        "id": 11, 
        "name": "Jila", 
        "luas": 1820.00, 
        "penduduk": 2800, 
        "batas": "Utara: Kabupaten Puncak, Selatan: Agimuga, Timur: Alama, Barat: Tembagapura",
        "deskripsi": "Jila terletak di punggung pegunungan tengah Papua, memiliki panorama alam lereng tebing yang menakjubkan."
    },
    {
        "id": 12, 
        "name": "Jita", 
        "luas": 1350.00, 
        "penduduk": 3200, 
        "batas": "Utara: Distrik Agimuga, Selatan: Laut Arafuru, Timur: Kabupaten Asmat, Barat: Mimika Timur Jauh",
        "deskripsi": "Berbatasan langsung dengan Asmat, Jita didominasi lanskap dataran basah berlumpur yang kaya akan hasil tangkapan kepiting bakau."
    },
    {
        "id": 13, 
        "name": "Mimika Timur Jauh", 
        "luas": 2050.00, 
        "penduduk": 4500, 
        "batas": "Utara: Distrik Agimuga, Selatan: Laut Arafuru, Timur: Distrik Jita, Barat: Distrik Mimika Timur",
        "deskripsi": "Membentang di garis pantai timur Mimika, distrik ini menjadi sentra komoditas perikanan tangkap tradisional nelayan lokal."
    },
    {
        "id": 14, 
        "name": "Mimika Barat Jauh", 
        "luas": 3450.00, 
        "penduduk": 2100, 
        "batas": "Utara: Kabupaten Kaimana, Selatan: Laut Arafuru, Timur: Distrik Mimika Barat Tengah, Barat: Kabupaten Kaimana",
        "deskripsi": "Distrik terluar bagian barat Mimika yang berbatasan langsung dengan Kaimana, didominasi kawasan rawa-rawa hutan basah."
    },
    {
        "id": 15, 
        "name": "Mimika Barat Tengah", 
        "luas": 2850.00, 
        "penduduk": 3800, 
        "batas": "Utara: Kabupaten Deiyai, Selatan: Laut Arafuru, Timur: Distrik Mimika Barat, Barat: Distrik Mimika Barat Jauh",
        "deskripsi": "Menghubungkan wilayah barat tengah pantai Mimika, ditopang oleh ekosistem sungai dan laut yang belum terjamah polusi."
    },
    {
        "id": 16, 
        "name": "Amar", 
        "luas": 1250.00, 
        "penduduk": 2950, 
        "batas": "Utara: Distrik Mimika Barat, Selatan: Laut Arafuru, Timur: Distrik Mimika Tengah, Barat: Distrik Mimika Barat Tengah",
        "deskripsi": "Distrik pesisir baru yang diproyeksikan Bappeda menjadi sentra budidaya perikanan laut terpadu masa depan."
    },
    {
        "id": 17, 
        "name": "Hoya", 
        "luas": 980.00, 
        "penduduk": 1500, 
        "batas": "Utara: Kabupaten Nduga, Selatan: Distrik Tembagapura, Timur: Distrik Jila, Barat: Kabupaten Puncak",
        "deskripsi": "Lembah terisolasi indah di kaki pegunungan bersalju, menyajikan potensi pertanian buah dataran tinggi yang khas."
    },
    {
        "id": 18, 
        "name": "Alama", 
        "luas": 1520.80, 
        "penduduk": 1980, 
        "batas": "Utara: Kabupaten Nduga, Selatan: Distrik Agimuga, Timur: Kabupaten Asmat, Barat: Distrik Jila",
        "deskripsi": "Kawasan paling timur pegunungan Mimika yang menyajikan panorama keindahan alam liar berselimut kabut awan putih tebal."
    }
]

def seed_wilayah(db: Session) -> dict:
    """
    [GRASP - INFORMATION EXPERT]
    Modul Seeder Kewilayahan Kabupaten Mimika.
    Menjamin data 18 Distrik dan DistrictProfiles terinisialisasi secara rapi dan terelasi kuat.
    """
    stats = {"districts_inserted": 0, "profiles_inserted": 0}
    
    for d in WILAYAH_DATA:
        # 1. Pengecekan Idempotensi Distrik [cite: DISTRICT_MAP]
        district = db.query(models.District).filter(models.District.id == d["id"]).first()
        if not district:
            district = models.District(
                id=d["id"],
                name=d["name"]
            )
            db.add(district)
            stats["districts_inserted"] += 1
            
        db.flush() # Flush agar ID District dapat diproses oleh relasi Profile di bawahnya

        # 2. Pengecekan Idempotensi Profil Distrik [cite: MOCK_DISTRICT_DRILLDOWN]
        profile = db.query(models.DistrictProfile).filter(models.DistrictProfile.district_id == d["id"]).first()
        if not profile:
            new_profile = models.DistrictProfile(
                district_id=d["id"],
                luas_wilayah=d["luas"],
                jumlah_penduduk=d["penduduk"],
                batas_wilayah=d["batas"],
                deskripsi=d["deskripsi"],
                # Seeding visual foto representatif untuk Theater Mode Galeri di frontend
                images=[
                    f"https://picsum.photos/seed/dist{d['id']}a/800/450",
                    f"https://picsum.photos/seed/dist{d['id']}b/800/450"
                ]
            )
            db.add(new_profile)
            stats["profiles_inserted"] += 1
            
    db.commit()
    return stats