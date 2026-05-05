from fastapi import APIRouter
from app.api.endpoints import categories, sources, datasets, data_ingest, data_view, dashboard, brida, auth, dataset_type, source_type

api_router = APIRouter()

# Grouping Router
api_router.include_router(categories.router, prefix="/categories", tags=["0. Master - Categories"])
api_router.include_router(source_type.router, prefix="/source-type", tags=["0. Master - Source Type"])
api_router.include_router(sources.router, prefix="/sources", tags=["1. Master - Sources (OPD)"])
api_router.include_router(datasets.router, prefix="/datasets", tags=["2. Master - Datasets"])
api_router.include_router(data_ingest.router, prefix="/ingest", tags=["3. Process - Upload & Cleaning"])
api_router.include_router(data_view.router, prefix="/view", tags=["4. Access - View & Catalog"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["5. Analytics - Dashboard"])
api_router.include_router(brida.router, prefix="/brida", tags=["6. Analytics - Survey"])
api_router.include_router(auth.router, prefix="/auth", tags=["7. Auth - Login"])