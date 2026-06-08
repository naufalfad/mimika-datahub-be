# app/api/api_router.py
from fastapi import APIRouter
from app.api.endpoints import (
    categories, sources, datasets, data_ingest, data_view, 
    dashboard, brida, auth, source_type, users, monitoring, gis, atlas,
    assets # [REFACTOR] Mengimpor endpoint baru untuk Aset Fisik
)

api_router = APIRouter()

# Grouping Router
api_router.include_router(users.router, prefix="/users", tags=["0. Admin - User Management"])
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["0. Admin - Monitoring OPD"])

# Kluster Master Data
api_router.include_router(categories.router, prefix="/categories", tags=["0. Master - Categories"])
api_router.include_router(source_type.router, prefix="/source-type", tags=["0. Master - Source Type"])
api_router.include_router(sources.router, prefix="/sources", tags=["1. Master - Sources (OPD)"])
api_router.include_router(datasets.router, prefix="/datasets", tags=["2. Master - Datasets"])

# [REFACTOR] Register Modul Baru: Manajemen Aset Fisik / GeoTagging
api_router.include_router(assets.router, prefix="/assets", tags=["2.5 Master - Aset Fisik (GeoTagging)"])

# Kluster Proses & Katalog
api_router.include_router(data_ingest.router, prefix="/ingest", tags=["3. Process - Upload & Cleaning"])
api_router.include_router(data_view.router, prefix="/view", tags=["4. Access - View & Catalog"])

# Kluster Analytics & GIS
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["5. Analytics - Dashboard"])
api_router.include_router(gis.router, prefix="/gis", tags=["5. Analytics - GIS / Spatial"])
api_router.include_router(brida.router, prefix="/brida", tags=["6. Analytics - Survey"])

# Kluster Eksternal & Scrollytelling
api_router.include_router(atlas.router, prefix="/atlas", tags=["Atlas Scrollytelling"])

# Kluster Auth
api_router.include_router(auth.router, prefix="/auth", tags=["7. Auth - Login"])