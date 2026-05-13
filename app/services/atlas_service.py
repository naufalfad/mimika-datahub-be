from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Float, desc
from app.models import models
import re

class AtlasService:
    """
    Information Expert: Bertanggung jawab melakukan agregasi data spasial 
    langsung dari kolom JSONB di tabel data_rows.
    """

    @staticmethod
    def get_indicator_data(db: Session, indicator_key: str):
        """
        Melakukan agregasi (rata-rata) nilai indikator tertentu per distrik.
        Contoh: indicator_key = 'stunting' atau 'jumlah_penduduk'
        """
        
        # 1. Menyiapkan query untuk mengambil data dari JSONB 'content'
        # Kita menggunakan jsonb_extract_path_text untuk performa maksimal
        # dan melakukan casting ke Float agar bisa dihitung secara matematis.
        
        query = (
            db.query(
                models.District.name.label("district_name"),
                func.avg(
                    cast(
                        func.jsonb_extract_path_text(models.DataRow.content, indicator_key),
                        Float
                    )
                ).label("average_value")
            )
            .join(models.Dataset, models.Dataset.id == models.DataRow.dataset_id)
            .join(models.District, models.District.id == models.Dataset.district_id)
            .filter(models.Dataset.status == "approved") # Hanya data yang sudah divalidasi
            .filter(func.jsonb_extract_path_text(models.DataRow.content, indicator_key).isnot(None))
            .group_by(models.District.name)
        )

        results = query.all()

        # 2. Melakukan post-processing untuk mencocokkan format key di Frontend (MimikaMap.tsx)
        # Frontend mengharapkan key seperti 'mimikabaru' (lowercase, tanpa spasi)
        
        formatted_data = {}
        for row in results:
            # Transformasi nama distrik menjadi slug/key (Contoh: "Mimika Baru" -> "mimikabaru")
            clean_key = row.district_name.lower().replace(" ", "")
            formatted_data[clean_key] = round(row.average_value, 2)

        return formatted_data

    @staticmethod
    def get_available_indicators(db: Session):
        """
        Mengambil daftar kolom (headers) yang tersedia dari dataset yang sudah di-approve.
        Digunakan untuk validasi indikator apa saja yang bisa ditampilkan di Atlas.
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
        Pure Fabrication: Memberikan metadata tambahan seperti satuan atau narasi
        berdasarkan key indikator yang diminta.
        """
        metadata_map = {
            "stunting": {
                "title": "Prevalensi Stunting",
                "unit": "%",
                "description": "Persentase balita yang mengalami gangguan pertumbuhan (stunting) berdasarkan standar WHO.",
                "color_scheme": "Reds" # Gradasi merah (Bahaya)
            },
            "jumlah_penduduk": {
                "title": "Kepadatan Penduduk",
                "unit": "Jiwa",
                "description": "Total populasi penduduk yang menetap di wilayah distrik terkait.",
                "color_scheme": "Blues" # Gradasi biru (Netral)
            },
            "pdrb": {
                "title": "Produk Domestik Regional Bruto",
                "unit": "Miliar Rp",
                "description": "Nilai tambah bruto yang timbul dari seluruh sektor ekonomi di distrik tersebut.",
                "color_scheme": "Greens" # Gradasi hijau (Ekonomi)
            }
        }
        
        return metadata_map.get(indicator_key.lower(), {
            "title": indicator_key.replace("_", " ").title(),
            "unit": "-",
            "description": "Indikator pembangunan sektoral Kabupaten Mimika.",
            "color_scheme": "YlGnBu"
        })