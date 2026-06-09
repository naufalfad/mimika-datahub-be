# seed.py
import os
import sys
import argparse
from sqlalchemy.orm import Session

# Menjamin direktori root terdaftar di dalam sys.path Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.db.seeders import seed_users, seed_wilayah, seed_assets, seed_datasets

def main():
    parser = argparse.ArgumentParser(description="Mimika DataHub - Modular Seeding Engine CLI")
    parser.add_argument(
        "--module", 
        type=str, 
        choices=["users", "wilayah", "aset", "dataset", "all"], 
        default="all",
        help="Pilih modul spesifik yang ingin di-seed atau jalankan 'all' untuk menyuntikkan seluruh database."
    )
    
    args = parser.parse_args()
    
    # 1. Inisialisasi Sesi Basis Data
    db: Session = SessionLocal()
    print("\n" + "="*60)
    print("🚀 MIMIKA DATAHUB - MODULAR SEEDER ENGINE ACTIVE")
    print("="*60)
    print(f"[Core] Membuka koneksi basis data. Menargetkan modul: '{args.module.upper()}'\n")

    try:
        # ====================================================================
        # PILIHAN A: JALANKAN SEMUA SEEDER (BERDASARKAN URUTAN DEPENDENSI FK) [1, 2, 10]
        # ====================================================================
        if args.module == "all":
            print("[Step 1/4] Mengeksekusi seeder akun pengguna & OPD...")
            stats_users = seed_users(db)
            print(f"👉 Hasil: {stats_users['sources_inserted']} OPD & {stats_users['users_inserted']} Akun Pengguna berhasil diproses.\n")

            print("[Step 2/4] Mengeksekusi seeder wilayah administrasi & profil...")
            stats_wilayah = seed_wilayah(db)
            print(f"👉 Hasil: {stats_wilayah['districts_inserted']} Distrik & {stats_wilayah['profiles_inserted']} Profil Wilayah berhasil diproses.\n")

            print("[Step 3/4] Mengeksekusi seeder kategori & koordinat aset fisik...")
            stats_assets = seed_assets(db)
            print(f"👉 Hasil: {stats_assets['categories_inserted']} Kategori Aset & {stats_assets['assets_inserted']} Titik Koordinat berhasil diproses.\n")

            print("[Step 4/4] Mengeksekusi seeder data sektoral & kalkulasi cache spasial...")
            stats_datasets = seed_datasets(db)
            print(f"👉 Hasil: {stats_datasets['datasets_inserted']} Dataset Sektoral & {stats_datasets['rows_inserted']} DataRow berhasil diproses.")
            if stats_datasets["cache_warmed"]:
                print("👉 Status Cache: Berhasil dihitung dan dipanaskan (SpatialCache Warmed Up).\n")

            print("="*60)
            print("🎉 SEEDING SELURUH DATABASE BERHASIL DISELESAIKAN!")
            print("="*60)
            print("Silakan login menggunakan akun terdaftar:")
            print("1. Username: admin  | Password: Mimika123! (Super Admin Bappeda)")
            print("2. Username: dinkes | Password: Mimika123! (Operator Dinas Kesehatan)")
            print("3. Username: brida  | Password: Mimika123! (Operator BRIDA)")
            print("="*60 + "\n")

        # ====================================================================
        # PILIHAN B: JALANKAN MODUL SPESIFIK SECARA TERISOLASI
        # ====================================================================
        elif args.module == "users":
            print("[Modular] Menjalankan Seeder Pengguna & OPD...")
            stats = seed_users(db)
            print(f"👉 Sukses menyisipkan {stats['sources_inserted']} OPD & {stats['users_inserted']} Akun.")
            
        elif args.module == "wilayah":
            print("[Modular] Menjalankan Seeder Spasial Wilayah...")
            stats = seed_wilayah(db)
            print(f"👉 Sukses menyisipkan {stats['districts_inserted']} Distrik & {stats['profiles_inserted']} Profil.")
            
        elif args.module == "aset":
            print("[Modular] Menjalankan Seeder Aset Geotagging...")
            stats = seed_assets(db)
            print(f"👉 Sukses menyisipkan {stats['categories_inserted']} Kategori Aset & {stats['assets_inserted']} Titik Koordinat.")
            
        elif args.module == "dataset":
            print("[Modular] Menjalankan Seeder Dataset & Caching...")
            stats = seed_datasets(db)
            print(f"👉 Sukses menyisipkan {stats['datasets_inserted']} Dataset & {stats['rows_inserted']} DataRow.")
            if stats["cache_warmed"]:
                print("👉 Database cache spasial 'stunting' berhasil dipanaskan.")

    except Exception as e:
        db.rollback()
        print("\n❌ [Fatal Error] Terjadi kegagalan saat proses seeding berlangsung!")
        print(f"Detail kesalahan: {str(e)}")
        sys.exit(1)
    finally:
        db.close()
        print("[Core] Koneksi basis data berhasil ditutup dengan aman.\n")

if __name__ == "__main__":
    main()