import os
from pathlib import Path

# --- KONFIGURASI ---
# Sesuaikan TARGET_DIRECTORY ke path backend Python kamu
TARGET_DIRECTORY = r"C:\Users\PC\Documents\Dev\mimika-datahub\mimika-datahub-be"
OUTPUT_FILE = r"C:\Users\PC\Documents\Dev\mimika-datahub\mimika-datahub-be\mimika-be-hybrid.txt"

# Folder yang BOLEH diambil (Whitelist)
ALLOWED_DIRS = {"src", "app", "models", "controllers", "services", "utils"}
# Folder yang HARAM hukumnya (Double-Lock)
FORBIDDEN_DIRS = {"venv", ".venv", "env", "__pycache__", ".git", "dist", "build", ".pytest_cache"}

# Ekstensi yang relevan untuk Python
INCLUDE_EXTENSIONS = {".py", ".json", ".sql", ".yaml", ".ini"}

def is_binary(file_path: Path) -> bool:
    try:
        with open(file_path, 'rb') as f:
            return b'\x00' in f.read(512)
    except Exception:
        return True

def main():
    target_path = Path(TARGET_DIRECTORY)
    if not target_path.is_dir():
        print(f"Error: Folder '{TARGET_DIRECTORY}' tidak ditemukan.")
        return

    files_to_process = []
    
    print("Memproses backend Python (Hybrid Mode)...")
    for file_path in target_path.rglob("*"):
        # Double Lock: Pastikan tidak ada folder terlarang
        if any(part in FORBIDDEN_DIRS for part in file_path.parts):
            continue
            
        # Whitelist: Hanya ambil yang di ALLOWED_DIRS atau file root yang relevan (seperti main.py)
        is_allowed = any(part in ALLOWED_DIRS for part in file_path.parts)
        is_root_py = file_path.parent == target_path and file_path.suffix == ".py"
        
        if (is_allowed or is_root_py) and file_path.is_file():
            if file_path.suffix in INCLUDE_EXTENSIONS:
                if not is_binary(file_path):
                    files_to_process.append(file_path)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("=== BACKEND STRUCTURE & CODE (PYTHON) ===\n\n")
        for file_path in sorted(files_to_process):
            relative_path = file_path.relative_to(target_path)
            try:
                content = file_path.read_text("utf-8", errors="ignore")
                f.write(f"\n--- FILE: {relative_path} ---\n")
                f.write(content)
                f.write("\n")
                print(f"-> Menyalin: {relative_path}")
            except Exception as e:
                print(f"-> Gagal baca {relative_path}: {e}")

    print(f"\nSelesai! Backend hybrid tersimpan di: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()