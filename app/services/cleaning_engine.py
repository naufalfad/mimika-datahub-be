import pandas as pd
import io
import hashlib
import json
import re
import numpy as np

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
    def clean_and_align(file_contents: bytes):
        # 1. BACA FILE SECARA RAW (Tanpa asumsi header)
        try:
            try:
                # header=None artinya kita baca semua cell sebagai data mentah
                df_raw = pd.read_excel(io.BytesIO(file_contents), header=None)
            except:
                df_raw = pd.read_csv(io.BytesIO(file_contents), header=None)
        except Exception as e:
            raise Exception(f"Format file tidak didukung: {str(e)}")

        # 2. LOGIKA DETEKSI HEADER DINAMIS (Scanning Top-Left)
        # Mencari baris pertama yang memiliki data paling banyak (asumsi itu header)
        # atau baris pertama yang tidak kosong.
        
        first_row_with_data = 0
        for i, row in df_raw.iterrows():
            # Jika baris ini memiliki lebih dari 1 kolom yang terisi, kita anggap ini start header
            if row.count() > 1: 
                first_row_with_data = i
                break
        
        # Potong dataframe dari baris yang ditemukan
        df_raw = df_raw.iloc[first_row_with_data:].reset_index(drop=True)
        
        # Jadikan baris pertama tersebut sebagai header
        df_raw.columns = df_raw.iloc[0]
        df = df_raw[1:].reset_index(drop=True)

        # 3. DETEKSI KOLOM KOSONG DI KIRI (Jika mulai dari kolom B, C, dst)
        # Hapus kolom yang namanya "Unnamed" atau NaN
        df = df.loc[:, df.columns.notna()]
        df = df.loc[:, ~df.columns.astype(str).str.contains('^Unnamed')]

        # 4. PENYELARASAN NAMA HEADER (Snake Case)
        def clean_header_name(col):
            c = str(col).strip().lower()
            c = re.sub(r'[^a-z0-9_]', '_', c)
            return re.sub(r'_+', '_', c).strip('_')

        df.columns = [clean_header_name(c) for c in df.columns]

        # 5. MEMBERSIHKAN DATA KOSONG & DUPLIKAT INTERNAL
        df = df.dropna(how='all') 

        # 6. PROSES DATA PER BARIS
        cleaned_records = []
        for _, row in df.iterrows():
            row_dict = row.to_dict()
            processed_row = {}
            
            for key, val in row_dict.items():
                if pd.isna(val):
                    processed_row[key] = None
                    continue
                
                numeric_keywords = ['jumlah', 'nilai', 'harga', 'total', 'value', 'biaya', 'realisasi', 'target', 'skor', 'tahun']
                if any(kw in key for kw in numeric_keywords):
                    processed_row[key] = CleaningEngine.clean_numeric_smart(val)
                else:
                    processed_row[key] = CleaningEngine.clean_text_smart(val)

            # 7. GENERATE HASH (Anti-Redundan)
            row_json = json.dumps(processed_row, sort_keys=True, default=str)
            row_hash = hashlib.md5(row_json.encode()).hexdigest()

            cleaned_records.append({
                "content": processed_row,
                "row_hash": row_hash
            })

        # 8. DEDUPLIKASI FINAL
        seen_hashes = set()
        final_records = []
        for item in cleaned_records:
            if item["row_hash"] not in seen_hashes:
                final_records.append(item)
                seen_hashes.add(item["row_hash"])

        return df.columns.tolist(), final_records