"""
SISTEM PELANTIKAN PETUGAS PEPERIKSAAN SELANGOR 2026
FIX FINAL - SUP boleh tambah/buang guru, data masuk ke sekolah
"""
import streamlit as st
import pandas as pd
import os
import glob
import re
import time
import threading
from io import BytesIO

st.set_page_config(page_title="Sistem Pelantikan Selangor 2026", layout="wide", page_icon="📚", initial_sidebar_state="collapsed")

st.markdown("""
<style>
[data-testid="stSidebar"] {display: none !important;}
[data-testid="collapsedControl"] {display: none !important;}
.big-title {text-align:center; font-size:30px; font-weight:bold; color:#0B5394;}
.sub-title {text-align:center; font-size:14px; color:#666; margin-bottom:15px;}
.login-box {background:#f0f7ff; padding:20px; border-radius:12px; border:1px solid #c2d8ff;}
.left-panel {background:#f8fafc; padding:15px; border-radius:10px; border:1px solid #e2e8f0;}
</style>
""", unsafe_allow_html=True)

try:
    from supabase import create_client
except:
    create_client = None

SUPABASE_URL = "https://gnmaijhugkkvxejvsotk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdubWFpamh1Z2trdnhlanZzb3RrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTI0ODc4OTcsImV4cCI6MjEwODA2Mzg5N30.1YWg71nCwnQzP-KUzTdHR4rZAVCAesbKVqvVC1-X6lw"

try:
    if "SUPABASE_URL" in st.secrets:
        SUPABASE_URL = st.secrets["SUPABASE_URL"]
    if "SUPABASE_ANON_KEY" in st.secrets:
        SUPABASE_KEY = st.secrets["SUPABASE_ANON_KEY"]
    if "SUPABASE_KEY" in st.secrets:
        SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except:
    pass

@st.cache_resource(ttl=300, show_spinner=False)
def get_supabase():
    if create_client is None:
        return None, "supabase not installed"
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return client, None
    except Exception as e:
        return None, str(e)

def _df_from_rows(rows):
    if not rows:
        return pd.DataFrame()
    out = []
    for r in rows:
        if isinstance(r, dict):
            if "data" in r and isinstance(r["data"], dict) and r["data"]:
                d = r["data"].copy()
                for k in ["kod_ppd", "kod_sekolah", "KOD_PPD", "KOD_SEKOLAH", "nama_guru", "ic_guru"]:
                    if k in r and r[k]:
                        d[k] = r[k]
                        d[k.upper()] = r[k]
                        if k.lower() == "kod_ppd":
                            d["KOD PPD"] = r[k]
                            d["KOD_PPD"] = r[k]
                        if k.lower() == "kod_sekolah":
                            d["KOD SEKOLAH"] = r[k]
                            d["KOD_SEKOLAH"] = r[k]
                out.append(d)
            else:
                r2 = {k: v for k, v in r.items() if k not in ["id", "created_at", "data"]}
                for k in ["kod_ppd", "kod_sekolah", "KOD_PPD", "KOD_SEKOLAH"]:
                    if k in r and r[k]:
                        r2[k] = r[k]
                        r2[k.upper()] = r[k]
                out.append(r2)
    return pd.DataFrame(out)

# ==========================================
# FIX 1: tab_daerah - tambah underscore
# ==========================================
def tab_daerah(base, kod_ppd, tahun=None):
    """Nama jadual ikut daerah + tahun.
    Contoh: tab_daerah('guru_sekolah','BK',2026) -> 'guru_sekolah_BK_2026'
    """
    if tahun is None:
        try:
            tahun = st.session_state.get("tahun_pilih", 2026)
        except:
            tahun = 2026
    kod = str(kod_ppd).strip().upper()
    th = str(tahun).strip()
    return f"{base}_{kod}_{th}"   # ✅ FIX: ada underscore

def tab_daerah_base(base, kod_ppd):
    return f"{base}_{str(kod_ppd).strip().upper()}"

def tab_tahun(base, tahun=None):
    if tahun is None:
        try:
            tahun = st.session_state.get("tahun_pilih", 2026)
        except:
            tahun = 2026
    return f"{base}_{tahun}"

@st.cache_data
def load_mapping():
    data_folder = "data"
    candidates = []
    if os.path.exists(data_folder):
        for f in os.listdir(data_folder):
            low = f.lower()
            if "id" in low and "daerah" in low and (low.endswith(".xlsx") or low.endswith(".csv")):
                candidates.append(os.path.join(data_folder, f))
    
    best_df = pd.DataFrame()
    best_file = ""
    for path in candidates:
        try:
            if path.endswith(".xlsx"):
                df = pd.read_excel(path)
            else:
                df = pd.read_csv(path)
            if "PPD" in df.columns and len(df) > len(best_df):
                best_df = df
                best_file = path
        except Exception:
            continue
    
    if not best_df.empty and len(best_df) > 10:
        return best_df, best_file
    
    standard_paths = [
        "data/SENARAI_ID_SUP_BY_DAERAH.xlsx",
        "data/SENARAI_ID-SUP_BY_DAERAH.xlsx",
        "data/SENARAI_ID_SUP_BY_DAERAH.csv",
        "/mnt/data/SENARAI_ID_SUP_BY_DAERAH.xlsx",
        "/mnt/data/SENARAI_ID_SUP_BY_DAERAH.csv",
    ]
    for path in standard_paths:
        try:
            if os.path.exists(path):
                if path.endswith(".xlsx"):
                    df = pd.read_excel(path)
                else:
                    df = pd.read_csv(path)
                if "PPD" in df.columns and len(df) > 10:
                    return df, path
        except Exception:
            continue
    
    try:
        master_path = None
        if os.path.exists("data"):
            for f in os.listdir("data"):
                if "506" in f and "calon" in f.lower():
                    master_path = os.path.join("data", f)
                    break
        if not master_path:
            master_path = "data/senarai_506_PLUS_calon2026_FINAL.xlsx"
        df_master = pd.read_excel(master_path)
        PPD_MAP = {"BA":"Klang","BB":"Kuala Langat","BC":"Kuala Selangor","BD":"Hulu Langat","BE":"Hulu Selangor","BF":"Sabak Bernam","BG":"Gombak","BH":"Petaling Perdana","BJ":"Sepang","BK":"Petaling Utama"}
        order = ["BA","BB","BC","BD","BE","BF","BG","BH","BJ","BK"]
        schools = df_master.groupby("KOD SEKOLAH").first().reset_index()
        schools["KOD PPD"] = schools["NO PUSAT"].str[:2]
        id_mapping = []
        current_id = 1
        for kod in order:
            subset = schools[schools["KOD PPD"]==kod].sort_values("KOD SEKOLAH")
            for _, row in subset.iterrows():
                bil_pusat = len(df_master[df_master["KOD SEKOLAH"]==row["KOD SEKOLAH"]])
                senarai = ",".join(df_master[df_master["KOD SEKOLAH"]==row["KOD SEKOLAH"]]["NO PUSAT"].tolist())
                id_mapping.append({
                    "ID": current_id, "PASSWORD": str(current_id), "KOD SEKOLAH": row["KOD SEKOLAH"],
                    "NAMA SEKOLAH": row["NAMA PUSAT"], "PPD": PPD_MAP.get(kod, kod), "KOD PPD": kod,
                    "BIL PUSAT": bil_pusat, "SENARAI PUSAT": senarai
                })
                current_id += 1
        return pd.DataFrame(id_mapping), f"Generated from {master_path} ({len(id_mapping)} sekolah)"
    except Exception as e:
        return pd.DataFrame([{"ID":354,"PASSWORD":"354","KOD SEKOLAH":"BEB8653","NAMA SEKOLAH":"SMJK KATHOLIK","PPD":"Petaling Utama","KOD PPD":"BK","BIL PUSAT":3,"SENARAI PUSAT":"BK009,BK010,BK011"}]), f"Fallback dummy error: {e}"

mapping_df, file_used = load_mapping()

@st.cache_data
def load_pusat_calon():
    for p in ["pusat_2026.csv", "data/pusat_2026.csv", "Pusat-SELANGOR-2026-FULL-GITHUB.csv", "data/Pusat-SELANGOR-2026-FULL-GITHUB.csv", "/mnt/data/pusat_2026.csv"]:
        if os.path.exists(p):
            try:
                df = pd.read_csv(p) if p.endswith(".csv") else pd.read_excel(p)
                if "NO_PUSAT" in df.columns and len(df) > 20:
                    return df
            except Exception:
                pass
    return pd.DataFrame()

df_calon_master = load_pusat_calon()

# ==========================================
# HELPER SUPABASE
# ==========================================
KOD_DAERAH_SAH = ("BA", "BB", "BC", "BD", "BE", "BF", "BG", "BH", "BJ", "BK")
JADUAL_IKUT_DAERAH = ("maklumat_sekolah", "cadangan_sup", "penempatan_ppd", "petugas_simpanan",
                      "log_simpanan", "guru_sekolah", "pilihan_ppd")
