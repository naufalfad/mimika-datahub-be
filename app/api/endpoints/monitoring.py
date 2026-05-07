from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from app.db.session import get_db
from app.models import models
from app.schemas import schemas
from app.api import deps
from typing import List

router = APIRouter()

@router.get("/opd-summary", response_model=schemas.MonitoringSummaryResponse)
def get_opd_monitoring(db: Session = Depends(get_db), admin: models.User = Depends(deps.get_admin_user)):
    now = datetime.now()
    current_month = now.month
    current_year = now.year

    # 1. Ambil semua User dengan role 'user'
    users_opd = db.query(models.User).filter(models.User.role == "user").all()
    total_opd = len(users_opd)
    
    lengkap_count = 0
    kurang_count = 0
    belum_kirim_count = 0
    table_data = []

    for u in users_opd:
        # Hitung jumlah upload disetujui bulan ini
        uploads = db.query(models.Dataset).filter(
            models.Dataset.user_id == u.id,
            extract('month', models.Dataset.created_at) == current_month,
            extract('year', models.Dataset.created_at) == current_year,
            models.Dataset.status == "approved"
        )
        
        count = uploads.count()
        last_data = uploads.order_by(models.Dataset.created_at.desc()).first()
        avg_q = db.query(func.avg(models.Dataset.quality_score)).filter(models.Dataset.user_id == u.id).scalar() or 0

        # Tentukan Status
        if count >= 12:
            status = "Lengkap"
            lengkap_count += 1
        elif count > 0:
            status = "Kurang"
            kurang_count += 1
        else:
            status = "Belum Kirim"
            belum_kirim_count += 1

        table_data.append({
            "user_id": u.id,
            "opd_name": u.full_name,
            "last_submit": last_data.created_at if last_data else None,
            "status": status,
            "progress": f"{count}/12",
            "upload_count": count,
            "avg_quality": round(float(avg_q), 2),
            "email": u.email,
            "username": u.username
        })

    # 2. Logika Tren 6 Bulan Terakhir (Line Chart)
    line_chart = []
    for i in range(5, -1, -1):
        target_date = now - timedelta(days=i*30)
        m = target_date.month
        y = target_date.year
        
        # Hitung berapa OPD yang 'Lengkap' pada bulan tersebut
        complete_this_month = 0
        for u in users_opd:
            c = db.query(models.Dataset).filter(
                models.Dataset.user_id == u.id,
                extract('month', models.Dataset.created_at) == m,
                extract('year', models.Dataset.created_at) == y,
                models.Dataset.status == "approved"
            ).count()
            if c >= 12: complete_this_month += 1
        
        percentage = (complete_this_month / total_opd * 100) if total_opd > 0 else 0
        line_chart.append({"bulan": target_date.strftime("%b"), "persentase": round(percentage, 2)})

    return {
        "cards": {
            "total_opd": total_opd,
            "lengkap": lengkap_count,
            "kurang": kurang_count,
            "belum_kirim": belum_kirim_count
        },
        "pie_chart": {
            "Lengkap": lengkap_count,
            "Kurang": kurang_count,
            "Belum Kirim": belum_kirim_count
        },
        "line_chart": line_chart,
        "table_data": table_data
    }

# Endpoint Aksi: Reminder
@router.post("/remind/{user_id}")
def send_reminder(user_id: int, db: Session = Depends(get_db), admin: models.User = Depends(deps.get_admin_user)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user: raise HTTPException(status_code=404, detail="User tidak ditemukan")
    
    # Di sini nantinya bisa integrasi ke Email atau WA blast
    return {"message": f"Reminder notifikasi berhasil dikirim ke {user.full_name} ({user.email})"}