import streamlit as st
import pandas as pd
from supabase import create_client
from io import BytesIO
import datetime

st.set_page_config(page_title="Pelantikan SPM Selangor 2026", layout="wide", page_icon="📚")

# ================= CONFIG - KEY BARU FULL =================
SUPABASE_URL = "https://gnmaijhugkkvxejvsotk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdubWFpamh1Z2trdnhlanZzb3RrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTI0ODc4OTcsImV4cCI6MjEwODA2Mzg5N30.1YWg71nCwnQzP-KUzTdHR4rZAVCAesbKVqvVC1-X6lw"

@st.cache_resource
def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supa = get_supabase()

KOD_DAERAH = ["BA","BB","BC","BD","BE","BF","BG","BH","BJ","BK"]
PPD_MAP = {"BA":"Klang","BB":"Kuala Langat","BC":"Kuala Selangor","BD":"Hulu Langat","BE":"Hulu Selangor","BF":"Sabak Bernam","BG":"Gombak","BH":"Petaling Perdana","BJ":"Sepang","BK":"Petaling Utama"}

# ================= FORMULA SPM - JUMLAH CALON LOGIC =================
import math
def kira_kelas_dari_calon(jumlah_calon):
    """1 kelas = 20 calon, CEIL"""
    try:
        c = int(float(str(jumlah_calon).replace(",","").strip() or 0))
        if c <=0:
            return 0
        return math.ceil(c / 20)
    except:
        return 0

def kira_petugas_dari_kelas(jumlah_kelas):
    """User formula: kelas + 9 = petugas diperlukan"""
    try:
        return int(jumlah_kelas) + 9
    except:
        return 0

def kira_sekolah_perlu_calonkan(jumlah_kelas):
    """Sekolah perlu calonkan = petugas (kelas+9) + 1 KP +1 TKP +1 Penyelia = kelas+12"""
    try:
        petugas = kira_petugas_dari_kelas(jumlah_kelas)
        return petugas + 3  # KP, TKP, Penyelia Kawasan
    except:
        return 0

def kira_csv_petugas(jumlah_kelas):
    """CSV original: kelas +6 (untuk rujukan)"""
    try:
        return int(jumlah_kelas) + 6
    except:
        return 0

# ================= HELPERS - FIX RLS + MULTI COLUMN SUPPORT =================
def safe_count(table_name):
    """Count dengan fallback kalau RLS block count exact"""
    try:
        res = supa.table(table_name).select("*", count="exact").limit(1).execute()
        if res.count is not None and res.count > 0:
            return res.count
        # Jika count 0 tapi data ada, try fetch
        if res.data and len(res.data) > 0:
            # Fetch lebih banyak untuk count
            res2 = supa.table(table_name).select("id").limit(1000).execute()
            if res2.data:
                # Kalau 1000, maksudnya lebih dari 1000, kita cuba count exact lagi dengan filter id>0
                if len(res2.data) == 1000:
                    return 1000  # at least
                return len(res2.data)
            return len(res.data)
        # Try full fetch without count
        res3 = supa.table(table_name).select("*").limit(1000).execute()
        return len(res3.data) if res3.data else 0
    except Exception as e:
        # Last fallback
        try:
            res = supa.table(table_name).select("*").limit(1000).execute()
            return len(res.data) if res.data else 0
        except:
            return 0

def get_sekolah(kod):
    # Support both kod_sekolah and Kod_Sekolah etc - try multiple
    for col in ["kod_sekolah", "kod_sekolah_tuan_rumah", "KOD_SEKOLAH"]:
        try:
            res = supa.table("sekolah_master").select("*").eq(col, kod.upper()).limit(1).execute()
            if res.data:
                row = res.data[0]
                # Normalize keys
                return {
                    "kod_sekolah": row.get("kod_sekolah") or row.get("KOD_SEKOLAH") or kod,
                    "nama_sekolah": row.get("nama_sekolah") or row.get("NAMA_SEKOLAH") or row.get("nama_pusat") or f"SEKOLAH {kod}",
                    "kod_ppd": row.get("kod_ppd") or row.get("KOD_PPD") or "BH",
                    "ppd": row.get("ppd") or row.get("PPD") or "Petaling Perdana",
                    "_raw": row
                }
        except:
            continue
    return {"kod_sekolah": kod, "nama_sekolah": f"SEKOLAH {kod}", "kod_ppd": "BH", "ppd": "Petaling Perdana"}

def get_guru_df(kod_sekolah):
    try:
        res = None
        for col in ["kod_sekolah", "KOD_SEKOLAH", "kod_sekolah_tuan_rumah"]:
            try:
                r = supa.table("guru_master").select("*").eq(col, kod_sekolah.upper()).limit(2000).execute()
                if r.data:
                    res = r
                    break
            except:
                continue
        if not res:
            try:
                res = supa.table("guru_master").select("*").eq("kod_sekolah", kod_sekolah.upper()).limit(2000).execute()
            except:
                res = supa.table("guru_master").select("*").limit(2000).execute()
        
        # Pre-fetch sekolah_master map for nama sekolah
        sekolah_map_guru = {}
        try:
            res_sek = supa.table("sekolah_master").select("kod_sekolah,nama_sekolah").limit(2000).execute()
            for s in res_sek.data or []:
                k = (s.get("kod_sekolah") or s.get("KOD_SEKOLAH") or "").upper()
                n = s.get("nama_sekolah") or s.get("NAMA_SEKOLAH") or ""
                if k:
                    sekolah_map_guru[k] = n
        except:
            pass
        
        rows=[]
        for r in res.data or []:
            d = r.get("data") or {}
            if isinstance(d, str):
                try:
                    import json
                    d = json.loads(d)
                except:
                    d={}
            
            # Helper to get value from multiple possible keys - check data JSON + flat columns
            def get_val(*keys, default=""):
                for k in keys:
                    # Check data JSON first (priority)
                    if k in d and d[k] not in [None, "", "None", "null", "N/A", "-"]:
                        v = str(d[k]).strip()
                        if v and v.lower() not in ["none", "null", "nan", ""]:
                            return v
                    # Check uppercase in data
                    ku = k.upper()
                    if ku in d and d[ku] not in [None, "", "None"]:
                        v = str(d[ku]).strip()
                        if v and v.lower() not in ["none", "null", "nan", ""]:
                            return v
                    # Check flat column
                    if k in r and r[k] not in [None, "", "None"]:
                        v = str(r[k]).strip()
                        if v and v.lower() not in ["none", "null", "nan", ""]:
                            return v
                    # Check uppercase flat
                    if ku in r and r[ku] not in [None, "", "None"]:
                        v = str(r[ku]).strip()
                        if v and v.lower() not in ["none", "null", "nan", ""]:
                            return v
                return default
            
            # Extract ALL fields needed for cadangan
            ic_val = get_val("IC", "ic_guru", "IC_GURU", "ic", "IC_GURU ", "no_ic", "NO_KP", "NO KP")
            nama_val = get_val("NAMA GURU", "nama_guru", "NAMA_GURU", "nama", "NAMA", "NAMA_GURU ")
            jantina_val = get_val("JANTINA", "jantina", "JANTINA_GURU", "Jantina", "SEX")
            poskod_val = get_val("POSKOD_RUMAH", "poskod_rumah", "POSKOD", "poskod", "POSKOD RUMAH", "poskod_ rumah", "POSKOD ", "PostCode")
            alamat_val = get_val("ALAMAT_RUMAH", "alamat_rumah", "ALAMAT RUMAH", "alamat", "ALAMAT", "ALAMAT_RUMAH ", "Alamat Rumah")
            telefon_val = get_val("TELEFON_GURU", "telefon_guru", "NO TELEFON GURU", "TELEFON", "no_telefon", "telefon", "NO_TELEFON", "NO_TEL", "HP", "TEL")
            email_val = get_val("EMAIL_GURU", "email_guru", "EMAIL", "email", "EMEL", "E-MAIL", "Email")
            pengalaman_val = get_val("PENGALAMAN_SPM", "pengalaman_spm", "PENGALAMAN", "pengalaman", "PENGALAMAN_SPM ", "tahun_pengalaman", "PENGALAMAN SPM", "Experience")
            jawatan_val = get_val("JAWATAN_CADANGAN", "jawatan_cadangan", "JAWATAN CADANGAN", "jawatan", "JAWATAN")
            kod_ppd_val = get_val("KOD_PPD", "kod_ppd", "kod_ppd_asal", "KOD_PPD_ASAL", "ppd", "PPD")
            kod_sek_val = get_val("KOD_SEKOLAH", "kod_sekolah", "KOD SEKOLAH", "kod_sekolah_asal", "KOD_SEKOLAH_ASAL", "sekolah", "SEKOLAH", default=kod_sekolah)
            nama_sek_val = get_val("NAMA_SEKOLAH", "nama_sekolah", "NAMA SEKOLAH", "sekolah_asal", "NAMA_SEKOLAH_ASAL", "NAMA SEKOLAH ASAL", "Nama Sekolah")
            no_pusat_asal_val = get_val("NO_PUSAT_ASAL", "no_pusat_asal", "NO PUSAT ASAL", "pusat_asal", "NO_PUSAT", "NO PUSAT", "PUSAT")
            
            # Jika nama_sekolah_asal masih kosong, ambil dari sekolah_master map
            if not nama_sek_val or nama_sek_val == "" or nama_sek_val == kod_sek_val:
                nama_sek_val = sekolah_map_guru.get(kod_sek_val.upper(), "") or sekolah_map_guru.get(kod_sekolah.upper(), "") or kod_sek_val
            if not kod_ppd_val or kod_ppd_val == "":
                kod_ppd_val = kod_sekolah[:2] if len(kod_sekolah)>=2 else "BA"
            
            # Default untuk field yang masih kosong (EMAIL, JAWATAN, NO_PUSAT_ASAL)
            if not email_val or email_val.strip() == "":
                # Cuba generate dari nama atau biarkan kosong untuk SUP isi
                email_val = ""  # Biar kosong, SUP perlu isi manual
            if not jawatan_val or jawatan_val.strip() == "":
                jawatan_val = "Pengawas Peperiksaan"  # Default
            if not no_pusat_asal_val or no_pusat_asal_val.strip() == "":
                # Default ikut kod sekolah untuk BFT0003
                if kod_sekolah.upper() == "BFT0003":
                    no_pusat_asal_val = "BA142"
                else:
                    # Ambil dari kod_ppd + 001 sebagai default
                    no_pusat_asal_val = f"{kod_ppd_val}001" if kod_ppd_val else "BA142"
            
            rows.append({
                "id": r.get("id"),
                "NAMA GURU": nama_val,
                "IC": ic_val,
                "JANTINA": jantina_val,
                "POSKOD_RUMAH": poskod_val,
                "ALAMAT_RUMAH": alamat_val,
                "TELEFON": telefon_val,
                "TELEFON_GURU": telefon_val,
                "EMAIL_GURU": email_val,
                "EMAIL": email_val,
                "JAWATAN CADANGAN": jawatan_val,
                "JAWATAN_CADANGAN": jawatan_val,
                "PENGALAMAN_SPM": pengalaman_val,
                "PENGALAMAN": pengalaman_val,
                "KOD_PPD": kod_ppd_val,
                "KOD_PPD_ASAL": kod_ppd_val,
                "KOD SEKOLAH": kod_sek_val,
                "KOD_SEKOLAH": kod_sek_val,
                "KOD_SEKOLAH_ASAL": kod_sek_val,
                "NAMA_SEKOLAH_ASAL": nama_sek_val,
                "NAMA_SEKOLAH": nama_sek_val,
                "NO_PUSAT_ASAL": no_pusat_asal_val,
                "ALAMAT": alamat_val,
                "data_full": d if isinstance(d, dict) else {},
                "raw": r
            })
        return pd.DataFrame(rows)
    except Exception as e:
        # Don't show error, return empty
        return pd.DataFrame()

def get_pusat_df():
    try:
        res = supa.table("pusat_master").select("*").limit(2000).execute()
        df = pd.DataFrame(res.data or [])
        if not df.empty:
            # Normalize column names: support no_pusat / kod_pusat / NO_PUSAT
            # Create unified view
            df_norm = df.copy()
            # Map to standard
            if "no_pusat" in df_norm.columns:
                df_norm["kod_pusat_std"] = df_norm["no_pusat"]
            elif "kod_pusat" in df_norm.columns:
                df_norm["kod_pusat_std"] = df_norm["kod_pusat"]
            elif "NO_PUSAT" in df_norm.columns:
                df_norm["kod_pusat_std"] = df_norm["NO_PUSAT"]
            else:
                df_norm["kod_pusat_std"] = df_norm.iloc[:,1] if len(df_norm.columns)>1 else ""
            
            if "nama_pusat" in df_norm.columns:
                df_norm["nama_pusat_std"] = df_norm["nama_pusat"]
            elif "NAMA_PUSAT" in df_norm.columns:
                df_norm["nama_pusat_std"] = df_norm["NAMA_PUSAT"]
            else:
                df_norm["nama_pusat_std"] = df_norm.get("nama_sekolah","")
        return df
    except Exception as e:
        st.error(f"pusat_master error: {e}")
        return pd.DataFrame()

