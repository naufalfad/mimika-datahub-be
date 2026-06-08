# app/api/endpoints/assets.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import json

from app.db.session import get_db
from app.models import models
from app.schemas import schemas
from app.api import deps
from app.services.asset_service import AssetService
from app.core.cloudinary_config import upload_multiple_images_to_cloudinary

router = APIRouter()

# ==========================================
# 1. KATEGORI ASET
# ==========================================

@router.post("/categories", response_model=schemas.AssetCategoryOut)
def create_asset_category(
    cat_in: schemas.AssetCategoryCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user) 
):
    """Menambahkan kategori aset baru (Contoh: Rumah Sakit, Jembatan, dll)"""
    existing = db.query(models.AssetCategory).filter(models.AssetCategory.name == cat_in.name).first()
    if existing:
        return existing
        
    new_cat = models.AssetCategory(**cat_in.dict())
    db.add(new_cat)
    db.commit()
    db.refresh(new_cat)
    return new_cat

@router.get("/categories", response_model=List[schemas.AssetCategoryOut])
def list_asset_categories(db: Session = Depends(get_db)):
    """Mengambil daftar seluruh kategori aset (Digunakan oleh Form Frontend)"""
    return db.query(models.AssetCategory).all()

# ==========================================
# 2. MANAJEMEN ASET (CRUD DENGAN MULTI-UPLOAD)
# ==========================================

@router.post("/", response_model=schemas.AssetOut)
async def create_asset(
    name: str = Form(...),
    source_id: int = Form(...),
    category_id: int = Form(...),
    lat: float = Form(...),
    lng: float = Form(...),
    district_id: Optional[int] = Form(None),
    description: Optional[str] = Form(None),
    details: Optional[str] = Form(None), # Dikirim sebagai JSON String dari FE
    images: List[UploadFile] = File(None), # [FASE 2] Mendukung upload banyak gambar
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Endpoint untuk membuat Aset Fisik / GeoTagging baru.
    Mendukung upload multiple gambar ke Cloudinary dan metadata dinamis (details).
    """
    # 1. Parsing Dynamic Metadata (details) dari String ke Dictionary
    parsed_details = {}
    if details:
        try:
            parsed_details = json.loads(details)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Format 'details' harus berupa JSON string yang valid.")

    # 2. Kumpulkan file gambar yang valid (tidak kosong)
    valid_images = []
    if images:
        for img in images:
            if img.filename and img.file:
                valid_images.append(img.file)

    # 3. Upload Gambar ke Cloudinary (Jika Ada)
    image_urls = []
    if valid_images:
        try:
            # Gunakan fungsi multi-upload dari Fase 2
            image_urls = upload_multiple_images_to_cloudinary(
                file_sources=valid_images, 
                folder_name="mimika_datahub/assets"
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Gagal mengunggah foto aset: {str(e)}")

    # 4. Susun Payload Pydantic
    payload = schemas.AssetCreate(
        name=name,
        source_id=source_id,
        category_id=category_id,
        district_id=district_id,
        lat=lat,
        lng=lng,
        description=description,
        details=parsed_details
    )
    
    # 5. Serahkan ke Pure Fabrication (AssetService)
    # Ini melindungi Router dari logika validasi geofencing yang kompleks
    return AssetService.create_asset(db, payload, current_user.id, image_urls)


@router.put("/{asset_id}", response_model=schemas.AssetOut)
async def update_asset(
    asset_id: int,
    name: str = Form(...),
    source_id: int = Form(...),
    category_id: int = Form(...),
    lat: float = Form(...),
    lng: float = Form(...),
    district_id: Optional[int] = Form(None),
    description: Optional[str] = Form(None),
    details: Optional[str] = Form(None),
    images: List[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Endpoint untuk melakukan Update data Aset.
    Pintar: Jika image tidak dikirim (None), foto lama akan dipertahankan.
    """
    parsed_details = {}
    if details:
        try:
            parsed_details = json.loads(details)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Format 'details' harus berupa JSON string yang valid.")

    # Ekstrak file valid
    valid_images = []
    if images:
        for img in images:
            if img.filename and img.file:
                valid_images.append(img.file)

    image_urls = []
    if valid_images:
        try:
            image_urls = upload_multiple_images_to_cloudinary(
                file_sources=valid_images, 
                folder_name="mimika_datahub/assets"
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Gagal mengunggah foto aset baru: {str(e)}")

    payload = schemas.AssetUpdate(
        name=name,
        source_id=source_id,
        category_id=category_id,
        district_id=district_id,
        lat=lat,
        lng=lng,
        description=description,
        details=parsed_details
    )
    
    return AssetService.update_asset(db, asset_id, payload, current_user.id, image_urls)


@router.patch("/{asset_id}/moderate", response_model=schemas.AssetOut)
def moderate_asset(
    asset_id: int,
    status: str = Form(...),
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(deps.get_admin_user)
):
    """Endpoint bagi Admin Bappeda untuk menerima/menolak Aset (Moderation Gate)"""
    return AssetService.moderate_asset(db, asset_id, status, admin_user)


@router.get("/my-assets", response_model=List[schemas.AssetOut])
def get_my_assets(db: Session = Depends(get_db), current_user: models.User = Depends(deps.get_current_user)):
    """Mengambil daftar aset untuk tabel manajemen di dashboard OPD."""
    return AssetService.get_my_assets(db, current_user.id)


@router.get("/all", response_model=List[schemas.AssetOut])
def get_all_assets(db: Session = Depends(get_db), admin_user: models.User = Depends(deps.get_admin_user)):
    """Endpoint khusus Administrator (Super Admin) untuk meja moderasi."""
    return AssetService.get_all_assets_for_admin(db)


@router.delete("/{asset_id}")
def delete_asset(asset_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(deps.get_current_user)):
    """Menghapus data aset fisik"""
    return AssetService.delete_asset(db, asset_id, current_user.id)

# ==========================================
# 3. ENGINE EKSPLORER SPASIAL (PUBLIC)
# ==========================================

@router.get("/public")
def get_public_assets(db: Session = Depends(get_db)):
    """
    Polymorphic Transformer:
    Mengambil data dari database relasional dan menyusun ulang bentuknya (Transform)
    menjadi Dictionary Grouping yang 100% kompatibel dengan komponen Frontend.
    Hanya mengembalikan data yang statusnya 'approved'.
    """
    assets = AssetService.get_public_assets(db)
    grouped_assets = {}
    
    for asset in assets:
        if not asset.owner: 
            continue
            
        opd_name = asset.owner.name
        opd_slug = opd_name.lower().replace(" ", "_")
        
        if opd_slug not in grouped_assets:
            grouped_assets[opd_slug] = []
            
        grouped_assets[opd_slug].append({
            "id": f"asset_{asset.id}",
            "name": asset.name,
            "type": asset.category.name if asset.category else "Umum",
            "lat": float(asset.lat),
            "lng": float(asset.lng),
            "image_url": asset.image_url,
            "images": asset.images or [], # Pastikan properti array images terkirim
            "details": asset.details or {},
            "config": {
                "color": asset.category.color if asset.category else "#0071bc",
                "iconUrl": asset.category.icon_url if asset.category and asset.category.icon_url else "/icons/markers/office.svg"
            }
        })
        
    return grouped_assets