from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from datetime import datetime

class CategoryCreate(BaseModel):
    name: str

class CategoryOut(BaseModel):
    id: int
    name: str
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
    answers: Dict[str, Any]

class UserOut(BaseModel):
    id: int
    username: str
    full_name: Optional[str]
    email: Optional[str] # Tambah ini
    role: str
    is_active: bool
    class Config:
        from_attributes = True