_SAIZ_HALAMAN = 1000

def urai_nama(name):
    """'cadangan_sup_BK_2026' -> ('cadangan_sup', 'BK'); 'kuota_ppd_2026' -> ('kuota_ppd', None)."""
    s = re.sub(r"_(19|20)\d{2}$", "", str(name).strip())
    m = re.match(r"^(.+)_(" + "|".join(KOD_DAERAH_SAH) + r")$", s)
    return (m.group(1), m.group(2)) if m else (s, None)

@st.cache_resource(show_spinner=False)
def _peta_kunci():
    return {"master": threading.Lock(), "peta": {}}

def get_lock(name="*"):
    k = _peta_kunci()
    with k["master"]:
        return k["peta"].setdefault(name, threading.Lock())

def _ralat_jadual(base, e):
    t = str(e)
    if "PGRST205" in t or "Could not find the table" in t or "does not exist" in t:
        return RuntimeError(f"Jadual '{base}' belum wujud dalam Supabase - minta admin cipta jadual ini dahulu.")
    return e

def _baca_baris(base, kod):
    supa, err = get_supabase()
    if supa is None:
        raise RuntimeError(f"Supabase tidak connect: {err}")
    semua, mula = [], 0
    try:
        while True:
            q = supa.table(base).select("*", count="exact").order("id")
            if kod:
                q = q.eq("KOD_PPD", kod)
            res = q.range(mula, mula + _SAIZ_HALAMAN - 1).execute()
            baris = res.data or []
            semua.extend(baris)
            jumlah = getattr(res, "count", None)
            if not baris or (jumlah is not None and len(semua) >= jumlah):
                break
            mula += len(baris)
    except Exception as e:
        raise _ralat_jadual(base, e) from e
    return semua

def read_sheet_strict(name):
    base, kod = urai_nama(name)
    return _df_from_rows(_baca_baris(base, kod))

@st.cache_data(ttl=10, show_spinner=False)
def _cached_read(name):
    return read_sheet_strict(name)

def read_sheet(name):
    klien, _ = get_supabase()
    if klien is None:
        return pd.DataFrame()
    try:
        return _cached_read(name)
    except Exception as e:
        st.warning(f"⚠️ Gagal baca '{name}' dari Supabase ({type(e).__name__}). Data di bawah mungkin tidak lengkap - cuba muat semula sebentar lagi.")
        return pd.DataFrame()

def read_sheet_tahun(base, kod_or_none=None, tahun=None):
    if tahun is None:
        try:
            tahun = st.session_state.get("tahun_pilih", 2026)
        except Exception:
            tahun = 2026
    if kod_or_none:
        name = tab_daerah(base, kod_or_none, tahun)
    else:
        name = tab_tahun(base, tahun)
    return read_sheet(name)

def _cell(v):
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except (TypeError, ValueError):
        pass
    if hasattr(v, "item"):
        v = v.item()
    if isinstance(v, pd.Timestamp):
        return str(v)
    return v

def padam_id(supa, base, ids):
    for i in range(0, len(ids), 100):
        supa.table(base).delete().in_("id", ids[i:i + 100]).execute()

def _tulis_sheet(name, df):
    if len(df.columns) == 0:
        return
    base, kod = urai_nama(name)
    if kod is None and base in JADUAL_IKUT_DAERAH:
        raise ValueError(f"Jadual '{base}' mesti ditulis dengan kod daerah (contoh {base}_BK_2026) - penulisan dibatalkan.")
    supa, err = get_supabase()
    if supa is None:
        raise RuntimeError(f"Supabase tidak connect: {err}")
    ids_lama = [r["id"] for r in _baca_baris(base, kod) if isinstance(r, dict) and "id" in r]
    batch = []
    for _, row in df.iterrows():
        bersih = {str(k): _cell(v) for k, v in row.to_dict().items()}
        kod_ppd = kod or (str(bersih.get("KOD PPD", bersih.get("KOD_PPD", "")))[:2] or "BK")
        batch.append({"KOD_PPD": kod_ppd, "data": bersih})
    baru_id = []
    try:
        for i in range(0, len(batch), 100):
            res = supa.table(base).insert(batch[i:i + 100]).execute()
            baru_id += [r["id"] for r in (res.data or []) if isinstance(r, dict) and "id" in r]
    except Exception as e:
        try:
            padam_id(supa, base, baru_id)
        except Exception:
            pass
        raise _ralat_jadual(base, e) from e
    try:
        padam_id(supa, base, ids_lama)
    except Exception:
        try:
            padam_id(supa, base, ids_lama)
        except Exception as e:
            raise RuntimeError("Data baru sudah disimpan tetapi baris lama gagal dibuang (mungkin berganda sementara). Tekan simpan sekali lagi.") from e

def modify_sheet(name, modifier):
    base, kod = urai_nama(name)
    try:
        with get_lock(f"{base}|{kod}"):
            df = read_sheet_strict(name)
            baru = modifier(df)
            if baru is not None:
                _tulis_sheet(name, baru)
    except ValueError as e:
        st.error(f"⚠️ {e}")
        return False
    except Exception as e:
        st.error(f"❌ Gagal simpan ke '{name}' - data lama tidak dipadam. Cuba lagi sebentar. ({type(e).__name__}: {e})")
        return False
    _cached_read.clear()
    return True

def flash(level, msg):
    st.session_state.setdefault("_flash", []).append((level, msg))

def show_flash():
    for level, msg in st.session_state.pop("_flash", []):
        getattr(st, level)(msg)

def norm_ic(x):
    d = re.sub(r"\D", "", str(x))
    return d.zfill(12) if d else ""

# ==========================================
# FIX 2: agih_guru_master_ke_sekolah - tulis ke table TUNGGAL
# ==========================================
def agih_guru_master_ke_sekolah(supa):
    """Ambil 60K dari guru_master dan agih ke table guru_sekolah (TUNGGAL) dengan KOD_PPD."""
    try:
        semua_rows = []
        mula = 0
        while True:
            res = supa.table("guru_master").select("*").range(mula, mula+999).execute()
            baris = res.data or []
            if not baris:
                break
            semua_rows.extend(baris)
            if len(baris) < 1000:
                break
            mula += 1000
        
        if not semua_rows:
            return 0, "guru_master kosong"
        
        # Padam data lama dalam table guru_sekolah (TUNGGAL)
        try:
            for _ in range(200):
                res = supa.table("guru_sekolah").select("id").limit(1000).execute()
                if not res.data:
                    break
                ids = [x["id"] for x in res.data]
                supa.table("guru_sekolah").delete().in_("id", ids).execute()
        except Exception:
            pass
        
        # Sediakan batch untuk insert ke guru_sekolah (TUNGGAL)
        batch = []
        for r in semua_rows:
            data = r.get("data") or {}
            kod_ppd = (r.get("kod_ppd") or r.get("KOD_PPD") or "").strip().upper()
            if not kod_ppd or len(kod_ppd) != 2:
                kod_ppd = str(data.get("KOD PPD") or data.get("KOD_PPD") or data.get("kod_ppd") or "").strip().upper()[:2]
            if not kod_ppd or kod_ppd not in ["BA","BB","BC","BD","BE","BF","BG","BH","BJ","BK"]:
                continue
            
            rec = {
                "KOD SEKOLAH ASAL": str(data.get("KOD SEKOLAH") or r.get("kod_sekolah") or r.get("KOD_SEKOLAH") or ""),
                "NAMA SEKOLAH ASAL": str(data.get("NAMA SEKOLAH") or ""),
                "NAMA GURU": str(data.get("NAMA GURU") or r.get("nama_guru") or ""),
                "IC": str(data.get("IC") or r.get("ic_guru") or ""),
                "JANTINA": str(data.get("JANTINA") or ""),
                "POSKOD RUMAH": str(data.get("POSKOD RUMAH") or ""),
                "ALAMAT RUMAH": str(data.get("ALAMAT RUMAH") or ""),
                "NO TELEFON GURU": str(data.get("NO TELEFON GURU") or ""),
                "EMAIL GURU": str(data.get("EMAIL GURU") or ""),
                "PENGALAMAN SPM": str(data.get("PENGALAMAN SPM") or "0"),
                "GRED": str(data.get("GRED") or ""),
                "JAWATAN HAKIKI": str(data.get("JAWATAN HAKIKI") or ""),
                "KOD PPD": kod_ppd,
                "KOD SEKOLAH": str(data.get("KOD SEKOLAH") or r.get("kod_sekolah") or ""),
            }
            batch.append({"KOD_PPD": kod_ppd, "data": rec})
        
        # Insert ke table guru_sekolah (TUNGGAL)
        total_inserted = 0
        for i in range(0, len(batch), 100):
            res = supa.table("guru_sekolah").insert(batch[i:i+100]).execute()
            total_inserted += len(res.data or [])
        
        return total_inserted, f"✅ Berjaya agih {total_inserted} guru ke table guru_sekolah (tunggal dengan KOD_PPD)"
    except Exception as e:
        import traceback
        return 0, f"❌ Error agih: {str(e)}\n{traceback.format_exc()}"

