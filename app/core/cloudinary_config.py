# app/core/cloudinary_config.py
import os
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()

# Konfigurasi koneksi ke Cloudinary
cloudinary.config( 
  cloud_name = os.getenv("CLOUD_NAME"), 
  api_key = os.getenv("API_KEY"), 
  api_secret = os.getenv("API_SECRET"),
  secure = True
)

def upload_image_to_cloudinary(file_source, folder_name, resource_type="image", filename=None):
    """
    Mengunggah satu file (file_stream atau bytes) ke Cloudinary.
    """
    upload_options = {
        "folder": folder_name,
        "resource_type": resource_type,
        "use_filename": True,
        "unique_filename": True,
        "invalidate": True 
    }
    
    if resource_type == "raw" and filename:
        upload_options["public_id"] = filename

    result = cloudinary.uploader.upload(file_source, **upload_options)
    return result.get("secure_url"), result.get("public_id")

# ============================================================================
# [FASE 2] FUNGSI MULTI-UPLOAD UNTUK MODE TEATER (GALLERY)
# ============================================================================
def upload_multiple_images_to_cloudinary(file_sources: list, folder_name: str, resource_type="image"):
    """
    Mengunggah banyak file sekaligus ke Cloudinary.
    Menerima list of file_stream/bytes dan mengembalikan array of Secure URLs.
    """
    secure_urls = []
    
    if not file_sources:
        return secure_urls
        
    for file_source in file_sources:
        try:
            url, _ = upload_image_to_cloudinary(file_source, folder_name, resource_type)
            secure_urls.append(url)
        except Exception as e:
            print(f"Peringatan: Gagal mengunggah salah satu gambar ke Cloudinary: {e}")
            # Opsional: Jika 1 gagal, kita raise error atau lanjut?
            # Secara best practice, kita throw exception agar data tidak setengah matang.
            raise Exception(f"Kegagalan unggah media: {str(e)}")
            
    return secure_urls