import os
from pathlib import Path    

# --- KONFIGURASI ---
TARGET_DIRECTORY = "C:\\Users\\ASUS\\Documents\\gthub\\mimika-datahub-be"
OUTPUT_FILE = "C:\\Users\\ASUS\\Documents\\gthub\\mimika-datahub-be\\mimika-be.txt"

# Tambahkan pengecualian direktori lintas ekosistem
EXCLUDE_DIRS = {
    "node_modules", ".git", "dist", "build", "__pycache__", ".vscode", ".idea", "venv",
    ".next", ".nuxt", ".svelte-kit", ".angular", ".cache", ".parcel-cache", ".vite",
    ".docusaurus", ".astro", ".storybook", ".turbo",
    "coverage", ".nyc_output", "jspm_packages", "bower_components", "elm-stuff",
    ".dart_tool", ".pub", ".pub-cache", "DerivedData", "android", "ios", "web/build",
    "vendor", "storage", "public/build", "public/storage", "assets",
    ".venv", "env", ".mypy_cache", ".pytest_cache", ".tox", ".nox",
    "build", "dist",
    ".gradle", ".mvn", "target", "out", ".settings", ".cxx",
    "bin", "obj", ".vs", "packages",
    "bin", "pkg", "vendor",
    "target",
    "Pods", "DerivedData",
    ".bundle", "log", "tmp", "vendor/bundle", 
    "dist-newstyle", "cmake-build-debug", "cmake-build-release", ".terraform",
}

# Tambahkan pengecualian file lintas ekosistem (nama persis)
EXCLUDE_FILES = {
    ".DS_Store", "package-lock.json", "yarn.lock", "Readme.md", "README.txt", "README.md",

    # Lockfiles & manifest lain
    "pnpm-lock.yaml", "bun.lockb", "composer.lock", "pubspec.lock",
    "Gemfile.lock", "Pipfile.lock", "poetry.lock", "Cargo.lock",
    "mix-manifest.json", "vite-manifest.json",

    # Env (tanpa wildcard → tambahkan varian umum)
    ".env.development", ".env.production", ".env.test", ".env.example",

    # Tools/metadata umum
    ".flutter-plugins", ".flutter-plugins-dependencies", ".packages",
    ".phpunit.result.cache",

    # Android/iOS/Xcode umpan balik build (file)
    "Generated.xcconfig", "LocalProperties.kt",
}

# Opsional: Jika Anda HANYA ingin menyalin ekstensi tertentu, isi daftar ini.
# Contoh: INCLUDE_EXTENSIONS = {".ts", ".tsx", ".css"}
# Jika dibiarkan kosong, skrip akan menyalin SEMUA file teks yang ditemukan.
INCLUDE_EXTENSIONS = {}

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

    print(f"Memproses folder: {target_path.resolve()}")

    files_to_process = []
    for file_path in sorted(target_path.rglob("*")):
        if any(part in EXCLUDE_DIRS for part in file_path.parts):
            continue

        if file_path.is_file() and file_path.name not in EXCLUDE_FILES:
            if INCLUDE_EXTENSIONS and file_path.suffix not in INCLUDE_EXTENSIONS:
                continue
            if not is_binary(file_path):
                files_to_process.append(file_path)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("="*50 + "\n")
        f.write("STRUKTUR FOLDER (DAFTAR FILE)\n")
        f.write("="*50 + "\n")
        if not files_to_process:
            f.write("Tidak ada file yang ditemukan.\n")
        else:
            for file_path in files_to_process:
                relative_path = file_path.relative_to(target_path.parent)
                f.write(str(relative_path).replace("\\", "/"))
                f.write("\n")
        f.write("\n\n")

        f.write("="*50 + "\n")
        f.write("ISI KODE\n")
        f.write("="*50 + "\n\n")
        
        for file_path in files_to_process:
            try:
                content = file_path.read_text("utf-8", errors="ignore")
                relative_path = file_path.relative_to(target_path.parent)
                
                f.write(f"--- START FILE: {str(relative_path).replace(os.sep, '/')} ---\n")
                f.write(content)
                f.write(f"\n--- END FILE: {str(relative_path).replace(os.sep, '/')} ---\n\n")
                print(f"-> Menyalin konten: {relative_path}")
            except Exception as e:
                print(f"-> Gagal membaca: {relative_path} ({e})")

    print(f"\nProses selesai! Output disimpan di '{OUTPUT_FILE}'.")

if __name__ == "__main__":
    main()
