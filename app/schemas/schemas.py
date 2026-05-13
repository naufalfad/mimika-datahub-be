from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from datetime import datetime

class CategoryCreate(BaseModel):
    name: str

class CategoryOut(BaseModel):
    id: int
    name: str
    template_url: Optional[str] = None
    class Config:
        from_attributes = True

# Schema untuk Source (OPD)
class SourceBase(BaseModel):
    name: str
    type: str
    icon: Optional[str] = "fa-database"

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

# Schema untuk Dataset (Judul Tabel)
class DatasetCreate(BaseModel):
    title: str
    source_id: int
    category_id: int
    source_type_id: int
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
    class Config:
        from_attributes = True

# Schema untuk Respon Upload
class Stats(BaseModel):
    inserted: int
    duplicates: int
    empty: int
    total: int
    quality_score: float


class UploadResponse(BaseModel):
    status: str
    dataset_id: int
    headers_found: list[str]
    stats: Stats

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
    role: str = "user" # 'admin' atau 'user'
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None # Opsional, diisi jika ingin ganti password
    role: Optional[str] = None
    is_active: Optional[bool] = None

class UserOut(UserBase):
    id: int
    class Config:
        from_attributes = True

# --- MONITORING SCHEMAS ---
class OPDMonitoringDetail(BaseModel):
    user_id: int
    opd_name: str
    last_submit: Optional[datetime] = None
    status: str # 'Lengkap', 'Kurang', 'Belum Kirim'
    progress: str # 'n/12'
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
    template_url: Optional[str] # Diambil dari relasi kategori
    category_name: str
    source_name: str
    created_at: datetime

    class Config:
        from_attributes = True