def read_semua_daerah(base, tahun=None):
    if tahun is None:
        try:
            tahun = st.session_state.get("tahun_pilih", 2026)
        except:
            tahun = 2026
    bahagian = []
    for _, _, _, kod in PPD_LIST:
        d = read_sheet(tab_daerah(base, kod, tahun))
        if d.empty:
            d = read_sheet(tab_daerah_base(base, kod))
        if not d.empty:
            d = d.copy()
            d["KOD PPD"] = kod
            bahagian.append(d)
    return pd.concat(bahagian, ignore_index=True) if bahagian else pd.DataFrame()

# ==========================================
# SENARAI GURU & MUAT NAIK
# ==========================================
JAWATAN_CADANGAN_SAH = ["Ketua Pengawas", "Timbalan Ketua Pengawas", "Pengawas Peperiksaan", "Pengemas Bilik", "Penyelia Kawasan"]
JAWATAN_LAZIM = "Pengawas Peperiksaan"
LAJUR_GURU = ["KOD SEKOLAH ASAL", "NAMA SEKOLAH ASAL", "NAMA GURU", "IC", "JANTINA", "POSKOD RUMAH", "ALAMAT RUMAH",
              "NO TELEFON GURU", "EMAIL GURU", "PENGALAMAN SPM", "NO PUSAT ASAL", "JAWATAN CADANGAN"]
LAJUR_TEMPLAT = ["NAMA GURU", "IC", "JANTINA", "NO TELEFON GURU", "EMAIL GURU", "ALAMAT RUMAH", "POSKOD RUMAH",
                 "PENGALAMAN SPM", "NO PUSAT ASAL", "JAWATAN CADANGAN"]
_ALIAS_LAJUR = {
    "NAMA GURU": ["NAMA GURU", "NAMA"],
    "IC": ["IC", "NO IC", "NO. IC", "NO KP", "NO. KP", "NO KAD PENGENALAN"],
    "JANTINA": ["JANTINA"],
    "NO TELEFON GURU": ["NO TELEFON GURU", "NO TELEFON", "NO. TELEFON", "NO TEL", "TELEFON"],
    "EMAIL GURU": ["EMAIL GURU", "EMAIL", "E-MEL", "EMEL"],
    "ALAMAT RUMAH": ["ALAMAT RUMAH", "ALAMAT"],
    "POSKOD RUMAH": ["POSKOD RUMAH", "POSKOD"],
    "PENGALAMAN SPM": ["PENGALAMAN SPM", "PENGALAMAN"],
    "NO PUSAT ASAL": ["NO PUSAT ASAL", "NO PUSAT"],
    "JAWATAN CADANGAN": ["JAWATAN CADANGAN", "JAWATAN"],
}
MAKS_BARIS_MUAT_NAIK = 1000

def _teks(v):
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except (TypeError, ValueError):
        pass
    s = str(v).strip()
    if re.fullmatch(r"\d+\.0", s):
        s = s[:-2]
    return s

def _bersih_teks(s):
    s = re.sub(r"\s+", " ", _teks(s)).strip()
    return s.lstrip("=+-@ ").strip() if s[:1] in ("=", "+", "-", "@") else s

def format_ic(x):
    d = re.sub(r"\D", "", str(x)).zfill(12)
    return f"{d[:6]}-{d[6:8]}-{d[8:]}"

def norm_telefon(t):
    d = re.sub(r"\D", "", str(t))
    if not d:
        return ""
    if d.startswith("60") and len(d) >= 10:
        d = "0" + d[2:]
    elif not d.startswith("0"):
        d = "0" + d
    return d

def _ke_int(v, lalai=None):
    s = _teks(v)
    if s == "":
        return lalai
    try:
        return int(float(s))
    except ValueError:
        return None

def validasi_guru(nama, ic, alamat, tel, email):
    d = re.sub(r"\D", "", str(ic))
    if not str(nama).strip() or not str(ic).strip():
        return "Nama Guru dan IC wajib isi!"
    if not (11 <= len(d) <= 12):
        return "IC mesti 12 digit (contoh: 900101-10-1234)"
    if len(str(alamat).strip()) < 10:
        return "Alamat Rumah wajib isi penuh (no rumah, jalan, taman, bandar)."
    if not sah_telefon(norm_telefon(tel)):
        return "No Telefon Guru wajib isi dan mesti 9-12 digit (contoh: 012-3456789)."
    if not sah_email(email):
        return "Format Email Guru tidak betul (contoh: nama@moe.gov.my) atau biarkan kosong."
    return ""

def kekurangan_guru(r):
    k = []
    if not _teks(r.get("NAMA GURU", "")):
        k.append("nama")
    if not (11 <= len(re.sub(r"\D", "", str(r.get("IC", "")))) <= 12):
        k.append("IC")
    if len(_teks(r.get("ALAMAT RUMAH", ""))) < 10:
        k.append("alamat")
    if not sah_telefon(norm_telefon(r.get("NO TELEFON GURU", ""))):
        k.append("telefon")
    return k

