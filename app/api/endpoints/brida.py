from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import models
from app.schemas import schemas
import hashlib
import json

router = APIRouter()

# 1. BUAT SURVEY BARU
@router.post("/create")
def create_survey(survey_in: schemas.SurveyCreate, db: Session = Depends(get_db)):
    new_survey = models.Survey(**survey_in.dict())
    db.add(new_survey)
    db.commit()
    db.refresh(new_survey)
    return new_survey

# 2. SUBMIT JAWABAN (Ditembak saat responden mengisi form)
@router.post("/submit-response")
def submit_response(res_in: schemas.SurveyResponseCreate, db: Session = Depends(get_db)):
    # Logika untuk standarisasi anonimitas
    # Jika email isinya "-", string kosong "", atau "anonim", kita ubah jadi None
    clean_email = res_in.email.strip() if res_in.email else None
    if clean_email in ["-", "", "anonim", "anonymous"]:
        clean_email = None

    new_res = models.SurveyResponse(
        survey_id=res_in.survey_id,
        email=clean_email,     # Simpan email yang sudah dibersihkan
        answers=res_in.answers
    )
    db.add(new_res)
    db.commit()
    return {"status": "success", "message": "Terima kasih, jawaban Anda telah tersimpan."}

# 3. GENERATE DATASET (Fitur Otomatisasi Bab IX)
@router.post("/generate-dataset/{survey_id}")
def generate_dataset(survey_id: int, db: Session = Depends(get_db)):
    # A. Ambil data survey dan semua jawabannya
    survey = db.query(models.Survey).filter(models.Survey.id == survey_id).first()
    responses = db.query(models.SurveyResponse).filter(models.SurveyResponse.survey_id == survey_id).all()
    
    if not responses:
        raise HTTPException(status_code=400, detail="Belum ada responden untuk survey ini.")

    # B. Pastikan ada Source 'BRIDA'
    brida_source = db.query(models.Source).filter(models.Source.name == "BRIDA").first()
    if not brida_source:
        brida_source = models.Source(name="BRIDA", type="brida", icon="fa-chart-line")
        db.add(brida_source)
        db.commit()
        db.refresh(brida_source)

    # C. Buat Dataset Baru di Katalog Utama
    new_dataset = models.Dataset(
        title=f"Dataset Survey: {survey.title}",
        source_id=brida_source.id,
        headers=list(responses[0].answers.keys()) # Ambil kunci jawaban sebagai header
    )
    db.add(new_dataset)
    db.commit()
    db.refresh(new_dataset)

    # D. Pindahkan setiap jawaban responden menjadi DataRow (bersih & anti-duplikat)
    for res in responses:
        content = res.answers
        row_json = json.dumps(content, sort_keys=True)
        row_hash = hashlib.md5(row_json.encode()).hexdigest()
        
        new_row = models.DataRow(
            dataset_id=new_dataset.id,
            content=content,
            row_hash=row_hash
        )
        db.add(new_row)
    
    db.commit()
    return {"status": "success", "dataset_id": new_dataset.id, "message": "Dataset survey berhasil dipublikasikan!"}

    # ==========================================
# TAMBAHAN: API UNTUK MENGAMBIL DATA SURVEY
# ==========================================

# 4. AMBIL SEMUA DAFTAR SURVEY (Untuk halaman Daftar Survey di Dashboard)
@router.get("/list")
def get_all_surveys(db: Session = Depends(get_db)):
    surveys = db.query(models.Survey).order_by(models.Survey.created_at.desc()).all()
    return surveys

# 5. AMBIL DETAIL SATU SURVEY BESERTA JAWABANNYA (Untuk halaman pengisian form atau hasil analisis)
@router.get("/{survey_id}")
def get_survey_detail(survey_id: int, db: Session = Depends(get_db)):
    survey = db.query(models.Survey).filter(models.Survey.id == survey_id).first()
    
    if not survey:
        raise HTTPException(status_code=404, detail="Survey tidak ditemukan.")
    
    # Ambil jumlah total responden untuk survey ini
    responses_count = db.query(models.SurveyResponse).filter(models.SurveyResponse.survey_id == survey_id).count()
    
    # Ambil data responses (Opsional: batasi / paginate jika data terlalu besar, untuk sementara di-load semua)
    responses = db.query(models.SurveyResponse).filter(models.SurveyResponse.survey_id == survey_id).all()

    return {
        "survey": survey,
        "total_responses": responses_count,
        "responses": responses
    }