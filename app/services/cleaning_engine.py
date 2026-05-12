import pandas as pd
import io
import hashlib
import json
import re
import numpy as np
from rapidfuzz import process, fuzz

class CleaningEngine:
    @staticmethod
    def clean_text_smart(text: str) -> str:
        """Pembersihan teks: spasi tanda baca, double space, dan title case"""
        if not text or pd.isna(text):
            return None
        
        text = str(text)
        # 1. Perbaikan spasi tanda baca: "," atau "." harus diikuti spasi (contoh: "A,B" -> "A, B")
        text = re.sub(r'([,.])(?!\s|$)', r'\1 ', text)
        
        # 2. Hapus spasi SEBELUM tanda baca (contoh: "Data , Baru" -> "Data, Baru")
        text = re.sub(r'\s+([,.])', r'\1', text)
        
        # 3. Hapus spasi ganda di tengah kalimat
        text = re.sub(r'\s+', ' ', text)
        
        # 4. Trim dan ubah ke Title Case agar rapi
        return text.strip().title()

    @staticmethod
    def clean_numeric_smart(val: any) -> any:
        """Pembersihan angka: menangani format Rp, ,00, dan pemisah ribuan Indonesia"""
        if pd.isna(val) or val == "" or val is None:
            return None
        
        # Jika sudah int/float murni, langsung kembalikan
        if isinstance(val, (int, float, np.integer, np.floating)):
            return float(val)
        
        s_val = str(val).strip().lower()

        # 1. Hilangkan simbol mata uang dan karakter non-penting
        s_val = s_val.replace('rp', '').replace('idr', '').replace('$', '').replace(' ', '')

        # 2. Tangani format ekor desimal kosong ",00" atau ".00"
        if s_val.endswith(',00') or s_val.endswith('.00'):
            s_val = s_val[:-3]

        try:
            # 3. Logika Pemisah Ribuan (Indonesia: Titik ribuan, Koma desimal)
            if '.' in s_val and ',' in s_val:
                # Contoh: 1.250.000,50 -> 1250000.50
                s_val = s_val.replace('.', '').replace(',', '.')
            elif ',' in s_val:
                # Cek jika koma berfungsi sebagai desimal (misal 150,5)
                parts = s_val.split(',')
                if len(parts[-1]) <= 2: # Asumsi desimal biasanya 1-2 angka
                    s_val = s_val.replace(',', '.')
                else:
                    # Jika lebih dari 2 angka, mungkin itu salah ketik ribuan pakai koma
                    s_val = s_val.replace(',', '')
            else:
                # Bersihkan sisa karakter non-angka kecuali titik desimal
                s_val = re.sub(r'[^\d.]', '', s_val)
            
            final_num = float(s_val)
            # Kembalikan sebagai Integer jika tidak ada komanya (.0)
            return int(final_num) if final_num.is_integer() else final_num
        except:
            return str(val).strip() # Balikkan string jika gagal konversi

    @staticmethod
    def fuzzy_match_district(val: any) -> str:
        """
        AI Parser: Menggunakan Levenshtein Distance untuk mendeteksi nama distrik.
        Akan mereturn nama standar jika similarity >= 80%.
        """
        if pd.isna(val) or val is None or str(val).strip() == "":
            return None
            
        text = str(val).strip().lower()
        
        # 1. Strip Prefiks Umum (Misal: "Kec.", "Kecamatan", "Distrik", "Wilayah")
        text = re.sub(r'^(kecamatan|kec\.|distrik|wilayah)\s*', '', text).strip()
        
        # 2. Kamus Absolut 18 Distrik di Mimika (Sesuai rujukan spasial GeoJSON)
        master_districts = [
            "Mimika Baru", "Kuala Kencana", "Tembagapura", "Wania", "Iwaka",
            "Kwamki Narama", "Mimika Timur", "Mimika Tengah", "Mimika Barat",
            "Agimuga", "Jila", "Jita", "Mimika Timur Jauh", "Mimika Barat Jauh",
            "Mimika Barat Tengah", "Amar", "Hoya", "Alama"
        ]
        
        # 3. Ekstraksi kemiripan dengan algoritma WRatio (Rapidfuzz)
        match = process.extractOne(text, master_districts, scorer=fuzz.WRatio)
        
        if match:
            best_match, score, _ = match
            if score >= 80: # Threshold aman untuk toleransi typo dari OPD
                return best_match
                
        # Jika tidak ada kecocokan absolut, kembalikan ke pembersihan teks standar.
        return CleaningEngine.clean_text_smart(val)

    @staticmethod
    def clean_and_align(file_contents: bytes):
        try:
            try:
                df_raw = pd.read_excel(io.BytesIO(file_contents), header=None)
            except:
                df_raw = pd.read_csv(io.BytesIO(file_contents), header=None)
        except Exception as e:
            raise Exception(f"Format file tidak didukung: {str(e)}")

        # =========================
        # 1. DETEKSI HEADER
        # =========================
        first_row_with_data = 0
        for i, row in df_raw.iterrows():
            if row.count() > 1:
                first_row_with_data = i
                break

        df_raw = df_raw.iloc[first_row_with_data:].reset_index(drop=True)
        df_raw.columns = df_raw.iloc[0]
        df = df_raw[1:].reset_index(drop=True)

        # =========================
        # 2. BERSIHKAN KOLOM
        # =========================
        df = df.loc[:, df.columns.notna()]
        df = df.loc[:, ~df.columns.astype(str).str.contains('^Unnamed')]

        def clean_header_name(col):
            c = str(col).strip().lower()
            c = re.sub(r'[^a-z0-9_]', '_', c)
            return re.sub(r'_+', '_', c).strip('_')

        df.columns = [clean_header_name(c) for c in df.columns]

        # =========================
        # 3. HITUNG BARIS KOSONG (SEBELUM DIHAPUS)
        # =========================
        empty_rows_count = df.isna().all(axis=1).sum()

        # =========================
        # 4. HAPUS BARIS KOSONG (BIAR TIDAK MASUK DB)
        # =========================
        df = df.dropna(how='all')

        # =========================
        # 5. PROSES DATA DENGAN SMART EXTRACTION
        # =========================
        cleaned_records = []

        # Scanner Heuristik untuk deteksi kolom spasial
        spatial_regex = re.compile(r'(?i)(distrik|wilayah|kecamatan|daerah|lokasi)')
        numeric_keywords = [
            'jumlah', 'nilai', 'harga', 'total', 'value', 'biaya', 
            'realisasi', 'target', 'skor', 'tahun'
        ]

        for _, row in df.iterrows():
            row_dict = row.to_dict()
            processed_row = {}
            spatial_match_name = None # Marker penampung spasial

            for key, val in row_dict.items():
                if pd.isna(val):
                    processed_row[key] = None
                    continue

                # Pipeline Eksekusi Berdasarkan Konteks Header
                if spatial_regex.search(str(key)):
                    # Intervensi GIS: Normalisasi nama wilayah menggunakan AI (Fuzzy Match)
                    normalized_val = CleaningEngine.fuzzy_match_district(val)
                    processed_row[key] = normalized_val
                    spatial_match_name = normalized_val # Simpan marker untuk di-extract oleh Controller
                elif any(kw in str(key).lower() for kw in numeric_keywords):
                    processed_row[key] = CleaningEngine.clean_numeric_smart(val)
                else:
                    processed_row[key] = CleaningEngine.clean_text_smart(val)

            # Suntikkan Marker Spasial rahasia untuk Grouping & Melting di Ingest Controller
            processed_row["_spatial_mapping"] = spatial_match_name

            # =========================
            # 6. HASH (UNTUK DETEKSI DUPLIKAT)
            # =========================
            row_json = json.dumps(processed_row, sort_keys=True, default=str)
            row_hash = hashlib.md5(row_json.encode()).hexdigest()

            cleaned_records.append({
                "content": processed_row,
                "row_hash": row_hash
            })

        return df.columns.tolist(), cleaned_records, int(empty_rows_count)