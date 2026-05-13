import os
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()
cloudinary.config( 
  cloud_name = os.getenv("CLOUD_NAME"), 
  api_key = os.getenv("API_KEY"), 
  api_secret = os.getenv("API_SECRET"),
  secure = True
)

def upload_image_to_cloudinary(file_bytes, folder_name):
    """
    Mengupload gambar ke Cloudinary. 
    Cloudinary akan otomatis membuat folder jika belum ada.
    """
    result = cloudinary.uploader.upload(
        file_bytes,
        folder=folder_name,
        use_filename=True,
        unique_filename=True
    )
    # Mengembalikan URL aman dan public_id (format: folder/filename)
    return result.get("secure_url"), result.get("public_id")