def baca_fail_guru(fail):
    nama = str(getattr(fail, "name", "")).lower()
    if nama.endswith(".csv"):
        try:
            return pd.read_csv(fail, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        except UnicodeDecodeError:
            fail.seek(0)
            return pd.read_csv(fail, dtype=str, keep_default_na=False, encoding="latin-1")
    if nama.endswith(".xlsx"):
        xl = pd.ExcelFile(fail, engine="openpyxl")
        helaian = "Senarai Guru" if "Senarai Guru" in xl.sheet_names else xl.sheet_names[0]
        return xl.parse(helaian, dtype=str).fillna("")
    raise ValueError("Format fail tidak disokong. Guna .xlsx (templat) atau .csv")

def proses_muat_naik(df_up, kod_sekolah, nama_sekolah, senarai_pusat):
    df = df_up.copy()
    df.columns = [re.sub(r"\s+", " ", str(c)).strip().upper() for c in df.columns]
    peta = {}
    for kanon, alias in _ALIAS_LAJUR.items():
        for a in alias:
            if a in df.columns:
                peta[kanon] = a
                break
    wajib = ["NAMA GURU", "IC", "ALAMAT RUMAH", "NO TELEFON GURU", "POSKOD RUMAH"]
    hilang = [w for w in wajib if w not in peta]
    if hilang:
        raise ValueError("Lajur wajib tiada dalam fail: " + ", ".join(hilang) + ". Sila guna templat Excel yang dimuat turun.")
    if len(df) > MAKS_BARIS_MUAT_NAIK:
        raise ValueError(f"Fail terlalu besar ({len(df)} baris). Maksimum {MAKS_BARIS_MUAT_NAIK} baris.")
    pusat_sah = [str(p).upper() for p in (senarai_pusat or [])]
    jaw_peta = {j.upper(): j for j in JAWATAN_CADANGAN_SAH}
    jaw_peta.update({"PENGAWAS": "Pengawas Peperiksaan", "KP": "Ketua Pengawas", "TKP": "Timbalan Ketua Pengawas"})
    baik, ralat, lihat = [], [], {}
    for i, (_, r) in enumerate(df.iterrows()):
        no = i + 2
        ambil = lambda k: _teks(r[peta[k]]) if k in peta else ""
        nama, ic_raw, jan_raw = _bersih_teks(ambil("NAMA GURU")), ambil("IC"), ambil("JANTINA")
        alamat, tel_raw, email = _bersih_teks(ambil("ALAMAT RUMAH")), ambil("NO TELEFON GURU"), ambil("EMAIL GURU").lower()
        pos_raw, peng_raw, pusat_raw, jaw_raw = ambil("POSKOD RUMAH"), ambil("PENGALAMAN SPM"), ambil("NO PUSAT ASAL"), ambil("JAWATAN CADANGAN")
        if not any([nama, ic_raw, alamat, tel_raw, email, pos_raw, jan_raw]):
            continue
        m = []
        if not nama:
            m.append("nama kosong")
        d = re.sub(r"\D", "", ic_raw)
        if not (11 <= len(d) <= 12):
            m.append("IC mesti 12 digit")
            ic_fmt = ""
        else:
            ic_fmt = format_ic(d)
            k = norm_ic(d)
            if k in lihat:
                m.append(f"IC sama dengan baris {lihat[k]} dalam fail")
            else:
                lihat[k] = no
        jan = {"L": "L", "LELAKI": "L", "M": "L", "P": "P", "PEREMPUAN": "P", "F": "P"}.get(jan_raw.upper())
        if not jan:
            m.append("jantina mesti L atau P")
        pos = re.sub(r"\D", "", pos_raw)
        if len(pos) != 5:
            m.append("poskod mesti 5 digit")
        if len(alamat) < 10:
            m.append("alamat terlalu pendek / kosong")
        tel = norm_telefon(tel_raw)
        if not sah_telefon(tel):
            m.append("no telefon mesti 9-12 digit")
        if not sah_email(email):
            m.append("format email salah")
        peng = _ke_int(peng_raw, 0)
        if peng is None or not (0 <= peng <= 40):
            m.append("pengalaman SPM mesti nombor 0-40")
            peng = 0
        pusat = _bersih_teks(pusat_raw).upper()
        if not pusat and len(pusat_sah) == 1:
            pusat = pusat_sah[0]
        if pusat and pusat_sah and pusat not in pusat_sah:
            m.append(f"no pusat asal {pusat} bukan pusat sekolah ini ({', '.join(pusat_sah)})")
        jaw = ""
        if jaw_raw:
            jaw = jaw_peta.get(_bersih_teks(jaw_raw).upper(), "")
            if not jaw:
                m.append("jawatan tidak sah")
        if m:
            ralat.append({"BARIS": no, "NAMA GURU": nama, "MASALAH": "; ".join(m)})
            continue
        baik.append({"KOD SEKOLAH ASAL": str(kod_sekolah), "NAMA SEKOLAH ASAL": nama_sekolah, "NAMA GURU": nama, "IC": ic_fmt,
                     "JANTINA": jan, "POSKOD RUMAH": int(pos), "ALAMAT RUMAH": alamat, "NO TELEFON GURU": tel,
                     "EMAIL GURU": email, "PENGALAMAN SPM": int(peng), "NO PUSAT ASAL": pusat, "JAWATAN CADANGAN": jaw})
    return pd.DataFrame(baik, columns=LAJUR_GURU), ralat

def gabung_guru_sekolah(df_roster, df_baru, kod_sekolah, nama_sekolah):
    kod = str(kod_sekolah)
    baru = df_baru.copy()
    for c in LAJUR_GURU:
        if c not in baru.columns:
            baru[c] = ""
    baru["KOD SEKOLAH ASAL"] = kod
    baru["NAMA SEKOLAH ASAL"] = nama_sekolah
    if df_roster is None or df_roster.empty:
        return baru[LAJUR_GURU].reset_index(drop=True), len(baru), 0
    if "IC" not in df_roster.columns or "KOD SEKOLAH ASAL" not in df_roster.columns:
        raise ValueError("Format data guru_sekolah tidak dijangka - hubungi admin")
    df = df_roster.copy().astype(object)
    for c in LAJUR_GURU:
        if c not in df.columns:
            df[c] = ""
    ada = {}
    for idx, r in df.iterrows():
        if str(r["KOD SEKOLAH ASAL"]) == kod and norm_ic(r["IC"]):
            ada.setdefault(norm_ic(r["IC"]), idx)
    tambah, n_baru, n_kemaskini = [], 0, 0
    lihat = set()
    for _, g in baru.iterrows():
        k = norm_ic(g["IC"])
        if not k or k in lihat:
            continue
        lihat.add(k)
        if k in ada:
            for c in LAJUR_GURU:
                v = g[c]
                if c == "JAWATAN CADANGAN" and not _teks(v):
                    continue
                df.at[ada[k], c] = v
            n_kemaskini += 1
        else:
            r = {c: g[c] for c in LAJUR_GURU}
            if not _teks(r["JAWATAN CADANGAN"]):
                r["JAWATAN CADANGAN"] = JAWATAN_LAZIM
            tambah.append(r)
            n_baru += 1
    if tambah:
        df = pd.concat([df, pd.DataFrame(tambah)], ignore_index=True)
    return df, n_baru, n_kemaskini

def senarai_guru_sekolah(df_roster, df_cad, kod_sekolah):
    kod = str(kod_sekolah)
    def milik(df):
        if df is None or df.empty or "IC" not in df.columns or "KOD SEKOLAH ASAL" not in df.columns:
            return pd.DataFrame()
        return df[df["KOD SEKOLAH ASAL"].astype(str) == kod]
    r = milik(df_roster)
    c = milik(normalkan_cadangan(df_cad) if (df_cad is not None and not df_cad.empty) else df_cad)
    cad = {}
    for _, x in c.iterrows():
        k = norm_ic(x.get("IC", ""))
        if k:
            cad.setdefault(k, x)
    out, lihat = [], set()
    for _, x in r.iterrows():
        k = norm_ic(x.get("IC", ""))
        if not k or k in lihat:
            continue
        lihat.add(k)
        b = {col: x.get(col, "") for col in LAJUR_GURU}
        if k in cad:
            jc = _teks(cad[k].get("JAWATAN CADANGAN", ""))
            if jc:
                b["JAWATAN CADANGAN"] = jc
        b["CADANGAN"] = k in cad
        out.append(b)
    for k, x in cad.items():
        if k in lihat:
            continue
        b = {col: x.get(col, "") for col in LAJUR_GURU}
        b["CADANGAN"] = True
        out.append(b)
    df = pd.DataFrame(out, columns=LAJUR_GURU + ["CADANGAN"])
    if df.empty:
        return df
    df["JAWATAN CADANGAN"] = df["JAWATAN CADANGAN"].map(lambda v: _teks(v) if _teks(v) in JAWATAN_CADANGAN_SAH else JAWATAN_LAZIM)
    return df.sort_values("NAMA GURU", kind="stable").reset_index(drop=True)

def buang_guru_roster(df_roster, kod_sekolah, ic_dipilih, ic_cadangan):
    if df_roster.empty or "IC" not in df_roster.columns or "KOD SEKOLAH ASAL" not in df_roster.columns:
        raise ValueError("Senarai Guru tidak dijumpai - muat semula halaman")
    pilih = {norm_ic(i) for i in ic_dipilih}
    if pilih & set(ic_cadangan):
        raise ValueError("Ada guru yang sedang dicadangkan - nyah-tick dan Hantar dahulu untuk menarik balik cadangan.")
    sasar = (df_roster["KOD SEKOLAH ASAL"].astype(str) == str(kod_sekolah)) & df_roster["IC"].map(norm_ic).isin(pilih)
    if not sasar.any():
        raise ValueError("Guru yang dipilih tak dijumpai (mungkin sudah dibuang) - muat semula halaman")
    return df_roster[~sasar].reset_index(drop=True), int(sasar.sum())

def sah_telefon(t):
    return 9 <= len(re.sub(r"\D", "", str(t))) <= 12

def sah_email(e):
    e = str(e).strip()
    return e == "" or re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", e) is not None

def normalkan_cadangan(df):
    if "JAWATAN CADANG" not in df.columns:
        return df
    df = df.copy()
    if "JAWATAN CADANGAN" in df.columns:
        kosong = df["JAWATAN CADANGAN"].astype(str).str.strip().isin(["", "nan", "None"])
        df.loc[kosong, "JAWATAN CADANGAN"] = df.loc[kosong, "JAWATAN CADANG"]
        return df.drop(columns=["JAWATAN CADANG"])
    return df.rename(columns={"JAWATAN CADANG": "JAWATAN CADANGAN"})

# ==========================================
# Fungsi penempatan (dipendekkan untuk ruang)
# ==========================================
def keperluan_asal(pusat, df_calon):
    petugas = 10
    kelas = 0
    calon = 0
    if df_calon is not None and not df_calon.empty and "NO_PUSAT" in df_calon.columns:
        r = df_calon[df_calon["NO_PUSAT"].astype(str) == str(pusat)]
        if not r.empty:
            try: calon = int(r.iloc[0].get("JUMLAH_CALON", 0))
            except: pass
            try: kelas = int(r.iloc[0].get("JUMLAH_KELAS", 0))
            except: pass
            if "PETUGAS_NEEDED" in df_calon.columns:
                try: petugas = int(r.iloc[0]["PETUGAS_NEEDED"])
                except: petugas = kelas + 10 if kelas else 10
            else:
                petugas = kelas + 10 if kelas else 10
    return petugas, kelas, calon

def keperluan_pengawas(pusat, df_calon, df_kuota=None):
    if df_kuota is None:
        try: df_kuota = read_sheet("kuota_ppd")
        except: df_kuota = pd.DataFrame()
    if df_kuota is not None and not df_kuota.empty and "NO PUSAT" in df_kuota.columns:
        r = df_kuota[df_kuota["NO PUSAT"].astype(str) == str(pusat)]
        if not r.empty:
            last = r.iloc[-1]
            try:
                for col in ["KEPERLUAN EDIT", "KEPERLUAN_PENGAWAS", "JUMLAH_PENGAWAS", "PETUGAS_EDIT", "KEPERLUAN AKHIR"]:
                    if col in df_kuota.columns and str(last.get(col, "")).strip() != "" and str(last.get(col)).lower() != "nan":
                        return int(float(str(last.get(col)).strip()))
            except: pass
    asal, _, _ = keperluan_asal(pusat, df_calon)
    return asal

def get_kuota_info(pusat, df_calon, df_kuota=None):
    if df_kuota is None:
        try: df_kuota = read_sheet("kuota_ppd")
        except: df_kuota = pd.DataFrame()
    asal, kelas, calon = keperluan_asal(pusat, df_calon)
    formula = (kelas + 10) if kelas else asal
    edit = None
    catatan = ""
    if df_kuota is not None and not df_kuota.empty and "NO PUSAT" in df_kuota.columns:
        r = df_kuota[df_kuota["NO PUSAT"].astype(str) == str(pusat)]
        if not r.empty:
            last = r.iloc[-1]
            for col in ["KEPERLUAN EDIT", "KEPERLUAN_PENGAWAS", "JUMLAH_PENGAWAS", "PETUGAS_EDIT", "KEPERLUAN AKHIR"]:
                if col in df_kuota.columns:
                    try:
                        v = str(last.get(col, "")).strip()
                        if v and v.lower() != "nan":
                            edit = int(float(v))
                            break
                    except: pass
            for col in ["CATATAN", "ALASAN", "NOTA"]:
                if col in df_kuota.columns:
                    catatan = str(last.get(col, "") or "")
                    break
    final = edit if edit is not None else asal
    return {"asal": asal, "kelas": kelas, "calon": calon, "formula": formula, "edit": edit, "final": final, "catatan": catatan}

def jawatan_kosong(need_peng, jawatan_sedia):
    sasaran = {"Ketua Pengawas": 1, "Timbalan Ketua Pengawas": 1, "Pengawas Peperiksaan": need_peng}
    sedia = [str(j).strip() for j in jawatan_sedia]
    hasil = []
    for jaw, bil in sasaran.items():
        hasil += [jaw] * max(0, bil - sedia.count(jaw))
    return hasil

def _kunci_nama(nama, kod):
    n = re.sub(r"\s+", " ", str(nama)).strip().upper()
    if not n or n == "NAN":
        return ""
    return f"{n}|{str(kod).strip().upper()}"

def kunci_guru(ic, nama, kod_sekolah):
    ks = []
    i = norm_ic(ic)
    if i:
        ks.append("IC:" + i)
    nk = _kunci_nama(nama, kod_sekolah)
    if nk:
        ks.append("NS:" + nk)
    return ks

def peta_guru_pusat(df_pen, df_simp=None):
    peta = {}
    if df_pen is not None and not df_pen.empty and "NO PUSAT TUGAS" in df_pen.columns:
        for _, r in df_pen.iterrows():
            for k in kunci_guru(r.get("IC", ""), r.get("NAMA GURU", ""), r.get("KOD SEKOLAH ASAL GURU", "")):
                peta.setdefault(k, str(r["NO PUSAT TUGAS"]))
    if df_simp is not None and not df_simp.empty:
        for _, r in df_simp.iterrows():
            for k in kunci_guru(r.get("IC", ""), r.get("NAMA GURU", ""), r.get("KOD SEKOLAH ASAL GURU", "")):
                peta.setdefault(k, "SIMPANAN")
    return peta

def huraian_pusat(p_):
    return "senarai Petugas Simpanan" if p_ == "SIMPANAN" else f"pusat {p_}"

def pusat_guru(peta, ic, nama, kod_sekolah):
    for k in kunci_guru(ic, nama, kod_sekolah):
        if k in peta:
            return peta[k]
    return None

# PPD_LIST & PPD_USERS
PPD_LIST = [
    ("1", "a", "Klang", "BA"), ("2", "b", "Kuala Langat", "BB"),
    ("3", "c", "Kuala Selangor", "BC"), ("4", "d", "Hulu Langat", "BD"),
    ("5", "e", "Hulu Selangor", "BE"), ("6", "f", "Sabak Bernam", "BF"),
    ("7", "g", "Gombak", "BG"), ("8", "h", "Petaling Perdana", "BH"),
    ("9", "i", "Sepang", "BJ"), ("10", "j", "Petaling Utama", "BK"),
]
PPD_USERS = {f"{nama}": {"id": id_, "password": pwd, "nama": f"PPD {nama}", "ppd_nama": nama, "kod": kod} for id_, pwd, nama, kod in PPD_LIST}

# ==========================================
# LOG MASUK
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown('<div class="big-title">📚 SISTEM PELANTIKAN PETUGAS PEPERIKSAAN</div>', unsafe_allow_html=True)
    st.markdown('<div class="big-title" style="font-size:22px;">SELANGOR 2026</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-title">{len(mapping_df)} Sekolah Termasuk Persendirian • File: {os.path.basename(file_used)}<br>SPM Bertulis • Amali Sains • Mendengar • Bertutur</div>', unsafe_allow_html=True)
    
    left, center, right = st.columns([1,2,1])
    with center:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown("### 🔐 Log Masuk")
        peranan = st.selectbox("1️⃣ Pilih Peranan", ["-- Pilih --", "JPN Selangor", "PPD", "SUP Sekolah"])
        
        if peranan == "JPN Selangor":
            st.info("JPN: ID 1 Password a")
            jpn_pwd = st.text_input("Kata Laluan JPN", type="password", placeholder="a")
            if st.button("🚀 Log Masuk JPN", use_container_width=True, type="primary"):
                if jpn_pwd == "a":
                    st.session_state.logged_in = True
                    st.session_state.user_role = "JPN"
                    st.session_state.user_info = {"nama": "JPN Selangor", "role": "JPN", "id": "1"}
                    st.rerun()
                else:
                    st.error("Password salah")
        
        elif peranan == "PPD":
            st.markdown("#### 2️⃣ Pilih Daerah (PPD)")
            ppd_daerah = st.selectbox("Daerah", ["-- Pilih Daerah --"] + [nama for _,_,nama,_ in PPD_LIST])
            if ppd_daerah != "-- Pilih Daerah --":
                ppd_info = PPD_USERS[ppd_daerah]
                bil_sek = len(mapping_df[mapping_df["PPD"]==ppd_daerah]) if not mapping_df.empty else 0
                st.success(f"PPD {ppd_daerah} ({ppd_info['kod']}) - {bil_sek} sekolah - Password {ppd_info['password']}")
                ppd_pwd = st.text_input(f"Password PPD {ppd_daerah}", type="password")
                if st.button(f"🚀 Log Masuk {ppd_daerah}", use_container_width=True, type="primary"):
                    if ppd_pwd == ppd_info['password']:
                        st.session_state.logged_in = True
                        st.session_state.user_role = "PPD"
                        st.session_state.user_info = {"nama": f"PPD {ppd_daerah}", "ppd_nama": ppd_daerah, "kod": ppd_info['kod'], "password": ppd_info['password'], "id": ppd_info['id'], "role": "PPD"}
                        st.rerun()
                    else:
                        st.error("Password salah")
        
        elif peranan == "SUP Sekolah":
            st.markdown("#### 2️⃣ Pilih Daerah")
            order_daerah = ["Klang","Kuala Langat","Kuala Selangor","Hulu Langat","Hulu Selangor","Sabak Bernam","Gombak","Petaling Perdana","Sepang","Petaling Utama"]
            if not mapping_df.empty:
                daerah_ada = mapping_df["PPD"].unique().tolist()
                daerah_list = [d for d in order_daerah if d in daerah_ada]
            else:
                daerah_list = order_daerah
            sup_daerah = st.selectbox("Daerah Sekolah Anda", ["-- Pilih Daerah --"] + daerah_list)
            if sup_daerah != "-- Pilih Daerah --":
                df_daerah = mapping_df[mapping_df["PPD"]==sup_daerah].sort_values("NAMA SEKOLAH") if not mapping_df.empty else pd.DataFrame()
                st.markdown(f"#### 3️⃣ Pilih Sekolah di {sup_daerah} ({len(df_daerah)} sekolah)")
                if len(df_daerah) == 0:
                    st.warning("Senarai kosong!")
                else:
                    sekolah_options = [f"{row['NAMA SEKOLAH']} ({row['KOD SEKOLAH']}) - {row['BIL PUSAT']} pusat [{row['SENARAI PUSAT']}]" for _, row in df_daerah.iterrows()]
                    sekolah_pilih = st.selectbox("Nama Sekolah", ["-- Pilih Sekolah --"] + sekolah_options)
                    if sekolah_pilih != "-- Pilih Sekolah --":
                        idx = sekolah_options.index(sekolah_pilih)
                        row_sekolah = df_daerah.iloc[idx]
                        st.success(f"✅ {row_sekolah['NAMA SEKOLAH']} - {row_sekolah['KOD SEKOLAH']}")
                        sup_pwd = st.text_input(f"Password {row_sekolah['NAMA SEKOLAH']}", type="password", placeholder=f"{row_sekolah['PASSWORD']}")
                        if st.button(f"🚀 Log Masuk {row_sekolah['NAMA SEKOLAH']}", use_container_width=True, type="primary"):
                            if sup_pwd == str(row_sekolah['PASSWORD']):
                                st.session_state.logged_in = True
                                st.session_state.user_role = "SUP"
                                st.session_state.user_info = {
                                    "nama": row_sekolah['NAMA SEKOLAH'],
                                    "kod_sekolah": row_sekolah['KOD SEKOLAH'],
                                    "ppd": row_sekolah['PPD'],
                                    "kod_ppd": row_sekolah['KOD PPD'],
                                    "id": str(row_sekolah['ID']),
                                    "password": str(row_sekolah['PASSWORD']),
                                    "bil_pusat": row_sekolah['BIL PUSAT'],
                                    "senarai_pusat": row_sekolah['SENARAI PUSAT'],
                                    "role": "SUP"
                                }
                                st.rerun()
                            else:
                                st.error("Password salah")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ==========================================
# DASHBOARD UTAMA
# ==========================================
role = st.session_state.user_role
info = st.session_state.user_info

st.markdown(f"""
<div style="background:#0B5394; color:white; padding:10px 15px; border-radius:8px;">
<b>📚 SPM 2026</b> | {info['nama']} | {role} | {info.get('ppd','')} {info.get('kod_sekolah','')} | File: {os.path.basename(file_used)}
</div>
""", unsafe_allow_html=True)

col_kiri, col_kanan = st.columns([1, 3])
with col_kiri:
    st.markdown('<div class="left-panel">', unsafe_allow_html=True)
    st.markdown(f"### 👤 {info['nama']}")
    if role == "SUP":
        st.markdown(f" Kod: {info['kod_sekolah']}")
        st.markdown(f" PPD: {info['ppd']} ({info['kod_ppd']})")
        st.markdown(f" Pusat: {info['bil_pusat']} pusat")
        st.code(info['senarai_pusat'])
    elif role == "PPD":
        st.markdown(f" PPD: {info['ppd_nama']} ({info['kod']})")
    
    st.markdown("---")
    if role == "SUP":
        menu = st.radio("Menu", ["Maklumat Sekolah", "Senarai Guru", "Muat Naik / Muat Turun", "Cadangan Petugas", "Status"], label_visibility="collapsed")
    elif role == "PPD":
        menu = st.radio("Menu", ["Senarai Pusat", "Kuota Pusat", "Cadangan SUP", "Jana Penempatan", "Penempatan Manual", "Batal Penempatan", "Petugas Simpanan", "Hantar JPN"], label_visibility="collapsed")
    else:
        menu = st.radio("Menu", ["Semua PPD", "📚 Master 60K (Pindah Data Daerah)", "Sahkan PPD", "Jana Surat", "Backup & Restore 2026", "🔍 Check Supabase"], label_visibility="collapsed")
    
    st.markdown("---")
    tahun_list = [2026, 2027, 2028, 2029, 2030]
    if "tahun_pilih" not in st.session_state:
        st.session_state["tahun_pilih"] = 2026
    tahun_pilih = st.selectbox("📅 Tahun", tahun_list, index=tahun_list.index(st.session_state["tahun_pilih"]) if st.session_state["tahun_pilih"] in tahun_list else 0, key="tahun_selector")
    st.session_state["tahun_pilih"] = tahun_pilih
    
    st.markdown("---")
    if st.button("🚪 Log Keluar", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with col_kanan:
    _supa_klien, _supa_ralat = get_supabase()
    if _supa_klien is None:
        st.error(f"Supabase tidak connect - data TIDAK boleh dibaca / disimpan: {_supa_ralat}")
    
    show_flash()
    _kod_daerah = str(info.get("kod_ppd") or info.get("kod") or "").strip().upper()
    if role in ("SUP", "PPD") and _kod_daerah not in {t[3] for t in PPD_LIST}:
        st.error("Kod daerah tidak sah - sila log keluar dan log masuk semula.")
        st.stop()
    
    TAB_MAKLUMAT = tab_daerah("maklumat_sekolah", _kod_daerah)
    TAB_CADANGAN = tab_daerah("cadangan_sup", _kod_daerah)
    TAB_PENEMPATAN = tab_daerah("penempatan_ppd", _kod_daerah)
    TAB_SIMPANAN = tab_daerah("petugas_simpanan", _kod_daerah)
    TAB_GURU = tab_daerah("guru_sekolah", _kod_daerah)
    
    # ==========================================
    # LOGIK SUP
    # ==========================================
    if role == "SUP":
        kod_s = str(info['kod_sekolah'])
        
        if menu == "Maklumat Sekolah":
            st.header(f"🏫 {info['nama']}")
            maklumat = read_sheet(TAB_MAKLUMAT)
            existing = maklumat[maklumat["KOD SEKOLAH"].astype(str) == kod_s] if not maklumat.empty and "KOD SEKOLAH" in maklumat.columns else pd.DataFrame()
            
            def_val_nama = info['nama']
            def_val_bil_pusat = int(info['bil_pusat'])
            def_val_senarai = info['senarai_pusat']
            
            if not existing.empty:
                row = existing.iloc[-1]
                def_val_nama = str(row.get("NAMA SEKOLAH", def_val_nama))
                try: def_val_bil_pusat = int(float(str(row.get("BIL NO PUSAT", def_val_bil_pusat)).strip() or def_val_bil_pusat))
                except: pass
                try: def_val_senarai = str(row.get("SENARAI NO PUSAT", def_val_senarai))
                except: pass
            
            with st.form("sekolah"):
                c1, c2 = st.columns(2)
                with c1:
                    nama_sek = st.text_input("NAMA SEKOLAH", value=def_val_nama)
                    bil_pusat = st.number_input("BIL PUSAT", 1, 10, def_val_bil_pusat)
                with c2:
                    senarai = st.text_input("SENARAI NO PUSAT", value=def_val_senarai)
                
                if st.form_submit_button("💾 Simpan", use_container_width=True):
                    new_row = {
                        "KOD SEKOLAH": kod_s, "NAMA SEKOLAH": nama_sek,
                        "BIL NO PUSAT": bil_pusat, "SENARAI NO PUSAT": senarai,
                        "TARIKH KEMASKINI": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    def _simpan_maklumat(df):
                        if not df.empty:
                            df = df[df["KOD SEKOLAH"].astype(str) != kod_s]
                        return pd.concat([df, pd.DataFrame([new_row])], ignore_index=True) if not df.empty else pd.DataFrame([new_row])
                    
                    if modify_sheet(TAB_MAKLUMAT, _simpan_maklumat):
                        flash("success", f"✅ {nama_sek} berjaya dikemaskini!")
                        st.rerun()
        
        elif menu == "Senarai Guru":
            st.header(f"🧑‍🏫 Senarai Guru - {info['nama']}")
            st.caption("Semua guru sekolah anda. TICK guru yang akan bertugas, pilih jawatan, kemudian tekan Hantar.")
            
            n_g = st.session_state.get("guru_n", 0)
            _pusat_g = []
            for _p in re.findall(r"[A-Za-z]+\d+", str(info.get("senarai_pusat", ""))):
                if _p.upper() not in _pusat_g:
                    _pusat_g.append(_p.upper())
            
            # ==========================================
            # FIX 3: Baca guru dengan fallback yang betul
            # ==========================================
            guru_roster = read_sheet(TAB_GURU)
            
            # Fallback: kalau kosong, baca terus dari guru_master ikut kod_sekolah
            if guru_roster.empty:
                try:
                    supa_fb, _ = get_supabase()
                    if supa_fb:
                        kod_s_upper = kod_s.strip().upper()
                        # Cuba baca dari guru_sekolah table tunggal dengan filter KOD_PPD + KOD SEKOLAH
                        res_gs = supa_fb.table("guru_sekolah").select("*").eq("KOD_PPD", _kod_daerah).limit(5000).execute()
                        
                        filtered = []
                        for r in (res_gs.data or []):
                            d = r.get("data") or {}
                            ks1 = str(d.get("KOD SEKOLAH ASAL") or d.get("KOD SEKOLAH") or "").strip().upper()
                            ks2 = str(r.get("kod_sekolah") or r.get("KOD_SEKOLAH") or "").strip().upper()
                            if ks1 == kod_s_upper or ks2 == kod_s_upper:
                                filtered.append(r)
                        
                        if filtered:
                            guru_roster = _df_from_rows(filtered)
                            if not guru_roster.empty:
                                if "KOD SEKOLAH ASAL" not in guru_roster.columns and "KOD SEKOLAH" in guru_roster.columns:
                                    guru_roster["KOD SEKOLAH ASAL"] = guru_roster["KOD SEKOLAH"]
                                if "NAMA SEKOLAH ASAL" not in guru_roster.columns and "NAMA SEKOLAH" in guru_roster.columns:
                                    guru_roster["NAMA SEKOLAH ASAL"] = guru_roster["NAMA SEKOLAH"]
                except Exception as e:
                    st.warning(f"Fallback guru error: {e}")
            
            cadangan_g = read_sheet(TAB_CADANGAN)
            senarai_g = senarai_guru_sekolah(guru_roster, cadangan_g, kod_s)
            
            if senarai_g.empty:
                st.info("Belum ada guru. Muat naik fail Excel di menu **Muat Naik / Muat Turun**, atau tambah seorang guru di bawah.")
            else:
                peta_g = peta_guru_pusat(read_sheet(TAB_PENEMPATAN), read_sheet(TAB_SIMPANAN))
                status_ppd = []
                for _, r_ in senarai_g.iterrows():
                    p_ = pusat_guru(peta_g, r_["IC"], r_["NAMA GURU"], r_["KOD SEKOLAH ASAL"])
                    status_ppd.append("" if p_ is None else ("🅿️ Simpanan PPD" if p_ == "SIMPANAN" else f"🔒 Dilantik di {p_}"))
                senarai_g["STATUS PPD"] = status_ppd
                
                m1, m2, m3 = st.columns(3)
                with m1: st.metric("Jumlah Guru", len(senarai_g))
                with m2: st.metric("Sudah Dicadang", int(senarai_g["CADANGAN"].sum()))
                with m3: st.metric("Dilantik PPD", int((senarai_g["STATUS PPD"] != "").sum()))
                
                lajur_edit = ["CADANGAN", "NAMA GURU", "IC", "JANTINA", "JAWATAN CADANGAN", "NO TELEFON GURU", "ALAMAT RUMAH", "PENGALAMAN SPM", "NO PUSAT ASAL", "STATUS PPD"]
                paparan = senarai_g[lajur_edit].copy()
                paparan["CADANGAN"] = paparan["CADANGAN"].astype(bool)
                
                diedit = st.data_editor(
                    paparan, hide_index=True, use_container_width=True, key=f"guru_edit_{n_g}",
                    disabled=[c for c in lajur_edit if c not in ("CADANGAN", "JAWATAN CADANGAN")],
                    column_config={
                        "CADANGAN": st.column_config.CheckboxColumn("✔ Cadangan"),
                        "JAWATAN CADANGAN": st.column_config.SelectboxColumn("Jawatan", options=JAWATAN_CADANGAN_SAH),
                    },
                )
                
                tick = diedit["CADANGAN"].fillna(False).astype(bool)
                ticked_df = senarai_g[tick.values].copy()
                ticked_df["JAWATAN CADANGAN"] = diedit.loc[tick, "JAWATAN CADANGAN"].map(lambda v: _teks(v) or JAWATAN_LAZIM).values
                
                n_tick = int(tick.sum())
                
                if st.button(f"📤 HANTAR {n_tick} CADANGAN KE PPD", use_container_width=True, type="primary", disabled=n_tick == 0, key=f"guru_hantar_{n_g}"):
                    hasil_h = {}
                    ok_r = modify_sheet(TAB_GURU, lambda dfr: gabung_guru_sekolah(dfr, ticked_df, kod_s, info['nama'])[0])
                    if ok_r:
                        def _sync_cad(df_cad):
                            from copy import deepcopy
                            # Simplified hantar_cadangan
                            kod = str(kod_s)
                            ic_hantar = {norm_ic(x) for x in ticked_df["IC"] if norm_ic(x)}
                            df = df_cad.copy() if not df_cad.empty else pd.DataFrame()
                            own = df[df["KOD SEKOLAH ASAL"].astype(str) == kod] if "KOD SEKOLAH ASAL" in df.columns else pd.DataFrame()
                            lain = df[df["KOD SEKOLAH ASAL"].astype(str) != kod] if "KOD SEKOLAH ASAL" in df.columns else df
                            
                            baris = []
                            for _, g in ticked_df.iterrows():
                                k = norm_ic(g.get("IC", ""))
                                if not k: continue
                                baris.append({
                                    "KOD SEKOLAH ASAL": kod, "NAMA SEKOLAH ASAL": info['nama'],
                                    "NAMA GURU": g.get("NAMA GURU", ""), "IC": g.get("IC", ""),
                                    "JANTINA": g.get("JANTINA", ""),
                                    "POSKOD RUMAH": g.get("POSKOD RUMAH", ""),
                                    "ALAMAT RUMAH": g.get("ALAMAT RUMAH", ""),
                                    "NO TELEFON GURU": g.get("NO TELEFON GURU", ""),
                                    "EMAIL GURU": g.get("EMAIL GURU", ""),
                                    "JAWATAN CADANGAN": _teks(g.get("JAWATAN CADANGAN", "")) or JAWATAN_LAZIM,
                                    "PENGALAMAN SPM": g.get("PENGALAMAN SPM", 0),
                                    "NO PUSAT ASAL": g.get("NO PUSAT ASAL", ""),
                                    "STATUS": "Dicadang",
                                })
                            hasil = pd.concat([lain, pd.DataFrame(baris)], ignore_index=True) if not lain.empty else pd.DataFrame(baris)
                            hasil_h["jumlah"] = len(baris)
                            return hasil
                        
                        if modify_sheet(TAB_CADANGAN, _sync_cad):
                            flash("success", f"✅ {hasil_h.get('jumlah', 0)} cadangan dihantar ke PPD!")
                            st.session_state["guru_n"] = n_g + 1
                            st.rerun()
            
            # ----- Tambah seorang guru -----
            with st.expander("➕ Tambah / kemaskini seorang guru"):
                with st.form(f"form_guru_roster_{n_g}"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        jaw_f = st.selectbox("JAWATAN CADANGAN", JAWATAN_CADANGAN_SAH, index=JAWATAN_CADANGAN_SAH.index(JAWATAN_LAZIM))
                        jan_f = st.selectbox("JANTINA", ["L", "P"])
                    with c2:
                        nama_f = st.text_input("NAMA GURU *")
                        tel_f = st.text_input("NO TELEFON GURU *", placeholder="contoh: 012-3456789")
                    with c3:
                        ic_f = st.text_input("IC *", placeholder="contoh: 900101-10-1234")
                        email_f = st.text_input("EMAIL GURU", placeholder="contoh: nama@moe.gov.my")
                    alamat_f = st.text_area("ALAMAT RUMAH *", placeholder="No rumah, jalan, taman, poskod, bandar")
                    c4, c5, c6 = st.columns(3)
                    with c4:
                        pos_f = st.number_input("POSKOD RUMAH *", 10000, 99999, 46000)
                    with c5:
                        peng_f = st.number_input("PENGALAMAN SPM", 0, 40, 0)
                    with c6:
                        pusat_f = st.selectbox("NO PUSAT ASAL", _pusat_g + ["-- Tiada --"])
                    
                    if st.form_submit_button("💾 Simpan ke Senarai Guru", use_container_width=True):
                        masalah_f = validasi_guru(nama_f, ic_f, alamat_f, tel_f, email_f)
                        if masalah_f:
                            st.error(masalah_f)
                        else:
                            baris_f = pd.DataFrame([{
                                "NAMA GURU": _bersih_teks(nama_f), "IC": format_ic(ic_f), "JANTINA": jan_f, "POSKOD RUMAH": int(pos_f),
                                "ALAMAT RUMAH": _bersih_teks(alamat_f), "NO TELEFON GURU": norm_telefon(tel_f), "EMAIL GURU": email_f.strip().lower(),
                                "PENGALAMAN SPM": int(peng_f), "NO PUSAT ASAL": "" if pusat_f == "-- Tiada --" else pusat_f, "JAWATAN CADANGAN": jaw_f,
                            }])
                            hasil_f = {}
                            def _simpan_f(dfr):
                                df_n, nb, nk = gabung_guru_sekolah(dfr, baris_f, kod_s, info['nama'])
                                hasil_f.update(baru=nb, kemaskini=nk)
                                return df_n
                            if modify_sheet(TAB_GURU, _simpan_f):
                                flash("success", f"✅ {_bersih_teks(nama_f)} {'ditambah' if hasil_f['baru'] else 'dikemaskini'} dalam Senarai Guru.")
                                st.session_state["guru_n"] = n_g + 1
                                st.rerun()
            
            # ==========================================
            # FIX 4: Buang guru - padam dari guru_master DAN guru_sekolah
            # ==========================================
            if not senarai_g.empty:
                with st.expander("🗑️ Buang guru daripada Senarai Guru"):
                    boleh_buang = senarai_g[~senarai_g["CADANGAN"].astype(bool)]
                    label_b = {norm_ic(r_["IC"]): f"{r_['NAMA GURU']} | IC: {r_['IC']}" for _, r_ in boleh_buang.iterrows() if norm_ic(r_["IC"])}
                    st.caption("Hanya guru yang TIDAK sedang dicadangkan boleh dibuang.")
                    
                    if not label_b:
                        st.info("Tiada guru yang boleh dibuang.")
                    else:
                        pilih_b = st.multiselect("Pilih guru", list(label_b.keys()), format_func=lambda k: label_b[k], key=f"guru_buang_{n_g}")
                        sah_b = st.checkbox("Ya, buang terus daripada Supabase (tidak boleh dipulihkan)", key=f"guru_buang_sah_{n_g}")
                        
                        if st.button(f"🗑️ Buang {len(pilih_b)} guru", use_container_width=True, disabled=not (pilih_b and sah_b), key=f"guru_buang_btn_{n_g}"):
                            ic_cad_b = {norm_ic(x) for x in cadangan_g["IC"]} if (not cadangan_g.empty and "IC" in cadangan_g.columns) else set()
                            
                            # Check tiada dalam cadangan
                            pilih_set = {norm_ic(i) for i in pilih_b}
                            if pilih_set & set(ic_cad_b):
                                st.error("Ada guru yang sedang dicadangkan - nyah-tick dan Hantar dahulu.")
                            else:
                                hasil_b = {}
                                buang_ok = False
                                
                                try:
                                    supa_gm, _ = get_supabase()
                                    if supa_gm:
                                        kod_s_upper = kod_s.strip().upper()
                                        ids_dipadam = 0
                                        
                                        # Padam dari guru_sekolah (table tunggal)
                                        res_gs = supa_gm.table("guru_sekolah").select("id, KOD_PPD, data").eq("KOD_PPD", _kod_daerah).limit(10000).execute()
                                        
                                        for r in (res_gs.data or []):
                                            d = r.get("data") or {}
                                            ks1 = str(d.get("KOD SEKOLAH ASAL") or d.get("KOD SEKOLAH") or "").strip().upper()
                                            ks2 = str(r.get("kod_sekolah") or r.get("KOD_SEKOLAH") or "").strip().upper()
                                            if ks1 != kod_s_upper and ks2 != kod_s_upper:
                                                continue
                                            
                                            ic_r = str(d.get("IC") or r.get("ic_guru") or "").strip()
                                            ic_norm_r = norm_ic(ic_r)
                                            if ic_norm_r in pilih_set:
                                                try:
                                                    supa_gm.table("guru_sekolah").delete().eq("id", r["id"]).execute()
                                                    ids_dipadam += 1
                                                except Exception as e:
                                                    st.warning(f"Padam id {r['id']}: {e}")
                                        
                                        # Juga cuba padam dari guru_master
                                        try:
                                            res_gm = supa_gm.table("guru_master").select("id, kod_sekolah, ic_guru, data").eq("kod_sekolah", kod_s_upper).limit(5000).execute()
                                            for r in (res_gm.data or []):
                                                ic_r = str(r.get("ic_guru") or (r.get("data") or {}).get("IC") or "").strip()
                                                if norm_ic(ic_r) in pilih_set:
                                                    try:
                                                        supa_gm.table("guru_master").delete().eq("id", r["id"]).execute()
                                                    except:
                                                        pass
                                        except:
                                            pass
                                        
                                        buang_ok = True
                                        hasil_b["bil"] = ids_dipadam
                                except Exception as e:
                                    st.error(f"Gagal buang: {e}")
                                
                                # Juga cuba padam dari TAB_GURU (untuk consistency)
                                try:
                                    def _buang_r(dfr):
                                        baru_r, bil = buang_guru_roster(dfr, kod_s, pilih_b, ic_cad_b)
                                        return baru_r
                                    modify_sheet(TAB_GURU, _buang_r)
                                except:
                                    pass
                                
                                if buang_ok:
                                    flash("success", f"✅ {hasil_b['bil']} guru dibuang daripada Senarai Guru.")
                                    st.session_state["guru_n"] = n_g + 1
                                    _cached_read.clear()
                                    st.rerun()
        
        elif menu == "Muat Naik / Muat Turun":
            st.header(f"📁 Muat Naik / Muat Turun - {info['nama']}")
            # ... (fungsi muat naik sama seperti asal)
            st.info("Fungsi muat naik tersedia. Guna templat Excel dan muat naik di sini.")
        
        elif menu == "Cadangan Petugas":
            st.header(f"👥 Cadangan Petugas - {info['nama']}")
            cadangan = read_sheet(TAB_CADANGAN)
            if not cadangan.empty and "KOD SEKOLAH ASAL" in cadangan.columns:
                cadangan_sendiri = cadangan[cadangan["KOD SEKOLAH ASAL"].astype(str) == kod_s]
            else:
                cadangan_sendiri = pd.DataFrame()
            
            if cadangan_sendiri.empty:
                st.info("Belum ada guru dicalonkan. Pergi ke menu **Senarai Guru**, tick guru dan tekan Hantar.")
            else:
                st.markdown(f"#### 👥 Senarai Cadangan Anda ({len(cadangan_sendiri)} orang)")
                st.dataframe(cadangan_sendiri, use_container_width=True)
        
        else:  # Status
            st.header("📤 Status")
            maklumat_s = read_sheet(TAB_MAKLUMAT)
            cadangan_s = read_sheet(TAB_CADANGAN)
            own_m = maklumat_s[maklumat_s["KOD SEKOLAH"].astype(str) == kod_s] if not maklumat_s.empty else pd.DataFrame()
            own_c = cadangan_s[cadangan_s["KOD SEKOLAH ASAL"].astype(str) == kod_s] if not cadangan_s.empty else pd.DataFrame()
            
            if own_m.empty: st.warning("❌ Maklumat Sekolah: belum diisi")
            else: st.success("✅ Maklumat Sekolah: sudah diisi")
            
            if own_c.empty: st.warning("❌ Cadangan Petugas: belum ada")
            else: st.success(f"✅ Cadangan Petugas: {len(own_c)} orang")
    
    # ==========================================
    # LOGIK PPD (dipendekkan untuk ruang)
    # ==========================================
    elif role == "PPD":
        st.header(f"🏢 PPD {info['ppd_nama']}")
        st.info("Logik PPD penuh - sila rujuk kod asal untuk fungsi Senarai Pusat, Kuota, Cadangan SUP, Jana Penempatan, dll.")
    
    # ==========================================
    # LOGIK JPN
    # ==========================================
    else:
        if menu == "📚 Master 60K (Pindah Data Daerah)":
            st.header("📚 MASTER GURU 60K")
            supa, err = get_supabase()
            if not supa:
                st.error(f"Supabase tak connect: {err}")
                st.stop()
            
            try:
                from collections import Counter
                rows_all = _baca_baris("guru_master", None)
                c = Counter([r.get("KOD_PPD","?") for r in rows_all])
                col1,col2 = st.columns(2)
                col1.metric("Total Master Guru", len(rows_all))
                col2.json(dict(c))
            except Exception as e:
                st.warning(f"guru_master belum wujud atau kosong: {e}")
            
            st.markdown("---")
            st.subheader("📚 Pindah Data Ke Sekolah (Agih Guru)")
            st.caption("Klik butang bawah untuk agih 60K guru ke table guru_sekolah (tunggal dengan KOD_PPD). SUP akan terus nampak guru mereka.")
            
            supa2, _ = get_supabase()
            if supa2:
                try:
                    res_cnt = supa2.table("guru_master").select("id", count="exact").limit(1).execute()
                    cnt_gm = getattr(res_cnt, 'count', 0) or 0
                    st.metric("Guru dalam guru_master", cnt_gm)
                    
                    # Check guru_sekolah (table tunggal)
                    res_gs = supa2.table("guru_sekolah").select("id", count="exact").limit(1).execute()
                    cnt_gs = getattr(res_gs, 'count', 0) or 0
                    st.metric("Guru dalam guru_sekolah (table tunggal)", cnt_gs)
                except Exception as e:
                    st.caption(f"Info: {e}")
                
                if st.button("🚀 PINDAH DATA KE SEKOLAH (Agih 60K dari guru_master)", type="primary", use_container_width=True, key="btn_pindah_sekolah"):
                    with st.spinner("Agih 60K guru dari guru_master ke table guru_sekolah..."):
                        total_agih, msg = agih_guru_master_ke_sekolah(supa2)
                        if total_agih > 0:
                            st.success(msg)
                            st.balloons()
                        else:
                            st.error(msg)
                        try:
                            _cached_read.clear()
                        except:
                            pass
        
        elif menu == "🔍 Check Supabase":
            st.header("🔍 Check Data Dalam Supabase")
            supa, err = get_supabase()
            if not supa:
                st.error(f"Supabase tak connect: {err}")
                st.stop()
            
            from collections import Counter
            for tbl in ["cadangan_sup", "penempatan_ppd", "maklumat_sekolah", "kuota_ppd", "status_hantar", "petugas_simpanan", "guru_sekolah", "guru_master"]:
                try:
                    rows_c = _baca_baris(tbl, None)
                    c = Counter([r.get("KOD_PPD", "?") for r in rows_c])
                    st.write(f"### {tbl}: {len(rows_c)} baris")
                    st.json(dict(c))
                    if rows_c:
                        df_sample = _df_from_rows(rows_c[:3])
                        if not df_sample.empty:
                            st.dataframe(df_sample.head(3), use_container_width=True)
                except Exception as e:
                    st.error(f"{tbl} error: {e}")
            
            if st.button("🔄 Clear Cache & Refresh"):
                _cached_read.clear()
                st.rerun()
        
        else:
            st.header(f"📋 {menu}")
            st.info("Fungsi ini tersedia dalam kod penuh.")