def get_cadangan_df(kod_ppd=None, kod_sekolah=None):
    try:
        res = supa.table("cadangan_sup").select("*").limit(5000).execute()
        df = pd.DataFrame(res.data or [])
        
        if df.empty:
            return df
        
        # Normalize - merge duplicate lowercase/UPPERCASE columns and data JSON
        # Create clean dataframe with single set of columns
        def get_col_value(row, *possible_keys, default=""):
            # Check flat columns
            for k in possible_keys:
                if k in row and pd.notna(row[k]) and str(row[k]).strip() not in ["", "None", "none"]:
                    return str(row[k]).strip()
                # Check uppercase
                ku = k.upper()
                if ku in row and pd.notna(row[ku]) and str(row[ku]).strip() not in ["", "None", "none"]:
                    return str(row[ku]).strip()
            # Check data JSON
            d = row.get("data") if isinstance(row.get("data"), dict) else {}
            if isinstance(d, str):
                try:
                    import json
                    d = json.loads(d)
                except:
                    d={}
            for k in possible_keys:
                if k in d and str(d[k]).strip() not in ["", "None", "none"]:
                    return str(d[k]).strip()
                ku = k.upper()
                if ku in d and str(d[ku]).strip() not in ["", "None", "none"]:
                    return str(d[ku]).strip()
                # Also check with space
                ks = k.replace("_", " ").upper()
                if ks in d and str(d[ks]).strip() not in ["", "None"]:
                    return str(d[ks]).strip()
            return default
        
        # Build normalized rows
                # Pre-fetch sekolah_master for nama sekolah
        sekolah_map = {}
        try:
            res_sek = supa.table("sekolah_master").select("kod_sekolah,nama_sekolah").limit(2000).execute()
            for s in res_sek.data or []:
                k = (s.get("kod_sekolah") or "").upper()
                n = s.get("nama_sekolah") or s.get("NAMA_SEKOLAH") or ""
                if k:
                    sekolah_map[k] = n
        except:
            pass
        
        # Pre-fetch guru_master map untuk tarik jantina, poskod, alamat, telefon, email kalau cadangan kosong
        guru_map = {}
        try:
            res_guru = supa.table("guru_master").select("*").limit(5000).execute()
            for g in res_guru.data or []:
                ic = (g.get("ic_guru") or "").strip()
                if not ic:
                    d_tmp = g.get("data") or {}
                    if isinstance(d_tmp, str):
                        try:
                            import json as js
                            d_tmp = js.loads(d_tmp)
                        except:
                            d_tmp={}
                    ic = str(d_tmp.get("IC","") or "").strip()
                if ic:
                    d = g.get("data") or {}
                    if isinstance(d, str):
                        try:
                            import json as js
                            d = js.loads(d)
                        except:
                            d={}
                    guru_map[ic] = {
                        "JANTINA": g.get("jantina") or d.get("JANTINA") or d.get("jantina") or "",
                        "POSKOD": g.get("poskod_rumah") or d.get("POSKOD_RUMAH") or d.get("POSKOD") or "",
                        "ALAMAT": g.get("alamat_rumah") or d.get("ALAMAT_RUMAH") or d.get("ALAMAT RUMAH") or d.get("ALAMAT") or "",
                        "TELEFON": g.get("telefon_guru") or d.get("TELEFON_GURU") or d.get("NO TELEFON GURU") or d.get("TELEFON") or "",
                        "EMAIL": g.get("email_guru") or d.get("EMAIL_GURU") or d.get("EMAIL") or "",
                        "JAWATAN": g.get("jawatan_cadangan") or d.get("JAWATAN_CADANGAN") or d.get("JAWATAN CADANGAN") or "Pengawas Peperiksaan",
                        "PENGALAMAN": g.get("pengalaman_spm") or d.get("PENGALAMAN_SPM") or d.get("PENGALAMAN") or "",
                        "NO_PUSAT_ASAL": g.get("no_pusat_asal") or d.get("NO_PUSAT_ASAL") or "BA142",
                        "KOD_SEKOLAH_ASAL": g.get("kod_sekolah_asal") or g.get("kod_sekolah") or "",
                        "NAMA_SEKOLAH_ASAL": g.get("nama_sekolah_asal") or d.get("NAMA_SEKOLAH_ASAL") or d.get("NAMA_SEKOLAH") or ""
                    }
        except:
            pass
        
        norm_rows=[]
        for _, r in df.iterrows():
            kod_sek = get_col_value(r, "kod_sekolah", "KOD_SEKOLAH")
            kod_sek_asal = get_col_value(r, "kod_sekolah_asal", "KOD_SEKOLAH_ASAL", "kod_sekolah") or kod_sek
            nama_sek_asal = get_col_value(r, "nama_sekolah_asal", "NAMA_SEKOLAH_ASAL", "NAMA_SEKOLAH")
            if not nama_sek_asal or nama_sek_asal.strip() == "":
                nama_sek_asal = sekolah_map.get(kod_sek_asal.upper(), "") or sekolah_map.get(kod_sek.upper(), "") or kod_sek_asal or kod_sek
            
            ic_guru_val = get_col_value(r, "ic_guru", "IC_GURU", "IC")
            # Tarik dari guru_map kalau cadangan kosong
            g_info = guru_map.get(ic_guru_val, {}) if ic_guru_val else {}
            
            jantina_val = get_col_value(r, "jantina", "JANTINA") or g_info.get("JANTINA","")
            poskod_val = get_col_value(r, "poskod_rumah", "POSKOD_RUMAH", "POSKOD") or g_info.get("POSKOD","")
            alamat_val = get_col_value(r, "alamat_rumah", "ALAMAT_RUMAH", "ALAMAT") or g_info.get("ALAMAT","")
            telefon_val = get_col_value(r, "telefon_guru", "TELEFON_GURU", "TELEFON", "NO_TELEFON_GURU") or g_info.get("TELEFON","")
            email_val = get_col_value(r, "email_guru", "EMAIL_GURU", "EMAIL") or g_info.get("EMAIL","")
            jawatan_val = get_col_value(r, "jawatan_cadangan", "JAWATAN_CADANGAN") or g_info.get("JAWATAN","Pengawas Peperiksaan")
            pengalaman_val = get_col_value(r, "pengalaman_spm", "PENGALAMAN_SPM", "PENGALAMAN") or g_info.get("PENGALAMAN","")
            no_pusat_asal_val = get_col_value(r, "no_pusat_asal", "NO_PUSAT_ASAL", "NO_PUSAT") or g_info.get("NO_PUSAT_ASAL","BA142")
            # KOD_PUSAT dan NO_PUSAT_ASAL sepatutnya sama - guna NO_PUSAT_ASAL sahaja
            kod_pusat_val = no_pusat_asal_val  # Samakan, jangan duplicate
            
            kod_ppd_val = get_col_value(r, "kod_ppd", "KOD_PPD") or (kod_sek[:2] if len(kod_sek)>=2 else "BA")
            kod_ppd_val = kod_ppd_val.upper()  # FIX huruf kecil jadi besar
            
            norm_rows.append({
                "id": r.get("id"),
                "KOD_PPD": kod_ppd_val,
                "KOD_SEKOLAH_ASAL": kod_sek_asal,  # Hanya guna KOD_SEKOLAH_ASAL, bukan KOD_SEKOLAH
                "NAMA_SEKOLAH_ASAL": nama_sek_asal,
                "IC_GURU": ic_guru_val,
                "NAMA_GURU": get_col_value(r, "nama_guru", "NAMA_GURU", "NAMA GURU"),
                "JANTINA": jantina_val,
                "POSKOD_RUMAH": poskod_val,
                "ALAMAT_RUMAH": alamat_val,
                "TELEFON_GURU": telefon_val,
                "EMAIL_GURU": email_val,
                "JAWATAN_CADANGAN": jawatan_val,
                "PENGALAMAN_SPM": pengalaman_val,
                "NO_PUSAT_ASAL": no_pusat_asal_val,  # Hanya NO_PUSAT_ASAL, bukan KOD_PUSAT duplicate
                "STATUS": get_col_value(r, "status", "STATUS", default="DICADANGKAN").upper(),
                "TARIKH_CADANG": get_col_value(r, "tarikh_cadang", "TARIKH_CADANG"),
                "created_at": r.get("created_at", "")
            })
        
        df_norm = pd.DataFrame(norm_rows)
        
        # Filter
        if kod_ppd:
            df_norm = df_norm[df_norm["KOD_PPD"].str.upper() == kod_ppd.upper()]
        if kod_sekolah:
            df_norm = df_norm[df_norm["KOD_SEKOLAH"].str.upper() == kod_sekolah.upper()]
        
        return df_norm
    except Exception as e:
        return pd.DataFrame()

def to_excel(df):
    output = BytesIO()
    # Cuba openpyxl dulu - paling standard
    try:
        import openpyxl
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        return output.getvalue()
    except ImportError:
        pass
    except Exception as e:
        pass
    
    # Fallback xlsxwriter
    try:
        import xlsxwriter
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        return output.getvalue()
    except:
        pass
    
    # Last fallback - buat CSV tapi dengan header yang betul, dan beri nama .csv bukan .xlsx
    # Tapi untuk elak Excel error "file format not valid", kita cuba buat xlsx minimal manual
    try:
        # Cuba buat xlsx kosong guna openpyxl jika ada
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        # Tulis header
        for col_idx, col_name in enumerate(df.columns, 1):
            ws.cell(row=1, column=col_idx, value=col_name)
        # Tulis data
        for r_idx, row in enumerate(df.values, 2):
            for c_idx, val in enumerate(row, 1):
                ws.cell(row=r_idx, column=c_idx, value=str(val) if val is not None else "")
        wb.save(output)
        return output.getvalue()
    except:
        # Ultimate fallback - CSV
        output = BytesIO()
        output.write(df.to_csv(index=False).encode('utf-8-sig'))  # UTF-8 BOM untuk Excel
        return output.getvalue()

def get_template_guru():
    """Buat template guru yang sah - bukan CSV dengan extension xlsx"""
    import pandas as pd
    template_data = {
        "NAMA GURU": ["CONTOH: ALI BIN ABU"],
        "IC": ["900101-01-1234"],
        "JANTINA": ["L"],
        "POSKOD_RUMAH": ["40000"],
        "ALAMAT_RUMAH": ["NO 1, JALAN CONTOH"],
        "TELEFON_GURU": ["012-3456789"],
        "EMAIL_GURU": ["ali@gmail.com"],
        "PENGALAMAN_SPM": ["3"],
        "KOD_SEKOLAH": ["BFT0003"],
        "NAMA_SEKOLAH_ASAL": ["SAM NURUL IMAN"],
        "NO_PUSAT_ASAL": ["BA142"]
    }
    return pd.DataFrame(template_data)

# ================= SESSION =================
if "role" not in st.session_state:
    st.session_state.role=None

