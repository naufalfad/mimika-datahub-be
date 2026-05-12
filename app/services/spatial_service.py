from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case
from app.models.models import District, Dataset
from typing import Dict, Any

class SpatialService:
    """
    Pure Fabrication Service yang didedikasikan untuk kalkulasi dan agregasi
    data spasial GIS tanpa mengotori domain logic dari dataset maupun core CRUD.
    """

    @staticmethod
    def get_district_stats(db: Session, category_id: int = None, year: int = None) -> Dict[str, int]:
        """
        Melakukan komputasi agregasi total dataset per distrik.
        
        Logika Kritis:
        Kita menggunakan OUTER JOIN dan eksekusi filter di dalam argumen COUNT (case expression).
        Jika kita menggunakan `.filter(Dataset.category_id == X)` di level query utama, 
        Outer Join akan berubah menjadi Inner Join secara otomatis di level SQL, 
        sehingga distrik dengan 0 dataset akan hilang dari Payload Response.
        """
        
        # 1. Bangun kondisi filter untuk kalkulasi kondisional (Dynamic Filtering)
        dataset_filters = []
        if category_id is not None:
            dataset_filters.append(Dataset.category_id == category_id)
        if year is not None:
            dataset_filters.append(Dataset.year == year)
            
        # 2. Definisikan ekspresi agregasi (Jika ada filter, hitung yang match saja. Jika tidak, hitung semua ID)
        if dataset_filters:
            # SQL Equivalent: COUNT(CASE WHEN (dataset.category_id = X AND dataset.year = Y) THEN dataset.id ELSE NULL END)
            aggregation_expr = func.count(
                case(
                    (and_(*dataset_filters), Dataset.id), 
                    else_=None
                )
            ).label("total_data")
        else:
            # SQL Equivalent: COUNT(dataset.id)
            aggregation_expr = func.count(Dataset.id).label("total_data")

        # 3. Eksekusi ORM Query menggunakan Left Outer Join
        query_results = (
            db.query(
                District.name.label("district_name"),
                aggregation_expr
            )
            .outerjoin(Dataset, District.id == Dataset.district_id)
            .group_by(District.name)
            .all()
        )

        # 4. Restrukturisasi hasil ke format Hash Map (Key-Value Dictionary)
        # Format ini menargetkan kompleksitas O(1) di iterasi map frontend.
        # Output: {"Mimika Baru": 150, "Wania": 85, "Agimuga": 0, ...}
        formatted_response = {
            row.district_name: row.total_data for row in query_results
        }

        return formatted_response

    @staticmethod
    def get_detailed_district_stats(db: Session) -> Dict[str, Any]:
        """
        [Opsional/Ekspansi] Metode tambahan untuk menampilkan statistik multivariabel
        Misal: Mengirimkan total baris (rows) atau rata-rata skor kualitas per distrik.
        """
        query_results = (
            db.query(
                District.name.label("district_name"),
                func.count(Dataset.id).label("total_datasets"),
                func.sum(Dataset.total_rows).label("total_rows"),
                func.avg(Dataset.quality_score).label("avg_quality")
            )
            .outerjoin(Dataset, District.id == Dataset.district_id)
            .group_by(District.name)
            .all()
        )

        formatted_response = {}
        for row in query_results:
            formatted_response[row.district_name] = {
                "total_datasets": row.total_datasets or 0,
                "total_rows": row.total_rows or 0,
                "avg_quality": round(row.avg_quality or 0.0, 2)
            }
            
        return formatted_response