from fastapi import APIRouter, Depends
from sqlalchemy import extract
from datetime import datetime
from app.db.session import get_db
from app.models import models

router = APIRouter()

@router.get("/main-stats")
def get_dashboard_main_stats(db: Session = Depends(get_db)):
    # 1. Kartu Statistik
    total_datasets = db.query(models.Dataset).filter(models.Dataset.status == "approved").count()
    total_sources = db.query(models.Source).count()
    active_users = db.query(models.User).filter(models.User.is_active == True).count()
    avg_quality = db.query(func.avg(models.Dataset.quality_score)).filter(models.Dataset.status == "approved").scalar() or 0

    # 2. Dataset Terbaru (5 terakhir)
    recent_datasets = db.query(models.Dataset).filter(models.Dataset.status == "approved")\
                        .order_by(models.Dataset.created_at.desc()).limit(5).all()

    # 3. Dataset Populer (Berdasarkan view_count terbanyak)
    popular_datasets = db.query(models.Dataset).filter(models.Dataset.status == "approved")\
                         .order_by(models.Dataset.view_count.desc()).limit(5).all()

    # 4. Tren Quality Score Per Bulan (6 bulan terakhir)
    # Query ini mengambil rata-rata skor kualitas dikelompokkan per bulan
    trend_query = db.query(
        extract('month', models.Dataset.created_at).label('month'),
        func.avg(models.Dataset.quality_score).label('avg_score')
    ).filter(models.Dataset.status == "approved")\
     .group_by('month').order_by('month').all()
    
    quality_trend = [{"bulan": int(t.month), "skor": round(float(t.avg_score), 2)} for t in trend_query]

    # 5. Status Kirim OPD Bulan Ini (Target 12 per bulan)
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    opd_status = []
    sources = db.query(models.Source).all()
    
    for s in sources:
        upload_count = db.query(models.Dataset).filter(
            models.Dataset.source_id == s.id,
            extract('month', models.Dataset.created_at) == current_month,
            extract('year', models.Dataset.created_at) == current_year
        ).count()
        
        target = 12
        persentase = round((upload_count / target) * 100, 2)
        
        opd_status.append({
            "opd_name": s.name,
            "terkirim": upload_count,
            "target": target,
            "persentase": f"{persentase}%",
            "status": "Lengkap" if upload_count >= target else "Belum Lengkap"
        })

    return {
        "cards": {
            "total_dataset": total_datasets,
            "total_sumber": total_sources,
            "user_aktif": active_users,
            "rata_rata_kualitas": f"{round(float(avg_quality), 2)}%"
        },
        "recent": recent_datasets,
        "popular": popular_datasets,
        "quality_trend": quality_trend,
        "opd_monthly_monitoring": opd_status
    }