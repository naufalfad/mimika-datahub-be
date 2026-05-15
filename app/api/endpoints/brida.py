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
from datetime import datetime

@router.post("/generate-dataset/{survey_id}")
def generate_dataset(survey_id: int, db: Session = Depends(get_db)):
    survey = db.query(models.Survey).filter(models.Survey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey tidak ditemukan.")
        
    responses = db.query(models.SurveyResponse).filter(models.SurveyResponse.survey_id == survey_id).all()
    if not responses:
        raise HTTPException(status_code=400, detail="Belum ada responden untuk survey ini.")

    # 1. Setup Source BRIDA (seperti sebelumnya)
    brida_source = db.query(models.Source).filter(models.Source.name == "BRIDA").first()
    if not brida_source:
        brida_source = models.Source(name="BRIDA", type="brida")
        db.add(brida_source)
        db.commit()
        db.refresh(brida_source)

    # 2. Kumpulkan Headers dengan Aman
    all_keys = set()
    for res in responses:
        if res.answers:
            all_keys.update(res.answers.keys())

    # 3. Ekstrak Tahun dari Survey (Jika tidak ada, pakai tahun saat ini)
    survey_year = survey.start_date.year if survey.start_date else datetime.utcnow().year

    # 4. Buat Dataset dengan Metadata yang LENGKAP
    new_dataset = models.Dataset(
        title=f"Hasil Survey: {survey.title}",
        description=survey.description,          # <-- Menarik deskripsi survey
        dataset_type="pemerintah",            # <-- Penanda khusus untuk dataset survey
        year=survey_year,                        # <-- Memasukkan tahun
        source_id=brida_source.id,
        headers=list(all_keys),
        total_rows=len(responses),               # <-- Menyimpan jumlah responden langsung
        status="approved",                      # <-- Asumsi langsung tayang di katalog
        # user_id=current_user.id                # (Buka comment ini jika endpoint diproteksi login admin)
    )
    db.add(new_dataset)
    db.commit()
    db.refresh(new_dataset)

    # 5. Insert DataRow (beserta menghitung data sukses masuk)
    inserted_rows = 0
    for res in responses:
        content = res.answers
        row_json = json.dumps(content, sort_keys=True)
        row_hash = hashlib.md5(row_json.encode()).hexdigest()
        
        # Opsional: Cek jika ada hash yang sama persis (jika perlu)
        # existing_row = db.query(models.DataRow).filter(models.DataRow.row_hash == row_hash, models.DataRow.dataset_id == new_dataset.id).first()
        # if not existing_row:
        
        new_row = models.DataRow(
            dataset_id=new_dataset.id,
            content=content,
            row_hash=row_hash
        )
        db.add(new_row)
        inserted_rows += 1
    
    # 6. Update last_ingest_stats (Bagus untuk audit sistem)
    new_dataset.last_ingest_stats = {
        "total_responses_processed": len(responses),
        "successful_inserts": inserted_rows,
        "generated_at": datetime.utcnow().isoformat()
    }
    
    db.commit()
    
    return {
        "status": "success", 
        "dataset_id": new_dataset.id, 
        "message": f"Dataset survey berhasil dibuat dengan {inserted_rows} baris data."
    }

    # ==========================================
# TAMBAHAN: API UNTUK MENGAMBIL DATA SURVEY
# ==========================================

# 4. AMBIL SEMUA DAFTAR SURVEY (Untuk halaman Daftar Survey di Dashboard)
@router.get("/list")
def get_all_surveys(db: Session = Depends(get_db)):
    surveys = db.query(models.Survey).order_by(models.Survey.created_at.desc()).all()
    return surveys

# ==========================================
# 1. TAMBAHKAN ENDPOINT STATS (TARUH DI ATAS /{survey_id})
# ==========================================
@router.get("/stats")
def get_survey_stats(db: Session = Depends(get_db)):
    # Hitung total survey
    total_surveys = db.query(models.Survey).count()
    
    # Hitung survey aktif (asumsi ada field is_active atau cek tanggal)
    # Jika tidak ada field is_active, bisa disesuaikan logikanya
    active_surveys = db.query(models.Survey).count() 
    
    # Hitung total semua jawaban (responses) dari semua survey
    total_responses = db.query(models.SurveyResponse).count()
    
    # Hitung dataset yang sudah terbentuk dari survey (Source BRIDA)
    # Kita cari ID source BRIDA dulu
    brida_source = db.query(models.Source).filter(models.Source.name == "BRIDA").first()
    datasets_count = 0
    if brida_source:
        datasets_count = db.query(models.Dataset).filter(models.Dataset.source_id == brida_source.id).count()

    return {
        "total": total_surveys,
        "active": active_surveys,
        "responses": total_responses,
        "datasets": datasets_count
    }

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