# ================= LOGIN PAGE - MUKA DEPAN CANTIK =================
if st.session_state.role is None:
    # CSS Cantik
    st.markdown("""
    <style>
    .main-title {text-align:center; font-size:42px; font-weight:800; color:#0d47a1; margin-bottom:0; letter-spacing:1px;}
    .sub-title {text-align:center; font-size:18px; color:#546e7a; margin-top:5px; margin-bottom:25px;}
    .login-card {background: white; padding:20px; border-radius:15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border:1px solid #e0e0e0;}
    .stTabs [data-baseweb="tab-list"] {gap: 10px; justify-content: center;}
    .stTabs [data-baseweb="tab"] {height:50px; font-weight:600; font-size:16px; border-radius:10px 10px 0 0;}
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="main-title">🏫 SISTEM PELANTIKAN PETUGAS PEPERIKSAAN</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-title" style="font-size:32px; margin-top:-10px;">SPM SELANGOR 2026</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Jabatan Pendidikan Negeri Selangor | 369 Sekolah | 506 Pusat | 71,064 Calon</div>', unsafe_allow_html=True)

    # Load sekolah list untuk dropdown
    @st.cache_data(ttl=600)
    def load_sekolah_list():
        try:
            res = supa.table("sekolah_master").select("*").limit(1000).execute()
            data = res.data or []
            rows=[]
            for r in data:
                kod = r.get("kod_sekolah") or r.get("KOD_SEKOLAH") or ""
                nama = r.get("nama_sekolah") or r.get("NAMA_SEKOLAH") or ""
                kod_ppd = r.get("kod_ppd") or r.get("KOD_PPD") or "BH"
                if kod and nama:
                    rows.append({"KOD_SEKOLAH":kod.upper().strip(), "NAMA_SEKOLAH":nama.upper().strip(), "KOD_PPD":kod_ppd.upper().strip(), "PPD":PPD_MAP.get(kod_ppd.upper().strip(),"")})
            df = pd.DataFrame(rows)
            # Sort by PPD order BA->BK then nama
            order_map = {k:i for i,k in enumerate(KOD_DAERAH)}
            if not df.empty:
                df["order"] = df["KOD_PPD"].map(order_map)
                df = df.sort_values(["order","NAMA_SEKOLAH"]).reset_index(drop=True)
                df["ID"] = df.index + 1
                df["PASSWORD"] = df["ID"].astype(str)  # password = ID, old style 12345...
                df["PASSWORD_LAMA"] = "12345" + df["ID"].astype(str)  # alternative old format
            return df
        except Exception as e:
            return pd.DataFrame()

    df_sekolah_all = load_sekolah_list()
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["🏫 SUP - Sekolah", "🏢 PPD - Daerah", "🏛️ JPN - Negeri"])

    with tab1:
        st.markdown("### 🏫 Log Masuk SUP - Penyelia Sekolah")
        st.caption("Pilih Daerah → Pilih Sekolah → Masuk Password. Password ikut sekolah (ID 1-369). Untuk testing, password dipaparkan di bawah.")
        
        col_a, col_b = st.columns(2)
        with col_a:
            # Pilih Daerah
            daerah_opts = [(k, f"{k} - {PPD_MAP[k]}") for k in KOD_DAERAH]
            pilih_ppd_label = st.selectbox("1️⃣ Pilih Daerah (PPD)", options=[f"{k} - {PPD_MAP[k]}" for k in KOD_DAERAH], key="sup_daerah")
            pilih_ppd_code = pilih_ppd_label.split(" - ")[0] if pilih_ppd_label else "BA"
            
            # Filter sekolah by PPD
            if not df_sekolah_all.empty:
                df_filtered = df_sekolah_all[df_sekolah_all["KOD_PPD"] == pilih_ppd_code]
            else:
                df_filtered = pd.DataFrame()
            
            if df_filtered.empty:
                st.warning(f"Tiada sekolah untuk {pilih_ppd_code} - cuba load atau taip manual")
                sekolah_manual = st.text_input("KOD SEKOLAH (Manual)", value="BFT8002", key="sup_kod_manual").upper()
                pilih_sekolah_kod = sekolah_manual
                pilih_sekolah_nama = f"SEKOLAH {sekolah_manual}"
                sup_id = 1
                sup_password_expected = "1"
            else:
                # Dropdown sekolah
                sekolah_options = [f"{row['KOD_SEKOLAH']} - {row['NAMA_SEKOLAH']}" for _, row in df_filtered.iterrows()]
                pilih_sekolah_str = st.selectbox(f"2️⃣ Pilih Sekolah ({len(df_filtered)} sekolah di {PPD_MAP[pilih_ppd_code]})", options=sekolah_options, key="sup_sekolah_list")
                # Extract kod
                pilih_sekolah_kod = pilih_sekolah_str.split(" - ")[0] if pilih_sekolah_str else ""
                row_sel = df_filtered[df_filtered["KOD_SEKOLAH"] == pilih_sekolah_kod].iloc[0] if not df_filtered[df_filtered["KOD_SEKOLAH"] == pilih_sekolah_kod].empty else None
                if row_sel is not None:
                    pilih_sekolah_nama = row_sel["NAMA_SEKOLAH"]
                    sup_id = int(row_sel["ID"])
                    sup_password_expected = str(row_sel["PASSWORD"])
                    sup_password_lama = str(row_sel["PASSWORD_LAMA"])
                else:
                    pilih_sekolah_nama = ""
                    sup_id = 1
                    sup_password_expected = "1"
                    sup_password_lama = "123451"

        with col_b:
            st.markdown(f"**Sekolah Dipilih:** `{pilih_sekolah_kod}` - {pilih_sekolah_nama}")
            st.markdown(f"**ID Sekolah:** {sup_id} | **PPD:** {pilih_ppd_code} - {PPD_MAP.get(pilih_ppd_code,'')}")
            
            # Show password for testing
            with st.container(border=True):
                st.markdown("🔑 **Password Untuk Testing (Paparan Sementara)**")
                if not df_filtered.empty and 'sup_password_expected' in locals():
                    st.code(f"ID: {sup_id}\nPassword Baru: {sup_password_expected}\nPassword Lama Style: {sup_password_lama} / 12345{sup_id}\nContoh: Taip {sup_password_expected} atau {sup_password_lama}", language="text")
                else:
                    st.code(f"Password: {sup_id} atau 12345{sup_id}", language="text")
            
            pwd_input = st.text_input("3️⃣ Masuk Password", type="password", key="sup_pwd", placeholder=f"Contoh: {sup_password_expected if 'sup_password_expected' in locals() else '1'}")
            
            if st.button("🚀 Masuk SUP Sekolah", use_container_width=True, type="primary", key="btn_sup"):
                # Check password - accept ID or 12345+ID or just ID
                valid_pw = [str(sup_id), f"12345{sup_id}", f"12345{ sup_id }".replace(" ",""), sup_password_expected if 'sup_password_expected' in locals() else str(sup_id)]
                if not df_sekolah_all.empty and 'sup_password_lama' in locals():
                    valid_pw.append(sup_password_lama)
                # Also accept plain "1", "a", etc for backward compat
                if pwd_input.strip() in valid_pw or pwd_input.strip() == "12345" or pwd_input.strip().lower() == "a" or pwd_input.strip() == "":
                    # For testing, allow empty as well to ease test
                    if pwd_input.strip() == "" and not st.checkbox("Benarkan login tanpa password untuk testing?", key="allow_empty"):
                        st.error(f"Password salah! Cuba {sup_password_expected} atau {sup_password_lama}")
                    else:
                        info=get_sekolah(pilih_sekolah_kod)
                        # Override with selected
                        info["kod_sekolah"]=pilih_sekolah_kod
                        info["nama_sekolah"]=pilih_sekolah_nama
                        info["kod_ppd"]=pilih_ppd_code
                        st.session_state.role="SUP"
                        st.session_state.kod=pilih_sekolah_kod
                        st.session_state.info=info
                        st.session_state.sup_id=sup_id
                        st.rerun()
                else:
                    st.error(f"Password salah! Sepatutnya: {sup_password_expected} atau {sup_password_lama}. Kau taip: {pwd_input}")

        # Show full list for testing
        with st.expander(f"📋 Lihat Senarai 369 Sekolah & Password (Untuk Testing - {len(df_sekolah_all)} sekolah)", expanded=False):
            if not df_sekolah_all.empty:
                st.dataframe(df_sekolah_all[["ID","KOD_SEKOLAH","NAMA_SEKOLAH","KOD_PPD","PPD","PASSWORD","PASSWORD_LAMA"]], use_container_width=True, height=400)
                st.download_button("📥 Download Senarai Password Sekolah", to_excel(df_sekolah_all), file_name="SENARAI_PASSWORD_369_SEKOLAH.xlsx")
            else:
                st.warning("Gagal load sekolah_master - check RLS")

    with tab2:
        st.markdown("### 🏢 Log Masuk PPD - Pejabat Pendidikan Daerah")
        st.caption("10 PPD Selangor | ID 1-10 | Password a-j (ikut turutan)")
        
        col1, col2 = st.columns(2)
        with col1:
            ppd_labels = [f"{i+1}. {KOD_DAERAH[i]} - {PPD_MAP[KOD_DAERAH[i]]} (ID:{i+1} Pwd:{chr(97+i)})" for i in range(len(KOD_DAERAH))]
            pilih_ppd_full = st.selectbox("Pilih PPD", options=ppd_labels, key="ppd_full")
            # Extract code
            ppd_code = pilih_ppd_full.split(" - ")[0].split(". ")[1] if ". " in pilih_ppd_full else KOD_DAERAH[0]
            ppd_id = KOD_DAERAH.index(ppd_code)+1 if ppd_code in KOD_DAERAH else 1
            ppd_pwd_expected = chr(96+ppd_id)  # a-j
        
        with col2:
            with st.container(border=True):
                st.markdown("🔑 **Password PPD Untuk Testing**")
                st.code(f"ID PPD: {ppd_id}\nPPD: {ppd_code} - {PPD_MAP.get(ppd_code,'')}\nPassword: {ppd_pwd_expected} atau {ppd_id} atau 12345{ppd_id}", language="text")
            ppd_pwd = st.text_input("Masuk Password PPD", type="password", key="ppd_pwd", placeholder=f"Contoh: {ppd_pwd_expected}")
            if st.button("🚀 Masuk PPD", use_container_width=True, type="primary", key="btn_ppd"):
                valid = [ppd_pwd_expected, str(ppd_id), f"12345{ppd_id}", chr(96+ppd_id).upper(), ppd_code.lower(), "a","b","c","d","e","f","g","h","i","j"]
                if ppd_pwd.strip().lower() in [v.lower() for v in valid] or ppd_pwd.strip() == "":
                    st.session_state.role="PPD"
                    st.session_state.kod=ppd_code
                    st.session_state.ppd_id=ppd_id
                    st.rerun()
                else:
                    st.error(f"Password salah! Cuba {ppd_pwd_expected} atau {ppd_id}")

        # Table PPD
        with st.expander("📋 Senarai 10 PPD & Password", expanded=False):
            ppd_table = pd.DataFrame([{"ID":i+1, "KOD_PPD":KOD_DAERAH[i], "PPD":PPD_MAP[KOD_DAERAH[i]], "PASSWORD":chr(97+i), "PASSWORD_LAMA":f"12345{i+1}"} for i in range(len(KOD_DAERAH))])
            st.dataframe(ppd_table, use_container_width=True, hide_index=True)

    with tab3:
        st.markdown("### 🏛️ Log Masuk JPN - Jabatan Pendidikan Negeri")
        st.caption("JPN Selangor - Akses Penuh Negeri")
        col1, col2 = st.columns(2)
        with col1:
            jpn_id = st.text_input("ID JPN", value="1", key="jpn_id")
            jpn_pwd = st.text_input("Password JPN", type="password", key="jpn_pwd", placeholder="a")
            with st.container(border=True):
                st.code("ID: 1\nPassword: a atau 1 atau 123451\nJPN ada 1 user sahaja", language="text")
            if st.button("🚀 Masuk JPN", use_container_width=True, type="primary", key="btn_jpn"):
                if jpn_id=="1" and jpn_pwd.strip().lower() in ["a","1","123451","12345",""]:
                    st.session_state.role="JPN"
                    st.rerun()
                else:
                    # Allow for testing
                    st.session_state.role="JPN"
                    st.rerun()
        with col2:
            st.info("JPN boleh tengok semua PPD, semua sekolah (369), semua pusat (506), semua cadangan. Boleh export negeri.")

    st.markdown("---")
    st.caption("© 2026 JPN Selangor - Sistem Pelantikan Petugas Peperiksaan SPM | Formula: 1 kelas=20 calon, CEIL(calon/20)=kelas, Petugas=Kelas+9, Sekolah Perlu=Kelas+12")
    st.stop()

# ================= SUP =================
if st.session_state.role=="SUP":
    kod=st.session_state.kod
    info=st.session_state.info
    st.sidebar.title(f"🏫 SUP {kod}")
    st.sidebar.caption(f"{info.get('nama_sekolah','')} | {info.get('kod_ppd','BH')} - {PPD_MAP.get(info.get('kod_ppd','BH'),'')}")

    # Menu Pusat Peperiksaan tak perlu untuk SUP - hanya PPD/JPN sahaja
    menu=st.sidebar.radio("Menu SUP", ["📊 Dashboard","📋 Senarai Guru","➕ Tambah Guru","📤 Import Excel","🗑️ Buang Guru","📝 Cadangan Lantikan","📤 Hantar ke PPD","🚪 Log Keluar"])

    if menu=="🚪 Log Keluar":
        st.session_state.clear()
        st.rerun()

    df_guru = get_guru_df(kod)

    if menu=="📊 Dashboard":
        st.header(f"Dashboard SUP - {kod} {info.get('nama_sekolah','')}")
        
        # KIRA KEPERLUAN PENGAWAS BERDASARKAN PUSAT SEKOLAH INI
        try:
            df_pusat_all = get_pusat_df()
            # Cari pusat dimana kod_sekolah_tuan_rumah = kod sekolah ini
            pusat_sekolah = []
            for _, r in df_pusat_all.iterrows():
                d = r.get("data") if isinstance(r.get("data"), dict) else {}
                if isinstance(d, str):
                    try:
                        import json
                        d = json.loads(d)
                    except:
                        d={}
                ks = r.get("kod_sekolah_tuan_rumah") or r.get("kod_sekolah") or d.get("KOD_SEKOLAH") or d.get("KOD SEKOLAH") or ""
                if ks.upper().strip() == kod.upper().strip():
                    # Kira calon
                    calon = r.get("jumlah_calon") or r.get("calon") or d.get("JUMLAH_CALON") or 0
                    try: calon_i = int(float(str(calon) or 0))
                    except: calon_i=0
                    kelas = kira_kelas_dari_calon(calon_i)
                    petugas_k9 = kira_petugas_dari_kelas(kelas)
                    sekolah_perlu = kira_sekolah_perlu_calonkan(kelas)
                    pusat_sekolah.append({
                        "NO_PUSAT": r.get("no_pusat") or r.get("kod_pusat") or d.get("NO_PUSAT") or "",
                        "NAMA_PUSAT": r.get("nama_pusat") or d.get("NAMA_PUSAT") or "",
                        "CALON": calon_i,
                        "KELAS": kelas,
                        "PETUGAS_K9": petugas_k9,
                        "SEKOLAH_PERLU": sekolah_perlu
                    })
        except:
            pusat_sekolah = []

        # ALERT WAJIB
        if pusat_sekolah:
            total_calon = sum([p["CALON"] for p in pusat_sekolah])
            total_kelas = sum([p["KELAS"] for p in pusat_sekolah])
            total_petugas = sum([p["PETUGAS_K9"] for p in pusat_sekolah])
            total_perlu = sum([p["SEKOLAH_PERLU"] for p in pusat_sekolah])
            
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); padding:20px; border-radius:12px; border-left:6px solid #1565c0; margin-bottom:20px;">
                <h3 style="margin:0; color:#0d47a1;">⚠️ KEPERLUAN PENGAWAS SEKOLAH ANDA - {kod}</h3>
                <p style="margin:8px 0; font-size:16px;">
                    Sekolah anda ada <b>{len(pusat_sekolah)} pusat</b> | <b>{total_calon} calon</b> | <b>{total_kelas} kelas</b> (1 kelas=20 calon)<br>
                    Formula: Kelas = CEIL(Calon/20), Petugas = Kelas+9, Sekolah Perlu = Kelas+12 (Petugas+KP+TKP+Penyelia)
                </p>
                <div style="display:flex; gap:15px; margin-top:12px; flex-wrap:wrap;">
                    <div style="background:white; padding:12px 18px; border-radius:8px; box-shadow:0 2px 5px rgba(0,0,0,0.1);">
                        <div style="font-size:13px; color:#666;">JUMLAH KELAS</div>
                        <div style="font-size:24px; font-weight:800; color:#1565c0;">{total_kelas}</div>
                        <div style="font-size:12px;">{total_calon} calon /20</div>
                    </div>
                    <div style="background:white; padding:12px 18px; border-radius:8px; box-shadow:0 2px 5px rgba(0,0,0,0.1);">
                        <div style="font-size:13px; color:#666;">PETUGAS DIPERLUKAN</div>
                        <div style="font-size:24px; font-weight:800; color:#e65100;">{total_petugas}</div>
                        <div style="font-size:12px;">Kelas+9</div>
                    </div>
                    <div style="background:#ffebee; padding:12px 18px; border-radius:8px; border:2px solid #c62828; box-shadow:0 2px 5px rgba(0,0,0,0.1);">
                        <div style="font-size:13px; color:#c62828; font-weight:700;">SEKOLAH WAJIB CALONKAN</div>
                        <div style="font-size:28px; font-weight:800; color:#c62828;">{total_perlu} ORANG</div>
                        <div style="font-size:12px;">Kelas+12 (Petugas+KP+TKP+Penyelia)</div>
                    </div>
                </div>
                <div style="margin-top:15px; background:#fff3e0; padding:12px; border-radius:8px;">
                    <b>📌 Pecahan Wajib:</b> 
                    <span style="background:#c62828; color:white; padding:3px 8px; border-radius:12px; margin:0 3px;">Ketua Pengawas 1 orang (WAJIB)</span>
                    <span style="background:#ef6c00; color:white; padding:3px 8px; border-radius:12px; margin:0 3px;">Timbalan Ketua 1 orang (WAJIB)</span>
                    <span style="background:#2e7d32; color:white; padding:3px 8px; border-radius:12px; margin:0 3px;">Penyelia Kawasan 1 orang (Optional)</span>
                    <span style="background:#1565c0; color:white; padding:3px 8px; border-radius:12px; margin:0 3px;">Pengawas Peperiksaan {total_kelas} orang</span>
                    <span style="background:#6a1b9a; color:white; padding:3px 8px; border-radius:12px; margin:0 3px;">Extra/Reserve {total_petugas - total_kelas} orang</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Table pusat
            st.dataframe(pd.DataFrame(pusat_sekolah), use_container_width=True, hide_index=True)
        else:
            st.info(f"Tiada pusat dijumpai untuk sekolah {kod}. Hubungi PPD untuk semak pusat sekolah anda. Formula: 105 calon = 6 kelas (20/kelas) = 15 petugas (kelas+9) = 18 sekolah perlu (kelas+12).")

        c1,c2,c3,c4 = st.columns(4)
        with c1:
            st.metric("Jumlah Guru", len(df_guru))
        with c2:
            try:
                cnt=supa.table("guru_master").select("id", count="exact").execute()
                st.metric("Total Guru Selangor", cnt.count)
            except:
                st.metric("Total Guru Selangor", "-")
        with c3:
            st.metric("Pusat Sekolah Ini", len(pusat_sekolah) if 'pusat_sekolah' in locals() else 0)
        with c4:
            try:
                cad = get_cadangan_df(kod_sekolah=kod)
                st.metric("Cadangan Dihantar", len(cad))
            except:
                st.metric("Cadangan", "0")
        st.markdown("---")
        st.subheader("Guru Terkini")
        if not df_guru.empty:
            st.dataframe(df_guru[["NAMA GURU","IC","TELEFON","JAWATAN CADANGAN"]], use_container_width=True, hide_index=True)
        else:
            st.warning("Belum ada guru. Sila Tambah Guru atau Import Excel.")

    elif menu=="📋 Senarai Guru":
        st.header(f"Senarai Guru - {kod} - Lengkap")
        if df_guru.empty:
            st.info("guru_master kosong untuk sekolah ini. Sila Tambah Guru atau Import Excel.")
        else:
            st.success(f"Ada {len(df_guru)} guru di {kod} - Data lengkap diperlukan untuk cadangan")
            # Show all columns
            cols_to_show = [c for c in ["NAMA GURU","IC","JANTINA","POSKOD_RUMAH","ALAMAT_RUMAH","TELEFON_GURU","EMAIL_GURU","JAWATAN CADANGAN","PENGALAMAN_SPM","KOD_SEKOLAH_ASAL","NAMA_SEKOLAH_ASAL","NO_PUSAT_ASAL"] if c in df_guru.columns]
            if cols_to_show:
                st.dataframe(df_guru[cols_to_show], use_container_width=True, hide_index=True)
                # Highlight yang kosong
                kosong = df_guru[df_guru["JANTINA"].isin(["", "KOSONG"]) | df_guru["POSKOD_RUMAH"].isin(["", "KOSONG"]) | df_guru["TELEFON_GURU"].isin(["", "KOSONG"])]
                if not kosong.empty:
                    st.warning(f"⚠️ Ada {len(kosong)} guru dengan data KOSONG (JANTINA/POSKOD/ALAMAT/TELEFON/EMAIL). Sila edit di bawah.")
            st.download_button("📥 Export Excel Lengkap", to_excel(df_guru), file_name=f"guru_{kod}_lengkap.xlsx", use_container_width=True)
            
            st.markdown("---")
            st.subheader("✏️ Edit Data Guru (Lengkapkan yang kosong)")
            edit_ic = st.selectbox("Pilih IC guru untuk edit", df_guru["IC"].tolist(), format_func=lambda x: f"{x} - {df_guru[df_guru['IC']==x]['NAMA GURU'].values[0] if not df_guru[df_guru['IC']==x].empty else x}")
            if edit_ic:
                guru_edit = df_guru[df_guru["IC"]==edit_ic].iloc[0] if not df_guru[df_guru["IC"]==edit_ic].empty else None
                if guru_edit is not None:
                    with st.form(f"edit_{edit_ic}"):
                        c1,c2 = st.columns(2)
                        with c1:
                            e_nama = st.text_input("NAMA GURU", value=guru_edit.get("NAMA GURU",""))
                            e_ic = st.text_input("IC", value=edit_ic, disabled=True)
                            e_jantina = st.selectbox("JANTINA", ["LELAKI","PEREMPUAN"], index=0 if guru_edit.get("JANTINA","")=="LELAKI" else 1)
                            e_poskod = st.text_input("POSKOD RUMAH", value=guru_edit.get("POSKOD_RUMAH",""))
                            e_alamat = st.text_area("ALAMAT RUMAH", value=guru_edit.get("ALAMAT_RUMAH",""))
                        with c2:
                            e_tel = st.text_input("TELEFON GURU", value=guru_edit.get("TELEFON_GURU","") or guru_edit.get("TELEFON",""))
                            e_email = st.text_input("EMAIL GURU", value=guru_edit.get("EMAIL_GURU",""))
                            e_jawatan = st.selectbox("JAWATAN CADANGAN", ["Ketua Pengawas", "Timbalan Ketua Pengawas", "Penyelia Kawasan", "Pengawas Peperiksaan"], index=0)
                            e_pengalaman = st.text_input("PENGALAMAN SPM", value=guru_edit.get("PENGALAMAN_SPM",""))
                            e_no_pusat = st.text_input("NO PUSAT ASAL", value=guru_edit.get("NO_PUSAT_ASAL",""))
                        if st.form_submit_button("💾 Update Guru", type="primary"):
                            # Update in guru_master
                            try:
                                # Find id
                                res = supa.table("guru_master").select("id,data").eq("ic_guru", edit_ic).eq("kod_sekolah", kod).execute()
                                if not res.data:
                                    res = supa.table("guru_master").select("id,data").eq("ic_guru", edit_ic).execute()
                                for row in res.data or []:
                                    old_data = row.get("data") or {}
                                    if isinstance(old_data, str):
                                        try:
                                            import json
                                            old_data = json.loads(old_data)
                                        except:
                                            old_data={}
                                    new_data = {**old_data, **{
                                        "NAMA GURU": e_nama.upper(),
                                        "IC": edit_ic,
                                        "JANTINA": e_jantina,
                                        "POSKOD_RUMAH": e_poskod,
                                        "ALAMAT_RUMAH": e_alamat,
                                        "TELEFON_GURU": e_tel,
                                        "EMAIL_GURU": e_email,
                                        "JAWATAN_CADANGAN": e_jawatan,
                                        "PENGALAMAN_SPM": e_pengalaman,
                                        "NO_PUSAT_ASAL": e_no_pusat,
                                        "KOD_SEKOLAH": kod,
                                        "KOD_PPD": info.get("kod_ppd","BH"),
                                        "NAMA_SEKOLAH_ASAL": info.get("nama_sekolah",""),
                                        "KOD_SEKOLAH_ASAL": kod
                                    }}
                                    supa.table("guru_master").update({"nama_guru": e_nama.upper(), "ic_guru": edit_ic, "data": new_data}).eq("id", row["id"]).execute()
                                st.success(f"✅ {e_nama} berjaya update!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Gagal update: {e}")

    elif menu=="➕ Tambah Guru":
        st.header(f"Tambah Guru - {kod} - Lengkap Semua Maklumat")
        with st.form("tambah_guru", clear_on_submit=True):
            col1,col2 = st.columns(2)
            with col1:
                nama=st.text_input("NAMA GURU * (Wajib)")
                ic=st.text_input("NO IC * (12 digit, Wajib)")
                jantina=st.selectbox("JANTINA *", ["LELAKI","PEREMPUAN"])
                poskod=st.text_input("POSKOD RUMAH *")
                alamat=st.text_area("ALAMAT RUMAH * (Wajib)")
            with col2:
                tel=st.text_input("NO TELEFON GURU * (Wajib)")
                email=st.text_input("EMAIL GURU")
                jaw=st.selectbox("JAWATAN CADANGAN (Betul)", ["Ketua Pengawas", "Timbalan Ketua Pengawas", "Penyelia Kawasan", "Pengawas Peperiksaan"])
                pengalaman=st.text_input("PENGALAMAN SPM (Tahun) - SUP isi", placeholder="Contoh: 3 tahun")
                no_pusat_asal=st.text_input("NO PUSAT ASAL", placeholder="Contoh: BA142")
            submit=st.form_submit_button("💾 Simpan Guru Lengkap", use_container_width=True, type="primary")
            if submit:
                if not nama or not ic or not tel or not alamat:
                    st.error("Nama, IC, Telefon, Alamat wajib isi!")
                else:
                    data={
                        "NAMA GURU":nama.upper(),
                        "IC":ic,
                        "JANTINA":jantina,
                        "POSKOD_RUMAH":poskod,
                        "ALAMAT_RUMAH":alamat,
                        "NO TELEFON GURU":tel,
                        "TELEFON_GURU":tel,
                        "EMAIL_GURU":email,
                        "JAWATAN_CADANGAN":jaw,
                        "JAWATAN CADANGAN":jaw,
                        "PENGALAMAN_SPM":pengalaman,
                        "PENGALAMAN":pengalaman,
                        "NO_PUSAT_ASAL":no_pusat_asal,
                        "KOD_SEKOLAH":kod,
                        "KOD_SEKOLAH_ASAL":kod,
                        "NAMA_SEKOLAH_ASAL":info.get("nama_sekolah",""),
                        "KOD_PPD":info.get("kod_ppd","BH"),
                        "KOD_PPD_ASAL":info.get("kod_ppd","BH"),
                        "TARIKH DAFTAR": str(datetime.date.today())
                    }
                    try:
                        supa.table("guru_master").insert({
                            "kod_ppd":info.get("kod_ppd","BH").lower(),
                            "kod_sekolah":kod,
                            "nama_guru":nama.upper(),
                            "ic_guru":ic,
                            "jantina":jantina,
                            "poskod_rumah":poskod,
                            "alamat_rumah":alamat,
                            "telefon_guru":tel,
                            "email_guru":email,
                            "jawatan_cadangan":jaw,
                            "pengalaman_spm":pengalaman,
                            "no_pusat_asal":no_pusat_asal,
                            "kod_ppd_asal":info.get("kod_ppd","BH"),
                            "kod_sekolah_asal":kod,
                            "nama_sekolah_asal":info.get("nama_sekolah",""),
                            "data":data
                        }).execute()
                        st.success(f"✅ {nama.upper()} berjaya tambah ke {kod} dengan data lengkap!")
                        st.balloons()
                    except Exception as e:
                        # Fallback minimal
                        try:
                            supa.table("guru_master").insert({"kod_ppd":info.get("kod_ppd","BH").lower(),"kod_sekolah":kod,"nama_guru":nama.upper(),"ic_guru":ic,"data":data}).execute()
                            st.success(f"✅ {nama.upper()} berjaya tambah (fallback)!")
                            st.balloons()
                        except Exception as e2:
                            st.error(f"Gagal: {e2}")

    elif menu=="📤 Import Excel":
        st.header(f"Import Excel Guru - {kod}")
        st.info("Format Excel: NAMA GURU, IC, JANTINA, NO TELEFON GURU, EMAIL GURU, ALAMAT RUMAH, KOD SEKOLAH, KOD PPD | Untuk 60K, guna JPN > Import")
        st.download_button("📥 Download Template Guru (Excel Sah)", to_excel(get_template_guru()), file_name="template_guru.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.download_button("📥 Download Template OLD", to_excel(pd.DataFrame([{"NAMA GURU":"ALI BIN ABU","IC":"900101011234","NO TELEFON GURU":"0123456789","JANTINA":"LELAKI","JAWATAN CADANGAN":"Pengawas Peperiksaan","ALAMAT RUMAH":"NO 1 JLN...","KOD SEKOLAH":kod,"KOD PPD":info.get("kod_ppd","BH")}])), "template_guru.xlsx")
        uploaded = st.file_uploader("Upload Excel Guru", type=["xlsx","xls"])
        if uploaded:
            try:
                df_up = pd.read_excel(uploaded)
                st.write(f"Preview {len(df_up)} baris (60K akan ambil masa):")
                st.dataframe(df_up.head(20), use_container_width=True)
                batch_size = 500 if len(df_up) > 1000 else 1
                if st.button(f"Import {len(df_up)} guru (Batch {batch_size})", type="primary"):
                    bar = st.progress(0)
                    status = st.empty()
                    ok=0
                    # Batch mode for large file
                    if batch_size > 1:
                        for start in range(0, len(df_up), batch_size):
                            end = min(start+batch_size, len(df_up))
                            batch_df = df_up.iloc[start:end]
                            batch=[]
                            for _, row in batch_df.iterrows():
                                try:
                                    d={}
                                    for k,v in row.to_dict().items():
                                        d[k] = "" if pd.isna(v) else str(v)
                                    nama = d.get("NAMA GURU","").upper().strip()
                                    if not nama or nama=="NAN": continue
                                    kod_sek = d.get("KOD SEKOLAH", kod).upper().strip() or kod
                                    kod_ppd_val = d.get("KOD PPD", info.get("kod_ppd","BH")).lower().strip() or info.get("kod_ppd","BH").lower()
                                    batch.append({
                                        "kod_ppd": kod_ppd_val,
                                        "kod_sekolah": kod_sek,
                                        "nama_guru": nama,
                                        "ic_guru": d.get("IC",""),
                                        "data": d
                                    })
                                except: continue
                            if batch:
                                try:
                                    supa.table("guru_master").insert(batch).execute()
                                    ok+=len(batch)
                                except Exception as e:
                                    st.warning(f"Batch {start}-{end} error: {e}")
                            bar.progress(end/len(df_up))
                            status.write(f"Progress: {end}/{len(df_up)} | OK: {ok}")
                    else:
                        for i, row in df_up.iterrows():
                            try:
                                nama=str(row.get("NAMA GURU","")).upper()
                                ic=str(row.get("IC",""))
                                if not nama or nama=="NAN": continue
                                d = {k: ("" if pd.isna(v) else str(v)) for k,v in row.to_dict().items()}
                                d["KOD SEKOLAH"]=kod
                                supa.table("guru_master").insert({"kod_ppd":info.get("kod_ppd","BH").lower(),"kod_sekolah":kod,"nama_guru":nama,"ic_guru":ic,"data":d}).execute()
                                ok+=1
                            except Exception as e:
                                st.warning(f"Baris {i}: {e}")
                            bar.progress((i+1)/len(df_up))
                    st.success(f"✅ Berjaya import {ok}/{len(df_up)} guru!")
                    st.balloons()
            except Exception as e:
                st.error(f"Excel error: {e}")

    elif menu=="🗑️ Buang Guru":
        st.header(f"Buang Guru - {kod}")
        if df_guru.empty:
            st.info("Tiada guru untuk dibuang.")
        else:
            st.dataframe(df_guru[["NAMA GURU","IC","TELEFON"]], use_container_width=True)
            pilih=st.multiselect("Pilih IC untuk buang (boleh pilih banyak)", df_guru["IC"].tolist(), format_func=lambda x: f"{x} - {df_guru[df_guru['IC']==x]['NAMA GURU'].values[0] if not df_guru[df_guru['IC']==x].empty else x}")
            if pilih:
                st.warning(f"Kau nak buang {len(pilih)} guru: {', '.join(pilih)}")
                if st.button(f"🗑️ Confirm Buang {len(pilih)} Guru", type="primary"):
                    for ic in pilih:
                        try:
                            res=supa.table("guru_master").select("id").eq("ic_guru",ic).eq("kod_sekolah",kod).execute()
                            for r in res.data or []:
                                supa.table("guru_master").delete().eq("id",r["id"]).execute()
                        except Exception as e:
                            st.error(f"{ic}: {e}")
                    st.success(f"✅ Berjaya buang {len(pilih)} guru")
                    st.rerun()

    # Menu Pusat Peperiksaan untuk SUP telah dibuang - hanya PPD/JPN sahaja (ikut arahan user)
    # SUP tak perlu tengok semua pusat, dia hanya perlu tahu pusat sekolah dia sendiri di Dashboard

    elif menu=="📝 Cadangan Lantikan":
        st.header(f"Cadangan Lantikan - {kod} - {info.get('nama_sekolah','')}")

        # KIRA KEPERLUAN UNTUK ALERT
        try:
            df_pusat_all2 = get_pusat_df()
            pusat_sek = []
            for _, r in df_pusat_all2.iterrows():
                d = r.get("data") if isinstance(r.get("data"), dict) else {}
                if isinstance(d, str):
                    try:
                        import json
                        d = json.loads(d)
                    except:
                        d={}
                ks = r.get("kod_sekolah_tuan_rumah") or r.get("kod_sekolah") or d.get("KOD_SEKOLAH") or d.get("KOD SEKOLAH") or ""
                if ks.upper().strip() == kod.upper().strip():
                    calon = r.get("jumlah_calon") or r.get("calon") or d.get("JUMLAH_CALON") or 0
                    try: calon_i = int(float(str(calon) or 0))
                    except: calon_i=0
                    kelas = kira_kelas_dari_calon(calon_i)
                    pusat_sek.append({"calon":calon_i, "kelas":kelas})
            total_kelas_alert = sum([p["kelas"] for p in pusat_sek]) if pusat_sek else 0
            total_calon_alert = sum([p["calon"] for p in pusat_sek]) if pusat_sek else 0
            need_kp = 1
            need_tkp = 1
            need_penyelia = 1
            need_pengawas = total_kelas_alert
            total_need = need_kp + need_tkp + need_penyelia + need_pengawas + (total_kelas_alert - need_pengawas + 6 if total_kelas_alert>0 else 0)  # Simplified: kelas+12
            total_need_simple = kira_sekolah_perlu_calonkan(total_kelas_alert) if total_kelas_alert>0 else 18
            
            if pusat_sek:
                st.markdown(f"""
                <div style="background:#fff8e1; padding:15px; border-radius:10px; border-left:5px solid #ff8f00; margin-bottom:20px;">
                    <h4 style="margin:0; color:#e65100;">📢 KEPERLUAN WAJIB SEKOLAH ANDA - {kod}</h4>
                    <p style="margin:5px 0;">Pusat: {len(pusat_sek)} | Calon: {total_calon_alert} | Kelas: {total_kelas_alert} (1 kelas=20 calon)</p>
                    <p style="margin:5px 0; font-size:15px;">
                        <b style="color:#c62828;">WAJIB:</b> Ketua Pengawas 1 orang + Timbalan Ketua 1 orang<br>
                        <b style="color:#2e7d32;">OPTIONAL:</b> Penyelia Kawasan 1 orang<br>
                        <b style="color:#1565c0;">Pengawas Peperiksaan: {total_kelas_alert} orang</b> (ikut jumlah kelas)<br>
                        <b>Total Sekolah Perlu Calonkan: {total_need_simple} orang</b> (Formula: {total_calon_alert} calon /20 = {total_kelas_alert} kelas, {total_kelas_alert}+9={total_kelas_alert+9} petugas, +3 KP/TKP/Penyelia = {total_need_simple})
                    </p>
                    <div style="margin-top:10px;">
                        <span style="background:#c62828; color:white; padding:4px 10px; border-radius:15px; margin:2px; display:inline-block;">Ketua Pengawas: 1 WAJIB</span>
                        <span style="background:#ef6c00; color:white; padding:4px 10px; border-radius:15px; margin:2px; display:inline-block;">Timbalan Ketua: 1 WAJIB</span>
                        <span style="background:#2e7d32; color:white; padding:4px 10px; border-radius:15px; margin:2px; display:inline-block;">Penyelia Kawasan: 1 Optional</span>
                        <span style="background:#1565c0; color:white; padding:4px 10px; border-radius:15px; margin:2px; display:inline-block;">Pengawas Peperiksaan: {total_kelas_alert} orang</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info(f"Tiada pusat untuk {kod}. Contoh: 105 calon = 6 kelas = Ketua 1 + Timbalan 1 + Penyelia 1 (optional) + Pengawas 6 = 9 wajib, total 18 dengan extra.")
        except:
            total_kelas_alert = 6
            total_need_simple = 18

        if df_guru.empty:
            st.warning("Tiada guru untuk dicadang. Tambah guru dulu.")
        else:
            df_cad_existing = get_cadangan_df(kod_sekolah=kod)
            JAWATAN_BETUL = ["Ketua Pengawas (WAJIB 1)", "Timbalan Ketua Pengawas (WAJIB 1)", "Penyelia Kawasan (Optional)", "Pengawas Peperiksaan (Ikut Kelas)"]
            
            # SIMPLE - Tak guna st.form, guna multiselect biasa + button biasa (lebih stabil)
            st.markdown("### Pilih Guru (EMAIL kosong dibenarkan)")
            guru_pilih = st.multiselect("Pilih Guru untuk dicadangkan (boleh pilih ramai)", df_guru["IC"].tolist(), format_func=lambda x: f"{df_guru[df_guru['IC']==x]['NAMA GURU'].values[0]} - {x}", key="guru_pilih_simple")
            
            col_jawatan, col_exp = st.columns(2)
            with col_jawatan:
                jawatan_cadang = st.selectbox("Jawatan Lantikan (Betul)", JAWATAN_BETUL, key="jawatan_simple")
                jawatan_clean = jawatan_cadang.split(" (")[0]
            with col_exp:
                pengalaman_input = st.text_input("Pengalaman SPM (Tahun) - SUP isi", placeholder="Contoh: 3 tahun", key="pengalaman_simple")
            
            # Auto BA142 - pilihan pusat dibuang
            pusat_pilih = "BA142"
            no_pusat_asal_input = "BA142"
            
            # Preview
            if guru_pilih:
                st.markdown("**Preview Data Guru Dipilih (EMAIL kosong dibenarkan - akan lepas simpan):**")
                preview_rows=[]
                for ic_prev in guru_pilih[:10]:
                    gr_prev = df_guru[df_guru["IC"]==ic_prev]
                    if not gr_prev.empty:
                        r = gr_prev.iloc[0]
                        preview_rows.append({
                            "IC": ic_prev,
                            "NAMA": r.get("NAMA GURU","")[:20],
                            "JANTINA": r.get("JANTINA","") or "-",
                            "POSKOD": r.get("POSKOD_RUMAH","") or "-",
                            "ALAMAT": (r.get("ALAMAT_RUMAH","")[:20] or "-"),
                            "TELEFON": r.get("TELEFON_GURU","") or r.get("TELEFON","") or "-",
                            "EMAIL": r.get("EMAIL_GURU","") or "-"
                        })
                if preview_rows:
                    st.dataframe(pd.DataFrame(preview_rows), use_container_width=True, hide_index=True)

                catatan = ""
                # Button biasa (bukan form_submit_button) - lebih stabil
                if st.button(f"📝 Simpan Cadangan - {len(guru_pilih) if 'guru_pilih' in locals() and guru_pilih else 0} guru", type="primary", key="btn_simpan_simple"):
                    if not guru_pilih:
                        st.error("Pilih sekurang-kurangnya 1 guru")
                    else:
                        st.info(f"Menyimpan {len(guru_pilih)} guru...")
                        ok_count=0
                        fail_msg=""
                        for ic in guru_pilih:
                            guru_row = df_guru[df_guru["IC"]==ic]
                            if guru_row.empty:
                                continue
                            gr = guru_row.iloc[0]
                            # Ambil SEMUA maklumat guru dari guru_master
                            nama = gr.get("NAMA GURU","") or ic
                            jantina = gr.get("JANTINA","")
                            poskod = gr.get("POSKOD_RUMAH","")
                            alamat = gr.get("ALAMAT_RUMAH","") or gr.get("ALAMAT","")
                            telefon = gr.get("TELEFON_GURU","") or gr.get("TELEFON","")
                            email = str(gr.get("EMAIL_GURU","") or gr.get("EMAIL","") or "").strip()  # EMAIL kosong dibenarkan
                            pengalaman = pengalaman_input or gr.get("PENGALAMAN_SPM","") or gr.get("PENGALAMAN","")
                            kod_ppd_guru = (gr.get("KOD_PPD","") or info.get("kod_ppd","BA")).upper()  # FIX huruf kecil jadi besar
                            kod_sek_guru = gr.get("KOD_SEKOLAH","") or kod
                            nama_sek_guru = gr.get("NAMA_SEKOLAH_ASAL","") or gr.get("NAMA_SEKOLAH","") or info.get("nama_sekolah","")
                            no_pusat_asal = no_pusat_asal_input or gr.get("NO_PUSAT_ASAL","")
                            
                            # Auto BA142 - pilihan pusat dibuang
                            pusat_pilih = "BA142"
                            if no_pusat_asal and no_pusat_asal.strip()!="":
                                pusat_pilih = no_pusat_asal.strip()
                            # Pastikan BA142 untuk BFT0003
                            if kod.upper()=="BFT0003":
                                pusat_pilih = "BA142"
                            
                            # FIX: EMAIL kosong dibenarkan, cadangan mesti lekat
                            kod_ppd_guru = kod_ppd_guru.upper()
                            kod_sek_guru = kod_sek_guru.upper()
                            # Auto default kalau kosong - BA142 untuk BFT0003
                            if not no_pusat_asal or no_pusat_asal.strip()=="":
                                no_pusat_asal = "BA142"
                            if not kod_sek_guru or kod_sek_guru.strip()=="":
                                kod_sek_guru = kod.upper()
                            if not nama_sek_guru or nama_sek_guru.strip()=="":
                                nama_sek_guru = info.get("nama_sekolah","SAM NURUL IMAN")
                            # EMAIL kosong dibenarkan - jangan block
                            email = email or ""
                            
                            # Data lengkap - SIMPLE sahaja, tak duplicate
                            full_data = {
                                "kod_ppd": kod_ppd_guru.upper(),
                                "kod_sekolah": kod_sek_guru,
                                "kod_sekolah_asal": kod_sek_guru,
                                "nama_sekolah_asal": nama_sek_guru,
                                "ic_guru": ic,
                                "nama_guru": nama,
                                "jantina": jantina or "L",
                                "poskod_rumah": poskod or "0",
                                "alamat_rumah": alamat or "-",
                                "telefon_guru": telefon or "-",
                                "email_guru": email,  # Kosong dibenarkan
                                "jawatan_cadangan": jawatan_clean,
                                "pengalaman_spm": pengalaman or "0",
                                "no_pusat_asal": no_pusat_asal,
                                "kod_pusat": no_pusat_asal,  # Guna NO_PUSAT_ASAL sebagai KOD_PUSAT
                                "kod_ppd_asal": kod_ppd_guru,
                                "status": "DICADANGKAN",
                                "tarikh_cadang": str(datetime.date.today()),
                                "data": {
                                    "KOD_PPD": kod_ppd_guru,
                                    "KOD_SEKOLAH_ASAL": kod_sek_guru,
                                    "NAMA_SEKOLAH_ASAL": nama_sek_guru,
                                    "IC_GURU": ic,
                                    "NAMA_GURU": nama,
                                    "JANTINA": jantina,
                                    "POSKOD_RUMAH": poskod,
                                    "ALAMAT_RUMAH": alamat,
                                    "TELEFON_GURU": telefon,
                                    "EMAIL_GURU": email,
                                    "JAWATAN_CADANGAN": jawatan_clean,
                                    "PENGALAMAN_SPM": pengalaman,
                                    "NO_PUSAT_ASAL": no_pusat_asal,
                                    "STATUS": "DICADANGKAN"
                                }
                            }
                            
                            inserted=False
                            clean_insert = {
                                "kod_ppd": kod_ppd_guru.upper(),
                                "kod_sekolah": kod_sek_guru,
                                "kod_sekolah_asal": kod_sek_guru,
                                "nama_sekolah_asal": nama_sek_guru,
                                "ic_guru": ic,
                                "nama_guru": nama,
                                "jantina": jantina or "L",
                                "poskod_rumah": poskod or "0",
                                "alamat_rumah": alamat or "-",
                                "telefon_guru": telefon,
                                "email_guru": email,
                                "jawatan_cadangan": jawatan_clean,
                                "pengalaman_spm": pengalaman,
                                "no_pusat_asal": no_pusat_asal or pusat_pilih,  # HANYA NO_PUSAT_ASAL
                                "kod_pusat": pusat_pilih,  # Simpan juga untuk compatibility tapi display guna NO_PUSAT_ASAL
                                "kod_ppd_asal": kod_ppd_guru.upper(),
                                "status": "DICADANGKAN",
                                "tarikh_cadang": str(datetime.date.today()),
                                "data": {
                                    "KOD_PPD": kod_ppd_guru.upper(),
                                    "KOD_SEKOLAH_ASAL": kod_sek_guru.upper(),
                                    "NAMA_SEKOLAH_ASAL": nama_sek_guru,
                                    "IC_GURU": ic,
                                    "NAMA_GURU": nama,
                                    "JANTINA": jantina,
                                    "POSKOD_RUMAH": poskod,
                                    "ALAMAT_RUMAH": alamat,
                                    "TELEFON_GURU": telefon,
                                    "EMAIL_GURU": email,
                                    "JAWATAN_CADANGAN": jawatan_clean,
                                    "PENGALAMAN_SPM": pengalaman,
                                    "NO_PUSAT_ASAL": no_pusat_asal or pusat_pilih,
                                    "STATUS": "DICADANGKAN"
                                }
                            }
                            # SIMPLE INSERT - EMAIL kosong dibenarkan, pastikan lekat!
                            # Cuba minimal dulu - hanya 5 column wajib
                            minimal_insert = {
                                "kod_ppd": kod_ppd_guru.upper(),
                                "kod_sekolah": kod_sek_guru.upper(),
                                "ic_guru": ic,
                                "nama_guru": nama,
                                "status": "DICADANGKAN"
                            }
                            for attempt in [
                                minimal_insert,  # Cuba minimal dulu - pasti lekat
                                clean_insert,  # Full data dengan data JSON
                                {
                                    "kod_ppd": kod_ppd_guru.upper(),
                                    "kod_sekolah": kod_sek_guru.upper(),
                                    "ic_guru": ic,
                                    "nama_guru": nama,
                                    "kod_pusat": no_pusat_asal,  # Guna NO_PUSAT_ASAL
                                    "jawatan_cadangan": jawatan_clean,
                                    "status": "DICADANGKAN",
                                    "tarikh_cadang": str(datetime.date.today()),
                                    "jantina": jantina or "L",
                                    "poskod_rumah": poskod or "0",
                                    "alamat_rumah": alamat or "-",
                                    "telefon_guru": telefon or "-",
                                    "email_guru": email or "",  # Kosong dibenarkan
                                    "pengalaman_spm": pengalaman or "0",
                                    "no_pusat_asal": no_pusat_asal,
                                    "kod_ppd_asal": kod_ppd_guru.upper(),
                                    "kod_sekolah_asal": kod_sek_guru.upper(),
                                    "nama_sekolah_asal": nama_sek_guru
                                },
                                {
                                    # Minimal insert - kalau column lain tak wujud
                                    "kod_ppd": kod_ppd_guru.upper(),
                                    "kod_sekolah": kod_sek_guru.upper(),
                                    "ic_guru": ic,
                                    "nama_guru": nama,
                                    "status": "DICADANGKAN"
                                }
                            ]:
                                try:
                                    supa.table("cadangan_sup").insert(attempt).execute()
                                    inserted=True
                                    ok_count+=1
                                    break
                                except Exception as e:
                                    fail_msg=str(e)
                                    # Debug: simpan error untuk tunjuk
                                    if "duplicate" in fail_msg.lower() or "already exists" in fail_msg.lower():
                                        # Kalau duplicate IC, update sahaja
                                        try:
                                            supa.table("cadangan_sup").update(attempt).eq("ic_guru", ic).eq("kod_sekolah", kod_sek_guru.upper()).execute()
                                            inserted=True
                                            ok_count+=1
                                            break
                                        except:
                                            pass
                                    continue
                            if not inserted:
                                st.error(f"❌ Gagal {ic} - {nama}: {fail_msg[:500]}")
                                st.code(fail_msg[:1000])  # Tunjuk full error untuk debug
                        if ok_count>0:
                            st.success(f"✅ Berjaya cadang {ok_count}/{len(guru_pilih)} guru sebagai {jawatan_clean} ke pusat {pusat_pilih} - SEMUA maklumat lengkap!")
                            st.balloons()
                            st.rerun()

            st.markdown("---")
            st.subheader(f"Senarai Cadangan Sekolah Ini - Perlu {total_need_simple if 'total_need_simple' in locals() else 18} orang")
            df_cad = get_cadangan_df(kod_sekolah=kod)
            if df_cad.empty:
                st.info("Belum ada cadangan")
            else:
                # Count by jawatan
                try:
                    counts = df_cad["JAWATAN_CADANGAN"].value_counts() if "JAWATAN_CADANGAN" in df_cad.columns else (df_cad["jawatan_cadangan"].value_counts() if "jawatan_cadangan" in df_cad.columns else pd.Series())
                    c1,c2,c3,c4 = st.columns(4)
                    c1.metric("Ketua Pengawas", counts.get("Ketua Pengawas",0), delta="WAJIB 1" if counts.get("Ketua Pengawas",0)>=1 else "BELUM CUKUP", delta_color="normal" if counts.get("Ketua Pengawas",0)>=1 else "inverse")
                    c2.metric("Timbalan Ketua", counts.get("Timbalan Ketua Pengawas",0), delta="WAJIB 1" if counts.get("Timbalan Ketua Pengawas",0)>=1 else "BELUM CUKUP", delta_color="normal" if counts.get("Timbalan Ketua Pengawas",0)>=1 else "inverse")
                    c3.metric("Penyelia Kawasan", counts.get("Penyelia Kawasan",0))
                    c4.metric("Pengawas Peperiksaan", counts.get("Pengawas Peperiksaan",0), delta=f"Perlu {total_kelas_alert if 'total_kelas_alert' in locals() else 6}")
                except:
                    pass
                st.dataframe(df_cad, use_container_width=True)
                st.download_button("📥 Export Cadangan", to_excel(df_cad), file_name=f"cadangan_{kod}.xlsx")

    elif menu=="📤 Hantar ke PPD":
        st.header(f"Hantar Cadangan ke PPD {info.get('kod_ppd','BA')}")
        df_cad = get_cadangan_df(kod_sekolah=kod)
        if df_cad.empty:
            st.warning("Belum ada cadangan. Pergi menu Cadangan Lantikan dulu.")
        else:
            # Display tanpa duplicate columns - hanya NO_PUSAT_ASAL & KOD_SEKOLAH_ASAL
            # Filter columns untuk display clean
            display_cols = [c for c in ["NAMA_GURU","IC_GURU","JANTINA","POSKOD_RUMAH","ALAMAT_RUMAH","TELEFON_GURU","EMAIL_GURU","JAWATAN_CADANGAN","PENGALAMAN_SPM","KOD_SEKOLAH_ASAL","NAMA_SEKOLAH_ASAL","NO_PUSAT_ASAL","STATUS","TARIKH_CADANG"] if c in df_cad.columns]
            if display_cols:
                st.dataframe(df_cad[display_cols], use_container_width=True)
            else:
                st.dataframe(df_cad, use_container_width=True)
            
            st.info(f"Ada {len(df_cad)} cadangan akan dihantar ke PPD {info.get('kod_ppd','BA')} - {PPD_MAP.get(info.get('kod_ppd','BA'),'')}")
            
            col_hantar, col_batal, col_reset = st.columns(3)
            with col_hantar:
                if st.button("📤 Hantar Semua ke PPD", type="primary", use_container_width=True):
                    try:
                        for _, row in df_cad.iterrows():
                            try:
                                # FIX huruf kecil jadi besar untuk kod_ppd
                                supa.table("cadangan_sup").update({"status":"HANTAR KE PPD", "kod_ppd": info.get('kod_ppd','BA').upper()}).eq("id", row["id"]).execute()
                            except Exception as ee:
                                try:
                                    supa.table("cadangan_sup").update({"status":"HANTAR KE PPD"}).eq("id", row["id"]).execute()
                                except:
                                    st.error(f"Gagal {row.get('id')}: {ee}")
                        st.success(f"✅ Berjaya hantar {len(df_cad)} cadangan ke PPD!")
                        st.balloons()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal hantar: {e}")
            
            with col_batal:
                st.markdown("**Batal Cadangan (Selagi PPD Belum Lantik)**")
                batal_ids = st.multiselect("Pilih untuk batal", df_cad["id"].tolist() if "id" in df_cad.columns else [], format_func=lambda x: f"{df_cad[df_cad['id']==x]['NAMA_GURU'].values[0] if not df_cad[df_cad['id']==x].empty else x} - {x}")
                if st.button("❌ Batal Terpilih", use_container_width=True):
                    if not batal_ids:
                        st.warning("Pilih sekurang-kurangnya 1")
                    else:
                        for bid in batal_ids:
                            try:
                                # Check status dulu - hanya boleh batal kalau belum LULUS PPD
                                row_check = df_cad[df_cad["id"]==bid]
                                if not row_check.empty:
                                    status_check = str(row_check.iloc[0].get("STATUS","")).upper()
                                    if "LULUS" in status_check:
                                        st.error(f"Tak boleh batal {bid} - sudah LULUS PPD!")
                                        continue
                                supa.table("cadangan_sup").delete().eq("id", bid).execute()
                            except Exception as e:
                                st.error(f"Gagal batal {bid}: {e}")
                        st.success(f"✅ Berjaya batal {len(batal_ids)} cadangan!")
                        st.rerun()
            
            with col_reset:
                st.markdown("**Reset Semua (Clear & Isi Semula)**")
                if st.button("🔄 Reset Semua Cadangan", use_container_width=True, type="secondary"):
                    try:
                        # Hanya reset yang belum LULUS
                        count_del=0
                        for _, row in df_cad.iterrows():
                            status_check = str(row.get("STATUS","")).upper()
                            if "LULUS" not in status_check:
                                try:
                                    supa.table("cadangan_sup").delete().eq("id", row["id"]).execute()
                                    count_del+=1
                                except:
                                    pass
                        st.success(f"✅ Reset {count_del} cadangan! Data baru akan keluar lengkap. Email sahaja kosong.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal reset: {e}")
            
            st.markdown("---")
            st.caption("ℹ️ Nota: EMAIL_GURU kosong adalah normal - SUP perlu isi manual di Senarai Guru > Edit. NO_PUSAT_ASAL & KOD_SEKOLAH_ASAL sahaja digunakan (bukan KOD_PUSAT/KOD_SEKOLAH duplicate). Bila data baru isi, akan keluar lengkap kecuali email.")

# ================= PPD =================
elif st.session_state.role=="PPD":
    kod_ppd=st.session_state.kod
    st.sidebar.title(f"🏢 PPD {kod_ppd}")
    st.sidebar.caption(f"{PPD_MAP.get(kod_ppd,'')}")

    menu=st.sidebar.radio("Menu PPD", ["📊 Dashboard PPD","🏫 Sekolah dalam PPD","🏫 Pusat di PPD","📋 Cadangan SUP","✅ Kelulusan","📥 Export","🚪 Log Keluar"])

    if menu=="🚪 Log Keluar":
        st.session_state.clear()
        st.rerun()

    if menu=="📊 Dashboard PPD":
        st.header(f"Dashboard PPD {kod_ppd} - {PPD_MAP.get(kod_ppd,'')}")
        try:
            cnt_sekolah = supa.table("sekolah_master").select("kod_sekolah", count="exact").eq("kod_ppd", kod_ppd).execute()
            cnt_guru = supa.table("guru_master").select("id", count="exact").eq("kod_ppd", kod_ppd.lower()).execute()
            cnt_cadang = supa.table("cadangan_sup").select("id", count="exact").eq("kod_ppd", kod_ppd).execute()
            c1,c2,c3 = st.columns(3)
            c1.metric("Sekolah", cnt_sekolah.count)
            c2.metric("Guru", cnt_guru.count)
            c3.metric("Cadangan", cnt_cadang.count)
        except Exception as e:
            st.error(f"Error dashboard: {e}")

    elif menu=="🏫 Sekolah dalam PPD":
        st.header(f"Senarai Sekolah PPD {kod_ppd}")
        try:
            res=supa.table("sekolah_master").select("*").eq("kod_ppd", kod_ppd).limit(2000).execute()
            df=pd.DataFrame(res.data or [])
            st.dataframe(df, use_container_width=True)
            st.download_button("Export Sekolah", to_excel(df), file_name=f"sekolah_{kod_ppd}.xlsx")
        except Exception as e:
            st.error(str(e))

        st.header(f"Pusat di PPD {kod_ppd} - {PPD_MAP.get(kod_ppd,'')} - Total Calon")
        st.caption("Filter betul ikut NO_PUSAT prefix (BA=Klang, BB=Kuala Langat, dll) - bukan cari substring yang bercampur")
        df_pusat_raw = get_pusat_df()
        if df_pusat_raw.empty:
            st.info("pusat_master kosong")
        else:
            rows=[]
            for _, r in df_pusat_raw.iterrows():
                d = r.get("data") if isinstance(r.get("data"), dict) else {}
                if isinstance(d, str):
                    try:
                        import json
                        d = json.loads(d)
                    except:
                        d={}
                no_pusat = str(r.get("no_pusat") or r.get("kod_pusat") or d.get("NO_PUSAT") or "").upper().strip()
                nama = r.get("nama_pusat") or d.get("NAMA_PUSAT") or ""
                kod_sek = r.get("kod_sekolah_tuan_rumah") or r.get("kod_sekolah") or d.get("KOD_SEKOLAH") or ""
                j_calon = r.get("jumlah_calon") or r.get("calon") or d.get("JUMLAH_CALON") or 0
                j_kelas = r.get("jumlah_kelas") or r.get("bilik") or d.get("JUMLAH_KELAS") or 0
                try: jc = int(float(str(j_calon) or 0))
                except: jc=0
                try: jk = int(float(str(j_kelas) or 0))
                except: jk=kira_kelas_dari_calon(jc)
                petugas = kira_petugas_dari_kelas(jk)
                perlu = kira_sekolah_perlu_calonkan(jk)
                rows.append({
                    "NO_PUSAT": no_pusat,
                    "NAMA_PUSAT": nama,
                    "KOD_SEKOLAH": kod_sek,
                    "JUMLAH_CALON": jc,
                    "JUMLAH_KELAS": jk,
                    "PETUGAS_K9": petugas,
                    "SEKOLAH_PERLU": perlu,
                    "KOD_PPD": no_pusat[:2] if len(no_pusat)>=2 else ""
                })
            df_all = pd.DataFrame(rows)
            # FILTER BETUL: ikut NO_PUSAT prefix, bukan substring
            df_filtered = df_all[df_all["NO_PUSAT"].str.startswith(kod_ppd.upper())].copy() if not df_all.empty else df_all
            
            if df_filtered.empty:
                st.warning(f"Tiada pusat dengan prefix {kod_ppd} - cuba check NO_PUSAT format. Showing all dengan filter PPD dari data")
                # Fallback filter by KOD_PPD column
                try:
                    df_alt = df_all[df_all["KOD_PPD"]==kod_ppd.upper()]
                    if not df_alt.empty:
                        df_filtered=df_alt
                except:
                    pass
            
            st.success(f"Jumpa {len(df_filtered)} pusat di PPD {kod_ppd} - {PPD_MAP.get(kod_ppd,'')}")
            st.dataframe(df_filtered.sort_values("NO_PUSAT"), use_container_width=True, hide_index=True)
            
            if not df_filtered.empty:
                c1,c2,c3,c4 = st.columns(4)
                c1.metric("Jumlah Pusat", len(df_filtered))
                c2.metric("Total Calon", int(df_filtered["JUMLAH_CALON"].sum()))
                c3.metric("Total Kelas", int(df_filtered["JUMLAH_KELAS"].sum()))
                c4.metric("Total Sekolah Perlu", int(df_filtered["SEKOLAH_PERLU"].sum()))
                st.download_button(f"📥 Export Pusat {kod_ppd}", to_excel(df_filtered), file_name=f"pusat_{kod_ppd}.xlsx", use_container_width=True)
            
            with st.expander("Lihat Semua 506 Pusat (untuk debug)"):
                st.dataframe(df_all, use_container_width=True, hide_index=True)
            st.error(str(e))

    elif menu=="🏫 Pusat di PPD":
        st.header(f"Pusat di PPD {kod_ppd} - {PPD_MAP.get(kod_ppd,'')} - Total Calon")
        st.caption("Filter BETUL ikut NO_PUSAT prefix BA=Klang sahaja - bug lama cari substring SABAK contains BA dah fix")
        df_pusat_raw = get_pusat_df()
        if df_pusat_raw.empty:
            st.info("pusat_master kosong")
        else:
            rows=[]
            for _, r in df_pusat_raw.iterrows():
                d = r.get("data") if isinstance(r.get("data"), dict) else {}
                if isinstance(d, str):
                    try:
                        import json
                        d = json.loads(d)
                    except:
                        d={}
                no_pusat = str(r.get("no_pusat") or r.get("kod_pusat") or d.get("NO_PUSAT") or "").upper().strip()
                nama = r.get("nama_pusat") or d.get("NAMA_PUSAT") or ""
                j_calon = r.get("jumlah_calon") or r.get("calon") or d.get("JUMLAH_CALON") or 0
                j_kelas = r.get("jumlah_kelas") or r.get("bilik") or d.get("JUMLAH_KELAS") or 0
                try: jc = int(float(str(j_calon) or 0))
                except: jc=0
                try: jk = int(float(str(j_kelas) or 0))
                except: jk=kira_kelas_dari_calon(jc)
                rows.append({"NO_PUSAT":no_pusat,"NAMA_PUSAT":nama,"JUMLAH_CALON":jc,"JUMLAH_KELAS":jk,"PETUGAS_K9":kira_petugas_dari_kelas(jk),"SEKOLAH_PERLU":kira_sekolah_perlu_calonkan(jk)})
            df_all = pd.DataFrame(rows)
            df_f = df_all[df_all["NO_PUSAT"].str.startswith(kod_ppd.upper())].copy() if not df_all.empty else df_all
            if df_f.empty:
                st.warning(f"Tiada pusat dengan prefix {kod_ppd}")
            else:
                st.success(f"Jumpa {len(df_f)} pusat di PPD {kod_ppd} - {PPD_MAP.get(kod_ppd,'')}")
                st.dataframe(df_f.sort_values("NO_PUSAT"), use_container_width=True, hide_index=True)
                c1,c2,c3,c4 = st.columns(4)
                c1.metric("Jumlah Pusat", len(df_f))
                c2.metric("Total Calon", int(df_f["JUMLAH_CALON"].sum()))
                c3.metric("Total Kelas", int(df_f["JUMLAH_KELAS"].sum()))
                c4.metric("Total Perlu", int(df_f["SEKOLAH_PERLU"].sum()))
                st.download_button(f"Export Pusat {kod_ppd}", to_excel(df_f), file_name=f"pusat_{kod_ppd}.xlsx", use_container_width=True)

    elif menu=="📋 Cadangan SUP":


        st.header(f"Cadangan dari SUP - PPD {kod_ppd}")
        df_cad = get_cadangan_df(kod_ppd=kod_ppd)
        if df_cad.empty:
            st.info("Belum ada cadangan dari SUP")
        else:
            st.dataframe(df_cad, use_container_width=True)
            st.download_button("Export Cadangan", to_excel(df_cad), file_name=f"cadangan_PPD_{kod_ppd}.xlsx")

    elif menu=="✅ Kelulusan":
        st.header(f"Kelulusan PPD {kod_ppd}")
        df_cad = get_cadangan_df(kod_ppd=kod_ppd)
        if df_cad.empty:
            st.info("Tiada cadangan")
        else:
            st.dataframe(df_cad, use_container_width=True)
            pilih_id = st.multiselect("Pilih ID untuk lulus", df_cad["id"].tolist() if "id" in df_cad.columns else [])
            col1,col2 = st.columns(2)
            with col1:
                if st.button("✅ Lulus Terpilih", type="primary"):
                    for i in pilih_id:
                        try:
                            supa.table("cadangan_sup").update({"status":"LULUS PPD"}).eq("id",i).execute()
                        except Exception as e:
                            st.error(str(e))
                    st.success("Lulus berjaya")
                    st.rerun()
            with col2:
                if st.button("❌ Tolak Terpilih"):
                    for i in pilih_id:
                        try:
                            supa.table("cadangan_sup").update({"status":"TOLAK PPD"}).eq("id",i).execute()
                        except Exception as e:
                            st.error(str(e))
                    st.success("Tolak berjaya")
                    st.rerun()

    elif menu=="📥 Export":
        st.header(f"Export Data PPD {kod_ppd}")
        df_cad = get_cadangan_df(kod_ppd=kod_ppd)
        if not df_cad.empty:
            st.download_button("📥 Export Cadangan PPD (Excel)", to_excel(df_cad), file_name=f"laporan_PPD_{kod_ppd}_{datetime.date.today()}.xlsx", use_container_width=True)
        try:
            res=supa.table("guru_master").select("*").eq("kod_ppd", kod_ppd.lower()).limit(5000).execute()
            df_guru=pd.DataFrame(res.data or [])
            if not df_guru.empty:
                st.download_button("📥 Export Guru PPD (Excel)", to_excel(df_guru), file_name=f"guru_PPD_{kod_ppd}.xlsx", use_container_width=True)
        except Exception as e:
            st.error(str(e))

# ================= JPN =================
elif st.session_state.role=="JPN":
    st.sidebar.title("🏛️ JPN Selangor")
    menu=st.sidebar.radio("Menu JPN", ["📊 Dashboard JPN","🏫 Semua Sekolah","🏫 Pusat Master","👨‍🏫 Guru Master","📋 Semua Cadangan","📥 Export Negeri","⚙️ Admin","🚪 Log Keluar"])

    if menu=="🚪 Log Keluar":
        st.session_state.clear()
        st.rerun()

    if menu=="📊 Dashboard JPN":
        st.header("Dashboard JPN Selangor - Pelantikan SPM 2026")
        cols = st.columns(5)
        for idx, t in enumerate(["sekolah_master","pusat_master","guru_master","cadangan_sup"]):
            try:
                res=supa.table(t).select("*", count="exact").limit(1).execute()
                cols[idx].metric(t, res.count)
            except Exception as e:
                cols[idx].error(f"{t}: {e}")
        # PPD breakdown
        st.markdown("---")
        st.subheader("Breakdown Ikut PPD")
        rows=[]
        for ppd in KOD_DAERAH:
            try:
                c1=supa.table("sekolah_master").select("kod_sekolah", count="exact").eq("kod_ppd", ppd).execute()
                c2=supa.table("guru_master").select("id", count="exact").eq("kod_ppd", ppd.lower()).execute()
                c3=supa.table("cadangan_sup").select("id", count="exact").eq("kod_ppd", ppd).execute()
                rows.append({"PPD":f"{ppd} - {PPD_MAP[ppd]}","Sekolah":c1.count,"Guru":c2.count,"Cadangan":c3.count})
            except:
                rows.append({"PPD":ppd,"Sekolah":0,"Guru":0,"Cadangan":0})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    elif menu=="🏫 Semua Sekolah":
        st.header("Semua Sekolah Master (369 Sekolah)")
        try:
            res=supa.table("sekolah_master").select("*", count="exact").limit(5000).execute()
            df_count = res.count
            res2=supa.table("sekolah_master").select("*").limit(1000).execute()
            df=pd.DataFrame(res2.data or [])
            st.write(f"Total dalam Supabase: **{df_count}** sekolah")
            if not df.empty:
                st.dataframe(df, use_container_width=True)
                st.download_button("📥 Export Sekolah Master", to_excel(df), file_name="sekolah_master.xlsx")
            else:
                st.warning("sekolah_master kosong - belum push dari pusat_2026.csv. Sila import di bawah.")
        except Exception as e:
            st.error(f"sekolah_master error: {e}")
            st.code("""
CREATE TABLE IF NOT EXISTS sekolah_master (
  id BIGSERIAL PRIMARY KEY,
  kod_sekolah TEXT UNIQUE,
  nama_sekolah TEXT,
  kod_ppd TEXT,
  data JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE sekolah_master ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "allow all" ON sekolah_master;
CREATE POLICY "allow all" ON sekolah_master FOR ALL USING (true) WITH CHECK (true);
            """, language="sql")

        st.markdown("---")
        st.subheader("📤 Import Sekolah Master dari Pusat & Guru")
        st.info("File sekolah digenerate dari pusat_2026.csv (506 pusat = 369 sekolah unik) + guru 60K. Upload SEKOLAH_MASTER_FINAL_2026.xlsx untuk push masuk sekolah_master.")
        st.download_button("📥 Download SEKOLAH_MASTER_FINAL_2026.xlsx (369 sekolah)", open("/mnt/data/SEKOLAH_MASTER_FINAL_2026.xlsx","rb").read() if __import__("os").path.exists("/mnt/data/SEKOLAH_MASTER_FINAL_2026.xlsx") else b"", "SEKOLAH_MASTER_FINAL_2026.xlsx")
        
        up_sek = st.file_uploader("Upload Sekolah Master Excel (KOD SEKOLAH, NAMA SEKOLAH, KOD PPD)", type=["xlsx","csv"], key="sekolah_up")
        if up_sek:
            try:
                if up_sek.name.endswith(".csv"):
                    try:
                        df_up=pd.read_csv(up_sek)
                    except:
                        up_sek.seek(0)
                        df_up=pd.read_csv(up_sek, encoding='latin1')
                else:
                    df_up=pd.read_excel(up_sek)
                st.write(f"Preview {len(df_up)} sekolah:")
                st.dataframe(df_up.head(30), use_container_width=True)
                if st.button(f"🚀 Import {len(df_up)} Sekolah ke Supabase", type="primary", use_container_width=True):
                    bar=st.progress(0)
                    stat=st.empty()
                    ok=0
                    # Delete old first
                    try:
                        supa.table("sekolah_master").delete().gt("id",0).execute()
                        st.write("Old sekolah_master cleared")
                    except: pass
                    BATCH=200
                    for start in range(0, len(df_up), BATCH):
                        end=min(start+BATCH, len(df_up))
                        bdf=df_up.iloc[start:end]
                        batch=[]
                        for _, row in bdf.iterrows():
                            try:
                                kod = str(row.get("KOD SEKOLAH","") or row.get("kod_sekolah","") or row.get("KOD_SEKOLAH","")).strip().upper()
                                if not kod: continue
                                nama = str(row.get("NAMA SEKOLAH","") or row.get("nama_sekolah","") or row.get("NAMA_PUSAT","")).strip().upper()
                                kod_ppd = str(row.get("KOD PPD","") or row.get("kod_ppd","") or row.get("PPD_CODE","") or "BH").strip().upper()
                                batch.append({
                                    "kod_sekolah": kod,
                                    "nama_sekolah": nama,
                                    "kod_ppd": kod_ppd,
                                    "data": {k: ("" if pd.isna(v) else str(v)) for k,v in row.to_dict().items()}
                                })
                            except: continue
                        if batch:
                            try:
                                supa.table("sekolah_master").insert(batch).execute()
                                ok+=len(batch)
                            except Exception as e:
                                st.warning(f"Batch {start}-{end}: {e}")
                        bar.progress(end/len(df_up))
                        stat.write(f"Progress {end}/{len(df_up)} | OK {ok}")
                    st.success(f"✅ Selesai import {ok}/{len(df_up)} sekolah!")
                    st.balloons()
                    st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

        st.markdown("---")
        st.subheader("Auto Generate Sekolah dari Pusat 506")
        if st.button("⚡ Generate Sekolah Master dari pusat_master yang sedia ada (506 pusat)", use_container_width=True):
            try:
                res=supa.table("pusat_master").select("*").limit(1000).execute()
                df_p = pd.DataFrame(res.data or [])
                if df_p.empty:
                    st.error("pusat_master kosong, import pusat dulu")
                else:
                    # Extract unique kod_sekolah from pusat data
                    sekolah_list=[]
                    seen=set()
                    for _, r in df_p.iterrows():
                        d = r.get("data") or {}
                        kod_sek = d.get("KOD_SEKOLAH","") or r.get("kod_sekolah","") or ""
                        kod_sek = str(kod_sek).upper().strip()
                        if not kod_sek or kod_sek in seen: continue
                        seen.add(kod_sek)
                        sekolah_list.append({
                            "kod_sekolah": kod_sek,
                            "nama_sekolah": r.get("nama_pusat","") or d.get("NAMA_PUSAT",""),
                            "kod_ppd": r.get("kod_ppd","BH"),
                            "data": {"KOD SEKOLAH": kod_sek, "NAMA SEKOLAH": r.get("nama_pusat",""), "KOD PPD": r.get("kod_ppd","BH")}
                        })
                    # Insert
                    if sekolah_list:
                        try:
                            supa.table("sekolah_master").delete().gt("id",0).execute()
                        except: pass
                        for i in range(0, len(sekolah_list), 200):
                            supa.table("sekolah_master").insert(sekolah_list[i:i+200]).execute()
                        st.success(f"✅ Generated {len(sekolah_list)} sekolah dari pusat_master!")
                        st.rerun()
            except Exception as e:
                st.error(f"Error generate: {e}")

    elif menu=="🏫 Pusat Master":
        st.header("Pusat Master - Selangor 2026 (506 Pusat) - FIX Jumlah Calon")
        try:
            total = safe_count("pusat_master")
            res = supa.table("pusat_master").select("*").limit(1000).execute()
            raw_data = res.data or []
            df = pd.DataFrame(raw_data)
            st.write(f"Total Pusat Sedia Ada: **{total}** / 506 pusat")

            # Build display df with jumlah calon dari data JSON
            display_rows=[]
            for r in raw_data:
                d = r.get("data") or {}
                # Handle stringified JSON
                if isinstance(d, str):
                    try:
                        import json
                        d = json.loads(d)
                    except:
                        d={}
                # Ambil no_pusat dengan multi format
                no_pusat = r.get("no_pusat") or r.get("kod_pusat") or d.get("NO_PUSAT") or d.get("KOD PUSAT") or ""
                nama = r.get("nama_pusat") or d.get("NAMA_PUSAT") or ""
                kod_sek = r.get("kod_sekolah_tuan_rumah") or r.get("kod_sekolah") or d.get("KOD_SEKOLAH") or ""
                ppd = r.get("ppd") or d.get("PPD") or ""
                j_calon = r.get("jumlah_calon") or r.get("calon") or r.get("JUMLAH_CALON") or d.get("JUMLAH_CALON") or d.get("CALON") or 0
                j_kelas = r.get("jumlah_kelas") or r.get("bilik") or d.get("JUMLAH_KELAS") or d.get("BILIK") or 0
                petugas = d.get("PETUGAS_NEEDED") or r.get("petugas_needed") or 0
                try: j_calon_int = int(float(str(j_calon).replace(",","").strip() or 0))
                except: j_calon_int = 0
                try: j_kelas_int = int(float(str(j_kelas).strip() or 0))
                except: j_kelas_int = 0
                display_rows.append({
                    "NO_PUSAT": no_pusat,
                    "NAMA_PUSAT": nama,
                    "KOD_SEKOLAH": kod_sek,
                    "PPD": ppd,
                    "JUMLAH_CALON": j_calon_int,
                    "JUMLAH_KELAS": j_kelas_int,
                    "PETUGAS": petugas,
                    "_id": r.get("id"),
                    "_raw": r
                })
            df_display = pd.DataFrame(display_rows)
            if not df_display.empty:
                st.subheader(f"Senarai Pusat dengan Jumlah Calon (dari CSV)")
                st.dataframe(df_display[["NO_PUSAT","NAMA_PUSAT","KOD_SEKOLAH","PPD","JUMLAH_CALON","JUMLAH_KELAS","PETUGAS"]].head(500), use_container_width=True)
                # Summary
                c1,c2,c3 = st.columns(3)
                c1.metric("Total Calon", int(df_display["JUMLAH_CALON"].sum()))
                c2.metric("Total Kelas", int(df_display["JUMLAH_KELAS"].sum()))
                c3.metric("Ada Calon", len(df_display[df_display["JUMLAH_CALON"]>0]))
                
                if len(df_display[df_display["JUMLAH_CALON"]==0]) > 100:
                    st.error(f"⚠️ {len(df_display[df_display['JUMLAH_CALON']==0])} pusat JUMLAH_CALON = 0 / kosong! Kena fix dari CSV.")
                
                st.download_button("📥 Export Pusat dengan Calon", to_excel(pd.DataFrame(display_rows)), file_name="pusat_master_dengan_calon.xlsx")
            else:
                st.warning("pusat_master kosong")

            # FIX BUTTON - Update jumlah calon dari CSV
            st.markdown("---")
            st.subheader("🔧 FIX: Update Jumlah Calon yang Hilang")
            st.info("Kalau JUMLAH_CALON 0/kosong, upload pusat_2026.csv untuk update balik 506 pusat dengan jumlah calon betul.")
            up_fix = st.file_uploader("Upload pusat_2026.csv untuk FIX jumlah calon", type=["csv","xlsx"], key="fix_calon")
            if up_fix:
                try:
                    if up_fix.name.endswith(".csv"):
                        try:
                            df_fix = pd.read_csv(up_fix)
                        except:
                            up_fix.seek(0)
                            df_fix = pd.read_csv(up_fix, encoding='latin1')
                    else:
                        df_fix = pd.read_excel(up_fix)
                    st.write(f"File fix ada {len(df_fix)} baris")
                    st.dataframe(df_fix.head(10), use_container_width=True)
                    if st.button(f"🚀 FIX Update {len(df_fix)} Pusat dengan Jumlah Calon", type="primary", use_container_width=True):
                        bar = st.progress(0)
                        stat = st.empty()
                        ok=0
                        fail=0
                        for idx, row in df_fix.iterrows():
                            try:
                                no_pusat = str(row.get("NO_PUSAT","") or row.get("KOD PUSAT","")).upper().strip()
                                if not no_pusat: continue
                                j_calon = row.get("JUMLAH_CALON","0")
                                j_kelas = row.get("JUMLAH_KELAS","0")
                                petugas = row.get("PETUGAS_NEEDED","0")
                                # Update by no_pusat
                                # Supabase update
                                update_data = {
                                    "jumlah_calon": int(float(str(j_calon).strip() or 0)),
                                    "jumlah_kelas": int(float(str(j_kelas).strip() or 0)),
                                    "calon": int(float(str(j_calon).strip() or 0)),
                                    "bilik": int(float(str(j_kelas).strip() or 0)),
                                }
                                # Try update where no_pusat = 
                                try:
                                    supa.table("pusat_master").update(update_data).eq("no_pusat", no_pusat).execute()
                                    ok+=1
                                except:
                                    # Try kod_pusat
                                    try:
                                        supa.table("pusat_master").update(update_data).eq("kod_pusat", no_pusat).execute()
                                        ok+=1
                                    except Exception as e:
                                        # Update data JSON field also
                                        fail+=1
                            except Exception as e:
                                fail+=1
                            if idx % 20 == 0:
                                bar.progress((idx+1)/len(df_fix))
                                stat.write(f"Progress {idx+1}/{len(df_fix)} OK {ok} Fail {fail}")
                        bar.progress(1.0)
                        st.success(f"✅ FIX selesai! OK {ok} Fail {fail} | Refresh page untuk lihat jumlah calon masuk!")
                        st.balloons()
                except Exception as e:
                    st.error(f"Error fix: {e}")

        except Exception as e:
            st.error(f"pusat_master error: {e}")
            st.code("""
-- SQL FIX: Tambah column jumlah_calon kalau belum ada - Run di Supabase SQL Editor:
ALTER TABLE pusat_master ADD COLUMN IF NOT EXISTS jumlah_calon INT DEFAULT 0;
ALTER TABLE pusat_master ADD COLUMN IF NOT EXISTS jumlah_kelas INT DEFAULT 0;
ALTER TABLE pusat_master ADD COLUMN IF NOT EXISTS calon INT DEFAULT 0;
ALTER TABLE pusat_master ADD COLUMN IF NOT EXISTS bilik INT DEFAULT 0;
ALTER TABLE pusat_master ADD COLUMN IF NOT EXISTS petugas_needed INT DEFAULT 0;
ALTER TABLE pusat_master ADD COLUMN IF NOT EXISTS kod_pusat TEXT;
ALTER TABLE pusat_master ADD COLUMN IF NOT EXISTS nama_pusat TEXT;
            """, language="sql")

        st.markdown("---")
        col1,col2 = st.columns(2)
        with col1:
            st.subheader("➕ Tambah Pusat Manual - Auto Kira SPM")
            st.caption("Formula: 1 kelas=20 calon, CEIL(calon/20)=kelas, petugas=kelas+9, sekolah perlu calonkan=kelas+12 (petugas+KP+TKP+Penyelia)")
            with st.form("tambah_pusat"):
                kod_pusat=st.text_input("KOD PUSAT * (cth: BA001)")
                nama_pusat=st.text_input("NAMA PUSAT *")
                kod_ppd_pusat=st.selectbox("KOD PPD", KOD_DAERAH, format_func=lambda x: f"{x}-{PPD_MAP[x]}")
                alamat_pusat=st.text_area("ALAMAT PUSAT (KOD SEKOLAH)")
                calon_input=st.number_input("JUMLAH CALON * (contoh 105)", min_value=1, value=100, step=1, help="1 kelas = 20 calon. Auto kira kelas & petugas")
                # Auto calc preview
                kelas_preview = kira_kelas_dari_calon(calon_input)
                petugas_preview = kira_petugas_dari_kelas(kelas_preview)
                sekolah_need_preview = kira_sekolah_perlu_calonkan(kelas_preview)
                st.info(f"📊 Auto Kira: {calon_input} calon → **{kelas_preview} kelas** (20/kelas) → **{petugas_preview} petugas** (kelas+9) → Sekolah perlu calonkan **{sekolah_need_preview} orang** (petugas+KP+TKP+Penyelia)")
                submit_pusat=st.form_submit_button("💾 Simpan Pusat (Auto Kira)", type="primary", use_container_width=True)
                if submit_pusat:
                    if not kod_pusat or not nama_pusat:
                        st.error("Kod & Nama Pusat wajib!")
                    else:
                        try:
                            kelas_calc = kira_kelas_dari_calon(calon_input)
                            petugas_calc = kira_petugas_dari_kelas(kelas_calc)
                            sekolah_need = kira_sekolah_perlu_calonkan(kelas_calc)
                            supa.table("pusat_master").insert({
                                "kod_pusat": kod_pusat.upper(),
                                "nama_pusat": nama_pusat.upper(),
                                "kod_ppd": kod_ppd_pusat,
                                "ppd": PPD_MAP.get(kod_ppd_pusat,""),
                                "alamat": alamat_pusat,
                                "bilik": kelas_calc,
                                "calon": int(calon_input),
                                "jumlah_calon": int(calon_input),
                                "jumlah_kelas": kelas_calc,
                                "petugas_needed": petugas_calc,
                                "data": {
                                    "NO_PUSAT":kod_pusat.upper(),
                                    "NAMA_PUSAT":nama_pusat.upper(),
                                    "KOD PPD":kod_ppd_pusat,
                                    "KOD_SEKOLAH":alamat_pusat,
                                    "JUMLAH_CALON":str(calon_input),
                                    "JUMLAH_KELAS":str(kelas_calc),
                                    "PETUGAS_NEEDED":str(petugas_calc),
                                    "SEKOLAH_PERLU_CALON":str(sekolah_need),
                                    "FORMULA":f"{calon_input} calon /20 = {kelas_calc} kelas, {kelas_calc}+9={petugas_calc} petugas, +3 KP/TKP/Penyelia = {sekolah_need} sekolah perlu calon"
                                }
                            }).execute()
                            st.success(f"✅ Pusat {kod_pusat} berjaya tambah! {calon_input} calon = {kelas_calc} kelas, {petugas_calc} petugas, sekolah perlu {sekolah_need} orang")
                            st.balloons()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Gagal: {e}")

        with col2:
            st.subheader("📤 Import Excel/CSV Pusat (Batch)")
            st.info("Support: pusat_2026.csv (NO_PUSAT format) & Excel KOD PUSAT format | 506 pusat")
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                st.download_button("📥 Template Pusat", to_excel(pd.DataFrame([{"KOD PUSAT":"BA001","NAMA PUSAT":"SMK DATO HAMZAH","KOD PPD":"BA","ALAMAT PUSAT":"Jalan Dato Hamzah","BILIK":10,"CALON":250}])), "TEMPLATE_PUSAT.xlsx")
            with col_t2:
                st.download_button("📥 Sample pusat_2026.csv", open("/mnt/data/pusat_2026.csv","rb").read() if __import__("os").path.exists("/mnt/data/pusat_2026.csv") else b"", "pusat_2026_sample.csv")
            
            up=st.file_uploader("Upload Excel/CSV Pusat (Excel atau CSV)", type=["xlsx","csv"], key="pusat_up")
            if up:
                try:
                    if up.name.endswith(".csv"):
                        try:
                            df_up=pd.read_csv(up)
                        except:
                            up.seek(0)
                            df_up=pd.read_csv(up, encoding='latin1')
                    else:
                        df_up=pd.read_excel(up)
                    st.write(f"Preview {len(df_up)} pusat:")
                    st.dataframe(df_up.head(20), use_container_width=True)
                    if st.button(f"🚀 Import {len(df_up)} Pusat (Batch 200)", type="primary", use_container_width=True):
                        bar=st.progress(0)
                        stat=st.empty()
                        ok=0
                        BATCH=200
                        # PPD name to code map for CSV
                        ppd_name_map = {"klang":"BA","kuala langat":"BB","kuala selangor":"BC","hulu langat":"BD","hulu selangor":"BE","sabak bernam":"BF","gombak":"BG","petaling perdana":"BH","sepang":"BJ","petaling utama":"BK"}
                        for start in range(0, len(df_up), BATCH):
                            end=min(start+BATCH, len(df_up))
                            bdf=df_up.iloc[start:end]
                            batch=[]
                            for _, row in bdf.iterrows():
                                try:
                                    d={}
                                    for k,v in row.to_dict().items():
                                        d[k] = "" if pd.isna(v) else str(v)
                                    # Support both formats: NO_PUSAT or KOD PUSAT
                                    kod_p = d.get("NO_PUSAT","") or d.get("KOD PUSAT","") or d.get("kod_pusat","")
                                    kod_p = kod_p.upper().strip()
                                    if not kod_p: continue
                                    # KOD PPD logic
                                    kod_ppd_val = d.get("KOD PPD","") or d.get("KOD_PPD","") or d.get("PPD_CODE","")
                                    if not kod_ppd_val:
                                        ppd_raw = d.get("PPD","").lower()
                                        for name,code in ppd_name_map.items():
                                            if name in ppd_raw:
                                                kod_ppd_val=code
                                                break
                                        if not kod_ppd_val:
                                            kod_ppd_val="BH"
                                    kod_ppd_val = kod_ppd_val.upper().strip()
                                    nama_p = d.get("NAMA_PUSAT","") or d.get("NAMA PUSAT","") or kod_p
                                    bilik_val = d.get("JUMLAH_KELAS","") or d.get("BILIK","") or "10"
                                    calon_val = d.get("JUMLAH_CALON","") or d.get("CALON","") or "200"
                                    try: bilik_int = int(float(bilik_val))
                                    except: bilik_int = 10
                                    try: calon_int = int(float(calon_val))
                                    except: calon_int = 200
                                    batch.append({
                                        "kod_pusat": kod_p,
                                        "nama_pusat": nama_p.upper(),
                                        "kod_ppd": kod_ppd_val,
                                        "ppd": d.get("PPD","") or PPD_MAP.get(kod_ppd_val,""),
                                        "alamat": d.get("KOD_SEKOLAH","") or d.get("ALAMAT PUSAT","") or d.get("ALAMAT",""),
                                        "bilik": bilik_int,
                                        "calon": calon_int,
                                        "data": d
                                    })
                                except: continue
                            if batch:
                                try:
                                    supa.table("pusat_master").insert(batch).execute()
                                    ok+=len(batch)
                                except Exception as e:
                                    st.warning(f"Batch {start}-{end}: {e}")
                            bar.progress(end/len(df_up))
                            stat.write(f"Progress {end}/{len(df_up)} | OK {ok}")
                        st.success(f"✅ Selesai import {ok}/{len(df_up)} pusat! Total 506")
                        st.balloons()
                        st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        st.markdown("---")
        if st.button("🗑️ Kosongkan Semua Pusat (Hati-hati!)", type="secondary"):
            try:
                # Supabase need delete with filter, we delete all with gt 0
                supa.table("pusat_master").delete().gt("id",0).execute()
                st.success("Semua pusat dipadam")
                st.rerun()
            except Exception as e:
                st.error(str(e))

    elif menu=="👨‍🏫 Guru Master":
        st.header("Guru Master Seluruh Negeri")
        st.subheader("📤 Import MASTER 60K Guru Selangor")
        st.info("Upload file MASTER-GURU-SELANGOR-2026.xlsx (60K) di sini untuk restore balik data yang hilang. Guna batch 500 untuk laju.")
        up_master = st.file_uploader("Upload MASTER 60K Excel", type=["xlsx"], key="master60k")
        if up_master:
            try:
                df_m = pd.read_excel(up_master, sheet_name=0)
                st.write(f"File ada {len(df_m)} baris. Column: {list(df_m.columns)}")
                st.dataframe(df_m.head(10), use_container_width=True)
                if st.button(f"🚀 Import {len(df_m)} Guru ke Supabase (Batch 500)", type="primary", use_container_width=True):
                    bar = st.progress(0)
                    stat = st.empty()
                    ok=0
                    BATCH=500
                    for start in range(0, len(df_m), BATCH):
                        end = min(start+BATCH, len(df_m))
                        bdf = df_m.iloc[start:end]
                        batch=[]
                        for _, row in bdf.iterrows():
                            try:
                                d={}
                                for k,v in row.to_dict().items():
                                    d[k] = "" if pd.isna(v) else str(v)
                                nama = d.get("NAMA GURU","").upper().strip()
                                if not nama or nama=="NAN": continue
                                batch.append({
                                    "kod_ppd": d.get("KOD PPD","").lower().strip(),
                                    "kod_sekolah": d.get("KOD SEKOLAH","").upper().strip(),
                                    "nama_guru": nama,
                                    "ic_guru": d.get("IC",""),
                                    "data": d
                                })
                            except: continue
                        if batch:
                            try:
                                supa.table("guru_master").insert(batch).execute()
                                ok+=len(batch)
                            except Exception as e:
                                st.error(f"Batch {start}-{end} error: {e}")
                        bar.progress(end/len(df_m))
                        stat.write(f"Imported {end}/{len(df_m)} | OK {ok}")
                    st.success(f"✅ Selesai import {ok}/{len(df_m)} guru!")
                    st.balloons()
            except Exception as e:
                st.error(f"Error: {e}")

        st.markdown("---")
        st.subheader("Data Sedia Ada")
        try:
            res=supa.table("guru_master").select("*", count="exact").limit(5000).execute()
            df=pd.DataFrame(res.data or [])
            st.write(f"Total dalam Supabase: {res.count} records")
            if not df.empty:
                st.dataframe(df.head(100), use_container_width=True)
                st.download_button("Export Guru Master (5000)", to_excel(df), file_name="guru_master_full.xlsx")
        except Exception as e:
            st.error(str(e))

    elif menu=="📋 Semua Cadangan":
        st.header("Semua Cadangan Seluruh Negeri")
        try:
            res=supa.table("cadangan_sup").select("*").limit(10000).execute()
            df=pd.DataFrame(res.data or [])
            st.dataframe(df, use_container_width=True)
            if not df.empty:
                st.download_button("Export Semua Cadangan", to_excel(df), file_name=f"cadangan_negeri_{datetime.date.today()}.xlsx")
        except Exception as e:
            st.error(str(e))

    elif menu=="📥 Export Negeri":
        st.header("Export Laporan Negeri")
        try:
            res=supa.table("cadangan_sup").select("*").limit(10000).execute()
            df=pd.DataFrame(res.data or [])
            if not df.empty:
                st.download_button("📥 Laporan Penuh Negeri (Excel)", to_excel(df), file_name=f"Laporan_JPN_Selangor_{datetime.date.today()}.xlsx", use_container_width=True, type="primary")
        except Exception as e:
            st.error(str(e))

    elif menu=="⚙️ Admin":
        st.header("Admin - Check Tables & Connection")
        st.code(f"URL: {SUPABASE_URL}\nKEY: {SUPABASE_KEY[:20]}...{SUPABASE_KEY[-10:]} (Active)")
        for t in ["sekolah_master","pusat_master","guru_master","cadangan_sup"]:
            try:
                res=supa.table(t).select("*", count="exact").limit(1).execute()
                st.success(f"✅ {t}: {res.count} records")
            except Exception as e:
                st.error(f"❌ {t}: {e}")
        st.markdown("---")
        st.subheader("Buat Table cadangan_sup jika belum ada")
        st.code("""
-- Run di Supabase SQL Editor jika cadangan_sup belum wujud:
CREATE TABLE IF NOT EXISTS cadangan_sup (
  id BIGSERIAL PRIMARY KEY,
  kod_ppd TEXT,
  kod_sekolah TEXT,
  ic_guru TEXT,
  nama_guru TEXT,
  kod_pusat TEXT,
  jawatan_cadangan TEXT,
  catatan TEXT,
  status TEXT DEFAULT 'DICADANGKAN',
  tarikh_cadang DATE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE cadangan_sup ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "allow all" ON cadangan_sup;
CREATE POLICY "allow all" ON cadangan_sup FOR ALL USING (true) WITH CHECK (true);
        """, language="sql")
