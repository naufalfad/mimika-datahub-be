from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.session import engine, Base
from app.api.api_router import api_router

# PENTING: Impor models di sini agar SQLAlchemy mengenali tabel-tabelnya
# from app.models import models 

# # Perintah paksa buat tabel
# print("Sedang membuat tabel...")
# try:
#     Base.metadata.create_all(bind=engine)
#     print("Tabel berhasil dibuat atau sudah ada.")
# except Exception as e:
#     print(f"Gagal membuat tabel: {e}")

app = FastAPI(title="Mimika DataHub - Versi 1")

# Setting CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def root():
    return {"message": "Mimika DataHub API is Running"}