# app/services/asset_service.py
import json
import os
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from shapely.geometry import Point, shape
from app.models import models
from app.schemas import schemas

class AssetService:
    """
    Pure Fabrication / Controller untuk Modul Aset Spasial.
    Bertanggung jawab atas validasi Geofencing, RBAC, dan Karantina Data.
    """

    @staticmethod
    def _load_geojson():
        """Memuat file batas wilayah Mimika untuk validasi Geofencing (Titik dalam Poligon)."""
        # Sesuaikan path ini dengan letak file GeoJSON Anda di Backend
        filepath = os.path.join(os.getcwd(), "mimika_18_distrik.json")
        if not os.path.exists(filepath):
            # Coba cari di folder static
            filepath = os.path.join(os.getcwd(), "static", "mimika_18_distrik.json")
            if not os.path.exists(filepath):
                return None
                
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def validate_geofence(lat: float, lng: float, district_name: str):
        """
        [PROTECTED VARIATIONS] Mencegah koordinat asal-asalan masuk ke database.
        Mengecek secara matematis apakah titik (lat, lng) berada di dalam Poligon distrik.
        """
        geo_data = AssetService._load_geojson()
        
        if not geo_data:
            print("Warning: mimika_18_distrik.json tidak ditemukan. Melewati validasi Geofencing.")
            return True # Bypass jika file map belum tersedia di server

        target_feature = None
        for feature in geo_data.get("features", []):
            if feature.get("properties", {}).get("district_name", "").lower() == district_name.lower():
                target_feature = feature
                break
        
        if not target_feature:
            raise ValueError(f"Batas wilayah geografis untuk '{district_name}' tidak dikenali oleh sistem.")

        # Shapely menggunakan format spasial X,Y (Longitude, Latitude)
        point = Point(lng, lat)
        polygon = shape(target_feature["geometry"])

        if not polygon.contains(point):
            raise ValueError(
                f"Koordinat yang Anda masukkan (Lat: {lat}, Lng: {lng}) meleset dan "
                f"berada DI LUAR batas administrasi Distrik {district_name}."
            )
        
        return True

    @staticmethod
    def create_asset(db: Session, payload: schemas.AssetCreate, user_id: int, image_urls: list):
        """Mendaftarkan Aset Baru oleh OPD"""
        
        # 1. Validasi Distrik dan Geofencing (Jika ada)
        if payload.district_id:
            district = db.query(models.District).filter(models.District.id == payload.district_id).first()
            if not district:
                raise HTTPException(status_code=404, detail="ID Distrik tidak valid.")
            
            try:
                # Engine Cek Spasial
                AssetService.validate_geofence(payload.lat, payload.lng, district.name)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
                
        # 2. Assign Cover Utama (Backward Compatibility) dan Array Galeri
        primary_image = image_urls[0] if image_urls else None

        # 3. Simpan ke Database dengan Status Karantina ("pending")
        new_asset = models.Asset(
            name=payload.name,
            user_id=user_id,
            source_id=payload.source_id,
            category_id=payload.category_id,
            district_id=payload.district_id,
            lat=payload.lat,
            lng=payload.lng,
            description=payload.description,
            details=payload.details,
            image_url=primary_image,
            images=image_urls,
            status="pending"  # Wajib karantina untuk ditinjau Admin
        )

        db.add(new_asset)
        db.commit()
        db.refresh(new_asset)
        return new_asset

    @staticmethod
    def get_my_assets(db: Session, user_id: int):
        """Mengambil data aset milik OPD yang sedang login (Creator Pattern)"""
        return db.query(models.Asset).filter(models.Asset.user_id == user_id).order_by(models.Asset.created_at.desc()).all()

    @staticmethod
    def get_all_assets_for_admin(db: Session):
        """Mengambil seluruh data aset (Digunakan Admin untuk Moderasi)"""
        return db.query(models.Asset).order_by(models.Asset.created_at.desc()).all()

    @staticmethod
    def get_public_assets(db: Session):
        """Endpoint Publik Explorer: Hanya merender aset yang sudah lulus karantina (approved)"""
        return db.query(models.Asset).filter(models.Asset.status == "approved").all()

    @staticmethod
    def update_asset(db: Session, asset_id: int, payload: schemas.AssetUpdate, user_id: int, new_image_urls: list = None):
        """Update data aset dan trigger validasi Geofencing ulang"""
        asset = db.query(models.Asset).filter(models.Asset.id == asset_id).first()
        if not asset:
            raise HTTPException(status_code=404, detail="Aset tidak ditemukan")
        
        # [RBAC] Validasi Kepemilikan Data
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if user.role != "admin" and asset.user_id != user_id:
            raise HTTPException(status_code=403, detail="Akses Ditolak: Anda tidak memiliki izin untuk mengubah aset ini.")

        update_data = payload.dict(exclude_unset=True)
        
        # Evaluasi Geofencing Jika Koordinat atau Distrik berubah
        new_lat = update_data.get("lat", asset.lat)
        new_lng = update_data.get("lng", asset.lng)
        new_district_id = update_data.get("district_id", asset.district_id)

        if ("lat" in update_data or "lng" in update_data or "district_id" in update_data) and new_district_id:
            district = db.query(models.District).filter(models.District.id == new_district_id).first()
            if district:
                try:
                    AssetService.validate_geofence(new_lat, new_lng, district.name)
                except ValueError as e:
                    raise HTTPException(status_code=400, detail=str(e))

        # Terapkan perubahan teks
        for key, value in update_data.items():
            setattr(asset, key, value)

        # Terapkan perubahan gambar
        if new_image_urls:
            # Karena logic kita replace (bukan append), array images lama ditimpa
            asset.images = new_image_urls
            asset.image_url = new_image_urls[0] if new_image_urls else None

        # [MODERASI] Jika OPD (user) mengupdate data, statusnya dilempar ke 'pending' lagi.
        # Jika Admin yang merubah, status tetap (atau sesuai form payload dari admin).
        if user.role != "admin":
            asset.status = "pending"

        db.commit()
        db.refresh(asset)
        return asset

    @staticmethod
    def moderate_asset(db: Session, asset_id: int, status: str, admin_user: models.User):
        """Ubah status aset (Terima/Tolak). Khusus Admin."""
        if admin_user.role != "admin":
            raise HTTPException(status_code=403, detail="Akses Ditolak.")
            
        if status not in ["approved", "rejected", "pending"]:
            raise HTTPException(status_code=400, detail="Kode status moderasi tidak valid.")
        
        asset = db.query(models.Asset).filter(models.Asset.id == asset_id).first()
        if not asset:
            raise HTTPException(status_code=404, detail="Aset tidak ditemukan.")
        
        asset.status = status
        db.commit()
        db.refresh(asset)
        return asset

    @staticmethod
    def delete_asset(db: Session, asset_id: int, user_id: int):
        """Hapus Aset"""
        asset = db.query(models.Asset).filter(models.Asset.id == asset_id).first()
        if not asset:
            raise HTTPException(status_code=404, detail="Aset tidak ditemukan.")

        user = db.query(models.User).filter(models.User.id == user_id).first()
        if user.role != "admin" and asset.user_id != user_id:
            raise HTTPException(status_code=403, detail="Akses Ditolak.")

        db.delete(asset)
        db.commit()
        return {"detail": f"Aset '{asset.name}' berhasil dihapus secara permanen."}