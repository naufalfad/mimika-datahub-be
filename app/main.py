from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.api.api_router import api_router

app = FastAPI(
    title="Mimika DataHub - Versi 1",
    description="Core Backend API with Spatial/GIS Capabilities"
)

# Inisialisasi folder static untuk aset publik jika diperlukan
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Daftar whitelist domain (Disiapkan untuk transisi ke Production)
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    # "https://domain-production-anda.com",
]

# Konfigurasi CORS Middleware
# Saat ini menggunakan ["*"] untuk kelancaran fase development.
# Sangat krusial agar Map Viewer di Frontend bebas melakukan fetch API GIS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Ganti menjadi `allow_origins=origins` saat deploy ke server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrasi Router Utama
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def root():
    return {"message": "Mimika DataHub API is Running"}