        # app/db/seeders/users.py
from sqlalchemy.orm import Session
from app.models import models
from app.core import security  # Mengimpor modul enkripsi password bawaan [cite: 830]

# ============================================================================
# DATA MASTER: LEMBAGA / OPD (Prasyarat Utama Relasi) [cite: ASSET_TAXONOMY_CONFIG]
# ============================================================================
SOURCES_DATA = [
    {"id": 1, "name": "BAPPEDA", "type": "opd"},
    {"id": 2, "name": "Dinas Kesehatan", "type": "opd"},
    {"id": 3, "name": "Dinas Pendidikan", "type": "opd"},
    {"id": 4, "name": "Dinas PUPR", "type": "opd"},
    {"id": 5, "name": "Dinas Sosial", "type": "opd"},
    {"id": 6, "name": "BPS Mimika", "type": "bps"}
]

# ============================================================================
# DATA TRANSAKSIONAL: AKUN PENGGUNA MASTER [cite: 830]
# ============================================================================
USERS_DATA = [
    {
        "username": "admin",
        "email": "admin@mimikakab.go.id",
        "full_name": "Bappeda Administrator",
        "role": "admin",
        "source_id": 1  # Terikat ke BAPPEDA
    },
    {
        "username": "brida",
        "email": "operator.brida@mimikakab.go.id",
        "full_name": "Operator BRIDA Mimika",
        "role": "brida",
        "source_id": 1  # Terikat ke BAPPEDA
    },
    {
        "username": "dinkes",
        "email": "operator.dinkes@mimikakab.go.id",
        "full_name": "Operator Dinas Kesehatan",
        "role": "user",  # Peran operator umum OPD (Dinkes) [cite: 1]
        "source_id": 2  # Terikat ke Dinas Kesehatan
    }
]

def seed_users(db: Session) -> dict:
    """
    [GRASP - INFORMATION EXPERT]
    Modul Seeder Pengguna & Lembaga.
    Mengeksekusi injeksi data master secara aman (Idempotent) dengan memeriksa
    keberadaan data kunci sebelum melakukan penyimpanan untuk menghindari IntegrityError.
    """
    stats = {"sources_inserted": 0, "users_inserted": 0}
    
    # 1. SEED MASTER OPD (SOURCES)
    for s in SOURCES_DATA:
        existing_source = db.query(models.Source).filter(models.Source.id == s["id"]).first()
        if not existing_source:
            # Cegah duplikasi berdasarkan nama unik jika ID bentrok di DB kustom
            name_check = db.query(models.Source).filter(models.Source.name == s["name"]).first()
            if not name_check:
                new_source = models.Source(
                    id=s["id"],
                    name=s["name"],
                    type=s["type"]
                )
                db.add(new_source)
                stats["sources_inserted"] += 1
                
    db.commit() # Commit tahap 1 agar relasi ID Source terbentuk dan terbaca oleh tahap 2

    # 2. SEED USERS [cite: 830]
    for u in USERS_DATA:
        existing_user = db.query(models.User).filter(models.User.username == u["username"]).first()
        if not existing_user:
            # Enkripsi password menggunakan modul Bcrypt standar keamanan kita [cite: 830, 831]
            hashed_pw = security.get_password_hash("Mimika123!")
            
            new_user = models.User(
                username=u["username"],
                email=u["email"],
                full_name=u["full_name"],
                role=u["role"],
                hashed_password=hashed_pw,
                is_active=True,
                source_id=u["source_id"]
            )
            db.add(new_user)
            stats["users_inserted"] += 1
            
    db.commit()
    return stats