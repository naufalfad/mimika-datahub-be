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

# Schema untuk Dataset (Judul Tabel)
class DatasetCreate(BaseModel):
    title: str
    source_id: int
    category_id: int
    year: int
    period: str
    description: Optional[str] = None

class DatasetOut(DatasetCreate):
    id: int
    headers: Optional[List[str]] = None
    total_rows: int
    quality_score: float
    created_at: datetime
    class Config:
        from_attributes = True

# Schema untuk Respon Upload
class UploadResponse(BaseModel):
    status: str
    dataset_id: int
    headers_found: List[str]
    new_records: int
    duplicates_ignored: int

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

