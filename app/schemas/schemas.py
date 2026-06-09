# app/schemas/schemas.py
from pydantic import BaseModel, field_validator
from typing import List, Optional, Any, Dict
from datetime import datetime

# --- GIS / SPATIAL SCHEMAS ---
class DistrictProfileBase(BaseModel):
    luas_wilayah: Optional[float] = None
    jumlah_penduduk: Optional[int] = None
    deskripsi: Optional[str] = None
    batas_wilayah: Optional[str] = None
    images: Optional[List[str]] = [] # [FIX] Mendukung array foto dengan default kosong

class DistrictProfileCreate(DistrictProfileBase):
    district_id: int

class DistrictProfileUpdate(DistrictProfileBase):
    pass

class DistrictProfileOut(DistrictProfileBase):
    id: int
    class Config:
        from_attributes = True

class DistrictBase(BaseModel):
    name: str

class DistrictCreate(DistrictBase):
    pass

class DistrictOut(DistrictBase):
    id: int
    profile: Optional[DistrictProfileOut] = None 
    class Config:
        from_attributes = True

class SpatialStatResponse(BaseModel):
    district_name: str
    total_dataset: int
    total_rows: Optional[int] = None
    avg_quality: Optional[float] = None

# --- CATEGORY SCHEMAS ---
class CategoryCreate(BaseModel):
    name: str

class CategoryOut(BaseModel):
    id: int
    name: str
    template_url: Optional[str] = None
    class Config:
        from_attributes = True

# --- SOURCE SCHEMAS ---
class SourceBase(BaseModel):
    name: str
    type: str

class SourceCreate(SourceBase):
    pass

class SourceOut(SourceBase):
    id: int
    class Config:
        from_attributes = True

class SourceTypeCreate(BaseModel):
    name: str

class SourceTypeOut(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

# --- DATASET SCHEMAS ---
class DatasetCreate(BaseModel):
    title: str
    source_id: int
    category_id: int
    source_type_id: int
    district_id: Optional[int] = None 
    year: int
    period: str
    dataset_type: str
    description: Optional[str] = None

class DatasetOut(DatasetCreate):
    id: int
    user_id: Optional[int]
    status: str
    headers: Optional[List[str]] = None
    total_rows: int
    quality_score: float
    created_at: datetime
    category: CategoryOut
    sourceType: SourceTypeOut
    district: Optional[DistrictOut] = None 
    class Config:
        from_attributes = True

# --- UPLOAD SCHEMAS ---
class Stats(BaseModel):
    inserted: int
    duplicates: int
    empty_rows: int
    empty_cells: int
    total: int
    quality_score: float

class UploadResponse(BaseModel):
    status: str
    dataset_id: int
    headers_found: list[str]
    stats: Stats

# --- SURVEY SCHEMAS ---
class SurveyCreate(BaseModel):
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    questions: List[Dict[str, Any]]
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class SurveyResponseCreate(BaseModel):
    survey_id: int
    email: Optional[str] = None
    answers: Dict[str, Any]

# --- USER SCHEMAS ---
class UserBase(BaseModel):
    username: str
    email: str
    full_name: str
    role: str = "user" 
    is_active: bool = True
    
    # [INTEGRASI OPD-USER BINDING] Menambahkan referensi instansi ke properti user dasar [1]
    source_id: Optional[int] = None # [1]

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None 
    role: Optional[str] = None
    is_active: Optional[bool] = None
    
    # [INTEGRASI OPD-USER BINDING] Mendukung update parameter instansi di halaman Manajemen Akun [1]
    source_id: Optional[int] = None # [1]

class UserOut(UserBase):
    id: int
    class Config:
        from_attributes = True

# --- MONITORING SCHEMAS ---
class OPDMonitoringDetail(BaseModel):
    user_id: int
    opd_name: str
    last_submit: Optional[datetime] = None
    status: str 
    progress: str 
    upload_count: int
    avg_quality: float
    email: Optional[str]
    username: str

class MonitoringSummaryResponse(BaseModel):
    cards: Dict[str, Any]
    pie_chart: Dict[str, int]
    line_chart: List[Dict[str, Any]]
    table_data: List[OPDMonitoringDetail]

class FilterItem(BaseModel):
    id: int
    name: str
    count: int

class SidebarStats(BaseModel):
    categories: List[FilterItem]
    sources: List[FilterItem]
    source_types: List[FilterItem]
    years: List[FilterItem]

class DatasetRecentOut(BaseModel):
    id: int
    title: str
    image_url: Optional[str]
    template_url: Optional[str] 
    category_name: str
    source_name: str
    created_at: datetime
    class Config:
        from_attributes = True

# --- ATLAS / SCROLLYTELLING SCHEMAS ---
class AtlasMetadata(BaseModel):
    title: str
    unit: str
    description: str
    color_scheme: str 

class AtlasIndicatorResponse(BaseModel):
    indicator: str
    metadata: AtlasMetadata
    data: Dict[str, float] 

class AtlasIndicatorMetaBrief(BaseModel):
    key: str
    metadata: AtlasMetadata

# ============================================================================
# [NEW] ASSET / GEOTAGGING SCHEMAS
# ============================================================================

class AssetCategoryBase(BaseModel):
    name: str
    icon_url: Optional[str] = None
    color: Optional[str] = "#0071bc"

class AssetCategoryCreate(AssetCategoryBase):
    pass

class AssetCategoryOut(AssetCategoryBase):
    id: int
    class Config:
        from_attributes = True

class AssetBase(BaseModel):
    name: str
    source_id: int
    category_id: int
    district_id: Optional[int] = None
    lat: float
    lng: float
    description: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class AssetCreate(AssetBase):
    """
    Skema untuk validasi input sebelum membuat aset.
    Sengaja tidak memuat user_id dan images karena akan ditangani internal via Controller di API.
    """
    pass

class AssetUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[int] = None
    district_id: Optional[int] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    description: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    status: Optional[str] = None # Admin berhak memperbarui status moderasi

class AssetOut(AssetBase):
    """Skema balikan API (Response DTO)"""
    id: int
    user_id: int
    status: str
    image_url: Optional[str] = None
    images: Optional[List[str]] = [] # [FIX DARI QA] Menjamin properti images selalu return array (walau kosong)
    created_at: datetime
    
    category: AssetCategoryOut 
    owner: Optional[SourceOut] = None
    district: Optional[DistrictOut] = None
    
    # [FIX DARI QA] Interceptor untuk memanipulasi data NULL dari SQLAlchemy
    @field_validator('status', mode='before')
    @classmethod
    def default_status(cls, v):
        if v is None:
            return "pending"
        return v
    
    class Config:
        from_attributes = True