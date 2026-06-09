# app/services/atlas_service.py
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Float, desc
from app.models import models
import re

class AtlasService:
    """
    Information Expert: Bertanggung jawab melakukan agregasi data spasial 
    langsung dari kolom JSON di tabel data_rows.
    """

    @staticmethod
    def get_indicator_data(db: Session, indicator_key: str):
        """
        Melakukan agregasi (rata-rata) nilai indikator tertentu per distrik.
        Contoh: indicator_key = 'stunting' atau 'jumlah_penduduk'
        """
        
        # 1. Menyiapkan query untuk mengambil data dari JSON 'content'
        # PERBAIKAN: Menggunakan .astext.cast(Float) bawaan SQLAlchemy 
        # karena kolom di database adalah tipe JSON, bukan JSONB.
        
        query = (
            db.query(
                models.District.name.label("district_name"),
                func.avg(
                    cast(
                        models.DataRow.content[indicator_key].astext,
                        Float
                    )
                ).label("average_value")
            )
            .join(models.Dataset, models.Dataset.id == models.DataRow.dataset_id)
            .join(models.District, models.District.id == models.Dataset.district_id)
            .filter(models.Dataset.status == "approved") # Hanya data yang sudah divalidasi
            .filter(models.DataRow.content[indicator_key].astext.isnot(None))
            .group_by(models.District.name)
        )

        results = query.all()

        # 2. Melakukan post-processing untuk mencocokkan format key di Frontend (MimikaMap.tsx)
        formatted_data = {}
        for row in results:
            clean_key = row.district_name.lower().replace(" ", "")
            formatted_data[clean_key] = round(row.average_value, 2) if row.average_value else 0

        return formatted_data

    @staticmethod
    def get_available_indicators(db: Session):
        """
        Mengambil daftar kolom (headers) yang tersedia dari dataset yang sudah di-approve.
        """
        latest_datasets = (
            db.query(models.Dataset.headers)
            .filter(models.Dataset.status == "approved")
            .filter(models.Dataset.headers.isnot(None))
            .all()
        )
        
        unique_indicators = set()
        for ds in latest_datasets:
            if ds.headers:
                unique_indicators.update(ds.headers)
        
        return list(unique_indicators)

    @staticmethod
    def get_indicator_metadata(indicator_key: str):
        """
        [PURE FABRICATION ENGINE]
        Memberikan metadata tambahan seperti satuan, narasi, skema warna,
        dan arah evaluasi data (direction) berdasarkan key indikator yang diminta.
        """
        indicator_key_lower = indicator_key.lower().strip()
        
        # 1. Registrasi Metadata Statis untuk Indikator Utama Bappeda
        metadata_map = {
            "stunting": {
                "title": "Prevalensi Stunting",
                "unit": "%",
                "description": "Persentase balita yang mengalami gangguan pertumbuhan (stunting) berdasarkan standar WHO.",
                "color_scheme": "Reds",
                "direction": "negative"  # <--- MAKIN TINGGI PERSENTASE = MAKIN BURUK (KRITIS) [3]
            },
            "jumlah_penduduk": {
                "title": "Kepadatan Penduduk",
                "unit": "Jiwa",
                "description": "Total populasi penduduk yang menetap di wilayah distrik terkait.",
                "color_scheme": "Blues",
                "direction": "positive"  # <--- MAKIN TINGGI JUMLAH = MAKIN MEMADAI (NORMAL) [3]
            },
            "pdrb": {
                "title": "Produk Domestik Regional Bruto",
                "unit": "Miliar Rp",
                "description": "Nilai tambah bruto yang timbul dari seluruh sektor ekonomi di distrik tersebut.",
                "color_scheme": "Greens",
                "direction": "positive"  # <--- MAKIN TINGGI NILAI EKONOMI = MAKIN MAJU (NORMAL) [3]
            }
        }
        
        # Jika kunci indikator terdaftar secara statis, kembalikan metadatanya langsung
        if indicator_key_lower in metadata_map:
            return metadata_map[indicator_key_lower]
            
        # 2. [PROTECTED VARIATIONS] Smart Fallback Engine:
        # Jika OPD mengunggah dataset tak terdaftar, tebak arah indikator secara cerdas
        # berdasarkan kecocokan semantik pola kata kunci negatif.
        negative_patterns = [
            r"stunting", r"miskin", r"kemiskinan", r"pengangguran", r"buruk", 
            r"sakit", r"mati", r"kematian", r"rusak", r"putus_sekolah", 
            r"lumpuh", r"kurang_gizi", r"gizi_buruk", r"kriminal"
        ]
        
        guessed_direction = "positive"
        for pattern in negative_patterns:
            if re.search(pattern, indicator_key_lower):
                guessed_direction = "negative"
                break
                
        # Menentukan visualisasi skema warna default berdasarkan arah perbandingan data
        default_color = "Reds" if guessed_direction == "negative" else "Blues"
        
        return {
            "title": indicator_key.replace("_", " ").title(),
            "unit": "-",
            "description": "Indikator pembangunan sektoral Kabupaten Mimika.",
            "color_scheme": default_color,
            "direction": guessed_direction  # [3]
        }