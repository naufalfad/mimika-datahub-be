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

class DistrictProfile(Base):
    """Tabel Master Data Statis untuk Informasi Profil Distrik (Pop-up Peta)"""
    __tablename__ = "district_profiles"
    id = Column(Integer, primary_key=True, index=True)
    # unique=True memastikan 1 Distrik hanya memiliki 1 Profil
    district_id = Column(Integer, ForeignKey("districts.id"), unique=True, nullable=False)
    
    luas_wilayah = Column(Float, nullable=True) # Dalam km persegi
    jumlah_penduduk = Column(Integer, nullable=True)
    deskripsi = Column(Text, nullable=True)
    batas_wilayah = Column(Text, nullable=True) # Misal: "Utara: Kab. A, Selatan: Laut Arafura"
    
    district = relationship("District", back_populates="profile")

class Source(Base):
    """Tabel OPD atau Sumber Data (BPS, Dinas Kesehatan, dll)"""
    __tablename__ = "sources"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    type = Column(String) # bps, opd, kementerian, dll
    
    datasets = relationship("Dataset", back_populates="owner")

class Category(Base):
    """Tabel Kategori Data (Kependudukan, Kesehatan, dll)"""
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    template_url = Column(String, nullable=True)
    
    datasets = relationship("Dataset", back_populates="category")

class SourceType(Base):
    """Tabel Jenis Sumber ())"""
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
    
    # Penambahan Foreign Key untuk Relasi Spasial (GIS)
    # nullable=True agar dataset tingkat Kabupaten (non-distrik) tetap dapat disimpan
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=True)

    year = Column(Integer)
    period = Column(String)
    description = Column(Text)
    view_count = Column(Integer, default=0)
    image_url = Column(String, nullable=True)
    file_url = Column(String, nullable=True)
    # merged_image_url = Column(String, nullable=True)

    total_rows = Column(Integer, default=0)
    quality_score = Column(Float, default=0.0) # Skor 0-100
    last_ingest_stats = Column(JSON) # Menyimpan info: {"duplicates": 5, "nulls": 2}
    
    # Kita simpan daftar kolom yang sudah dirapikan di sini (misal: ["nama", "tahun", "jumlah"])
    headers = Column(JSON) 
    
    # Workflow Persetujuan Data
    status = Column(String, default="pending")
    structure_type = Column(String, default="tabular")
    
    # Workflow Karantina Spasial (Fase 4 - Anomaly Handling)
    spatial_status = Column(String, default="mapped") # "mapped" jika dikenali AI, "unmapped" jika gagal dikenali
    needs_review = Column(Boolean, default=False) # Flag penanda butuh intervensi manual dari Admin
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    owner = relationship("Source", back_populates="datasets")
    rows = relationship("DataRow", back_populates="dataset", cascade="all, delete-orphan")
    category = relationship("Category", back_populates="datasets")
    sourceType = relationship("SourceType", back_populates="datasets")
    uploader = relationship("User")
    
    # Penambahan Relationship ke entitas District
    district = relationship("District", back_populates="datasets")

class DataRow(Base):
    """Tabel Penampung Isi File yang Sudah Bersih"""
    __tablename__ = "data_rows"
    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"))
    
    # Isi satu baris file dalam format JSON (Contoh: {"nama": "Mimika Baru", "jumlah": 150})
    # Ini sangat fleksibel untuk jumlah kolom berapapun.
    content = Column(JSON) 
    
    # Hash unik untuk mencegah redundansi (Cek apakah baris isinya sama persis)
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
    # Menyimpan struktur pertanyaan: [{"text": "Puas?", "type": "rating"}, ...]
    questions = Column(JSON) 
    status = Column(String, default="active") # active / closed
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    responses = relationship("SurveyResponse", back_populates="survey", cascade="all, delete-orphan")

class SurveyResponse(Base):
    __tablename__ = "survey_responses"
    id = Column(Integer, primary_key=True, index=True)
    survey_id = Column(Integer, ForeignKey("surveys.id"))
    # Menyimpan jawaban responden: {"pertanyaan_1": "Sangat Puas", "pertanyaan_2": 5}
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