# app/models/models.py
from sqlalchemy import Column, Integer, Float, String, ForeignKey, DateTime, JSON, Text, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base
import datetime

class District(Base):
    """Tabel Master Distrik (Wilayah Administratif Kabupaten Mimika)"""
    __tablename__ = "districts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    
    datasets = relationship("Dataset", back_populates="district")
    # Relasi One-to-One ke DistrictProfile
    profile = relationship("DistrictProfile", back_populates="district", uselist=False, cascade="all, delete-orphan")
    
    # Relasi ke Asset
    assets = relationship("Asset", back_populates="district")

class DistrictProfile(Base):
    """Tabel Master Data Statis untuk Informasi Profil Distrik (Pop-up Peta)"""
    __tablename__ = "district_profiles"
    id = Column(Integer, primary_key=True, index=True)
    district_id = Column(Integer, ForeignKey("districts.id"), unique=True, nullable=False)
    
    luas_wilayah = Column(Float, nullable=True) # Dalam km persegi
    jumlah_penduduk = Column(Integer, nullable=True)
    deskripsi = Column(Text, nullable=True)
    batas_wilayah = Column(Text, nullable=True) # Misal: "Utara: Kab. A, Selatan: Laut Arafura"
    
    # [FASE 1] Menyimpan array URL foto wilayah untuk fitur Cinematic Theater
    images = Column(JSON, nullable=True) 
    
    district = relationship("District", back_populates="profile")

class Source(Base):
    """Tabel OPD atau Sumber Data (BPS, Dinas Kesehatan, dll)"""
    __tablename__ = "sources"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    type = Column(String) # bps, opd, kementerian, dll
    
    datasets = relationship("Dataset", back_populates="owner")
    assets = relationship("Asset", back_populates="owner")

class Category(Base):
    """Tabel Kategori Data (Kependudukan, Kesehatan, dll)"""
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    template_url = Column(String, nullable=True)
    
    datasets = relationship("Dataset", back_populates="category")

class SourceType(Base):
    """Tabel Jenis Sumber"""
    __tablename__ = "source_type"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    
    datasets = relationship("Dataset", back_populates="sourceType")

class Dataset(Base):
    """Tabel Metadata File (Judul, Nama Kolom asli)"""
    __tablename__ = "datasets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String, nullable=False)
    dataset_type = Column(String)

    source_id = Column(Integer, ForeignKey("sources.id"))
    category_id = Column(Integer, ForeignKey("categories.id"))
    source_type_id = Column(Integer, ForeignKey("source_type.id"))
    
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=True)

    year = Column(Integer)
    period = Column(String)
    description = Column(Text)
    view_count = Column(Integer, default=0)
    image_url = Column(String, nullable=True)
    file_url = Column(String, nullable=True)

    total_rows = Column(Integer, default=0)
    quality_score = Column(Float, default=0.0) 
    last_ingest_stats = Column(JSON) 
    headers = Column(JSON) 
    
    status = Column(String, default="pending")
    structure_type = Column(String, default="tabular")
    spatial_status = Column(String, default="mapped")
    needs_review = Column(Boolean, default=False) 
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    owner = relationship("Source", back_populates="datasets")
    rows = relationship("DataRow", back_populates="dataset", cascade="all, delete-orphan")
    category = relationship("Category", back_populates="datasets")
    sourceType = relationship("SourceType", back_populates="datasets")
    uploader = relationship("User")
    district = relationship("District", back_populates="datasets")

class DataRow(Base):
    """Tabel Penampung Isi File yang Sudah Bersih"""
    __tablename__ = "data_rows"
    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"))
    content = Column(JSON) 
    row_hash = Column(String, index=True)

    dataset = relationship("Dataset", back_populates="rows")

class Survey(Base):
    __tablename__ = "surveys"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String)
    location = Column(String)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    questions = Column(JSON) 
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    responses = relationship("SurveyResponse", back_populates="survey", cascade="all, delete-orphan")

class SurveyResponse(Base):
    __tablename__ = "survey_responses"
    id = Column(Integer, primary_key=True, index=True)
    survey_id = Column(Integer, ForeignKey("surveys.id"))
    answers = Column(JSON)
    email = Column(String, nullable=True) 
    submitted_at = Column(DateTime, default=datetime.datetime.utcnow)

    survey = relationship("Survey", back_populates="responses")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    role = Column(String, default="user")
    email = Column(String, unique=True, index=True)
    is_active = Column(Boolean, default=True)

    # [FASE 1] Relasi ke aset untuk melacak uploader (Creator Pattern)
    assets = relationship("Asset", back_populates="uploader")

# ============================================================================
# [NEW] DOMAIN SPASIAL: MANAJEMEN ASET / GEOTAGGING
# ============================================================================

class AssetCategory(Base):
    """Tabel Master Kategori Aset Fisik (Rumah Sakit, Sekolah, Jembatan, dll)"""
    __tablename__ = "asset_categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    
    icon_url = Column(String, nullable=True)
    color = Column(String, default="#0071bc")
    
    assets = relationship("Asset", back_populates="category")

class Asset(Base):
    """Tabel Penampung Data Aset Fisik / Hasil GeoTagging dari OPD"""
    __tablename__ = "assets"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    
    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False) # Siapa yang menginput (Authorisasi)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False) # OPD Pemilik
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=True) # Wilayah
    category_id = Column(Integer, ForeignKey("asset_categories.id"), nullable=False) # Tipe Aset
    
    # Spasial Coordinates (Crucial for GIS)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    
    # Media & Penjelasan
    image_url = Column(String, nullable=True) # Tetap dipertahankan untuk backward compatibility (cover utama)
    images = Column(JSON, nullable=True) # [FASE 1] Array URL Foto (Multiupload Cloudinary)
    description = Column(Text, nullable=True)
    
    # Dynamic Metadata
    details = Column(JSON, nullable=True)
    
    # Status Moderasi
    status = Column(String, default="pending") # pending | approved | rejected
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relasi
    uploader = relationship("User", back_populates="assets")
    owner = relationship("Source", back_populates="assets")
    district = relationship("District", back_populates="assets")
    category = relationship("AssetCategory", back_populates="assets")

class SpatialCache(Base):
    """Tabel Cache Agregasi untuk mempercepat load Peta Choropleth"""
    __tablename__ = "spatial_caches"
    id = Column(Integer, primary_key=True, index=True)
    indicator_key = Column(String, index=True, nullable=False) # misal: 'stunting', 'pdrb'
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)
    value = Column(Float, nullable=False)
    last_calculated = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    district = relationship("District")