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

def upload_image_to_cloudinary(file_source, folder_name, resource_type="image", filename=None):
    """
    file_source bisa berupa file_stream atau bytes.
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