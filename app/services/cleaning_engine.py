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
            
            if not s_val: return None
            
            final_num = float(s_val)
            # Kembalikan sebagai Integer jika tidak ada komanya (.0)
            return int(final_num) if final_num.is_integer() else final_num
        except:
            return str(val).strip() # Balikkan string jika gagal konversi

    @staticmethod
    def clean_and_align(file_contents: bytes, filename: str = ""):
        """Membaca file dan melakukan pembersihan data secara otomatis"""
        ext = filename.split('.')[-1].lower() if filename else ""
        file_buffer = io.BytesIO(file_contents)
        
        try:
            # logic pembacaan berdasarkan ekstensi
            if ext == 'xls':
                try:
                    df_raw = pd.read_excel(file_buffer, header=None, engine='xlrd')
                except Exception as e:
                    file_buffer.seek(0)
                    try:
                        dfs = pd.read_html(file_buffer, header=None)
                        if not dfs: raise ValueError("Tidak ditemukan tabel HTML")
                        df_raw = max(dfs, key=lambda d: d.shape[0] * d.shape[1])
                    except ValueError:
                        file_buffer.seek(0)
                        df_raw = pd.read_csv(file_buffer, header=None, sep='\t')

            elif ext == 'xlsx':
                df_raw = pd.read_excel(file_buffer, header=None, engine='openpyxl')
            elif ext == 'csv':
                df_raw = pd.read_csv(file_buffer, header=None)
            else:
                try:
                    df_raw = pd.read_excel(file_buffer, header=None)
                except:
                    file_buffer.seek(0)
                    df_raw = pd.read_csv(file_buffer, header=None)
        except Exception as e:
            raise Exception(f"Gagal membaca isi file {ext if ext else ''}: {str(e)}")

        # === PERBAIKAN 1: Netralkan struktur kolom dari bawaan HTML/Excel ===
        df_raw.columns = range(df_raw.shape[1]) 

        # === PERBAIKAN 3: Bersihkan spasi kosong dengan aman (hanya pada kolom string) ===
        df_raw = df_raw.replace({'\xa0': ' '}, regex=True)
        # Terapkan regex hapus spasi kosong hanya pada tipe data object/string agar tidak error
        for col in df_raw.select_dtypes(include=['object']).columns:
            df_raw[col] = df_raw[col].replace(r'^\s*$', np.nan, regex=True)

        # ===============================
        # 1. DETEKSI & GABUNG MULTI-HEADER
        # ===============================
        
        first_row_idx = 0
        for i, row in df_raw.iterrows():
            if row.count() > 1:
                first_row_idx = i
                break
        
        header_candidates = df_raw.iloc[first_row_idx : first_row_idx + 3].copy()
        header_candidates = header_candidates.ffill(axis=1)

        header_rows_count = 1
        # === PERBAIKAN 2: Logika Header lebih cerdas agar data teks tidak tertelan ===
        for i in range(1, len(header_candidates)):
            row = header_candidates.iloc[i]
            numeric_count = pd.to_numeric(row, errors='coerce').notnull().sum()
            
            # Cek apakah ada data dalam baris ini yang karakternya panjang (indikasi ini adalah data riil, bukan header)
            has_long_text = any(isinstance(val, str) and len(str(val)) > 30 for val in row.dropna())

            # Jika banyak angka ATAU ada teks yang panjang, HENTIKAN (ini adalah baris data!)
            if numeric_count > 1 or has_long_text:
                break
            else:
                header_rows_count = i + 1

        # Gabungkan baris-baris header menjadi satu string
        combined_headers = []
        actual_header_df = header_candidates.iloc[:header_rows_count]
        
        for col_idx in range(len(actual_header_df.columns)):
            levels = actual_header_df.iloc[:, col_idx].dropna().astype(str).tolist()
            clean_levels = [str(l).strip() for l in levels if str(l).strip().lower() not in ['nan', 'unnamed']]
            combined_name = "_".join(dict.fromkeys(clean_levels))
            
            # Jika kolom tidak punya nama sama sekali setelah dibersihkan
            if not combined_name: combined_name = f"unnamed_{col_idx}"
            combined_headers.append(combined_name)

        data_start_idx = first_row_idx + header_rows_count
        
        while data_start_idx < len(df_raw) and df_raw.iloc[data_start_idx].dropna().empty:
            data_start_idx += 1

        df = df_raw.iloc[data_start_idx:].reset_index(drop=True)
        df.columns = combined_headers

        # ==================================
        # 2. PEMBERSIHAN KOLOM & BARIS KOSONG
        # ==================================
        
        # Hapus kolom yang namanya kosong sama sekali
        df = df.loc[:, [bool(str(c).strip()) for c in df.columns]]
        
        # Bersihkan nama kolom menggunakan fungsi yang sudah Anda buat
        def clean_header_name(col):
            if not col: return "unnamed_column"
            c = str(col).strip().lower()
            c = re.sub(r'[^a-z0-9_]', '_', c)
            return re.sub(r'_+', '_', c).strip('_')

        df.columns = [clean_header_name(c) for c in df.columns]

        # Hapus kolom Unnamed yang tidak sengaja terbentuk
        df = df.loc[:, ~df.columns.str.contains('unnamed')]
        
        # Hitung baris kosong sebelum dihapus
        empty_rows_count = df.isna().all(axis=1).sum()
        df = df.dropna(how='all').reset_index(drop=True)

        # =========================
        # 5. PROSES DATA
        # =========================
        cleaned_records = []
        total_empty_cells = 0 

        for _, row in df.iterrows():
            row_dict = row.to_dict()
            processed_row = {}

            for key, val in row_dict.items():
                if pd.isna(val) or val == "" or str(val).strip().lower() in ['nan', 'n/a', '-', 'null']:
                    processed_row[key] = None
                    total_empty_cells += 1
                    continue

                # Cek apakah kolom ini kemungkinan berisi angka
                numeric_keywords = [
                    'jumlah', 'nilai', 'harga', 'total',
                    'value', 'biaya', 'realisasi',
                    'target', 'skor', 'tahun', 'kapasitas', 'luas'
                ]

                if any(kw in key for kw in numeric_keywords):
                    res = CleaningEngine.clean_numeric_smart(val)
                else:
                    res = CleaningEngine.clean_text_smart(val)

                if res is None:
                    total_empty_cells += 1
                
                processed_row[key] = res

            # =========================
            # 6. HASH (UNTUK DETEKSI DUPLIKAT)
            # =========================
            row_json = json.dumps(processed_row, sort_keys=True, default=str)
            row_hash = hashlib.md5(row_json.encode()).hexdigest()

            cleaned_records.append({
                "content": processed_row,
                "row_hash": row_hash
            })

        return df.columns.tolist(), cleaned_records, int(empty_rows_count), int(total_empty_cells)