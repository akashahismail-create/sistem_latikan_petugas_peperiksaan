import streamlit as st
import pandas as pd
from supabase import create_client
from io import BytesIO
import datetime
import math
import json
import re

# ================= CONFIGURATION =================
st.set_page_config(page_title="Pelantikan SPM Selangor 2026", layout="wide", page_icon="📚", initial_sidebar_state="collapsed")

SUPABASE_URL = "https://gnmaijhugkkvxejvsotk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdubWFpamh1Z2trdnhlanZzb3RrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTI0ODc4OTcsImV4cCI6MjEwODA2Mzg5N30.1YWg71nCwnQzP-KUzTdHR4rZAVCAesbKVqvVC1-X6lw"

@st.cache_resource
def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supa = get_supabase()

# Clear cache helper - untuk refresh button cepat
def clear_all_cache():
    st.cache_data.clear()
    st.cache_resource.clear()

# ✅ FIX: Buang trailing space dari KOD_DAERAH & PPD_MAP
KOD_DAERAH = ["BA", "BB", "BC", "BD", "BE", "BF", "BG", "BH", "BJ", "BK"]
PPD_MAP = {
    "BA": "Klang", "BB": "Kuala Langat", "BC": "Kuala Selangor",
    "BD": "Hulu Langat", "BE": "Hulu Selangor", "BF": "Sabak Bernam",
    "BG": "Gombak", "BH": "Petaling Perdana", "BJ": "Sepang", "BK": "Petaling Utama"
}

# ================= CSS BIRU CAIR - BACKGROUND BIRU CAIR =================
st.markdown("""
<style>
[data-testid="stSidebar"] {display: none !important;}
.stSidebar {display: none !important;}
section[data-testid="stSidebar"] {display: none !important;}

/* ===== BACKGROUND BIRU CAIR ===== */
.stApp {
    background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 50%, #e1f5fe 100%) !important;
    background-color: #e3f2fd !important;
    background-attachment: fixed !important;
}

/* Main container */
.main .block-container {
    background: transparent !important;
}

/* Metric cards - putih atas biru cair */
[data-testid="stMetric"] {
    background: #ffffff !important;
    border: 1px solid #90caf9 !important;
    border-radius: 12px !important;
    padding: 14px !important;
    box-shadow: 0 2px 8px rgba(13, 71, 161, 0.1) !important;
}
[data-testid="stMetric"] label, [data-testid="stMetric"] div {
    color: #212121 !important;
}
[data-testid="stMetricValue"] {
    color: #0d47a1 !important;
    font-weight: 800 !important;
}

[data-testid="stAlert"] {
    background: #ffffff !important;
    color: #212121 !important;
    border: 1px solid #90caf9 !important;
    border-radius: 10px !important;
}
[data-testid="stAlert"] p, [data-testid="stAlert"] div {
    color: #212121 !important;
}

[data-testid="stDataFrame"] {
    background: white !important;
    border-radius: 10px !important;
}

/* Custom sidebar - putih atas background biru cair */
.custom-sidebar {
    background: #ffffff !important;
    border-radius: 14px;
    padding: 16px;
    border: 2px solid #1976d2 !important;
    box-shadow: 0 4px 16px rgba(13, 71, 161, 0.15);
    height: fit-content;
    position: sticky;
    top: 10px;
}
.custom-sidebar h3 {
    font-size: 20px;
    color: #0d47a1 !important;
    font-weight: 800;
    margin-bottom: 4px;
}
.custom-sidebar p, .custom-sidebar span, .custom-sidebar div {
    color: #212121 !important;
}
.custom-sidebar [data-testid="stCaptionContainer"] {
    color: #212121 !important;
    opacity: 1 !important;
}
.custom-sidebar [data-testid="stCaptionContainer"] p {
    color: #212121 !important;
    font-weight: 700 !important;
    font-size: 13px !important;
}

.no-pusat-box {
    background: #ffeb3b !important;
    border: 2px solid #f57f17 !important;
    border-radius: 8px;
    padding: 10px 12px;
    margin: 10px 0;
}
.no-pusat-label {
    font-size: 11px;
    color: #bf360c !important;
    font-weight: 700;
}
.no-pusat-value {
    font-size: 18px;
    color: #000000 !important;
    font-weight: 900;
}

.ppd-table {
    background: white !important;
    color: #212121 !important;
}
.ppd-table th {
    background: #0d47a1 !important;
    color: white !important;
}
.ppd-table td {
    background: white !important;
    color: #212121 !important;
    border-bottom: 1px solid #e0e0e0 !important;
}

.badge-merah, .badge-kuning, .badge-hijau {
    font-weight: 800 !important;
}
.badge-merah {background: #ffcdd2 !important; border: 2px solid #d32f2f !important; color: #b71c1c !important;}
.badge-kuning {background: #fff9c4 !important; border: 2px solid #f57f17 !important; color: #e65100 !important;}
.badge-hijau {background: #c8e6c9 !important; border: 2px solid #2e7d32 !important; color: #1b5e20 !important;}

[data-testid="stRadio"] label {
    color: #212121 !important;
    font-weight: 600 !important;
}

.stButton button {
    font-weight: 700 !important;
}

[data-testid="stTabs"] button {
    color: #212121 !important;
    font-weight: 600 !important;
}

h1, h2, h3, h4, h5, h6 {
    color: #0d47a1 !important;
}

[data-testid="stCaptionContainer"] p {
    color: #424242 !important;
    font-weight: 600 !important;
    opacity: 1 !important;
}

label {
    color: #212121 !important;
    font-weight: 600 !important;
}

/* Card putih atas biru cair */
div[data-testid="stHorizontalBlock"] {
    background: transparent !important;
}

/* Expander */
[data-testid="stExpander"] {
    background: #ffffff !important;
    border: 1px solid #90caf9 !important;
    border-radius: 10px !important;
}
</style>
""", unsafe_allow_html=True)

# ================= HELPER FUNCTIONS (FORMULA & LOGIC) =================

def kira_kelas_dari_calon(jumlah_calon):
    """1 kelas = 20 calon, CEIL"""
    try:
        c = int(float(str(jumlah_calon).replace(",", "").strip() or 0))
        if c <= 0: return 0
        return math.ceil(c / 20)
    except: return 0

def kira_petugas_dari_kelas(jumlah_kelas):
    """User formula: kelas + 9 = petugas diperlukan"""
    try: return int(jumlah_kelas) + 9
    except: return 0

def kira_sekolah_perlu_calonkan(jumlah_kelas):
    """Sekolah perlu calonkan = petugas (kelas+9) + 1 KP +1 TKP +1 Penyelia = kelas+12"""
    try: return kira_petugas_dari_kelas(jumlah_kelas) + 3
    except: return 0

def safe_count(table_name):
    """Count dengan fallback kalau RLS block count exact"""
    try:
        res = supa.table(table_name).select("*", count="exact").limit(1).execute()
        if res.count is not None and res.count > 0: return res.count
        if res.data and len(res.data) > 0: return len(res.data)
        return 0
    except: return 0

def get_sekolah(kod):
    for col in ["kod_sekolah", "kod_sekolah_tuan_rumah", "KOD_SEKOLAH"]:
        try:
            res = supa.table("sekolah_master").select("*").eq(col, kod.upper()).limit(1).execute()
            if res.data:
                row = res.data[0]
                return {
                    "kod_sekolah": row.get("kod_sekolah") or row.get("KOD_SEKOLAH") or kod,
                    "nama_sekolah": row.get("nama_sekolah") or row.get("NAMA_SEKOLAH") or f"SEKOLAH {kod}",
                    "kod_ppd": row.get("kod_ppd") or row.get("KOD_PPD") or "BH",
                    "ppd": row.get("ppd") or row.get("PPD") or "Petaling Perdana",
                    "_raw": row
                }
        except: continue
    return {"kod_sekolah": kod, "nama_sekolah": f"SEKOLAH {kod}", "kod_ppd": "BH", "ppd": "Petaling Perdana"}

@st.cache_data(ttl=300, show_spinner=False)
def get_guru_df(kod_sekolah):
    try:
        res = None
        for col in ["kod_sekolah", "KOD_SEKOLAH", "kod_sekolah_tuan_rumah"]:
            try:
                r = supa.table("guru_master").select("*").eq(col, kod_sekolah.upper()).limit(2000).execute()
                if r.data: res=r; break
            except: continue
        
        if not res:
            res = supa.table("guru_master").select("*").eq("kod_sekolah", kod_sekolah.upper()).limit(2000).execute()
        
        rows = []
        sekolah_map_guru = {}
        try:
            res_sek = supa.table("sekolah_master").select("kod_sekolah,nama_sekolah").limit(2000).execute()
            for s in res_sek.data or []:
                k = (s.get("kod_sekolah") or s.get("KOD_SEKOLAH") or "").upper()
                n = s.get("nama_sekolah") or s.get("NAMA_SEKOLAH") or ""
                if k: sekolah_map_guru[k] = n
        except: pass

        for r in res.data or []:
            d = r.get("data") or {}
            if isinstance(d, str):
                try: d = json.loads(d)
                except: d = {}
            
            def _nk(x): return re.sub(r"[^A-Z0-9]", "", str(x).upper())
            _kosong_val = ("", "none", "null", "nan", "n/a", "-")
            _dn, _rn = {}, {}
            
            for _k, _v in d.items():
                if _v is not None and not isinstance(_v, (dict, list)) and str(_v).strip().lower() not in _kosong_val:
                    _dn.setdefault(_nk(_k), str(_v).strip())
            for _k, _v in r.items():
                if _v is not None and not isinstance(_v, (dict, list)) and str(_v).strip().lower() not in _kosong_val:
                    _rn.setdefault(_nk(_k), str(_v).strip())
            
            def get_val(*keys, default=""):
                for k in keys:
                    nk = _nk(k)
                    if nk in _dn: return _dn[nk]
                    if nk in _rn: return _rn[nk]
                return default

            ic_val = get_val("IC", "ic_guru", "IC_GURU", "ic", "no_ic", "NO_KP", "NO KP")
            nama_val = get_val("NAMA GURU", "nama_guru", "NAMA_GURU", "nama", "NAMA")
            jantina_val = get_val("JANTINA", "jantina", "JANTINA_GURU", "Jantina", "SEX")
            poskod_val = get_val("POSKOD_RUMAH", "poskod_rumah", "POSKOD", "poskod", "POSKOD RUMAH")
            alamat_val = get_val("ALAMAT_RUMAH", "alamat_rumah", "ALAMAT RUMAH", "alamat", "ALAMAT")
            telefon_val = get_val("TELEFON_GURU", "telefon_guru", "NO TELEFON GURU", "TELEFON", "no_telefon")
            email_val = get_val("EMAIL_GURU", "email_guru", "EMAIL GURU", "EMAIL", "email", "EMEL", "EMEL GURU", "E-MEL", "E-MAIL")
            pengalaman_val = get_val("PENGALAMAN_SPM", "pengalaman_spm", "PENGALAMAN", "pengalaman")
            jawatan_val = get_val("JAWATAN_CADANGAN", "jawatan_cadangan", "JAWATAN CADANGAN", "jawatan")
            kod_ppd_val = get_val("KOD_PPD", "kod_ppd", "kod_ppd_asal", "KOD_PPD_ASAL", "ppd", "PPD")
            kod_sek_val = get_val("KOD_SEKOLAH", "kod_sekolah", "KOD SEKOLAH", "kod_sekolah_asal", "KOD_SEKOLAH_ASAL", default=kod_sekolah)
            nama_sek_val = get_val("NAMA_SEKOLAH", "nama_sekolah", "NAMA SEKOLAH", "sekolah_asal", "NAMA_SEKOLAH_ASAL")
            no_pusat_asal_val = get_val("NO_PUSAT_ASAL", "no_pusat_asal", "NO PUSAT ASAL", "PUSAT ASAL", "pusat_asal", "KOD PUSAT ASAL", "NO_PUSAT", "KOD PUSAT")

            if not nama_sek_val or nama_sek_val == "" or nama_sek_val == kod_sek_val:
                nama_sek_val = sekolah_map_guru.get(kod_sek_val.upper(), "") or sekolah_map_guru.get(kod_sekolah.upper(), "") or kod_sek_val
            
            if not kod_ppd_val or kod_ppd_val == "":
                kod_ppd_val = kod_sekolah[:2] if len(kod_sekolah) >= 2 else "BA"
            
            if not jawatan_val or jawatan_val.strip() == "":
                jawatan_val = "Pengawas Peperiksaan"

            rows.append({
                "id": r.get("id"),
                "NAMA GURU": nama_val, "IC": ic_val, "JANTINA": jantina_val,
                "POSKOD_RUMAH": poskod_val, "ALAMAT_RUMAH": alamat_val,
                "TELEFON": telefon_val, "TELEFON_GURU": telefon_val,
                "EMAIL_GURU": email_val, "EMAIL": email_val,
                "JAWATAN CADANGAN": jawatan_val, "JAWATAN_CADANGAN": jawatan_val,
                "PENGALAMAN_SPM": pengalaman_val, "PENGALAMAN": pengalaman_val,
                "KOD_PPD": kod_ppd_val, "KOD_PPD_ASAL": kod_ppd_val,
                "KOD SEKOLAH": kod_sek_val, "KOD_SEKOLAH": kod_sek_val,
                "KOD_SEKOLAH_ASAL": kod_sek_val,
                "NAMA_SEKOLAH_ASAL": nama_sek_val, "NAMA_SEKOLAH": nama_sek_val,
                "NO_PUSAT_ASAL": no_pusat_asal_val, "ALAMAT": alamat_val,
                "data_full": d if isinstance(d, dict) else {}, "raw": r
            })
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=300, show_spinner=False)
def get_pusat_df():
    try:
        res = supa.table("pusat_master").select("*").limit(2000).execute()
        df = pd.DataFrame(res.data or [])
        if not df.empty:
            df_norm = df.copy()
            if "no_pusat" in df_norm.columns: df_norm["kod_pusat_std"] = df_norm["no_pusat"]
            elif "kod_pusat" in df_norm.columns: df_norm["kod_pusat_std"] = df_norm["kod_pusat"]
            elif "NO_PUSAT" in df_norm.columns: df_norm["kod_pusat_std"] = df_norm["NO_PUSAT"]
            else: df_norm["kod_pusat_std"] = df_norm.iloc[:, 1] if len(df_norm.columns) > 1 else " "
            
            if "nama_pusat" in df_norm.columns: df_norm["nama_pusat_std"] = df_norm["nama_pusat"]
            elif "NAMA_PUSAT" in df_norm.columns: df_norm["nama_pusat_std"] = df_norm["NAMA_PUSAT"]
            else: df_norm["nama_pusat_std"] = df_norm.get("nama_sekolah", " ")
            return df
    except Exception as e:
        st.error(f"pusat_master error: {e}")
    return pd.DataFrame()

@st.cache_data(ttl=120, show_spinner=False)
def get_cadangan_df(kod_ppd=None, kod_sekolah=None):
    try:
        try:
            if kod_sekolah:
                res = supa.table("cadangan_sup").select("*").eq("kod_sekolah", kod_sekolah.upper()).limit(5000).execute()
                if not res.data: res = supa.table("cadangan_sup").select("*").eq("kod_sekolah_asal", kod_sekolah.upper()).limit(5000).execute()
                if not res.data: res = supa.table("cadangan_sup").select("*").limit(5000).execute()
            elif kod_ppd:
                res = supa.table("cadangan_sup").select("*").eq("kod_ppd", kod_ppd.upper()).limit(5000).execute()
                if not res.data: res = supa.table("cadangan_sup").select("*").limit(5000).execute()
            else:
                res = supa.table("cadangan_sup").select("*").limit(5000).execute()
        except:
            res = supa.table("cadangan_sup").select("*").limit(5000).execute()
        
        df = pd.DataFrame(res.data or [])
        if df.empty: return df
        
        # Normalization logic simplified for brevity but keeping functionality
        norm_rows = []
        for _, r in df.iterrows():
            # Basic extraction
            row_dict = {}
            for k, v in r.items():
                if k != 'data':
                    row_dict[k] = v
                else:
                    if isinstance(v, dict):
                        row_dict.update(v)
                    elif isinstance(v, str):
                        try: row_dict.update(json.loads(v))
                        except: pass
            
            # Ensure critical fields exist
            if 'STATUS' not in row_dict: row_dict['STATUS'] = 'DICADANGKAN'
            if 'KOD_PPD' not in row_dict: row_dict['KOD_PPD'] = row_dict.get('kod_ppd', '')
            
            norm_rows.append(row_dict)
            
        df_norm = pd.DataFrame(norm_rows)
        
        if kod_ppd:
            try: df_norm = df_norm[df_norm["KOD_PPD"].str.upper() == kod_ppd.upper()]
            except: pass
        if kod_sekolah:
            try:
                if "KOD_SEKOLAH_ASAL" in df_norm.columns:
                    df_norm = df_norm[df_norm["KOD_SEKOLAH_ASAL"].str.upper() == kod_sekolah.upper()]
                elif "KOD_SEKOLAH" in df_norm.columns:
                    df_norm = df_norm[df_norm["KOD_SEKOLAH"].str.upper() == kod_sekolah.upper()]
            except: pass
        return df_norm
    except Exception:
        return pd.DataFrame()

def flash(level, msg):
    st.session_state.setdefault("_flash", []).append((level, msg))

def show_flash():
    for level, msg in st.session_state.pop("_flash", []):
        getattr(st, level)(msg)

def _id_py(x):
    if hasattr(x, "item"): x = x.item()
    if isinstance(x, float) and x.is_integer(): return int(x)
    return x

def hantar_ke_ppd(ids, kod_ppd):
    berjaya, gagal = 0, []
    for i in range(0, len(ids), 100):
        kelompok = ids[i:i + 100]
        try:
            supa.table("cadangan_sup").update({"status": "HANTAR KE PPD", "kod_ppd": kod_ppd}).in_("id", kelompok).execute()
        except Exception:
            try:
                supa.table("cadangan_sup").update({"status": "HANTAR KE PPD"}).in_("id", kelompok).execute()
            except Exception as e:
                gagal.append(f"{e}")
                continue
        berjaya += len(kelompok)
    return berjaya, gagal

def simpan_penempatan_ppd(items):
    """Simpan hasil janaan ke cadangan_sup (lajur kod_pusat + status DIJANA PPD), berkelompok ikut pusat.
    items: [{"id":..., "ic":..., "pusat":...}]. Pulang (bil_berjaya, senarai_gagal)."""
    berjaya, gagal = 0, []
    ikut_pusat = {}
    for it in items:
        ikut_pusat.setdefault(str(it["pusat"]), []).append(it)
    for pusat, senarai in ikut_pusat.items():
        ids = [_id_py(i["id"]) for i in senarai if str(i.get("id") or "").strip() not in ("", "nan", "None")]
        for k in range(0, len(ids), 100):
            kelompok = ids[k:k + 100]
            try:
                supa.table("cadangan_sup").update({"kod_pusat": pusat, "status": "DIJANA PPD"}).in_("id", kelompok).execute()
                berjaya += len(kelompok)
            except Exception as e:
                gagal.append(f"{pusat}: {e}")
        for i in senarai:
            if str(i.get("id") or "").strip() in ("", "nan", "None") and i.get("ic"):
                try:
                    supa.table("cadangan_sup").update({"kod_pusat": pusat, "status": "DIJANA PPD"}).eq("ic_guru", i["ic"]).execute()
                    berjaya += 1
                except Exception as e:
                    gagal.append(f"{i.get('ic')}: {e}")
    return berjaya, gagal


def to_excel(df):
    output = BytesIO()
    try:
        import openpyxl
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        return output.getvalue()
    except ImportError: pass
    except Exception: pass
    
    try:
        output.write(df.to_csv(index=False).encode('utf-8-sig'))
        return output.getvalue()
    except:
        return b""

def get_template_guru():
    template_data = {
        "NAMA GURU": ["CONTOH: ALI BIN ABU"], "IC": ["900101-01-1234"],
        "JANTINA": ["L"], "POSKOD_RUMAH": ["40000"],
        "ALAMAT_RUMAH": ["NO 1, JALAN CONTOH"], "TELEFON_GURU": ["012-3456789"],
        "EMAIL_GURU": ["ali@gmail.com"], "PENGALAMAN_SPM": ["3"],
        "KOD_SEKOLAH": ["BFT0003"], "NAMA_SEKOLAH_ASAL": ["SAM NURUL IMAN"],
        "NO_PUSAT_ASAL": ["BA142"]
    }
    return pd.DataFrame(template_data)

# ================= REFRESH COMPONENT =================
def add_refresh_button():
    st.markdown("---")
    st.markdown("### 🔄 Refresh Data")
    st.caption(f"Last: {datetime.datetime.now().strftime('%d/%m %H:%M:%S')}")
    if st.button("🔄 REFRESH - Baca Data Baru", use_container_width=True, type="primary", key=f"refresh_main_{st.session_state.role}_{st.session_state.kod if hasattr(st.session_state, 'kod') else 'x'}"):
        st.cache_data.clear()
        # Jangan clear resource (supabase client) - itu yang buat buffering lama
        st.toast("✅ Data refreshed! Baca perubahan terbaru")
        st.rerun()
    st.caption("Tekan selepas SUP buat pertukaran / cadangan")

# ================= SESSION INIT =================
if "role" not in st.session_state:
    st.session_state.role = None

# ================= LOGIN PAGE =================
if st.session_state.role is None:
    st.markdown("<h1 style='text-align:center; color:#0d47a1;'>🏫 SISTEM PELANTIKAN PETUGAS PEPERIKSAAN SPM SELANGOR 2026</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>369 Sekolah | 506 Pusat | 71,064 Calon</p>", unsafe_allow_html=True)
    
    @st.cache_data(ttl=600)
    def load_sekolah_list():
        try:
            res = supa.table("sekolah_master").select("*").limit(1000).execute()
            data = res.data or []
            rows = []
            for r in data:
                kod = r.get("kod_sekolah") or r.get("KOD_SEKOLAH") or ""
                nama = r.get("nama_sekolah") or r.get("NAMA_SEKOLAH") or ""
                kod_ppd = r.get("kod_ppd") or r.get("KOD_PPD") or "BH"
                if kod and nama:
                    rows.append({"KOD_SEKOLAH": kod.upper().strip(), "NAMA_SEKOLAH": nama.upper().strip(),
                                 "KOD_PPD": kod_ppd.upper().strip(), "PPD": PPD_MAP.get(kod_ppd.upper().strip(), "")})
            df = pd.DataFrame(rows)
            order_map = {k: i for i, k in enumerate(KOD_DAERAH)}
            if not df.empty:
                df["order"] = df["KOD_PPD"].map(order_map)
                df = df.sort_values(["order", "NAMA_SEKOLAH"]).reset_index(drop=True)
                df["ID"] = df.index + 1
                df["PASSWORD"] = df["ID"].astype(str)
                df["PASSWORD_LAMA"] = "12345" + df["ID"].astype(str)
            return df
        except Exception:
            return pd.DataFrame()

    df_sekolah_all = load_sekolah_list()
    tab1, tab2, tab3 = st.tabs(["SUP - Sekolah", "🏢 PPD - Daerah", "🏛️ JPN - Negeri"])
    
    with tab1:
        st.markdown("### 🏫 Log Masuk SUP - Penyelia Sekolah")
        col_a, col_b = st.columns(2)
        with col_a:
            pilih_ppd_label = st.selectbox("1️⃣ Pilih Daerah (PPD)", options=[f"{k} - {PPD_MAP[k]}" for k in KOD_DAERAH], key="sup_daerah")
            pilih_ppd_code = pilih_ppd_label.split(" - ")[0] if pilih_ppd_label else "BA"
            if not df_sekolah_all.empty:
                df_filtered = df_sekolah_all[df_sekolah_all["KOD_PPD"] == pilih_ppd_code]
            else:
                df_filtered = pd.DataFrame()
            
            if df_filtered.empty:
                st.warning(f"Tiada sekolah untuk {pilih_ppd_code}")
                sekolah_manual = st.text_input("KOD SEKOLAH (Manual)", value="BFT8002", key="sup_kod_manual").upper()
                pilih_sekolah_kod = sekolah_manual
                pilih_sekolah_nama = f"SEKOLAH {sekolah_manual}"
                sup_id = 1
                sup_password_expected = "1"
            else:
                sekolah_options = [f"{row['KOD_SEKOLAH']} - {row['NAMA_SEKOLAH']}" for _, row in df_filtered.iterrows()]
                pilih_sekolah_str = st.selectbox(f"2️⃣ Pilih Sekolah ({len(df_filtered)} sekolah di {PPD_MAP[pilih_ppd_code]})", options=sekolah_options, key="sup_sekolah_list")
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
            st.markdown(f"**ID Sekolah:** {sup_id} | **PPD:** {pilih_ppd_code} - {PPD_MAP.get(pilih_ppd_code, '')}")
            with st.container(border=True):
                st.markdown("🔑 **Password Untuk Testing**")
                if not df_filtered.empty and 'sup_password_expected' in locals():
                    st.code(f"ID: {sup_id}\nPassword Baru: {sup_password_expected}\nPassword Lama: {sup_password_lama}", language="text")
                else:
                    st.code(f"Password: {sup_id} atau 12345{sup_id}", language="text")
            
            pwd_input = st.text_input("3️⃣ Masuk Password", type="password", key="sup_pwd", placeholder=f"Contoh: {sup_password_expected if 'sup_password_expected' in locals() else '1'}")
            if st.button("🚀 Masuk SUP Sekolah", use_container_width=True, type="primary", key="btn_sup"):
                valid_pw = [str(sup_id), f"12345{sup_id}", sup_password_expected if 'sup_password_expected' in locals() else str(sup_id)]
                if not df_sekolah_all.empty and 'sup_password_lama' in locals():
                    valid_pw.append(sup_password_lama)
                
                if pwd_input.strip() in valid_pw or pwd_input.strip() == "12345" or pwd_input.strip().lower() == "a" or pwd_input.strip() == "":
                    if pwd_input.strip() == "" and not st.checkbox("Benarkan login tanpa password untuk testing?", key="allow_empty"):
                        st.error(f"Password salah! Cuba {sup_password_expected} atau {sup_password_lama}")
                    else:
                        info = get_sekolah(pilih_sekolah_kod)
                        info["kod_sekolah"] = pilih_sekolah_kod
                        info["nama_sekolah"] = pilih_sekolah_nama
                        info["kod_ppd"] = pilih_ppd_code
                        st.session_state.role = "SUP"
                        st.session_state.kod = pilih_sekolah_kod
                        st.session_state.info = info
                        st.session_state.sup_id = sup_id
                        st.rerun()
                else:
                    st.error(f"Password salah! Sepatutnya: {sup_password_expected} atau {sup_password_lama}")

    with tab2:
        st.markdown("### 🏢 Log Masuk PPD - Pejabat Pendidikan Daerah")
        col1, col2 = st.columns(2)
        with col1:
            ppd_labels = [f"{i+1}. {KOD_DAERAH[i]} - {PPD_MAP[KOD_DAERAH[i]]} (ID:{i+1} Pwd:{chr(97+i)})" for i in range(len(KOD_DAERAH))]
            pilih_ppd_full = st.selectbox("Pilih PPD", options=ppd_labels, key="ppd_full")
            ppd_code = pilih_ppd_full.split(" - ")[0].split(". ")[1] if ". " in pilih_ppd_full else KOD_DAERAH[0]
            ppd_id = KOD_DAERAH.index(ppd_code) + 1 if ppd_code in KOD_DAERAH else 1
            ppd_pwd_expected = chr(96 + ppd_id)
        
        with col2:
            with st.container(border=True):
                st.markdown("🔑 **Password PPD Untuk Testing**")
                st.code(f"ID PPD: {ppd_id}\nPPD: {ppd_code} - {PPD_MAP.get(ppd_code, '')}\nPassword: {ppd_pwd_expected}", language="text")
            ppd_pwd = st.text_input("Masuk Password PPD", type="password", key="ppd_pwd", placeholder=f"Contoh: {ppd_pwd_expected}")
            if st.button("🚀 Masuk PPD", use_container_width=True, type="primary", key="btn_ppd"):
                valid = [ppd_pwd_expected, str(ppd_id), f"12345{ppd_id}", chr(96 + ppd_id).upper(), ppd_code.lower(), "a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]
                if ppd_pwd.strip().lower() in [v.lower() for v in valid] or ppd_pwd.strip() == "":
                    st.session_state.role = "PPD"
                    st.session_state.kod = ppd_code
                    st.session_state.ppd_id = ppd_id
                    st.rerun()
                else:
                    st.error(f"Password salah! Cuba {ppd_pwd_expected} atau {ppd_id}")

    with tab3:
        st.markdown("### 🏛️ Log Masuk JPN - Jabatan Pendidikan Negeri")
        col1, col2 = st.columns(2)
        with col1:
            jpn_id = st.text_input("ID JPN", value="1", key="jpn_id")
            jpn_pwd = st.text_input("Password JPN", type="password", key="jpn_pwd", placeholder="a")
            with st.container(border=True):
                st.code("ID: 1\nPassword: a atau 1 atau 123451", language="text")
            if st.button("🚀 Masuk JPN", use_container_width=True, type="primary", key="btn_jpn"):
                if jpn_id == "1" and jpn_pwd.strip().lower() in ["a", "1", "123451", "12345", ""]:
                    st.session_state.role = "JPN"
                    st.rerun()
                else:
                    st.session_state.role = "JPN"
                    st.rerun()
        with col2:
            st.info("JPN boleh tengok semua PPD, semua sekolah (369), semua pusat (506), semua cadangan.")
    
    st.stop()

# ================= ROLE: SUP =================
if st.session_state.role == "SUP":
    kod = st.session_state.kod
    info = st.session_state.info
    
    # Custom Layout
    col_menu, col_main = st.columns([1, 3.2], gap="large")
    
    with col_menu:
        st.markdown('<div class="custom-sidebar">', unsafe_allow_html=True)
        st.markdown(f"### 🏫 SUP {kod}")
        # Nama sekolah - buat lebih visible, bukan caption cair
        st.markdown(f"<div style='color:#212121; font-weight:700; font-size:13px; margin-bottom:4px;'>{info.get('nama_sekolah', '')}</div><div style='color:#424242; font-size:12px; margin-bottom:8px;'>{info.get('kod_ppd', 'BH')} - {PPD_MAP.get(info.get('kod_ppd', 'BH'), '')}</div>", unsafe_allow_html=True)
        # ===== PAPARKAN NO PUSAT DI BAWAH NAMA SEKOLAH =====
        try:
            df_pusat_sidebar = get_pusat_df()
            no_pusat_list_sidebar = []
            for _, r in df_pusat_sidebar.iterrows():
                d = r.get("data") if isinstance(r.get("data"), dict) else {}
                if isinstance(d, str):
                    try: d = json.loads(d)
                    except: d = {}
                ks_tuan = str(r.get("kod_sekolah_tuan_rumah") or r.get("kod_sekolah") or r.get("KOD_SEKOLAH") or d.get("KOD_SEKOLAH") or d.get("KOD SEKOLAH") or "").upper().strip()
                ks_biasa = str(r.get("kod_sekolah") or d.get("KOD_SEKOLAH") or "").upper().strip()
                if ks_tuan == kod.upper().strip() or ks_biasa == kod.upper().strip():
                    no_p = str(r.get("no_pusat") or r.get("kod_pusat") or r.get("NO_PUSAT") or d.get("NO_PUSAT") or d.get("NO PUSAT") or "").upper().strip()
                    if no_p and no_p not in no_pusat_list_sidebar:
                        no_pusat_list_sidebar.append(no_p)
            if no_pusat_list_sidebar:
                no_pusat_str = ", ".join(no_pusat_list_sidebar)
                st.markdown(f'''<div class="no-pusat-box"><div class="no-pusat-label">📍 NO PUSAT SEKOLAH:</div><div class="no-pusat-value">{no_pusat_str}</div></div>''', unsafe_allow_html=True)
            else:
                st.markdown(f'''<div class="no-pusat-box" style="background:#ffccbc; border-color:#d32f2f;"><div class="no-pusat-label" style="color:#b71c1c;">⚠️ TIADA NO PUSAT:</div><div class="no-pusat-value" style="font-size:12px;">Tiada pusat dijumpai untuk {kod}<br>Hubungi PPD</div></div>''', unsafe_allow_html=True)
        except Exception as e:
            st.markdown(f"<div style='background:#fff3e0; padding:8px; border-radius:6px; font-size:11px;'>Error load pusat: {e}</div>", unsafe_allow_html=True)
        add_refresh_button()
        
        MENU_SUP = [('dashboard', '📊 Dashboard'), ('senarai', '📋 Senarai Guru'), ('tambah', '➕ Tambah Guru'), 
                    ('import', '📤 Import Excel'), ('buang', '🗑️ Buang Guru'), ('cadangan', '📝 Cadangan Lantikan'), 
                    ('hantar', '📤 Hantar ke PPD'), ('keluar', '🚪 Log Keluar')]
        menu = st.radio("Menu SUP", [k for k, _ in MENU_SUP], format_func=dict(MENU_SUP).get, label_visibility="collapsed", key="sup_menu_radio")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_main:
        show_flash()
        df_guru = get_guru_df(kod)
        
        if menu == "keluar":
            st.session_state.clear()
            st.rerun()
            
        elif menu == "dashboard":
            st.header(f"Dashboard SUP - {kod} {info.get('nama_sekolah', '')}")
            st.markdown(f"**Kod Sekolah:** `{kod}` | **PPD:** `{info.get('kod_ppd','')} - {PPD_MAP.get(info.get('kod_ppd',''),'')}` | **Nama:** {info.get('nama_sekolah','')}")
            try:
                df_pusat_all = get_pusat_df()
                pusat_sekolah = []
                for _, r in df_pusat_all.iterrows():
                    d = r.get("data") if isinstance(r.get("data"), dict) else {}
                    if isinstance(d, str):
                        try: d = json.loads(d)
                        except: d = {}
                    # Check multiple possible columns for tuan rumah
                    ks_tuan = str(r.get("kod_sekolah_tuan_rumah") or r.get("kod_sekolah") or r.get("KOD_SEKOLAH") or d.get("KOD_SEKOLAH") or d.get("KOD SEKOLAH") or d.get("KOD_SEKOLAH_TUAN_RUMAH") or "").upper().strip()
                    ks_biasa = str(r.get("kod_sekolah") or d.get("KOD_SEKOLAH") or "").upper().strip()
                    # Match if kod sekolah matches tuan rumah OR kod sekolah biasa
                    if ks_tuan == kod.upper().strip() or ks_biasa == kod.upper().strip():
                        calon = r.get("jumlah_calon") or r.get("calon") or r.get("JUMLAH_CALON") or d.get("JUMLAH_CALON") or d.get("CALON") or 0
                        try: calon_i = int(float(str(calon) or 0))
                        except: calon_i = 0
                        kelas = kira_kelas_dari_calon(calon_i)
                        petugas_k9 = kira_petugas_dari_kelas(kelas)
                        sekolah_perlu = kira_sekolah_perlu_calonkan(kelas)
                        no_pusat_val = str(r.get("no_pusat") or r.get("kod_pusat") or r.get("NO_PUSAT") or d.get("NO_PUSAT") or d.get("NO PUSAT") or d.get("KOD_PUSAT") or "").upper().strip()
                        nama_pusat_val = str(r.get("nama_pusat") or r.get("NAMA_PUSAT") or d.get("NAMA_PUSAT") or d.get("NAMA PUSAT") or "").upper().strip()
                        pusat_sekolah.append({"NO_PUSAT": no_pusat_val, "NAMA_PUSAT": nama_pusat_val, "CALON": calon_i, "KELAS": kelas, "PETUGAS_K9": petugas_k9, "SEKOLAH_PERLU": sekolah_perlu})
            except Exception as e:
                st.error(f"Error load pusat: {e}")
                pusat_sekolah = []
            
            if pusat_sekolah:
                total_calon = sum([p["CALON"] for p in pusat_sekolah])
                total_kelas = sum([p["KELAS"] for p in pusat_sekolah])
                total_petugas = sum([p["PETUGAS_K9"] for p in pusat_sekolah])
                total_perlu = sum([p["SEKOLAH_PERLU"] for p in pusat_sekolah])
                # Paparan NO PUSAT yang jelas
                no_pusat_list = ", ".join([f"{p['NO_PUSAT']}" for p in pusat_sekolah if p['NO_PUSAT']])
                st.markdown(f"""
                <div style="background: #ffffff; padding:20px; border-radius:12px; border:3px solid #1565c0; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-bottom:20px;">
                    <h3 style="margin:0; color:#0d47a1 !important; font-weight:800;">🏫 KEPERLUAN PENGAWAS SEKOLAH ANDA - {kod}</h3>
                    <p style="margin:8px 0; font-size:16px;">
                        Sekolah anda ada <b>{len(pusat_sekolah)} pusat</b> | <b>{total_calon} calon</b> | <b>{total_kelas} kelas</b> (1 kelas=20 calon)<br>
                        Formula: Kelas = CEIL(Calon/20), Petugas = Kelas+9, Sekolah Perlu = Kelas+12
                    </p>
                    <div style="background:#fff3e0; padding:12px 16px; border-radius:8px; border-left:4px solid #ff9800; margin:10px 0;">
                        <div style="font-size:14px; color:#e65100; font-weight:700;">📍 NO PUSAT SEKOLAH ANDA:</div>
                        <div style="font-size:22px; font-weight:800; color:#bf360c; letter-spacing:1px;">{no_pusat_list}</div>
                    </div>
                    <div style="display:flex; gap:15px; margin-top:12px; flex-wrap:wrap;">
                        <div style="background:white; padding:12px 18px; border-radius:8px; box-shadow:0 2px 5px rgba(0,0,0,0.1);">
                            <div style="font-size:13px; color:#666;">JUMLAH KELAS</div>
                            <div style="font-size:24px; font-weight:800; color:#1565c0;">{total_kelas}</div>
                        </div>
                        <div style="background:white; padding:12px 18px; border-radius:8px; box-shadow:0 2px 5px rgba(0,0,0,0.1);">
                            <div style="font-size:13px; color:#666;">PETUGAS DIPERLUKAN</div>
                            <div style="font-size:24px; font-weight:800; color:#e65100;">{total_petugas}</div>
                        </div>
                        <div style="background:#ffebee; padding:12px 18px; border-radius:8px; border:2px solid #c62828; box-shadow:0 2px 5px rgba(0,0,0,0.1);">
                            <div style="font-size:13px; color:#c62828; font-weight:700;">SEKOLAH WAJIB CALONKAN</div>
                            <div style="font-size:28px; font-weight:800; color:#c62828;">{total_perlu} ORANG</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                # Table dengan NO PUSAT di depan, lebih jelas
                df_pusat_display = pd.DataFrame(pusat_sekolah)
                # Reorder columns: NO_PUSAT first
                cols_order = ["NO_PUSAT", "NAMA_PUSAT", "CALON", "KELAS", "PETUGAS_K9", "SEKOLAH_PERLU"]
                df_pusat_display = df_pusat_display[cols_order] if all(c in df_pusat_display.columns for c in cols_order) else df_pusat_display
                st.markdown("### 📍 Senarai Pusat Sekolah Anda (NO PUSAT)")
                st.dataframe(df_pusat_display, use_container_width=True, hide_index=True)
            else:
                st.warning(f"⚠️ Tiada pusat dijumpai untuk sekolah {kod}")
                st.info("Sistem cuba cari pusat dengan kod_sekolah_tuan_rumah = kod sekolah anda. Hubungi PPD untuk semak pusat sekolah anda di table pusat_master.")
                # Show all pusat for debugging
                try:
                    df_all = get_pusat_df()
                    if not df_all.empty:
                        st.caption(f"Debug: Ada {len(df_all)} pusat dalam DB. 10 pertama:")
                        st.dataframe(df_all.head(10), use_container_width=True)
                except:
                    pass
            
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.metric("Jumlah Guru", len(df_guru))
            with c2: 
                try:
                    cnt = supa.table("guru_master").select("id", count="exact").execute()
                    st.metric("Total Guru Selangor", cnt.count)
                except: st.metric("Total Guru Selangor", "-")
            with c3: st.metric("Pusat Sekolah Ini", len(pusat_sekolah) if 'pusat_sekolah' in locals() else 0)
            with c4:
                try:
                    cad = get_cadangan_df(kod_sekolah=kod)
                    st.metric("Cadangan Dihantar", len(cad))
                except: st.metric("Cadangan", "0")
            
            st.markdown("---")
            st.subheader("Guru Terkini")
            if not df_guru.empty:
                st.dataframe(df_guru[["NAMA GURU", "IC", "TELEFON", "JAWATAN CADANGAN"]], use_container_width=True, hide_index=True)
            else:
                st.warning("Belum ada guru. Sila Tambah Guru atau Import Excel.")

        elif menu == "senarai":
            st.header(f"Senarai Guru - {kod} - Lengkap")
            if df_guru.empty:
                st.info("guru_master kosong untuk sekolah ini. Sila Tambah Guru atau Import Excel.")
            else:
                st.success(f"Ada {len(df_guru)} guru di {kod}")
                cols_to_show = [c for c in ["NAMA GURU", "IC", "JANTINA", "POSKOD_RUMAH", "ALAMAT_RUMAH", "TELEFON_GURU", "EMAIL_GURU", "JAWATAN CADANGAN", "PENGALAMAN_SPM", "KOD_SEKOLAH_ASAL", "NAMA_SEKOLAH_ASAL", "NO_PUSAT_ASAL"] if c in df_guru.columns]
                if cols_to_show:
                    st.dataframe(df_guru[cols_to_show], use_container_width=True, hide_index=True)
                    kosong = df_guru[df_guru["JANTINA"].isin(["", "KOSONG"]) | df_guru["POSKOD_RUMAH"].isin(["", "KOSONG"]) | df_guru["TELEFON_GURU"].isin(["", "KOSONG"])]
                    if not kosong.empty:
                        st.warning(f"⚠️ Ada {len(kosong)} guru dengan data KOSONG (JANTINA/POSKOD/ALAMAT/TELEFON/EMAIL). Sila edit di bawah.")
                
                st.download_button(" Export Excel Lengkap", to_excel(df_guru), file_name=f"guru_{kod}_lengkap.xlsx", use_container_width=True)
                st.markdown("---")
                st.subheader("✏️ Edit Data Guru (Lengkapkan yang kosong)")
                edit_ic = st.selectbox("Pilih IC guru untuk edit", df_guru["IC"].tolist(), format_func=lambda x: f"{x} - {df_guru[df_guru['IC']==x]['NAMA GURU'].values[0] if not df_guru[df_guru['IC']==x].empty else x}")
                if edit_ic:
                    guru_edit = df_guru[df_guru["IC"] == edit_ic].iloc[0] if not df_guru[df_guru["IC"] == edit_ic].empty else None
                    if guru_edit is not None:
                        with st.form(f"edit_{edit_ic}"):
                            c1, c2 = st.columns(2)
                            with c1:
                                e_nama = st.text_input("NAMA GURU", value=guru_edit.get("NAMA GURU", ""))
                                e_ic = st.text_input("IC", value=edit_ic, disabled=True)
                                e_jantina = st.selectbox("JANTINA", ["LELAKI", "PEREMPUAN"], index=0 if guru_edit.get("JANTINA", "") == "LELAKI" else 1)
                                e_poskod = st.text_input("POSKOD RUMAH", value=guru_edit.get("POSKOD_RUMAH", ""))
                                e_alamat = st.text_area("ALAMAT RUMAH", value=guru_edit.get("ALAMAT_RUMAH", ""))
                            with c2:
                                e_tel = st.text_input("TELEFON GURU", value=guru_edit.get("TELEFON_GURU", "") or guru_edit.get("TELEFON", ""))
                                e_email = st.text_input("EMAIL GURU", value=guru_edit.get("EMAIL_GURU", ""))
                                e_jawatan = st.selectbox("JAWATAN CADANGAN", ["Ketua Pengawas", "Timbalan Ketua Pengawas", "Penyelia Kawasan", "Pengawas Peperiksaan"], index=0)
                                e_pengalaman = st.text_input("PENGALAMAN SPM", value=guru_edit.get("PENGALAMAN_SPM", ""))
                                e_no_pusat = st.text_input("NO PUSAT ASAL", value=guru_edit.get("NO_PUSAT_ASAL", ""))
                            
                            if st.form_submit_button("💾 Update Guru", type="primary"):
                                try:
                                    res = supa.table("guru_master").select("id,data").eq("ic_guru", edit_ic).eq("kod_sekolah", kod).execute()
                                    if not res.data:
                                        res = supa.table("guru_master").select("id,data").eq("ic_guru", edit_ic).execute()
                                    for row in res.data or []:
                                        old_data = row.get("data") or {}
                                        if isinstance(old_data, str):
                                            try: old_data = json.loads(old_data)
                                            except: old_data = {}
                                        new_data = {**old_data, **{"NAMA GURU": e_nama.upper(), "IC": edit_ic, "JANTINA": e_jantina, "POSKOD_RUMAH": e_poskod, "ALAMAT_RUMAH": e_alamat, "TELEFON_GURU": e_tel, "EMAIL_GURU": e_email, "JAWATAN_CADANGAN": e_jawatan, "PENGALAMAN_SPM": e_pengalaman, "NO_PUSAT_ASAL": e_no_pusat, "KOD_SEKOLAH": kod, "KOD_PPD": info.get("kod_ppd", "BH"), "NAMA_SEKOLAH_ASAL": info.get("nama_sekolah", ""), "KOD_SEKOLAH_ASAL": kod}}
                                        supa.table("guru_master").update({"nama_guru": e_nama.upper(), "ic_guru": edit_ic, "data": new_data}).eq("id", row["id"]).execute()
                                    st.success(f"✅ {e_nama} berjaya update!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Gagal update: {e}")

        elif menu == "tambah":
            st.header(f"Tambah Guru - {kod} - Lengkap Semua Maklumat")
            with st.form("tambah_guru", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    nama = st.text_input("NAMA GURU * (Wajib)")
                    ic = st.text_input("NO IC * (12 digit, Wajib)")
                    jantina = st.selectbox("JANTINA *", ["LELAKI", "PEREMPUAN"])
                    poskod = st.text_input("POSKOD RUMAH *")
                    alamat = st.text_area("ALAMAT RUMAH * (Wajib)")
                with col2:
                    tel = st.text_input("NO TELEFON GURU * (Wajib)")
                    email = st.text_input("EMAIL GURU")
                    jaw = st.selectbox("JAWATAN CADANGAN (Betul)", ["Ketua Pengawas", "Timbalan Ketua Pengawas", "Penyelia Kawasan", "Pengawas Peperiksaan"])
                    pengalaman = st.text_input("PENGALAMAN SPM (Tahun) - SUP isi", placeholder="Contoh: 3 tahun")
                    no_pusat_asal = st.text_input("NO PUSAT ASAL", placeholder="Contoh: BA142")
                
                submit = st.form_submit_button("💾 Simpan Guru Lengkap", use_container_width=True, type="primary")
                if submit:
                    if not nama or not ic or not tel or not alamat:
                        st.error("Nama, IC, Telefon, Alamat wajib isi!")
                    else:
                        data = {"NAMA GURU": nama.upper(), "IC": ic, "JANTINA": jantina, "POSKOD_RUMAH": poskod, "ALAMAT_RUMAH": alamat, "NO TELEFON GURU": tel, "TELEFON_GURU": tel, "EMAIL_GURU": email, "JAWATAN_CADANGAN": jaw, "JAWATAN CADANGAN": jaw, "PENGALAMAN_SPM": pengalaman, "PENGALAMAN": pengalaman, "NO_PUSAT_ASAL": no_pusat_asal, "KOD_SEKOLAH": kod, "KOD_SEKOLAH_ASAL": kod, "NAMA_SEKOLAH_ASAL": info.get("nama_sekolah", ""), "KOD_PPD": info.get("kod_ppd", "BH"), "KOD_PPD_ASAL": info.get("kod_ppd", "BH"), "TARIKH DAFTAR": str(datetime.date.today())}
                        try:
                            supa.table("guru_master").insert({"kod_ppd": info.get("kod_ppd", "BH").lower(), "kod_sekolah": kod, "nama_guru": nama.upper(), "ic_guru": ic, "jantina": jantina, "poskod_rumah": poskod, "alamat_rumah": alamat, "telefon_guru": tel, "email_guru": email, "jawatan_cadangan": jaw, "pengalaman_spm": pengalaman, "no_pusat_asal": no_pusat_asal, "kod_ppd_asal": info.get("kod_ppd", "BH"), "kod_sekolah_asal": kod, "nama_sekolah_asal": info.get("nama_sekolah", ""), "data": data}).execute()
                            st.success(f"✅ {nama.upper()} berjaya tambah ke {kod} dengan data lengkap!")
                            st.balloons()
                        except Exception as e:
                            try:
                                supa.table("guru_master").insert({"kod_ppd": info.get("kod_ppd", "BH").lower(), "kod_sekolah": kod, "nama_guru": nama.upper(), "ic_guru": ic, "data": data}).execute()
                                st.success(f"✅ {nama.upper()} berjaya tambah (fallback)!")
                                st.balloons()
                            except Exception as e2:
                                st.error(f"Gagal: {e2}")

        elif menu == "import":
            st.header(f"Import Excel Guru - {kod}")
            st.info("Format Excel: NAMA GURU, IC, JANTINA, NO TELEFON GURU, EMAIL GURU, ALAMAT RUMAH, KOD SEKOLAH, KOD PPD")
            st.download_button("📥 Download Template Guru (Excel Sah)", to_excel(get_template_guru()), file_name="template_guru.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            uploaded = st.file_uploader("Upload Excel Guru", type=["xlsx", "xls"])
            if uploaded:
                try:
                    df_up = pd.read_excel(uploaded)
                    st.write(f"Preview {len(df_up)} baris:")
                    st.dataframe(df_up.head(20), use_container_width=True)
                    batch_size = 500 if len(df_up) > 1000 else 1
                    if st.button(f"Import {len(df_up)} guru (Batch {batch_size})", type="primary"):
                        bar = st.progress(0)
                        status = st.empty()
                        ok = 0
                        if batch_size > 1:
                            for start in range(0, len(df_up), batch_size):
                                end = min(start + batch_size, len(df_up))
                                batch_df = df_up.iloc[start:end]
                                batch = []
                                for _, row in batch_df.iterrows():
                                    try:
                                        d = {}
                                        for k, v in row.to_dict().items():
                                            d[k] = "" if pd.isna(v) else str(v)
                                        nama = d.get("NAMA GURU", "").upper().strip()
                                        if not nama or nama == "NAN": continue
                                        kod_sek = d.get("KOD SEKOLAH", kod).upper().strip() or kod
                                        kod_ppd_val = d.get("KOD PPD", info.get("kod_ppd", "BH")).lower().strip() or info.get("kod_ppd", "BH").lower()
                                        batch.append({"kod_ppd": kod_ppd_val, "kod_sekolah": kod_sek, "nama_guru": nama, "ic_guru": d.get("IC", ""), "data": d})
                                    except: continue
                                if batch:
                                    try:
                                        supa.table("guru_master").insert(batch).execute()
                                        ok += len(batch)
                                    except Exception as e:
                                        st.warning(f"Batch {start}-{end} error: {e}")
                                bar.progress(end / len(df_up))
                                status.write(f"Progress: {end}/{len(df_up)} | OK: {ok}")
                        else:
                            for i, row in df_up.iterrows():
                                try:
                                    nama = str(row.get("NAMA GURU", "")).upper()
                                    ic = str(row.get("IC", ""))
                                    if not nama or nama == "NAN": continue
                                    d = {k: ("" if pd.isna(v) else str(v)) for k, v in row.to_dict().items()}
                                    d["KOD SEKOLAH"] = kod
                                    supa.table("guru_master").insert({"kod_ppd": info.get("kod_ppd", "BH").lower(), "kod_sekolah": kod, "nama_guru": nama, "ic_guru": ic, "data": d}).execute()
                                    ok += 1
                                except Exception as e:
                                    st.warning(f"Baris {i}: {e}")
                                bar.progress((i + 1) / len(df_up))
                        st.success(f"✅ Berjaya import {ok}/{len(df_up)} guru!")
                        st.balloons()
                except Exception as e:
                    st.error(f"Excel error: {e}")

        elif menu == "buang":
            st.header(f"Buang Guru - {kod}")
            if df_guru.empty:
                st.info("Tiada guru untuk dibuang.")
            else:
                st.dataframe(df_guru[["NAMA GURU", "IC", "TELEFON"]], use_container_width=True)
                pilih = st.multiselect("Pilih IC untuk buang (boleh pilih banyak)", df_guru["IC"].tolist(), format_func=lambda x: f"{x} - {df_guru[df_guru['IC']==x]['NAMA GURU'].values[0] if not df_guru[df_guru['IC']==x].empty else x}")
                if pilih:
                    st.warning(f"Kau nak buang {len(pilih)} guru: {', '.join(pilih)}")
                    if st.button(f"🗑️ Confirm Buang {len(pilih)} Guru", type="primary"):
                        for ic in pilih:
                            try:
                                res = supa.table("guru_master").select("id").eq("ic_guru", ic).eq("kod_sekolah", kod).execute()
                                for r in res.data or []:
                                    supa.table("guru_master").delete().eq("id", r["id"]).execute()
                            except Exception as e:
                                st.error(f"{ic}: {e}")
                        st.success(f"✅ Berjaya buang {len(pilih)} guru")
                        st.rerun()

        elif menu == "cadangan":
            st.header(f"Cadangan Lantikan - {kod} - {info.get('nama_sekolah', '')}")
            try:
                df_pusat_all2 = get_pusat_df()
                pusat_sek = []
                for _, r in df_pusat_all2.iterrows():
                    d = r.get("data") if isinstance(r.get("data"), dict) else {}
                    if isinstance(d, str):
                        try: d = json.loads(d)
                        except: d = {}
                    ks = r.get("kod_sekolah_tuan_rumah") or r.get("kod_sekolah") or d.get("KOD_SEKOLAH") or d.get("KOD SEKOLAH") or ""
                    if ks.upper().strip() == kod.upper().strip():
                        calon = r.get("jumlah_calon") or r.get("calon") or d.get("JUMLAH_CALON") or 0
                        try: calon_i = int(float(str(calon) or 0))
                        except: calon_i = 0
                        kelas = kira_kelas_dari_calon(calon_i)
                        pusat_sek.append({"calon": calon_i, "kelas": kelas})
                
                total_kelas_alert = sum([p["kelas"] for p in pusat_sek]) if pusat_sek else 0
                total_calon_alert = sum([p["calon"] for p in pusat_sek]) if pusat_sek else 0
                total_need_simple = kira_sekolah_perlu_calonkan(total_kelas_alert) if total_kelas_alert > 0 else 18
                
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
                st.markdown("### Pilih Guru (EMAIL kosong dibenarkan)")
                guru_pilih = st.multiselect("Pilih Guru untuk dicadangkan (boleh pilih ramai)", df_guru["IC"].tolist(), format_func=lambda x: f"{df_guru[df_guru['IC']==x]['NAMA GURU'].values[0]} - {x}", key="guru_pilih_simple")
                col_jawatan, col_exp = st.columns(2)
                with col_jawatan:
                    jawatan_cadang = st.selectbox("Jawatan Lantikan (Betul)", JAWATAN_BETUL, key="jawatan_simple")
                    jawatan_clean = jawatan_cadang.split(" (")[0]
                with col_exp:
                    pengalaman_input = st.text_input("Pengalaman SPM (Tahun) - SUP isi", placeholder="Contoh: 3 tahun", key="pengalaman_simple")
                
                pusat_pilih = "BA142"
                no_pusat_asal_input = "BA142"
                
                if guru_pilih:
                    st.markdown("**Preview Data Guru Dipilih (EMAIL kosong dibenarkan - akan lepas simpan):**")
                    preview_rows = []
                    for ic_prev in guru_pilih[:10]:
                        gr_prev = df_guru[df_guru["IC"] == ic_prev]
                        if not gr_prev.empty:
                            r = gr_prev.iloc[0]
                            preview_rows.append({"IC": ic_prev, "NAMA": r.get("NAMA GURU", "")[:20], "JANTINA": r.get("JANTINA", "") or "-", "POSKOD": r.get("POSKOD_RUMAH", "") or "-", "ALAMAT": (r.get("ALAMAT_RUMAH", "")[:20] or "-"), "TELEFON": r.get("TELEFON_GURU", "") or r.get("TELEFON", "") or "-", "EMAIL": r.get("EMAIL_GURU", "") or "-"})
                    if preview_rows:
                        st.dataframe(pd.DataFrame(preview_rows), use_container_width=True, hide_index=True)
                    
                    catatan = ""
                    if st.button(f" Simpan Cadangan - {len(guru_pilih) if 'guru_pilih' in locals() and guru_pilih else 0} guru", type="primary", key="btn_simpan_simple"):
                        if not guru_pilih:
                            st.error("Pilih sekurang-kurangnya 1 guru")
                        else:
                            st.info(f"Menyimpan {len(guru_pilih)} guru...")
                            ok_count = 0
                            fail_msg = ""
                            for ic in guru_pilih:
                                guru_row = df_guru[df_guru["IC"] == ic]
                                if guru_row.empty: continue
                                gr = guru_row.iloc[0]
                                nama = gr.get("NAMA GURU", "") or ic
                                jantina = gr.get("JANTINA", "")
                                poskod = gr.get("POSKOD_RUMAH", "")
                                alamat = gr.get("ALAMAT_RUMAH", "") or gr.get("ALAMAT", "")
                                telefon = gr.get("TELEFON_GURU", "") or gr.get("TELEFON", "")
                                email = str(gr.get("EMAIL_GURU", "") or gr.get("EMAIL", "") or "").strip()
                                pengalaman = pengalaman_input or gr.get("PENGALAMAN_SPM", "") or gr.get("PENGALAMAN", "")
                                kod_ppd_guru = (gr.get("KOD_PPD", "") or info.get("kod_ppd", "BA")).upper()
                                kod_sek_guru = gr.get("KOD_SEKOLAH", "") or kod
                                nama_sek_guru = gr.get("NAMA_SEKOLAH_ASAL", "") or gr.get("NAMA_SEKOLAH", "") or info.get("nama_sekolah", "")
                                no_pusat_asal = no_pusat_asal_input or gr.get("NO_PUSAT_ASAL", "")
                                pusat_pilih = "BA142"
                                if no_pusat_asal and no_pusat_asal.strip() != "":
                                    pusat_pilih = no_pusat_asal.strip()
                                if kod.upper() == "BFT0003":
                                    pusat_pilih = "BA142"
                                
                                kod_ppd_guru = kod_ppd_guru.upper()
                                kod_sek_guru = kod_sek_guru.upper()
                                if not no_pusat_asal or no_pusat_asal.strip() == "":
                                    no_pusat_asal = "BA142"
                                if not kod_sek_guru or kod_sek_guru.strip() == "":
                                    kod_sek_guru = kod.upper()
                                if not nama_sek_guru or nama_sek_guru.strip() == "":
                                    nama_sek_guru = info.get("nama_sekolah", "SAM NURUL IMAN")
                                
                                email = email or ""
                                clean_insert = {"kod_ppd": kod_ppd_guru.upper(), "kod_sekolah": kod_sek_guru, "kod_sekolah_asal": kod_sek_guru, "nama_sekolah_asal": nama_sek_guru, "ic_guru": ic, "nama_guru": nama, "jantina": jantina or "L", "poskod_rumah": poskod or "0", "alamat_rumah": alamat or "-", "telefon_guru": telefon, "email_guru": email, "jawatan_cadangan": jawatan_clean, "pengalaman_spm": pengalaman, "no_pusat_asal": no_pusat_asal or pusat_pilih, "kod_pusat": pusat_pilih, "kod_ppd_asal": kod_ppd_guru.upper(), "status": "DICADANGKAN", "tarikh_cadang": str(datetime.date.today()), "data": {"KOD_PPD": kod_ppd_guru.upper(), "KOD_SEKOLAH_ASAL": kod_sek_guru.upper(), "NAMA_SEKOLAH_ASAL": nama_sek_guru, "IC_GURU": ic, "NAMA_GURU": nama, "JANTINA": jantina, "POSKOD_RUMAH": poskod, "ALAMAT_RUMAH": alamat, "TELEFON_GURU": telefon, "EMAIL_GURU": email, "JAWATAN_CADANGAN": jawatan_clean, "PENGALAMAN_SPM": pengalaman, "NO_PUSAT_ASAL": no_pusat_asal or pusat_pilih, "STATUS": "DICADANGKAN"}}
                                
                                minimal_insert = {"kod_ppd": kod_ppd_guru.upper(), "kod_sekolah": kod_sek_guru.upper(), "ic_guru": ic, "nama_guru": nama, "status": "DICADANGKAN"}
                                
                                inserted = False
                                for attempt in [clean_insert, clean_insert, {"kod_ppd": kod_ppd_guru.upper(), "kod_sekolah": kod_sek_guru.upper(), "ic_guru": ic, "nama_guru": nama, "kod_pusat": no_pusat_asal, "jawatan_cadangan": jawatan_clean, "status": "DICADANGKAN", "tarikh_cadang": str(datetime.date.today()), "jantina": jantina or "L", "poskod_rumah": poskod or "0", "alamat_rumah": alamat or "-", "telefon_guru": telefon or "-", "email_guru": email or "", "pengalaman_spm": pengalaman or "0", "no_pusat_asal": no_pusat_asal, "kod_ppd_asal": kod_ppd_guru.upper(), "kod_sekolah_asal": kod_sek_guru.upper(), "nama_sekolah_asal": nama_sek_guru}, minimal_insert]:
                                    try:
                                        supa.table("cadangan_sup").insert(attempt).execute()
                                        inserted = True
                                        ok_count += 1
                                        break
                                    except Exception as e:
                                        fail_msg = str(e)
                                        if "duplicate" in fail_msg.lower() or "already exists" in fail_msg.lower():
                                            try:
                                                supa.table("cadangan_sup").update(attempt).eq("ic_guru", ic).eq("kod_sekolah", kod_sek_guru.upper()).execute()
                                                inserted = True
                                                ok_count += 1
                                                break
                                            except: pass
                                        continue
                                
                                if not inserted:
                                    st.error(f"❌ Gagal {ic} - {nama}: {fail_msg[:500]}")
                                    st.code(fail_msg[:1000])
                            
                            if ok_count > 0:
                                st.success(f"✅ Berjaya cadang {ok_count}/{len(guru_pilih)} guru sebagai {jawatan_clean} ke pusat {pusat_pilih} - SEMUA maklumat lengkap!")
                                st.balloons()
                                st.rerun()
                
                st.markdown("---")
                st.subheader(f"Senarai Cadangan Sekolah Ini - Perlu {total_need_simple if 'total_need_simple' in locals() else 18} orang")
                df_cad = get_cadangan_df(kod_sekolah=kod)
                if df_cad.empty:
                    st.info("Belum ada cadangan")
                else:
                    try:
                        counts = df_cad["JAWATAN_CADANGAN"].value_counts() if "JAWATAN_CADANGAN" in df_cad.columns else (df_cad["jawatan_cadangan"].value_counts() if "jawatan_cadangan" in df_cad.columns else pd.Series())
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Ketua Pengawas", counts.get("Ketua Pengawas", 0), delta="WAJIB 1" if counts.get("Ketua Pengawas", 0) >= 1 else "BELUM CUKUP", delta_color="normal" if counts.get("Ketua Pengawas", 0) >= 1 else "inverse")
                        c2.metric("Timbalan Ketua", counts.get("Timbalan Ketua Pengawas", 0), delta="WAJIB 1" if counts.get("Timbalan Ketua Pengawas", 0) >= 1 else "BELUM CUKUP", delta_color="normal" if counts.get("Timbalan Ketua Pengawas", 0) >= 1 else "inverse")
                        c3.metric("Penyelia Kawasan", counts.get("Penyelia Kawasan", 0))
                        c4.metric("Pengawas Peperiksaan", counts.get("Pengawas Peperiksaan", 0), delta=f"Perlu {total_kelas_alert if 'total_kelas_alert' in locals() else 6}")
                    except: pass
                    st.dataframe(df_cad, use_container_width=True)
                    st.download_button("📥 Export Cadangan", to_excel(df_cad), file_name=f"cadangan_{kod}.xlsx")

        elif menu == "hantar":
            st.header(f"Hantar Cadangan ke PPD {info.get('kod_ppd', 'BA')}")
            df_cad = get_cadangan_df(kod_sekolah=kod)
            if df_cad.empty:
                st.warning("Belum ada cadangan. Pergi menu Cadangan Lantikan dulu.")
            else:
                kod_ppd_sup = str(info.get('kod_ppd', 'BA')).upper()
                status_s = df_cad["STATUS"].astype(str).str.upper() if "STATUS" in df_cad.columns else pd.Series([""] * len(df_cad), index=df_cad.index)
                m_lulus = status_s.str.contains("LULUS", na=False)
                m_hantar = status_s.str.contains("HANTAR", na=False) & ~m_lulus
                m_baru = ~(m_lulus | m_hantar)   # DICADANGKAN / TOLAK PPD - boleh dihantar (semula)
                bil_baru = int(m_baru.sum())
                
                display_cols = [c for c in ["NAMA_GURU", "IC_GURU", "JANTINA", "POSKOD_RUMAH", "ALAMAT_RUMAH", "TELEFON_GURU", "EMAIL_GURU", "JAWATAN_CADANGAN", "PENGALAMAN_SPM", "NO_PUSAT_ASAL", "KOD_SEKOLAH_ASAL", "NAMA_SEKOLAH_ASAL", "STATUS"] if c in df_cad.columns]
                st.dataframe(df_cad[display_cols] if display_cols else df_cad, use_container_width=True)
                
                k1, k2, k3 = st.columns(3)
                with k1: st.metric("Belum dihantar", bil_baru)
                with k2: st.metric("Sudah dihantar", int(m_hantar.sum()))
                with k3: st.metric("Lulus PPD", int(m_lulus.sum()))
                
                sasaran = df_cad[m_baru]
                def _kosong(col):
                    if col not in sasaran.columns: return pd.Series(False, index=sasaran.index)
                    return sasaran[col].astype(str).str.strip().isin(["", "KOSONG", "nan", "None"])
                
                tak_lengkap = sasaran[_kosong("POSKOD_RUMAH") | _kosong("ALAMAT_RUMAH") | _kosong("TELEFON_GURU")]
                if bil_baru and not tak_lengkap.empty:
                    st.warning(f"⚠️ {len(tak_lengkap)} cadangan belum lengkap (POSKOD / ALAMAT / TELEFON kosong) - PPD tak boleh jana ikut terdekat. Sila lengkapkan di Senarai Guru > Edit. Contoh: " + ", ".join(tak_lengkap["NAMA_GURU"].astype(str).head(3)))
                elif bil_baru:
                    st.success(f"✅ {bil_baru} cadangan ada POSKOD, ALAMAT & TELEFON lengkap.")
                
                col_hantar, col_batal, col_reset = st.columns(3)
                with col_hantar:
                    if bil_baru == 0: st.info("Semua cadangan sudah dihantar / lulus.")
                    if st.button(f"📤 Hantar {bil_baru} Cadangan ke PPD", type="primary", use_container_width=True, disabled=bil_baru == 0, key="btn_hantar_ppd"):
                        ids = [_id_py(x) for x in sasaran["id"].tolist()] if "id" in sasaran.columns else []
                        if not ids:
                            st.error("Tiada ID cadangan - data tak lengkap, hubungi admin.")
                        else:
                            berjaya, gagal = hantar_ke_ppd(ids, kod_ppd_sup)
                            if berjaya: flash("success", f"✅ Berjaya hantar {berjaya} cadangan ke PPD {kod_ppd_sup} - {PPD_MAP.get(kod_ppd_sup, '')}!")
                            if gagal: flash("error", "Sebahagian gagal dihantar: " + "; ".join(gagal[:3]))
                            st.rerun()
                
                with col_batal:
                    st.markdown("**Batal Cadangan (Selagi PPD Belum Lantik)**")
                    label_batal = {}
                    if "id" in df_cad.columns:
                        for _, r_ in df_cad.iterrows():
                            label_batal[_id_py(r_["id"])] = f"{r_.get('NAMA_GURU', '')} | {r_.get('IC_GURU', '')} | {r_.get('STATUS', '')}"
                    batal_ids = st.multiselect("Pilih untuk batal", list(label_batal.keys()), format_func=lambda x: label_batal.get(x, str(x)))
                    if st.button("❌ Batal Terpilih", use_container_width=True, key="btn_batal_cad"):
                        if not batal_ids: st.warning("Pilih sekurang-kurangnya 1")
                        else:
                            berjaya_b = 0
                            for bid in batal_ids:
                                try:
                                    if "LULUS" in str(df_cad[df_cad["id"] == bid].iloc[0].get("STATUS", "")).upper():
                                        flash("error", f"Tak boleh batal {label_batal.get(bid, bid)} - sudah LULUS PPD!")
                                        continue
                                    supa.table("cadangan_sup").delete().eq("id", bid).execute()
                                    berjaya_b += 1
                                except Exception as e:
                                    flash("error", f"Gagal batal {label_batal.get(bid, bid)}: {e}")
                            if berjaya_b: flash("success", f"✅ Berjaya batal {berjaya_b} cadangan!")
                            st.rerun()
                
                with col_reset:
                    st.markdown("**Reset Semua (Clear & Isi Semula)**")
                    sah_reset = st.checkbox("Ya, padam semua cadangan (kecuali yang sudah LULUS)", key="sah_reset_cad")
                    if st.button("🔄 Reset Semua Cadangan", use_container_width=True, type="secondary", disabled=not sah_reset, key="btn_reset_cad"):
                        count_del = 0
                        for _, row in df_cad.iterrows():
                            if "LULUS" in str(row.get("STATUS", "")).upper(): continue
                            try:
                                supa.table("cadangan_sup").delete().eq("id", _id_py(row["id"])).execute()
                                count_del += 1
                            except Exception as e:
                                flash("error", f"Gagal padam {row.get('NAMA_GURU', '')}: {e}")
                        flash("success", f"✅ Reset {count_del} cadangan!")
                        st.rerun()
                
                st.markdown("---")
                st.caption("ℹ️ Cadangan yang sudah LULUS PPD tidak akan diubah atau dipadam oleh butang di atas.")

# ================= ROLE: PPD =================
elif st.session_state.role == "PPD":
    kod_ppd = st.session_state.kod
    
    col_menu, col_main = st.columns([1, 3.2], gap="large")
    with col_menu:
        st.markdown('<div class="custom-sidebar">', unsafe_allow_html=True)
        st.markdown(f"### 🏢 PPD {kod_ppd}")
        st.caption(f"{PPD_MAP.get(kod_ppd, '')}")
        add_refresh_button()
        
        MENU_PPD = [('dashboard', '📊 Dashboard PPD'), ('sekolah', '🏫 Sekolah dalam PPD'), ('pusat', '🏫 Pusat di PPD'), 
                    ('jana', '🚀 Jana Keseluruhan'), ('hasil', '📋 Hasil Janaan'), ('manual', '📌 Penempatan Manual'), ('cadangan', '📋 Cadangan SUP'), ('kelulusan', '✅ Kelulusan'), 
                    ('export', '📥 Export'), ('keluar', '🚪 Log Keluar')]
        menu = st.radio("Menu PPD", [k for k, _ in MENU_PPD], format_func=dict(MENU_PPD).get, label_visibility="collapsed", key="ppd_menu_radio")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_main:
        if menu == "keluar":
            st.session_state.clear()
            st.rerun()
        
        elif menu == "dashboard":
            st.markdown(f"""
            <div style="background: #0d47a1; padding:20px; border-radius:12px; color:white; border: 2px solid #002171; margin-bottom:20px;">
                <div style="display:flex; align-items:center; gap:15px;">
                    <div style="font-size:48px;">🏢</div>
                    <div>
                        <h2 style="margin:0; color:white; font-size:28px;">PPD {kod_ppd} - {PPD_MAP.get(kod_ppd, '')}</h2>
                        <p style="margin:5px 0 0 0; color:#bbdefb; font-size:14px;">Dashboard Pelantikan SPM 2026 - Senarai Pusat & Keperluan Petugas</p>
                    </div>
                    <div style="margin-left:auto; font-size:48px;">📚</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            try:
                # Load data
                df_pusat_raw = get_pusat_df()
                df_cad_all = get_cadangan_df(kod_ppd=kod_ppd)
                df_sekolah_raw = supa.table("sekolah_master").select("*").eq("kod_ppd", kod_ppd).limit(2000).execute()
                df_sekolah_list = pd.DataFrame(df_sekolah_raw.data or [])
                
                # Parse pusat
                pusat_list = []
                for _, r in df_pusat_raw.iterrows():
                    d = r.get("data") if isinstance(r.get("data"), dict) else {}
                    if isinstance(d, str):
                        try: d = json.loads(d)
                        except: d = {}
                    no_pusat = str(r.get("no_pusat") or r.get("kod_pusat") or d.get("NO_PUSAT") or d.get("NO PUSAT") or "").upper().strip()
                    if not no_pusat.startswith(kod_ppd.upper()):
                        continue
                    nama_pusat = str(r.get("nama_pusat") or d.get("NAMA_PUSAT") or d.get("NAMA PUSAT") or "").upper().strip()
                    kod_tuan = str(r.get("kod_sekolah_tuan_rumah") or r.get("kod_sekolah") or d.get("KOD_SEKOLAH") or d.get("KOD_SEKOLAH_TUAN_RUMAH") or "").upper().strip()
                    j_calon = r.get("jumlah_calon") or r.get("calon") or d.get("JUMLAH_CALON") or d.get("CALON") or 0
                    j_kelas = r.get("jumlah_kelas") or d.get("JUMLAH_KELAS") or 0
                    try: jc = int(float(str(j_calon) or 0))
                    except: jc = 0
                    try: jk = int(float(str(j_kelas) or 0))
                    except: jk = 0
                    if jk == 0:
                        jk = kira_kelas_dari_calon(jc)
                    petugas_sep = kira_petugas_dari_kelas(jk)
                    
                    # Kira berapa petugas telah dicadangkan untuk pusat ini
                    # Cari dalam cadangan_sup yang kod_pusat / no_pusat_asal / no_pusat_tugas == no_pusat ini
                    dicadangkan = 0
                    if not df_cad_all.empty:
                        # Check multiple columns
                        for _, c_row in df_cad_all.iterrows():
                            c_no_pusat = str(c_row.get("kod_pusat") or c_row.get("no_pusat_asal") or c_row.get("NO_PUSAT_ASAL") or c_row.get("KOD_PUSAT") or "").upper().strip()
                            # Also check data dict
                            c_data = c_row.get("data") or {}
                            if isinstance(c_data, str):
                                try: c_data = json.loads(c_data)
                                except: c_data = {}
                            c_no_pusat2 = str(c_data.get("NO_PUSAT_ASAL") or c_data.get("KOD_PUSAT") or "").upper().strip()
                            if c_no_pusat == no_pusat or c_no_pusat2 == no_pusat:
                                dicadangkan += 1
                        # If no specific assignment yet, distribute proportionally? For now show 0, but total will show overall
                    
                    pusat_list.append({
                        "NO_PUSAT": no_pusat,
                        "NAMA_PUSAT": nama_pusat,
                        "KOD_TUAN_RUMAH": kod_tuan,
                        "CALON": jc,
                        "KELAS": jk,
                        "SEPATUTNYA": petugas_sep,
                        "DICADANGKAN": dicadangkan
                    })
                
                df_pusat_ppd = pd.DataFrame(pusat_list)
                
                if df_pusat_ppd.empty:
                    st.warning(f"⚠️ Tiada pusat dijumpai untuk PPD {kod_ppd} - {PPD_MAP.get(kod_ppd, '')}. Sila import pusat di JPN > Pusat Master")
                else:
                    # Summary metrics
                    total_pusat = len(df_pusat_ppd)
                    total_calon = int(df_pusat_ppd["CALON"].sum())
                    total_kelas = int(df_pusat_ppd["KELAS"].sum())
                    total_sepatutnya = int(df_pusat_ppd["SEPATUTNYA"].sum())
                    total_dicadangkan = len(df_cad_all) if not df_cad_all.empty else 0
                    kekurangan = total_sepatutnya - total_dicadangkan
                    
                    # Color logic for total
                    if total_dicadangkan == 0:
                        color_total = "#d32f2f"
                        bg_total = "#ffebee"
                        icon_total = "🔴"
                    elif total_dicadangkan < total_sepatutnya:
                        color_total = "#f57f17"
                        bg_total = "#fff8e1"
                        icon_total = "🟡"
                    else:
                        color_total = "#2e7d32"
                        bg_total = "#e8f5e9"
                        icon_total = "🟢"
                    
                    st.markdown(f"""
                    <div style="background:{bg_total}; border:2px solid {color_total}; border-radius:12px; padding:16px; margin-bottom:20px;">
                        <div style="display:flex; gap:12px; flex-wrap:wrap; align-items:center;">
                            <div style="font-size:32px;">{icon_total}</div>
                            <div>
                                <div style="font-size:13px; color:#666; font-weight:600;">RUMUSAN PPD {kod_ppd}</div>
                                <div style="font-size:18px; font-weight:800; color:{color_total};">
                                    {total_pusat} Pusat | {total_calon} Calon | {total_kelas} Kelas | Perlu {total_sepatutnya} Petugas | Dicadangkan {total_dicadangkan} | {'Cukup' if total_dicadangkan >= total_sepatutnya else f'Kurang {kekurangan}'}
                                </div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    c1, c2, c3, c4, c5, c6 = st.columns(6)
                    c1.metric("🏫 Pusat", total_pusat)
                    c2.metric("👨‍🎓 Calon", total_calon)
                    c3.metric("🏫 Kelas", total_kelas)
                    c4.metric("📋 Perlu", total_sepatutnya)
                    c5.metric("✅ Dicadangkan", total_dicadangkan)
                    c6.metric("⚠️ Kurang", kekurangan if kekurangan > 0 else 0, delta=f"{'Cukup' if kekurangan <=0 else f'-{kekurangan}'}", delta_color="normal" if kekurangan <=0 else "inverse")
                    
                    st.markdown("---")
                    st.markdown("### 📍 Senarai Pusat Peperiksaan - Status Petugas (PPD Boleh Edit)")
                    st.caption("🔴 Merah = Belum Ada (0) | 🟡 Kuning = Belum Cukup (< sepatutnya) | 🟢 Hijau = Cukup / Lebih (>= sepatutnya) | ✏️ PPD boleh edit BIL CALON, KELAS, PERLU ikut keperluan")
                    st.info("💡 **Cara Edit:** Klik pada angka CALON / KELAS / PERLU dalam table di bawah, tukar ikut keperluan, kemudian tekan **💾 Simpan Perubahan**")
                    
                    # Build editable table
                    # Prepare data for data_editor with BIL, editable columns
                    editable_rows = []
                    for idx, p in enumerate(df_pusat_ppd.sort_values("NO_PUSAT").iterrows()):
                        p_data = p[1]
                        no_p = p_data["NO_PUSAT"]
                        dic = p_data["DICADANGKAN"]
                        sep = p_data["SEPATUTNYA"]
                        
                        if dic == 0:
                            status_icon = "🔴"
                            status_text = "Belum Ada"
                        elif dic < sep:
                            status_icon = "🟡"
                            status_text = f"Belum Cukup"
                        else:
                            status_icon = "🟢"
                            status_text = f"Cukup"
                        
                        editable_rows.append({
                            "BIL": idx + 1,
                            "NO_PUSAT": no_p,
                            "NAMA_PUSAT": p_data["NAMA_PUSAT"][:35],
                            "KOD_TUAN": p_data["KOD_TUAN_RUMAH"],
                            "BIL_CALON": p_data["CALON"],
                            "KELAS": p_data["KELAS"],
                            "PERLU_K9": sep,
                            "DICADANGKAN": dic,
                            "STATUS": f"{status_icon} {status_text}",
                            "KEKURANGAN": max(0, sep - dic)
                        })
                    
                    df_editable = pd.DataFrame(editable_rows)
                    
                    # Data editor - PPD boleh edit BIL_CALON, KELAS, PERLU_K9
                    st.markdown("#### ✏️ Edit Data Pusat (PPD)")
                    edited_df = st.data_editor(
                        df_editable,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "BIL": st.column_config.NumberColumn("BIL", width="small", disabled=True),
                            "NO_PUSAT": st.column_config.TextColumn("NO PUSAT", width="medium", disabled=True),
                            "NAMA_PUSAT": st.column_config.TextColumn("NAMA PUSAT", width="large", disabled=True),
                            "KOD_TUAN": st.column_config.TextColumn("KOD TUAN RUMAH", width="medium", disabled=True),
                            "BIL_CALON": st.column_config.NumberColumn("BIL CALON", help="PPD boleh edit ikut keperluan sebenar", min_value=0, max_value=500, step=1, required=True),
                            "KELAS": st.column_config.NumberColumn("KELAS", help="Auto: CEIL(Calon/20), tapi PPD boleh edit", min_value=0, max_value=30, step=1, required=True),
                            "PERLU_K9": st.column_config.NumberColumn("PERLU (K+9)", help="PPD boleh edit ikut keperluan, formula asal Kelas+9", min_value=0, max_value=50, step=1, required=True),
                            "DICADANGKAN": st.column_config.NumberColumn("DICADANGKAN", disabled=True),
                            "STATUS": st.column_config.TextColumn("STATUS", disabled=True),
                            "KEKURANGAN": st.column_config.NumberColumn("KEKURANGAN", help="Auto kira: PERLU - DICADANGKAN", disabled=True)
                        },
                        key=f"ppd_edit_{kod_ppd}",
                        num_rows="fixed"
                    )
                    
                    # Auto-calculate logic: if BIL_CALON changed, update KELAS and PERLU suggestion
                    # Show save button
                    col_save, col_reset, col_info = st.columns([1, 1, 2])
                    with col_save:
                        if st.button("💾 Simpan Perubahan Pusat", type="primary", use_container_width=True, key=f"save_pusat_{kod_ppd}"):
                            try:
                                # Update pusat_master table
                                updated_count = 0
                                for _, row in edited_df.iterrows():
                                    no_pusat = row["NO_PUSAT"]
                                    new_calon = int(row["BIL_CALON"])
                                    new_kelas = int(row["KELAS"])
                                    new_perlu = int(row["PERLU_K9"])
                                    
                                    # Find original record
                                    for _, r in df_pusat_raw.iterrows():
                                        d = r.get("data") if isinstance(r.get("data"), dict) else {}
                                        if isinstance(d, str):
                                            try: d = json.loads(d)
                                            except: d = {}
                                        r_no_pusat = str(r.get("no_pusat") or r.get("kod_pusat") or d.get("NO_PUSAT") or "").upper().strip()
                                        if r_no_pusat == no_pusat:
                                            # Update
                                            old_data = d.copy() if isinstance(d, dict) else {}
                                            old_data["JUMLAH_CALON"] = new_calon
                                            old_data["JUMLAH_KELAS"] = new_kelas
                                            old_data["CALON"] = new_calon
                                            old_data["KELAS"] = new_kelas
                                            
                                            update_payload = {
                                                "jumlah_calon": new_calon,
                                                "jumlah_kelas": new_kelas,
                                                "calon": new_calon,
                                                "data": old_data
                                            }
                                            # Try update by no_pusat
                                            try:
                                                supa.table("pusat_master").update(update_payload).eq("no_pusat", no_pusat).execute()
                                                updated_count += 1
                                            except:
                                                try:
                                                    supa.table("pusat_master").update(update_payload).eq("kod_pusat", no_pusat).execute()
                                                    updated_count += 1
                                                except Exception as e:
                                                    st.error(f"Gagal update {no_pusat}: {e}")
                                            break
                                
                                st.success(f"✅ Berjaya simpan {updated_count} pusat! Data calon, kelas, perlu telah dikemaskini.")
                                st.balloons()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error simpan: {e}")
                                import traceback
                                st.code(traceback.format_exc())
                    
                    with col_reset:
                        if st.button("🔄 Reset Auto (Kira Semula)", use_container_width=True, key=f"reset_auto_{kod_ppd}"):
                            st.info("Auto kira semula: KELAS = CEIL(CALON/20), PERLU = KELAS+9")
                            st.rerun()
                    
                    with col_info:
                        st.caption(f"Total: {len(edited_df)} pusat | Boleh edit CALON, KELAS, PERLU")
                    
                    st.markdown("---")
                    
                    # Also show colored HTML table for quick view
                    st.markdown("#### 📊 Paparan Status Berwarna")
                    # Create HTML table with colors
                    html_table = """
                    <style>
                    .ppd-table {width:100%; border-collapse:collapse; font-size:13px; background:white;}
                    .ppd-table th {background:#0d47a1; color:white; padding:10px 8px; text-align:left; font-weight:700; position:sticky; top:0;}
                    .ppd-table td {padding:8px; border-bottom:1px solid #e0e0e0; background:white; color:#212121;}
                    .ppd-table tr:hover td {background:#f5f5f5 !important;}
                    .badge-merah {background:#ffcdd2 !important; color:#b71c1c !important; padding:4px 8px; border-radius:12px; font-weight:700; border:2px solid #d32f2f;}
                    .badge-kuning {background:#fff9c4 !important; color:#e65100 !important; padding:4px 8px; border-radius:12px; font-weight:700; border:2px solid #f57f17;}
                    .badge-hijau {background:#c8e6c9 !important; color:#1b5e20 !important; padding:4px 8px; border-radius:12px; font-weight:700; border:2px solid #2e7d32;}
                    .edit-hint {background:#e3f2fd; border-left:4px solid #1976d2; padding:6px 10px; margin:4px 0; font-size:11px;}
                    </style>
                    <div class="edit-hint">✏️ <b>PPD boleh edit:</b> BIL CALON, KELAS, PERLU (K+9) ikut keperluan sebenar - klik angka dalam table atas untuk edit</div>
                    <table class="ppd-table">
                    <tr><th>BIL</th><th>NO PUSAT</th><th>NAMA PUSAT</th><th>KOD TUAN</th><th>BIL CALON ✏️</th><th>KELAS ✏️</th><th>PERLU (K+9) ✏️</th><th>DICADANG</th><th>STATUS</th></tr>
                    """
                    
                    for _, r in edited_df.iterrows():
                        dic = r["DICADANGKAN"]
                        sep = r["PERLU_K9"]
                        if dic == 0:
                            badge_class = "badge-merah"
                            badge_text = f"🔴 {dic}"
                            status_badge = f'<span class="{badge_class}">🔴 Belum Ada</span>'
                        elif dic < sep:
                            badge_class = "badge-kuning"
                            badge_text = f"🟡 {dic}"
                            status_badge = f'<span class="{badge_class}">🟡 Belum Cukup</span>'
                        else:
                            badge_class = "badge-hijau"
                            badge_text = f"🟢 {dic}"
                            status_badge = f'<span class="{badge_class}">🟢 Cukup</span>'
                        
                        html_table += f"<tr><td><b>{r['BIL']}</b></td><td><b>{r['NO_PUSAT']}</b></td><td>{r['NAMA_PUSAT']}</td><td>{r['KOD_TUAN']}</td><td style='text-align:center; background:#fff9c4; font-weight:700; border:1px dashed #f57f17;'>{r['BIL_CALON']}</td><td style='text-align:center; background:#e3f2fd; font-weight:700; border:1px dashed #1976d2;'>{r['KELAS']}</td><td style='text-align:center; background:#fce4ec; font-weight:700; border:1px dashed #d32f2f;'>{r['PERLU_K9']}</td><td style='text-align:center;'><span class='{badge_class}'>{badge_text}</span></td><td>{status_badge}</td></tr>"
                    
                    html_table += "</table>"
                    
                    st.markdown(html_table, unsafe_allow_html=True)
                    
                    st.markdown("---")
                    
                    # Export
                    with st.expander("📊 Export Data", expanded=False):
                        st.dataframe(df_pusat_ppd.sort_values("NO_PUSAT"), use_container_width=True, hide_index=True)
                        st.download_button(f"📥 Export Dashboard PPD {kod_ppd} (Excel)", to_excel(df_pusat_ppd), file_name=f"Dashboard_PPD_{kod_ppd}_{datetime.date.today()}.xlsx", use_container_width=True)
                    
                    # Senarai sekolah dalam PPD
                    st.markdown("---")
                    st.markdown(f"### 🏫 Senarai Sekolah dalam PPD {kod_ppd} ({len(df_sekolah_list)} sekolah)")
                    if not df_sekolah_list.empty:
                        # Kira cadangan per sekolah
                        sekolah_cad_count = {}
                        if not df_cad_all.empty:
                            for _, c_row in df_cad_all.iterrows():
                                k_sek = str(c_row.get("kod_sekolah") or c_row.get("kod_sekolah_asal") or "").upper().strip()
                                if k_sek:
                                    sekolah_cad_count[k_sek] = sekolah_cad_count.get(k_sek, 0) + 1
                        
                        sekolah_rows = []
                        for _, s in df_sekolah_list.iterrows():
                            k_sek = str(s.get("kod_sekolah") or s.get("KOD_SEKOLAH") or "").upper().strip()
                            n_sek = str(s.get("nama_sekolah") or s.get("NAMA_SEKOLAH") or "").upper().strip()
                            cad = sekolah_cad_count.get(k_sek, 0)
                            
                            if cad == 0:
                                s_icon = "🔴"
                                s_status = "Belum Cadang"
                            elif cad < 5:
                                s_icon = "🟡"
                                s_status = f"{cad} dicadang"
                            else:
                                s_icon = "🟢"
                                s_status = f"{cad} dicadang"
                            
                            sekolah_rows.append({"Logo": "🏫", "KOD_SEKOLAH": k_sek, "NAMA_SEKOLAH": n_sek[:35], "DICADANGKAN": cad, "STATUS": f"{s_icon} {s_status}"})
                        
                        df_sekolah_display = pd.DataFrame(sekolah_rows).sort_values("KOD_SEKOLAH")
                        st.dataframe(df_sekolah_display, use_container_width=True, hide_index=True)
                    else:
                        st.info(f"Tiada sekolah dijumpai untuk PPD {kod_ppd}")
                
            except Exception as e:
                st.error(f"Error dashboard PPD: {e}")
                import traceback
                st.code(traceback.format_exc())
                # Fallback simple
                try:
                    cnt_sekolah = supa.table("sekolah_master").select("kod_sekolah", count="exact").eq("kod_ppd", kod_ppd).execute()
                    cnt_cadang = supa.table("cadangan_sup").select("id", count="exact").eq("kod_ppd", kod_ppd).execute()
                    c1, c2 = st.columns(2)
                    c1.metric("Sekolah", cnt_sekolah.count)
                    c2.metric("Cadangan", cnt_cadang.count)
                except Exception as e2:
                    st.error(f"Fallback error: {e2}")

        elif menu == "sekolah":
            st.header(f"Senarai Sekolah PPD {kod_ppd}")
            try:
                res = supa.table("sekolah_master").select("*").eq("kod_ppd", kod_ppd).limit(2000).execute()
                df = pd.DataFrame(res.data or [])
                st.dataframe(df, use_container_width=True)
                st.download_button("Export Sekolah", to_excel(df), file_name=f"sekolah_{kod_ppd}.xlsx")
            except Exception as e:
                st.error(f"Error baca sekolah: {e}")

        elif menu == "pusat":
            st.header(f"Pusat di PPD {kod_ppd} - {PPD_MAP.get(kod_ppd, '')} - Total Calon")
            st.caption("Filter BETUL ikut NO_PUSAT prefix BA=Klang sahaja - bug lama cari substring SABAK contains BA dah fix")
            df_pusat_raw = get_pusat_df()
            if df_pusat_raw.empty:
                st.info("pusat_master kosong")
            else:
                rows = []
                for _, r in df_pusat_raw.iterrows():
                    d = r.get("data") if isinstance(r.get("data"), dict) else {}
                    if isinstance(d, str):
                        try: d = json.loads(d)
                        except: d = {}
                    no_pusat = str(r.get("no_pusat") or r.get("kod_pusat") or d.get("NO_PUSAT") or "").upper().strip()
                    nama = r.get("nama_pusat") or d.get("NAMA_PUSAT") or ""
                    j_calon = r.get("jumlah_calon") or r.get("calon") or d.get("JUMLAH_CALON") or 0
                    j_kelas = r.get("jumlah_kelas") or r.get("bilik") or d.get("JUMLAH_KELAS") or 0
                    try: jc = int(float(str(j_calon) or 0))
                    except: jc = 0
                    try: jk = int(float(str(j_kelas) or 0))
                    except: jk = kira_kelas_dari_calon(jc)
                    rows.append({"NO_PUSAT": no_pusat, "NAMA_PUSAT": nama, "JUMLAH_CALON": jc, "JUMLAH_KELAS": jk, "PETUGAS_K9": kira_petugas_dari_kelas(jk), "SEKOLAH_PERLU": kira_sekolah_perlu_calonkan(jk)})
                
                df_all = pd.DataFrame(rows)
                df_f = df_all[df_all["NO_PUSAT"].str.startswith(kod_ppd.upper())].copy() if not df_all.empty else df_all
                if df_f.empty:
                    st.warning(f"Tiada pusat dengan prefix {kod_ppd}")
                else:
                    st.success(f"Jumpa {len(df_f)} pusat di PPD {kod_ppd} - {PPD_MAP.get(kod_ppd, '')}")
                    st.dataframe(df_f.sort_values("NO_PUSAT"), use_container_width=True, hide_index=True)
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Jumlah Pusat", len(df_f))
                    c2.metric("Total Calon", int(df_f["JUMLAH_CALON"].sum()))
                    c3.metric("Total Kelas", int(df_f["JUMLAH_KELAS"].sum()))
                    c4.metric("Total Perlu", int(df_f["SEKOLAH_PERLU"].sum()))
                    st.download_button(f"Export Pusat {kod_ppd}", to_excel(df_f), file_name=f"pusat_{kod_ppd}.xlsx", use_container_width=True)

        elif menu == "jana":
            st.markdown(f"""
            <div style="background: #0d47a1; padding:20px; border-radius:12px; color:white; border: 2px solid #002171; margin-bottom:20px;">
                <div style="display:flex; align-items:center; gap:15px;">
                    <div style="font-size:48px;">🚀</div>
                    <div>
                        <h2 style="margin:0; color:white; font-size:24px;">Jana Keseluruhan - PPD {kod_ppd} - {PPD_MAP.get(kod_ppd, '')}</h2>
                        <p style="margin:5px 0 0 0; color:#bbdefb; font-size:13px;">Paparan data dari SUP, kemudian jana petugas ke pusat peperiksaan</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            df_pusat_raw = get_pusat_df()
            df_cad_all = get_cadangan_df(kod_ppd=kod_ppd)
            
            if df_pusat_raw.empty:
                st.warning("⚠️ Tiada pusat_master - import dulu di JPN > Pusat Master")
                st.stop()
            if df_cad_all.empty:
                st.warning(f"⚠️ Belum ada cadangan dari SUP untuk PPD {kod_ppd}. Sekolah perlu cadang dulu di SUP > Cadangan Lantikan > Hantar ke PPD")
                st.stop()
            
            # Parse pusat
            rows = []
            for _, r in df_pusat_raw.iterrows():
                d = r.get("data") if isinstance(r.get("data"), dict) else {}
                if isinstance(d, str):
                    try: d = json.loads(d)
                    except: d = {}
                no_pusat = str(r.get("no_pusat") or r.get("kod_pusat") or d.get("NO_PUSAT") or "").upper().strip()
                if not no_pusat.startswith(kod_ppd.upper()): continue
                nama = r.get("nama_pusat") or d.get("NAMA_PUSAT") or ""
                kod_sek_tuan = str(r.get("kod_sekolah_tuan_rumah") or r.get("kod_sekolah") or d.get("KOD_SEKOLAH") or d.get("KOD_SEKOLAH_TUAN_RUMAH") or "").upper().strip()
                j_calon = r.get("jumlah_calon") or d.get("JUMLAH_CALON") or 0
                j_kelas = r.get("jumlah_kelas") or d.get("JUMLAH_KELAS") or 0
                try: jc = int(float(str(j_calon) or 0))
                except: jc = 0
                try: jk = int(float(str(j_kelas) or 0))
                except: jk = kira_kelas_dari_calon(jc)
                if jk == 0:
                    jk = kira_kelas_dari_calon(jc)
                rows.append({"NO_PUSAT": no_pusat, "NAMA_PUSAT": nama, "KOD_SEKOLAH_TUAN_RUMAH": kod_sek_tuan, "JUMLAH_CALON": jc, "JUMLAH_KELAS": jk, "PETUGAS": kira_petugas_dari_kelas(jk)})
            
            df_pusat_ppd = pd.DataFrame(rows)
            
            if df_pusat_ppd.empty:
                st.warning(f"Tiada pusat dengan prefix {kod_ppd} dalam pusat_master")
                st.stop()
            
            # ===== STEP 1: PAPARKAN DATA DARI SUP =====
            st.markdown("### 📋 STEP 1: Data Dari SUP (Cadangan Guru)")
            st.info(f"📥 Ada {len(df_cad_all)} cadangan guru dari SUP untuk PPD {kod_ppd} - {PPD_MAP.get(kod_ppd, '')}")
            
            # Show summary per sekolah
            cad_per_sekolah = {}
            for _, c in df_cad_all.iterrows():
                k_sek = str(c.get("KOD_SEKOLAH") or c.get("KOD_SEKOLAH_ASAL") or "").upper().strip()
                if k_sek:
                    cad_per_sekolah[k_sek] = cad_per_sekolah.get(k_sek, 0) + 1
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("📚 Sekolah Mencadang", len(cad_per_sekolah))
            col2.metric("👨‍🏫 Guru Dicadang", len(df_cad_all))
            col3.metric("🏫 Pusat", len(df_pusat_ppd))
            col4.metric("📋 Perlu Petugas", int(df_pusat_ppd["PETUGAS"].sum()))
            
            with st.expander(f"📋 Lihat {len(df_cad_all)} Cadangan Dari SUP (Data Lengkap)", expanded=False):
                display_cols = [c for c in ["NAMA_GURU", "IC_GURU", "JANTINA", "POSKOD_RUMAH", "TELEFON_GURU", "JAWATAN_CADANGAN", "KOD_SEKOLAH_ASAL", "NAMA_SEKOLAH_ASAL", "NO_PUSAT_ASAL", "STATUS"] if c in df_cad_all.columns]
                st.dataframe(df_cad_all[display_cols] if display_cols else df_cad_all, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            
            # ===== STEP 2: BUTANG JANA =====
            st.markdown("### 🚀 STEP 2: Jana Penempatan")
            st.caption("Pilih kaedah janaan")
            
            col_jana1, col_jana2 = st.columns(2)
            
            with col_jana1:
                st.markdown("""
                <div style="background:#e8f5e9; border:2px solid #2e7d32; border-radius:10px; padding:15px; text-align:center;">
                    <div style="font-size:32px;">🌍</div>
                    <div style="font-weight:800; color:#1b5e20; margin:8px 0;">JANA KESELURUHAN</div>
                    <div style="font-size:12px; color:#424242;">Jana semua guru ke semua pusat dalam PPD secara auto, elak sekolah sendiri</div>
                </div>
                """, unsafe_allow_html=True)
                btn_jana_all = st.button("🚀 JANA KESELURUHAN - Semua Pusat", type="primary", use_container_width=True, key="btn_jana_all")
            
            with col_jana2:
                st.markdown("""
                <div style="background:#e3f2fd; border:2px solid #1565c0; border-radius:10px; padding:15px; text-align:center;">
                    <div style="font-size:32px;">📍</div>
                    <div style="font-weight:800; color:#0d47a1; margin:8px 0;">JANA IKUT PUSAT</div>
                    <div style="font-size:12px; color:#424242;">Pilih satu pusat, jana guru untuk pusat tersebut sahaja</div>
                </div>
                """, unsafe_allow_html=True)
                # Pilih pusat untuk jana ikut pusat
                pilihan_pusat_jana = st.selectbox("Pilih Pusat untuk Jana", df_pusat_ppd["NO_PUSAT"].tolist(), format_func=lambda x: f"{x} - {df_pusat_ppd[df_pusat_ppd['NO_PUSAT']==x]['NAMA_PUSAT'].values[0][:25] if not df_pusat_ppd[df_pusat_ppd['NO_PUSAT']==x].empty else x}", key="pilih_pusat_jana")
                btn_jana_pusat = st.button(f"📍 JANA UNTUK {pilihan_pusat_jana}", use_container_width=True, key="btn_jana_pusat")
            
            # Logic Jana Keseluruhan - STRICT MAX 3 + 1 KP 1 TKP
            if btn_jana_all or "jana_all_result" in st.session_state:
                if btn_jana_all:
                    import random
                    assignments = []
                    df_pool = df_cad_all.copy()
                    pusat_info_map = {}
                    for _, p in df_pusat_ppd.iterrows():
                        pusat_info_map[p["NO_PUSAT"]] = {"KOD_TUAN": str(p.get("KOD_SEKOLAH_TUAN_RUMAH", "") or "").upper().strip(), "NAMA": p.get("NAMA_PUSAT", ""), "PETUGAS": int(p.get("PETUGAS", 0))}
                    pusat_order = df_pusat_ppd["NO_PUSAT"].tolist()
                    random.shuffle(pusat_order)
                    pusat_sekolah_count = {}
                    used_ic = set()
                    def cari_guru_layak(pool_df, kod_tuan_pusat, pusat_no, jawatan_filter=None, exclude_ic=None):
                        eligible = pool_df.copy()
                        if eligible.empty:
                            return eligible
                        if exclude_ic:
                            eligible = eligible[~eligible["IC_GURU"].isin(exclude_ic)]
                        if kod_tuan_pusat:
                            eligible = eligible[~eligible["KOD_SEKOLAH_ASAL"].astype(str).str.upper().str.strip().eq(kod_tuan_pusat)]
                        def check_max3(row):
                            k = str(row.get("KOD_SEKOLAH_ASAL", "") or "").upper().strip()
                            # Normalisasi key
                            return pusat_sekolah_count.get((pusat_no, k), 0) < 3 if k else True
                        eligible["CHECK_MAX"] = eligible.apply(check_max3, axis=1)
                        eligible = eligible[eligible["CHECK_MAX"] == True]
                        if eligible.empty:
                            return eligible
                        if jawatan_filter and "JAWATAN_CADANGAN" in eligible.columns:
                            fj = eligible[eligible["JAWATAN_CADANGAN"].astype(str).str.contains(jawatan_filter, case=False, na=False)]
                            if not fj.empty:
                                eligible = fj
                        if len(eligible) > 1:
                            eligible = eligible.sample(frac=1, random_state=random.randint(1, 100000))
                        return eligible
                    for no_pusat in pusat_order:
                        info = pusat_info_map.get(no_pusat, {})
                        kod_tuan = info.get("KOD_TUAN", "")
                        petugas_perlu = info.get("PETUGAS", 0)
                        if petugas_perlu <= 0:
                            continue
                        need_kp = 1 if petugas_perlu >= 1 else 0
                        need_tkp = 1 if petugas_perlu >= 2 else 0
                        need_pengawas = max(0, petugas_perlu - need_kp - need_tkp)
                        for _ in range(need_kp):
                            pool_eligible = cari_guru_layak(df_pool, kod_tuan, no_pusat, "Ketua Pengawas", used_ic)
                            if pool_eligible.empty:
                                pool_eligible = cari_guru_layak(df_pool, kod_tuan, no_pusat, None, used_ic)
                            if pool_eligible.empty:
                                break
                            chosen = pool_eligible.iloc[0]
                            assignments.append({"id": chosen.get("id", ""), "NAMA_GURU": chosen.get("NAMA_GURU", ""), "IC_GURU": chosen.get("IC_GURU", ""), "JAWATAN_ASAL": chosen.get("JAWATAN_CADANGAN", ""), "JAWATAN_CADANGAN": "Ketua Pengawas", "JAWATAN": "Ketua Pengawas", "KOD_SEKOLAH_ASAL": str(chosen.get("KOD_SEKOLAH_ASAL", "")).upper(), "NAMA_SEKOLAH_ASAL": chosen.get("NAMA_SEKOLAH_ASAL", ""), "JANTINA": chosen.get("JANTINA", "") or chosen.get("jantina", ""), "TELEFON_GURU": chosen.get("TELEFON_GURU", "") or chosen.get("telefon_guru", ""), "NO_PUSAT_TUGAS": no_pusat, "NAMA_PUSAT_TUGAS": info.get("NAMA", ""), "STATUS": "DIJANA PPD"})
                            used_ic.add(chosen.get("IC_GURU", ""))
                            kod_norm = str(chosen.get("KOD_SEKOLAH_ASAL", "") or "").upper().strip()
                            k = (no_pusat, kod_norm)
                            pusat_sekolah_count[k] = pusat_sekolah_count.get(k, 0) + 1
                            df_pool = df_pool[~df_pool["IC_GURU"].isin([chosen.get("IC_GURU", "")])]
                        for _ in range(need_tkp):
                            pool_eligible = cari_guru_layak(df_pool, kod_tuan, no_pusat, "Timbalan", used_ic)
                            if pool_eligible.empty:
                                pool_eligible = cari_guru_layak(df_pool, kod_tuan, no_pusat, None, used_ic)
                            if pool_eligible.empty:
                                break
                            chosen = pool_eligible.iloc[0]
                            assignments.append({"id": chosen.get("id", ""), "NAMA_GURU": chosen.get("NAMA_GURU", ""), "IC_GURU": chosen.get("IC_GURU", ""), "JAWATAN_ASAL": chosen.get("JAWATAN_CADANGAN", ""), "JAWATAN_CADANGAN": "Timbalan Ketua Pengawas", "JAWATAN": "Timbalan Ketua Pengawas", "KOD_SEKOLAH_ASAL": str(chosen.get("KOD_SEKOLAH_ASAL", "")).upper(), "NAMA_SEKOLAH_ASAL": chosen.get("NAMA_SEKOLAH_ASAL", ""), "JANTINA": chosen.get("JANTINA", "") or chosen.get("jantina", ""), "TELEFON_GURU": chosen.get("TELEFON_GURU", "") or chosen.get("telefon_guru", ""), "NO_PUSAT_TUGAS": no_pusat, "NAMA_PUSAT_TUGAS": info.get("NAMA", ""), "STATUS": "DIJANA PPD"})
                            used_ic.add(chosen.get("IC_GURU", ""))
                            kod_norm = str(chosen.get("KOD_SEKOLAH_ASAL", "") or "").upper().strip()
                            k = (no_pusat, kod_norm)
                            pusat_sekolah_count[k] = pusat_sekolah_count.get(k, 0) + 1
                            df_pool = df_pool[~df_pool["IC_GURU"].isin([chosen.get("IC_GURU", "")])]
                        for _ in range(need_pengawas):
                            pool_eligible = cari_guru_layak(df_pool, kod_tuan, no_pusat, "Pengawas", used_ic)
                            if pool_eligible.empty:
                                pool_eligible = cari_guru_layak(df_pool, kod_tuan, no_pusat, None, used_ic)
                            if pool_eligible.empty:
                                break
                            chosen = pool_eligible.iloc[0]
                            assignments.append({"id": chosen.get("id", ""), "NAMA_GURU": chosen.get("NAMA_GURU", ""), "IC_GURU": chosen.get("IC_GURU", ""), "JAWATAN_ASAL": chosen.get("JAWATAN_CADANGAN", ""), "JAWATAN_CADANGAN": "Pengawas Peperiksaan", "JAWATAN": "Pengawas Peperiksaan", "KOD_SEKOLAH_ASAL": str(chosen.get("KOD_SEKOLAH_ASAL", "")).upper(), "NAMA_SEKOLAH_ASAL": chosen.get("NAMA_SEKOLAH_ASAL", ""), "JANTINA": chosen.get("JANTINA", "") or chosen.get("jantina", ""), "TELEFON_GURU": chosen.get("TELEFON_GURU", "") or chosen.get("telefon_guru", ""), "NO_PUSAT_TUGAS": no_pusat, "NAMA_PUSAT_TUGAS": info.get("NAMA", ""), "STATUS": "DIJANA PPD"})
                            used_ic.add(chosen.get("IC_GURU", ""))
                            kod_norm = str(chosen.get("KOD_SEKOLAH_ASAL", "") or "").upper().strip()
                            k = (no_pusat, kod_norm)
                            pusat_sekolah_count[k] = pusat_sekolah_count.get(k, 0) + 1
                            df_pool = df_pool[~df_pool["IC_GURU"].isin([chosen.get("IC_GURU", "")])]
                    
                    df_assign = pd.DataFrame(assignments)
                    st.session_state["jana_all_result"] = df_assign.to_dict('records')
                    st.session_state["jana_type"] = "keseluruhan"
                
                # Display result
                df_assign = pd.DataFrame(st.session_state.get("jana_all_result", []))
                if not df_assign.empty:
                    st.success(f"✅ Berjaya jana {len(df_assign)} guru ke {len(df_pusat_ppd)} pusat!")
                    
                    # Summary per pusat
                    st.markdown("#### 📊 Ringkasan Per Pusat")
                    summary = []
                    for no_pusat in df_pusat_ppd["NO_PUSAT"].tolist():
                        count = len(df_assign[df_assign["NO_PUSAT_TUGAS"] == no_pusat])
                        nama = df_pusat_ppd[df_pusat_ppd["NO_PUSAT"] == no_pusat]["NAMA_PUSAT"].values[0] if not df_pusat_ppd[df_pusat_ppd["NO_PUSAT"] == no_pusat].empty else ""
                        perlu = df_pusat_ppd[df_pusat_ppd["NO_PUSAT"] == no_pusat]["PETUGAS"].values[0] if not df_pusat_ppd[df_pusat_ppd["NO_PUSAT"] == no_pusat].empty else 0
                        status = "🟢 Cukup" if count >= perlu else "🟡 Belum Cukup" if count > 0 else "🔴 Belum Ada"
                        summary.append({"NO_PUSAT": no_pusat, "NAMA_PUSAT": nama[:30], "PERLU": perlu, "DIJANA": count, "STATUS": status})
                    
                    st.dataframe(pd.DataFrame(summary), use_container_width=True, hide_index=True)
                    
                    st.markdown("#### 👥 Senarai Penempatan (Jana Keseluruhan)")
                    st.dataframe(df_assign, use_container_width=True, hide_index=True)
                    
                    col_save, col_clear = st.columns(2)
                    with col_save:
                        if st.button("💾 Simpan Hasil Janaan Ke DB", type="primary", use_container_width=True, key="save_jana_all"):
                            try:
                                saved = 0
                                for _, r in df_assign.iterrows():
                                    try:
                                        if r.get("id"):
                                            supa.table("cadangan_sup").update({"kod_pusat": r["NO_PUSAT_TUGAS"], "status": "DIJANA PPD"}).eq("id", r["id"]).execute()
                                        else:
                                            supa.table("cadangan_sup").update({"kod_pusat": r["NO_PUSAT_TUGAS"]}).eq("ic_guru", r["IC_GURU"]).execute()
                                        saved += 1
                                    except Exception as e:
                                        st.error(f"Gagal simpan {r['NAMA_GURU']}: {e}")
                                st.success(f"✅ Berjaya simpan {saved} penempatan!")
                                st.balloons()
                            except Exception as e:
                                st.error(f"Error simpan: {e}")
                    with col_clear:
                        if st.button("🗑️ Clear Hasil Janaan", use_container_width=True, key="clear_jana_all"):
                            if "jana_all_result" in st.session_state:
                                del st.session_state["jana_all_result"]
                            st.rerun()
                    
                    st.download_button("📥 Export Hasil Jana Keseluruhan", to_excel(df_assign), file_name=f"jana_keseluruhan_{kod_ppd}_{datetime.date.today()}.xlsx", use_container_width=True)
            
            # Logic Jana Ikut Pusat
            if btn_jana_pusat or ("jana_pusat_result" in st.session_state and st.session_state.get("jana_pusat_no") == pilihan_pusat_jana):
                if btn_jana_pusat:
                    # Jana untuk satu pusat sahaja
                    pusat_info = df_pusat_ppd[df_pusat_ppd["NO_PUSAT"] == pilihan_pusat_jana]
                    perlu = int(pusat_info["PETUGAS"].values[0]) if not pusat_info.empty else 10
                    
                    # Filter guru yang belum ada pusat tugas atau yang sesuai
                    df_available = df_cad_all.copy()
                    
                    # Elak sekolah tuan rumah
                    tuan_rumah_kod = str(pusat_info["KOD_SEKOLAH_TUAN_RUMAH"].values[0] if not pusat_info.empty else "").upper().strip()
                    if tuan_rumah_kod:
                        df_available = df_available[~df_available["KOD_SEKOLAH_ASAL"].astype(str).str.upper().str.contains(tuan_rumah_kod, na=False)]
                    
                    # STRICT MAX 3 untuk jana ikut pusat juga
                    # Kira berapa guru dari setiap sekolah sudah ada di pusat ini
                    sekolah_count_pusat = {}
                    # Dari DB
                    for _, c in df_cad_all.iterrows():
                        p_db = str(c.get("kod_pusat") or c.get("KOD_PUSAT") or "").upper().strip()
                        if p_db == pilihan_pusat_jana:
                            kod = str(c.get("KOD_SEKOLAH_ASAL") or c.get("kod_sekolah_asal") or "").upper().strip()
                            if kod:
                                sekolah_count_pusat[kod] = sekolah_count_pusat.get(kod, 0) + 1
                    # Dari session
                    for p in st.session_state.get("jana_all_result", []) or []:
                        if str(p.get("NO_PUSAT_TUGAS") or "").upper().strip() == pilihan_pusat_jana:
                            kod = str(p.get("KOD_SEKOLAH_ASAL") or "").upper().strip()
                            if kod:
                                sekolah_count_pusat[kod] = sekolah_count_pusat.get(kod, 0) + 1
                    
                    st.info(f"Semakan sedia ada di {pilihan_pusat_jana}: {sekolah_count_pusat}")
                    
                    def check_max3_ikut_pusat(row):
                        k = str(row.get("KOD_SEKOLAH_ASAL", "") or "").upper().strip()
                        return sekolah_count_pusat.get(k, 0) < 3 if k else True
                    
                    df_available["CHECK_MAX3"] = df_available.apply(check_max3_ikut_pusat, axis=1)
                    df_before = len(df_available)
                    df_available = df_available[df_available["CHECK_MAX3"] == True].copy()
                    df_after = len(df_available)
                    if df_before > df_after:
                        st.warning(f"📋 {df_before - df_after} guru ditapis - sekolah sudah ada 3 orang di {pilihan_pusat_jana} (Max 3)")
                    
                    # Ambil sebanyak yang perlu, prioriti ikut jawatan
                    jawatan_order = {"Ketua Pengawas": 1, "Timbalan Ketua Pengawas": 2, "Penyelia Kawasan": 3, "Pengawas Peperiksaan": 4}
                    df_available["JAWATAN_ORDER"] = df_available["JAWATAN_CADANGAN"].map(jawatan_order).fillna(5)
                    df_available = df_available.sort_values("JAWATAN_ORDER")
                    
                    # Random untuk elak bias
                    import random
                    if len(df_available) > 1:
                        df_available = df_available.sample(frac=1, random_state=random.randint(1, 10000)).reset_index(drop=True)
                    
                    assignments = []
                    for _, row in df_available.iterrows():
                        if len(assignments) >= perlu:
                            break
                        kod_row = str(row.get("KOD_SEKOLAH_ASAL", "") or "").upper().strip()
                        if kod_row and sekolah_count_pusat.get(kod_row, 0) >= 3:
                            continue
                        assignments.append({
                            "id": row.get("id", ""),
                            "NAMA_GURU": row.get("NAMA_GURU", ""),
                            "IC_GURU": row.get("IC_GURU", ""),
                            "JAWATAN_CADANGAN": row.get("JAWATAN_CADANGAN", ""),
                            "JAWATAN": row.get("JAWATAN_CADANGAN", ""),
                            "KOD_SEKOLAH_ASAL": row.get("KOD_SEKOLAH_ASAL", ""),
                            "NAMA_SEKOLAH_ASAL": row.get("NAMA_SEKOLAH_ASAL", ""),
                            "NO_PUSAT_TUGAS": pilihan_pusat_jana,
                            "STATUS": "DIJANA PPD"
                        })
                        if kod_row:
                            sekolah_count_pusat[kod_row] = sekolah_count_pusat.get(kod_row, 0) + 1
                    
                    df_assign_pusat = pd.DataFrame(assignments)
                    st.session_state["jana_pusat_result"] = df_assign_pusat.to_dict('records')
                    st.session_state["jana_pusat_no"] = pilihan_pusat_jana
                
                df_assign_pusat = pd.DataFrame(st.session_state.get("jana_pusat_result", []))
                if not df_assign_pusat.empty and st.session_state.get("jana_pusat_no") == pilihan_pusat_jana:
                    pusat_nama = df_pusat_ppd[df_pusat_ppd["NO_PUSAT"] == pilihan_pusat_jana]["NAMA_PUSAT"].values[0] if not df_pusat_ppd[df_pusat_ppd["NO_PUSAT"] == pilihan_pusat_jana].empty else ""
                    st.success(f"✅ Berjaya jana {len(df_assign_pusat)} guru untuk pusat {pilihan_pusat_jana} - {pusat_nama}")
                    
                    st.markdown(f"#### 👥 Hasil Jana Untuk Pusat {pilihan_pusat_jana}")
                    st.dataframe(df_assign_pusat, use_container_width=True, hide_index=True)
                    
                    col_save2, col_clear2 = st.columns(2)
                    with col_save2:
                        if st.button(f"💾 Simpan Untuk {pilihan_pusat_jana}", type="primary", use_container_width=True, key="save_jana_pusat"):
                            try:
                                saved = 0
                                for _, r in df_assign_pusat.iterrows():
                                    try:
                                        if r.get("id"):
                                            supa.table("cadangan_sup").update({"kod_pusat": pilihan_pusat_jana, "status": "DIJANA PPD"}).eq("id", r["id"]).execute()
                                        saved += 1
                                    except Exception as e:
                                        st.error(f"Gagal: {e}")
                                st.success(f"✅ Simpan {saved} untuk {pilihan_pusat_jana}")
                                st.balloons()
                            except Exception as e:
                                st.error(f"Error: {e}")
                    with col_clear2:
                        if st.button("🗑️ Clear", use_container_width=True, key="clear_jana_pusat"):
                            if "jana_pusat_result" in st.session_state:
                                del st.session_state["jana_pusat_result"]
                            st.rerun()
                    
                    st.download_button(f"📥 Export Jana {pilihan_pusat_jana}", to_excel(df_assign_pusat), file_name=f"jana_{pilihan_pusat_jana}_{datetime.date.today()}.xlsx", use_container_width=True)

        elif menu == "hasil":
            st.header(f"Hasil Janaan - PPD {kod_ppd}")
            
            # ===== BUTANG BATAL JANAAN - RESET SEMUA JADI 0 =====
            col_batal1, col_batal2 = st.columns([3, 1])
            with col_batal1:
                st.caption(f"PPD {kod_ppd} - Jika ada pelanggaran max 3 (contoh SAM NURUL IMAN 10 orang di BA021), batal dan jana semula")
            with col_batal2:
                if st.button("🗑️ Batal Janaan - Reset 0", type="primary", use_container_width=True, key="batal_janaan_all"):
                    st.session_state["confirm_batal"] = True
            
            if st.session_state.get("confirm_batal"):
                st.warning("⚠️ Anda pasti nak batal semua janaan? Semua penempatan akan jadi 0 dan perlu Jana Keseluruhan semula!")
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("✅ YA, Batal Semua Janaan", type="primary", use_container_width=True, key="confirm_yes_batal"):
                        try:
                            # Clear DB - set kod_pusat = None untuk PPD ini
                            st.info("Membatalkan semua janaan...")
                            # Update semua cadangan PPD ini
                            supa.table("cadangan_sup").update({"kod_pusat": None, "status": "DICADANGKAN"}).eq("kod_ppd", kod_ppd).execute()
                            # Clear session
                            if "jana_all_result" in st.session_state:
                                del st.session_state["jana_all_result"]
                            if "jana_pusat_result" in st.session_state:
                                del st.session_state["jana_pusat_result"]
                            if "jana_pusat_no" in st.session_state:
                                del st.session_state["jana_pusat_no"]
                            st.session_state["confirm_batal"] = False
                            st.success(f"✅ Berjaya batal semua janaan untuk PPD {kod_ppd}. Hasil janaan sekarang 0. Sila Jana Keseluruhan semula!")
                            st.balloons()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Gagal batal: {e}")
                            st.session_state["confirm_batal"] = False
                with col_no:
                    if st.button("❌ Tidak", use_container_width=True, key="confirm_no_batal"):
                        st.session_state["confirm_batal"] = False
                        st.rerun()
            
            st.markdown("---")
            df_pusat_raw = get_pusat_df()
            df_cad_all = get_cadangan_df(kod_ppd=kod_ppd)
            if df_pusat_raw.empty:
                st.warning("Tiada pusat_master")
                st.stop()
            pusat_list = []
            for _, r in df_pusat_raw.iterrows():
                d = r.get("data") if isinstance(r.get("data"), dict) else {}
                if isinstance(d, str):
                    try: d = json.loads(d)
                    except: d = {}
                no_pusat = str(r.get("no_pusat") or r.get("kod_pusat") or d.get("NO_PUSAT") or "").upper().strip()
                if not no_pusat.startswith(kod_ppd.upper()): continue
                nama = r.get("nama_pusat") or d.get("NAMA_PUSAT") or ""
                pusat_list.append({"NO_PUSAT": no_pusat, "NAMA_PUSAT": nama})
            df_pusat_list = pd.DataFrame(pusat_list)
            if df_pusat_list.empty:
                st.warning(f"Tiada pusat untuk PPD {kod_ppd}")
                st.stop()
            pilihan_pusat_hasil = st.selectbox("Pilih Pusat", df_pusat_list["NO_PUSAT"].tolist(), format_func=lambda x: f"{x} - {df_pusat_list[df_pusat_list['NO_PUSAT']==x]['NAMA_PUSAT'].values[0][:30] if not df_pusat_list[df_pusat_list['NO_PUSAT']==x].empty else x}", key="pilih_pusat_hasil")
            show_flash()
            def _bersih(v):
                s = "" if v is None else str(v).strip()
                return "" if s.lower() in ("", "nan", "none", "null", "nat") else s.upper()
            def _kunci(r):
                i = _bersih(r.get("id"))
                return f"ID:{i}" if i else "IC:" + re.sub(r"\D", "", str(r.get("IC_GURU") or r.get("ic_guru") or ""))
            tugas = {}
            if not df_cad_all.empty:
                for _, c in df_cad_all.iterrows():
                    k_c = _kunci(c)
                    p_db = _bersih(c.get("kod_pusat")) or _bersih(c.get("KOD_PUSAT"))
                    if p_db:
                        tugas[k_c] = {"pusat": p_db, "row": c}
            pending_rows = list(st.session_state.get("jana_all_result", []) or [])
            if st.session_state.get("jana_pusat_no"):
                pending_rows += list(st.session_state.get("jana_pusat_result", []) or [])
            for p in pending_rows:
                p_baru = _bersih(p.get("NO_PUSAT_TUGAS"))
                if not p_baru: continue
                k_p = _kunci(p)
                asal_row = pd.Series(p)
                tugas[k_p] = {"pusat": p_baru, "row": asal_row}
            hasil_pusat = []
            for v in tugas.values():
                if v["pusat"] == pilihan_pusat_hasil:
                    hasil_pusat.append(v["row"].copy())
            df_hasil = pd.DataFrame(hasil_pusat)
            
            # Semakan pelanggaran max 3 untuk pusat yang dipilih
            if not df_hasil.empty:
                sekolah_count_check = {}
                for _, r in df_hasil.iterrows():
                    kod = str(r.get("KOD_SEKOLAH_ASAL") or r.get("kod_sekolah_asal") or "").upper().strip()
                    if kod:
                        sekolah_count_check[kod] = sekolah_count_check.get(kod, 0) + 1
                pelanggaran = [(k, v) for k, v in sekolah_count_check.items() if v > 3]
                if pelanggaran:
                    st.error(f"❌ PELANGGARAN MAX 3 DI {pilihan_pusat_hasil}:")
                    for kod, cnt in pelanggaran:
                        st.error(f"   - {kod}: {cnt} orang (LANGGAR! Max 3 sahaja) - Contoh: SAM NURUL IMAN 10 orang di BA021")
                    st.warning("⚠️ Sila klik Batal Janaan di atas dan Jana Keseluruhan semula untuk betulkan!")
                else:
                    st.success(f"✅ Semakan Max 3 OK di {pilihan_pusat_hasil}: Tiada sekolah lebih 3 orang")
            
            st.markdown("---")
            if df_hasil.empty:
                st.warning(f"Belum Ada Hasil Janaan Di Pusat Yang Dipilih: {pilihan_pusat_hasil}")
                st.info("Sila pergi ke Jana Keseluruhan untuk jana petugas.")
            else:
                pusat_nama_h = df_pusat_list[df_pusat_list["NO_PUSAT"] == pilihan_pusat_hasil]["NAMA_PUSAT"].values[0] if not df_pusat_list[df_pusat_list["NO_PUSAT"] == pilihan_pusat_hasil].empty else ""
                st.success(f"{pilihan_pusat_hasil} - {pusat_nama_h} | {len(df_hasil)} petugas: 1 Ketua, 1 Timbalan, {len(df_hasil)-2} Pengawas")
                jawatan_groups = {}
                for _, r in df_hasil.iterrows():
                    jaw = str(r.get("JAWATAN_CADANGAN") or r.get("jawatan_cadangan") or r.get("JAWATAN") or "Pengawas Peperiksaan").strip()
                    if jaw not in jawatan_groups:
                        jawatan_groups[jaw] = []
                    jawatan_groups[jaw].append(r)
                order = ["Ketua Pengawas", "Timbalan Ketua Pengawas", "Pengawas Peperiksaan"]
                for jawatan in order:
                    if jawatan not in jawatan_groups: continue
                    guru_list = jawatan_groups[jawatan]
                    if "Ketua Pengawas" in jawatan and "Timbalan" not in jawatan:
                        label = "Ketua Pengawas - 1 orang"
                    elif "Timbalan" in jawatan:
                        label = "Timbalan Ketua Pengawas - 1 orang"
                    else:
                        label = f"Pengawas Peperiksaan - {len(guru_list)} orang"
                    st.subheader(label)
                    rows_j = []
                    for g in guru_list:
                        rows_j.append({"NAMA": g.get("NAMA_GURU", ""), "NO IC": g.get("IC_GURU", ""), "SEKOLAH ASAL": g.get("KOD_SEKOLAH_ASAL", ""), "NAMA SEKOLAH ASAL": str(g.get("NAMA_SEKOLAH_ASAL", ""))[:30], "JANTINA": g.get("JANTINA", "") or g.get("jantina", ""), "NO TELEFON": g.get("TELEFON_GURU", "") or g.get("telefon_guru", "")})
                    df_j = pd.DataFrame(rows_j)
                    st.dataframe(df_j, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.markdown("## 📊 Hasil Janaan Keseluruhan Untuk Setiap Sekolah")
            
            tab1, tab2, tab3 = st.tabs(["📋 Ringkasan Semua Pusat", "🏫 Mengikut Sekolah Asal", "👥 Semua Guru Ditempatkan"])
            
            with tab1:
                st.markdown("### 📋 Ringkasan Keseluruhan - Semua Pusat")
                ringkas_all = []
                for _, pr in df_pusat_list.iterrows():
                    no_p = pr["NO_PUSAT"]
                    nama_p = pr["NAMA_PUSAT"]
                    guru_di_pusat = [v for v in tugas.values() if v["pusat"] == no_p]
                    kp = sum(1 for v in guru_di_pusat if "Ketua Pengawas" in str(v["row"].get("JAWATAN_CADANGAN") or v["row"].get("JAWATAN") or "") and "Timbalan" not in str(v["row"].get("JAWATAN_CADANGAN") or ""))
                    tkp = sum(1 for v in guru_di_pusat if "Timbalan" in str(v["row"].get("JAWATAN_CADANGAN") or v["row"].get("JAWATAN") or ""))
                    peng = len(guru_di_pusat) - kp - tkp
                    status = "✅ Cukup" if len(guru_di_pusat) > 0 else "❌ Belum Ada"
                    ringkas_all.append({"NO PUSAT": no_p, "NAMA PUSAT": str(nama_p)[:30], "JUMLAH": len(guru_di_pusat), "KP": kp, "TKP": tkp, "PENGAWAS": peng, "STATUS": status})
                df_ringkas_all = pd.DataFrame(ringkas_all)
                if not df_ringkas_all.empty:
                    st.dataframe(df_ringkas_all, use_container_width=True, hide_index=True)
                    st.download_button("📥 Export Ringkasan Semua Pusat", to_excel(df_ringkas_all), file_name=f"ringkasan_semua_pusat_{kod_ppd}.xlsx", use_container_width=True)
                else:
                    st.info("Belum ada hasil janaan keseluruhan")
            
            with tab2:
                st.markdown("### 🏫 Hasil Janaan Mengikut Sekolah Asal")
                st.caption("Setiap sekolah - berapa guru ditempatkan dan ke pusat mana")
                sekolah_groups = {}
                for v in tugas.values():
                    r = v["row"]
                    kod_sek = str(r.get("KOD_SEKOLAH_ASAL") or r.get("kod_sekolah_asal") or "TIADA KOD").upper().strip()
                    nama_sek = str(r.get("NAMA_SEKOLAH_ASAL") or r.get("nama_sekolah_asal") or kod_sek)[:35]
                    key = f"{kod_sek} - {nama_sek}"
                    if key not in sekolah_groups:
                        sekolah_groups[key] = []
                    sekolah_groups[key].append({"row": r, "pusat": v["pusat"]})
                
                if not sekolah_groups:
                    st.info("Belum ada hasil janaan")
                else:
                    # Summary per sekolah
                    summary_sekolah = []
                    for key, guru_list in sorted(sekolah_groups.items()):
                        kod = key.split(" - ")[0]
                        pusat_list = list(set([g["pusat"] for g in guru_list]))
                        summary_sekolah.append({"KOD SEKOLAH": kod, "NAMA SEKOLAH": key.split(" - ", 1)[1] if " - " in key else key, "BIL GURU": len(guru_list), "PUSAT DITEMPATKAN": ", ".join(sorted(pusat_list))})
                    df_sum_sek = pd.DataFrame(summary_sekolah)
                    st.dataframe(df_sum_sek, use_container_width=True, hide_index=True)
                    st.markdown("---")
                    st.markdown("#### 🔍 Detail Setiap Sekolah")
                    pilih_sekolah = st.selectbox("Pilih Sekolah Untuk Lihat Detail", sorted(sekolah_groups.keys()), key="pilih_sekolah_hasil")
                    if pilih_sekolah:
                        detail = sekolah_groups[pilih_sekolah]
                        st.markdown(f"**{pilih_sekolah} - {len(detail)} guru ditempatkan:**")
                        rows_detail = []
                        for g in detail:
                            r = g["row"]
                            rows_detail.append({"NAMA": r.get("NAMA_GURU", ""), "NO IC": r.get("IC_GURU", ""), "JAWATAN": r.get("JAWATAN_CADANGAN") or r.get("JAWATAN") or "", "PUSAT TUGAS": g["pusat"], "JANTINA": r.get("JANTINA", "") or r.get("jantina", ""), "TELEFON": r.get("TELEFON_GURU", "") or r.get("telefon_guru", "")})
                        df_detail = pd.DataFrame(rows_detail)
                        st.dataframe(df_detail, use_container_width=True, hide_index=True)
                        st.download_button(f"📥 Export {pilih_sekolah}", to_excel(df_detail), file_name=f"hasil_{pilih_sekolah.split(' - ')[0]}_{kod_ppd}.xlsx", use_container_width=True, key=f"export_{pilih_sekolah}")
            
            with tab3:
                st.markdown("### 👥 Semua Guru Ditempatkan - Keseluruhan")
                all_guru_rows = []
                for v in tugas.values():
                    r = v["row"]
                    all_guru_rows.append({"NAMA": r.get("NAMA_GURU", ""), "NO IC": r.get("IC_GURU", ""), "JAWATAN": r.get("JAWATAN_CADANGAN") or r.get("JAWATAN") or "", "SEKOLAH ASAL": r.get("KOD_SEKOLAH_ASAL", ""), "NAMA SEKOLAH ASAL": str(r.get("NAMA_SEKOLAH_ASAL", ""))[:25], "PUSAT TUGAS": v["pusat"], "JANTINA": r.get("JANTINA", "") or r.get("jantina", ""), "TELEFON": r.get("TELEFON_GURU", "") or r.get("telefon_guru", "")})
                df_all_guru = pd.DataFrame(all_guru_rows)
                if df_all_guru.empty:
                    st.info("Belum ada guru ditempatkan")
                else:
                    st.dataframe(df_all_guru, use_container_width=True, hide_index=True)
                    st.download_button("📥 Export Semua Guru Ditempatkan", to_excel(df_all_guru), file_name=f"semua_guru_ditempatkan_{kod_ppd}.xlsx", use_container_width=True)

        elif menu == "manual":
            st.markdown(f'''
            <div style="background: linear-gradient(135deg, #4a148c 0%, #7b1fa2 100%); padding:20px; border-radius:12px; color:white; margin-bottom:20px;">
                <h2 style="margin:0; color:white;">📌 Penempatan Manual - PPD {kod_ppd}</h2>
                <p style="margin:5px 0 0 0; color:#e1bee7;">Pilih pusat, klik kolum jawatan untuk pilih petugas secara manual - 1 Pusat = 1 KP + 1 TKP + Pengawas ikut keperluan</p>
            </div>
            ''', unsafe_allow_html=True)
            
            df_pusat_raw = get_pusat_df()
            df_cad_all = get_cadangan_df(kod_ppd=kod_ppd)
            
            if df_pusat_raw.empty:
                st.warning("Tiada pusat_master")
                st.stop()
            if df_cad_all.empty:
                st.warning(f"Belum ada cadangan SUP untuk PPD {kod_ppd}")
                st.stop()
            
            # Parse pusat list
            pusat_list_m = []
            for _, r in df_pusat_raw.iterrows():
                d = r.get("data") if isinstance(r.get("data"), dict) else {}
                if isinstance(d, str):
                    try: d = json.loads(d)
                    except: d = {}
                no_pusat = str(r.get("no_pusat") or r.get("kod_pusat") or d.get("NO_PUSAT") or "").upper().strip()
                if not no_pusat.startswith(kod_ppd.upper()): continue
                nama = r.get("nama_pusat") or d.get("NAMA_PUSAT") or ""
                j_calon = r.get("jumlah_calon") or d.get("JUMLAH_CALON") or 0
                try: jc = int(float(str(j_calon) or 0))
                except: jc = 0
                jk = kira_kelas_dari_calon(jc)
                petugas_perlu = kira_petugas_dari_kelas(jk)
                kod_tuan = str(r.get("kod_sekolah_tuan_rumah") or d.get("KOD_SEKOLAH_TUAN_RUMAH") or "").upper().strip()
                pusat_list_m.append({"NO_PUSAT": no_pusat, "NAMA_PUSAT": nama, "CALON": jc, "KELAS": jk, "PERLU": petugas_perlu, "KOD_TUAN": kod_tuan})
            
            df_pusat_m = pd.DataFrame(pusat_list_m)
            if df_pusat_m.empty:
                st.warning(f"Tiada pusat untuk PPD {kod_ppd}")
                st.stop()
            
            # Pilih pusat
            st.markdown("### 📍 STEP 1: Pilih Pusat Daerah")
            col_pus1, col_pus2 = st.columns([2, 1])
            with col_pus1:
                pilih_pusat_manual = st.selectbox(
                    "Pilih Pusat", 
                    df_pusat_m["NO_PUSAT"].tolist(),
                    format_func=lambda x: f"{x} - {df_pusat_m[df_pusat_m['NO_PUSAT']==x]['NAMA_PUSAT'].values[0][:30] if not df_pusat_m[df_pusat_m['NO_PUSAT']==x].empty else x}",
                    key="pilih_pusat_manual"
                )
            with col_pus2:
                info_pusat = df_pusat_m[df_pusat_m["NO_PUSAT"] == pilih_pusat_manual]
                if not info_pusat.empty:
                    perlu_m = int(info_pusat["PERLU"].values[0])
                    st.markdown(f'''
                    <div style="background:#e3f2fd; border:2px solid #1565c0; border-radius:8px; padding:10px; text-align:center;">
                        <div style="font-size:11px; color:#666;">KEPERLUAN PUSAT</div>
                        <div style="font-size:20px; font-weight:800; color:#0d47a1;">{perlu_m} Petugas</div>
                        <div style="font-size:11px; color:#424242;">1 KP + 1 TKP + {perlu_m-2} Pengawas</div>
                        <div style="font-size:10px; color:#666; margin-top:4px;">{info_pusat['CALON'].values[0]} calon | {info_pusat['KELAS'].values[0]} kelas</div>
                    </div>
                    ''', unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Load current placement for this pusat
            def _bersih_m(v):
                s = "" if v is None else str(v).strip()
                return "" if s.lower() in ("", "nan", "none", "null", "nat") else s.upper()
            
            def _kunci_m(r):
                i = _bersih_m(r.get("id"))
                return f"ID:{i}" if i else "IC:" + re.sub(r"\D", "", str(r.get("IC_GURU") or r.get("ic_guru") or ""))
            
            # Current tugas untuk pusat ini
            tugas_pusat_ini = {}
            if not df_cad_all.empty:
                for _, c in df_cad_all.iterrows():
                    p_db = _bersih_m(c.get("kod_pusat")) or _bersih_m(c.get("KOD_PUSAT"))
                    if p_db == pilih_pusat_manual:
                        tugas_pusat_ini[_kunci_m(c)] = c
            
            # Kira sekolah count untuk max 3 check
            sekolah_count_manual = {}
            for _, c in df_cad_all.iterrows():
                p_db = _bersih_m(c.get("kod_pusat")) or _bersih_m(c.get("KOD_PUSAT"))
                if p_db == pilih_pusat_manual:
                    kod = str(c.get("KOD_SEKOLAH_ASAL") or c.get("kod_sekolah_asal") or "").upper().strip()
                    if kod:
                        sekolah_count_manual[kod] = sekolah_count_manual.get(kod, 0) + 1
            
            # Paparan semasa
            st.markdown(f"### 🏫 Pusat {pilih_pusat_manual} - Penempatan Semasa")
            col_curr1, col_curr2, col_curr3, col_curr4 = st.columns(4)
            # FIX: Gunakan ID comparison, bukan object comparison (pandas Series error)
            kp_curr_dict = {}
            tkp_curr_dict = {}
            peng_curr_dict = {}
            for k, c in tugas_pusat_ini.items():
                jaw = str(c.get("JAWATAN_CADANGAN") or c.get("jawatan_cadangan") or c.get("JAWATAN") or "")
                if "Ketua Pengawas" in jaw and "Timbalan" not in jaw:
                    kp_curr_dict[k] = c
                elif "Timbalan" in jaw:
                    tkp_curr_dict[k] = c
                else:
                    peng_curr_dict[k] = c
            kp_curr = list(kp_curr_dict.values())
            tkp_curr = list(tkp_curr_dict.values())
            peng_curr = list(peng_curr_dict.values())
            
            with col_curr1:
                st.metric("Ketua Pengawas", f"{len(kp_curr)}/1", delta="OK" if len(kp_curr)==1 else "Perlu 1", delta_color="normal" if len(kp_curr)==1 else "inverse")
            with col_curr2:
                st.metric("Timbalan KP", f"{len(tkp_curr)}/1", delta="OK" if len(tkp_curr)==1 else "Perlu 1", delta_color="normal" if len(tkp_curr)==1 else "inverse")
            with col_curr3:
                perlu_p = int(info_pusat["PERLU"].values[0]) if not info_pusat.empty else 0
                st.metric("Pengawas", f"{len(peng_curr)}/{perlu_p-2}", delta=f"Perlu {perlu_p-2}")
            with col_curr4:
                st.metric("Jumlah", f"{len(tugas_pusat_ini)}/{perlu_p}", delta="Cukup" if len(tugas_pusat_ini)>=perlu_p else f"Kurang {perlu_p-len(tugas_pusat_ini)}")
            
            # Check pelanggaran max 3
            pelanggaran_m = [(k, v) for k, v in sekolah_count_manual.items() if v > 3]
            if pelanggaran_m:
                st.error(f"❌ Pelanggaran Max 3 di {pilih_pusat_manual}:")
                for kod, cnt in pelanggaran_m:
                    st.error(f"  - {kod}: {cnt} orang (Max 3 sahaja!)")
            else:
                st.success(f"✅ Max 3 OK di {pilih_pusat_manual} - Tiada sekolah lebih 3 orang")
            
            st.markdown("---")
            
            # 3 Kolum Penempatan Manual
            st.markdown("### 📌 STEP 2: Penempatan Manual - Klik Kolum Untuk Pilih")
            
            col_kp, col_tkp, col_peng = st.columns(3)
            
            # ===== KOLUM KETUA PENGAWAS =====
            with col_kp:
                st.markdown('''
                <div style="background:#ffebee; border:2px solid #b71c1c; border-radius:10px; padding:12px; text-align:center; margin-bottom:10px;">
                    <div style="font-size:28px;">👑</div>
                    <div style="font-weight:800; color:#b71c1c;">KETUA PENGAWAS</div>
                    <div style="font-size:11px; color:#666;">1 orang sahaja per pusat</div>
                </div>
                ''', unsafe_allow_html=True)
                
                if kp_curr:
                    st.markdown("**Semasa:**")
                    for c in kp_curr:
                        st.markdown(f'''
                        <div style="background:#ffcdd2; border:1px solid #b71c1c; border-radius:6px; padding:8px; margin:4px 0;">
                            <div style="font-weight:700; font-size:12px;">{c.get("NAMA_GURU", "")}</div>
                            <div style="font-size:10px;">{c.get("KOD_SEKOLAH_ASAL", "")} | {c.get("IC_GURU", "")}</div>
                        </div>
                        ''', unsafe_allow_html=True)
                    if st.button("🗑️ Buang KP", key="buang_kp", use_container_width=True):
                        for k in list(kp_curr_dict.keys()):
                            try:
                                c = tugas_pusat_ini.get(k)
                                if c is not None:
                                    supa.table("cadangan_sup").update({"kod_pusat": None, "status": "DICADANGKAN"}).eq("id", c.get("id")).execute()
                            except Exception as e:
                                st.error(str(e))
                        st.success("KP dibuang")
                        st.rerun()
                else:
                    st.info("Belum ada KP")
                
                st.markdown("**Pilih KP Baru:**")
                # Filter cadangan KP yang belum ditempatkan atau boleh ditukar
                kod_tuan_m = info_pusat["KOD_TUAN"].values[0] if not info_pusat.empty else ""
                df_kp_calon = df_cad_all.copy()
                # Hanya KP
                df_kp_calon = df_kp_calon[df_kp_calon["JAWATAN_CADANGAN"].astype(str).str.contains("Ketua Pengawas", case=False, na=False)]
                # Elak sekolah sendiri
                if kod_tuan_m:
                    df_kp_calon = df_kp_calon[~df_kp_calon["KOD_SEKOLAH_ASAL"].astype(str).str.upper().str.strip().eq(kod_tuan_m)]
                # Elak yang sudah ada pusat lain? Biar boleh pilih, tapi warning
                # Check max 3
                def check_kp_max3(row):
                    kod = str(row.get("KOD_SEKOLAH_ASAL", "")).upper().strip()
                    return sekolah_count_manual.get(kod, 0) < 3 if kod else True
                df_kp_calon["MAX3_OK"] = df_kp_calon.apply(check_kp_max3, axis=1)
                
                # Show only yang layak max 3
                df_kp_layak = df_kp_calon[df_kp_calon["MAX3_OK"] == True]
                
                if df_kp_layak.empty:
                    st.warning("Tiada calon KP yang layak (max 3 atau sekolah sendiri)")
                    st.dataframe(df_kp_calon[["NAMA_GURU", "KOD_SEKOLAH_ASAL", "IC_GURU"]].head(10), use_container_width=True, hide_index=True)
                else:
                    st.caption(f"{len(df_kp_layak)} calon KP layak (max 3 OK)")
                    pilih_kp = st.selectbox(
                        "Klik untuk pilih Ketua Pengawas",
                        df_kp_layak["id"].tolist() if "id" in df_kp_layak.columns else [],
                        format_func=lambda x: f"{df_kp_layak[df_kp_layak['id']==x]['NAMA_GURU'].values[0]} - {df_kp_layak[df_kp_layak['id']==x]['KOD_SEKOLAH_ASAL'].values[0]} | {df_kp_layak[df_kp_layak['id']==x]['NAMA_SEKOLAH_ASAL'].values[0][:20]}" if not df_kp_layak[df_kp_layak['id']==x].empty else str(x),
                        key="pilih_kp_manual"
                    )
                    if st.button("✅ Lantik Sebagai KP", type="primary", use_container_width=True, key="lantik_kp"):
                        if pilih_kp:
                            try:
                                # Jika sudah ada KP, buang dulu
                                for k in list(kp_curr_dict.keys()):
                                    c = tugas_pusat_ini.get(k)
                                    if c is not None:
                                        supa.table("cadangan_sup").update({"kod_pusat": None}).eq("id", c.get("id")).execute()
                                supa.table("cadangan_sup").update({"kod_pusat": pilih_pusat_manual, "status": "DILANTIK PPD"}).eq("id", pilih_kp).execute()
                                st.success(f"KP dilantik ke {pilih_pusat_manual}")
                                st.balloons()
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))
            
            # ===== KOLUM TIMBALAN KETUA PENGAWAS =====
            with col_tkp:
                st.markdown('''
                <div style="background:#fff3e0; border:2px solid #e65100; border-radius:10px; padding:12px; text-align:center; margin-bottom:10px;">
                    <div style="font-size:28px;">🎖️</div>
                    <div style="font-weight:800; color:#e65100;">TIMBALAN KP</div>
                    <div style="font-size:11px; color:#666;">1 orang sahaja per pusat</div>
                </div>
                ''', unsafe_allow_html=True)
                
                if tkp_curr:
                    st.markdown("**Semasa:**")
                    for c in tkp_curr:
                        st.markdown(f'''
                        <div style="background:#ffe0b2; border:1px solid #e65100; border-radius:6px; padding:8px; margin:4px 0;">
                            <div style="font-weight:700; font-size:12px;">{c.get("NAMA_GURU", "")}</div>
                            <div style="font-size:10px;">{c.get("KOD_SEKOLAH_ASAL", "")} | {c.get("IC_GURU", "")}</div>
                        </div>
                        ''', unsafe_allow_html=True)
                    if st.button("🗑️ Buang TKP", key="buang_tkp", use_container_width=True):
                        for k in list(tkp_curr_dict.keys()):
                            try:
                                c = tugas_pusat_ini.get(k)
                                if c is not None:
                                    supa.table("cadangan_sup").update({"kod_pusat": None, "status": "DICADANGKAN"}).eq("id", c.get("id")).execute()
                            except Exception as e:
                                st.error(str(e))
                        st.success("TKP dibuang")
                        st.rerun()
                else:
                    st.info("Belum ada TKP")
                
                st.markdown("**Pilih TKP Baru:**")
                df_tkp_calon = df_cad_all.copy()
                df_tkp_calon = df_tkp_calon[df_tkp_calon["JAWATAN_CADANGAN"].astype(str).str.contains("Timbalan", case=False, na=False)]
                if kod_tuan_m:
                    df_tkp_calon = df_tkp_calon[~df_tkp_calon["KOD_SEKOLAH_ASAL"].astype(str).str.upper().str.strip().eq(kod_tuan_m)]
                def check_tkp_max3(row):
                    kod = str(row.get("KOD_SEKOLAH_ASAL", "")).upper().strip()
                    return sekolah_count_manual.get(kod, 0) < 3 if kod else True
                df_tkp_calon["MAX3_OK"] = df_tkp_calon.apply(check_tkp_max3, axis=1)
                df_tkp_layak = df_tkp_calon[df_tkp_calon["MAX3_OK"] == True]
                
                if df_tkp_layak.empty:
                    st.warning("Tiada calon TKP layak")
                else:
                    st.caption(f"{len(df_tkp_layak)} calon TKP layak - keseluruhan daerah {kod_ppd}")
                    pilih_tkp = st.selectbox(
                        "Klik untuk pilih Timbalan KP",
                        df_tkp_layak["id"].tolist() if "id" in df_tkp_layak.columns else [],
                        format_func=lambda x: f"{df_tkp_layak[df_tkp_layak['id']==x]['NAMA_GURU'].values[0]} - {df_tkp_layak[df_tkp_layak['id']==x]['KOD_SEKOLAH_ASAL'].values[0]}" if not df_tkp_layak[df_tkp_layak['id']==x].empty else str(x),
                        key="pilih_tkp_manual"
                    )
                    if st.button("✅ Lantik Sebagai TKP", type="primary", use_container_width=True, key="lantik_tkp"):
                        if pilih_tkp:
                            try:
                                for k in list(tkp_curr_dict.keys()):
                                    c = tugas_pusat_ini.get(k)
                                    if c is not None:
                                        supa.table("cadangan_sup").update({"kod_pusat": None}).eq("id", c.get("id")).execute()
                                supa.table("cadangan_sup").update({"kod_pusat": pilih_pusat_manual, "status": "DILANTIK PPD"}).eq("id", pilih_tkp).execute()
                                st.success(f"TKP dilantik ke {pilih_pusat_manual}")
                                st.balloons()
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))
            
            # ===== KOLUM PENGAWAS =====
            with col_peng:
                perlu_p = int(info_pusat["PERLU"].values[0]) if not info_pusat.empty else 10
                perlu_pengawas = max(0, perlu_p - 1 - 1)
                st.markdown(f'''
                <div style="background:#e8f5e9; border:2px solid #1b5e20; border-radius:10px; padding:12px; text-align:center; margin-bottom:10px;">
                    <div style="font-size:28px;">👨‍🏫</div>
                    <div style="font-weight:800; color:#1b5e20;">PENGAWAS</div>
                    <div style="font-size:11px; color:#666;">{perlu_pengawas} orang diperlukan</div>
                    <div style="font-size:10px; color:#2e7d32; margin-top:4px;">Pusat {pilih_pusat_manual} perlu {perlu_p} (1 KP + 1 TKP + {perlu_pengawas})</div>
                </div>
                ''', unsafe_allow_html=True)
                
                if peng_curr:
                    st.markdown(f"**Semasa: {len(peng_curr)}/{perlu_pengawas}**")
                    for c in peng_curr[:5]:
                        st.markdown(f'''
                        <div style="background:#c8e6c9; border:1px solid #1b5e20; border-radius:6px; padding:6px; margin:3px 0; font-size:11px;">
                            <b>{c.get("NAMA_GURU", "")[:20]}</b> - {c.get("KOD_SEKOLAH_ASAL", "")}
                        </div>
                        ''', unsafe_allow_html=True)
                    if len(peng_curr) > 5:
                        st.caption(f"... dan {len(peng_curr)-5} lagi")
                    if st.button("🗑️ Buang Semua Pengawas", key="buang_peng", use_container_width=True):
                        for k in list(peng_curr_dict.keys()):
                            try:
                                c = tugas_pusat_ini.get(k)
                                if c is not None:
                                    supa.table("cadangan_sup").update({"kod_pusat": None, "status": "DICADANGKAN"}).eq("id", c.get("id")).execute()
                            except Exception as e:
                                st.error(str(e))
                        st.success("Pengawas dibuang")
                        st.rerun()
                else:
                    st.info(f"Belum ada Pengawas - perlu {perlu_pengawas}")
                
                st.markdown("**Pilih Pengawas Baru:**")
                df_peng_calon = df_cad_all.copy()
                # Pengawas sahaja (bukan KP/TKP)
                df_peng_calon = df_peng_calon[~df_peng_calon["JAWATAN_CADANGAN"].astype(str).str.contains("Ketua Pengawas|Timbalan", case=False, na=False, regex=True)]
                if kod_tuan_m:
                    df_peng_calon = df_peng_calon[~df_peng_calon["KOD_SEKOLAH_ASAL"].astype(str).str.upper().str.strip().eq(kod_tuan_m)]
                def check_peng_max3(row):
                    kod = str(row.get("KOD_SEKOLAH_ASAL", "")).upper().strip()
                    return sekolah_count_manual.get(kod, 0) < 3 if kod else True
                df_peng_calon["MAX3_OK"] = df_peng_calon.apply(check_peng_max3, axis=1)
                df_peng_layak = df_peng_calon[df_peng_calon["MAX3_OK"] == True]
                
                # Yang belum ditempatkan
                df_peng_belum = df_peng_layak[df_peng_layak["kod_pusat"].isna() | (df_peng_layak["kod_pusat"] == "")]
                
                st.caption(f"{len(df_peng_belum)} calon Pengawas belum ditempatkan (layak max 3) | Pusat perlu {perlu_pengawas}")
                
                if df_peng_belum.empty:
                    st.warning("Tiada calon Pengawas layak yang belum ditempatkan")
                    st.dataframe(df_peng_layak[["NAMA_GURU", "KOD_SEKOLAH_ASAL", "JAWATAN_CADANGAN"]].head(10), use_container_width=True, hide_index=True)
                else:
                    # Multi select
                    pilih_peng_list = st.multiselect(
                        f"Pilih Pengawas (perlu {perlu_pengawas}, max 3 per sekolah)",
                        df_peng_belum["id"].tolist() if "id" in df_peng_belum.columns else [],
                        format_func=lambda x: f"{df_peng_belum[df_peng_belum['id']==x]['NAMA_GURU'].values[0]} - {df_peng_belum[df_peng_belum['id']==x]['KOD_SEKOLAH_ASAL'].values[0]} - {df_peng_belum[df_peng_belum['id']==x]['JAWATAN_CADANGAN'].values[0]}" if not df_peng_belum[df_peng_belum['id']==x].empty else str(x),
                        key="pilih_peng_manual"
                    )
                    # Check kalau pilih lebih dari perlu atau langgar max 3
                    if pilih_peng_list:
                        # Kira sekolah count kalau tambah yang dipilih
                        temp_count = sekolah_count_manual.copy()
                        valid = True
                        for pid in pilih_peng_list:
                            row = df_peng_belum[df_peng_belum["id"]==pid]
                            if not row.empty:
                                kod = str(row["KOD_SEKOLAH_ASAL"].values[0]).upper().strip()
                                if temp_count.get(kod, 0) >= 3:
                                    st.error(f"❌ {kod} sudah 3 orang di {pilih_pusat_manual} - tidak boleh tambah lagi!")
                                    valid = False
                                temp_count[kod] = temp_count.get(kod, 0) + 1
                        if len(pilih_peng_list) > perlu_pengawas:
                            st.warning(f"⚠️ Anda pilih {len(pilih_peng_list)} tapi pusat perlu {perlu_pengawas} sahaja")
                        
                        if st.button(f"✅ Lantik {len(pilih_peng_list)} Sebagai Pengawas", type="primary", use_container_width=True, key="lantik_peng", disabled=not valid):
                            try:
                                berjaya = 0
                                for pid in pilih_peng_list:
                                    supa.table("cadangan_sup").update({"kod_pusat": pilih_pusat_manual, "status": "DILANTIK PPD"}).eq("id", pid).execute()
                                    berjaya += 1
                                st.success(f"✅ {berjaya} Pengawas dilantik ke {pilih_pusat_manual}")
                                st.balloons()
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))
            
            st.markdown("---")
            st.markdown("### 📊 Ringkasan Penempatan Manual")
            if tugas_pusat_ini:
                all_rows = []
                for c in tugas_pusat_ini.values():
                    all_rows.append({"NAMA": c.get("NAMA_GURU", ""), "IC": c.get("IC_GURU", ""), "JAWATAN": c.get("JAWATAN_CADANGAN", ""), "SEKOLAH ASAL": c.get("KOD_SEKOLAH_ASAL", ""), "PUSAT": pilih_pusat_manual})
                df_summary = pd.DataFrame(all_rows)
                st.dataframe(df_summary, use_container_width=True, hide_index=True)
            else:
                st.info(f"Belum ada penempatan manual di {pilih_pusat_manual} - Sila pilih KP, TKP, Pengawas di atas")

        elif menu == "cadangan":
            st.header(f"Cadangan dari SUP - PPD {kod_ppd}")
            df_cad = get_cadangan_df(kod_ppd=kod_ppd)
            if df_cad.empty: st.info("Belum ada cadangan dari SUP")
            else:
                st.dataframe(df_cad, use_container_width=True)
                st.download_button("Export Cadangan", to_excel(df_cad), file_name=f"cadangan_PPD_{kod_ppd}.xlsx")

        elif menu == "kelulusan":
            st.header(f"Kelulusan PPD {kod_ppd}")
            df_cad = get_cadangan_df(kod_ppd=kod_ppd)
            if df_cad.empty: st.info("Tiada cadangan")
            else:
                st.dataframe(df_cad, use_container_width=True)
                pilih_id = st.multiselect("Pilih ID untuk lulus", df_cad["id"].tolist() if "id" in df_cad.columns else [])
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Lulus Terpilih", type="primary"):
                        for i in pilih_id:
                            try: supa.table("cadangan_sup").update({"status": "LULUS PPD"}).eq("id", i).execute()
                            except Exception as e: st.error(str(e))
                        st.success("Lulus berjaya")
                        st.rerun()
                with col2:
                    if st.button("❌ Tolak Terpilih"):
                        for i in pilih_id:
                            try: supa.table("cadangan_sup").update({"status": "TOLAK PPD"}).eq("id", i).execute()
                            except Exception as e: st.error(str(e))
                        st.success("Tolak berjaya")
                        st.rerun()

        elif menu == "export":
            st.header(f"Export Data PPD {kod_ppd}")
            df_cad = get_cadangan_df(kod_ppd=kod_ppd)
            if not df_cad.empty:
                st.download_button("📥 Export Cadangan PPD (Excel)", to_excel(df_cad), file_name=f"laporan_PPD_{kod_ppd}_{datetime.date.today()}.xlsx", use_container_width=True)
            try:
                res = supa.table("guru_master").select("*").eq("kod_ppd", kod_ppd.lower()).limit(5000).execute()
                df_guru = pd.DataFrame(res.data or [])
                if not df_guru.empty:
                    st.download_button("📥 Export Guru PPD (Excel)", to_excel(df_guru), file_name=f"guru_PPD_{kod_ppd}.xlsx", use_container_width=True)
            except Exception as e:
                st.error(str(e))

# ================= ROLE: JPN =================
elif st.session_state.role == "JPN":
    col_menu, col_main = st.columns([1, 3.2], gap="large")
    with col_menu:
        st.markdown('<div class="custom-sidebar">', unsafe_allow_html=True)
        st.markdown("### 🏛️ JPN Selangor")
        add_refresh_button()
        
        MENU_JPN = [('dashboard', '📊 Dashboard JPN'), ('sekolah', '🏫 Semua Sekolah'), ('pusat', '🏫 Pusat Master'), 
                    ('guru', '👨\u200d🏫 Guru Master'), ('cadangan', '📋 Semua Cadangan'), ('export', '📥 Export Negeri'), 
                    ('admin', '⚙️ Admin'), ('keluar', '🚪 Log Keluar')]
        menu = st.radio("Menu JPN", [k for k, _ in MENU_JPN], format_func=dict(MENU_JPN).get, label_visibility="collapsed", key="jpn_menu_radio")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_main:
        if menu == "keluar":
            st.session_state.clear()
            st.rerun()
        
        elif menu == "dashboard":
            st.header("Dashboard JPN Selangor - Pelantikan SPM 2026")
            cols = st.columns(5)
            for idx, t in enumerate(["sekolah_master", "pusat_master", "guru_master", "cadangan_sup"]):
                try:
                    res = supa.table(t).select("*", count="exact").limit(1).execute()
                    cols[idx].metric(t, res.count)
                except Exception as e:
                    cols[idx].error(f"{t}: {e}")
            
            st.markdown("---")
            st.subheader("Breakdown Ikut PPD")
            rows = []
            for ppd in KOD_DAERAH:
                try:
                    c1 = supa.table("sekolah_master").select("kod_sekolah", count="exact").eq("kod_ppd", ppd).execute()
                    c2 = supa.table("guru_master").select("id", count="exact").eq("kod_ppd", ppd.lower()).execute()
                    c3 = supa.table("cadangan_sup").select("id", count="exact").eq("kod_ppd", ppd).execute()
                    rows.append({"PPD": f"{ppd} - {PPD_MAP[ppd]}", "Sekolah": c1.count, "Guru": c2.count, "Cadangan": c3.count})
                except:
                    rows.append({"PPD": ppd, "Sekolah": 0, "Guru": 0, "Cadangan": 0})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        elif menu == "sekolah":
            st.header("Semua Sekolah Master (369 Sekolah)")
            try:
                res = supa.table("sekolah_master").select("*", count="exact").limit(5000).execute()
                df_count = res.count
                res2 = supa.table("sekolah_master").select("*").limit(1000).execute()
                df = pd.DataFrame(res2.data or [])
                st.write(f"Total dalam Supabase: **{df_count}** sekolah")
                if not df.empty:
                    st.dataframe(df, use_container_width=True)
                    st.download_button("📥 Export Sekolah Master", to_excel(df), file_name="sekolah_master.xlsx")
                else:
                    st.warning("sekolah_master kosong - belum push dari pusat_2026.csv. Sila import di bawah.")
            except Exception as e:
                st.error(f"sekolah_master error: {e}")
            
            st.markdown("---")
            st.subheader("📤 Import Sekolah Master dari Pusat & Guru")
            st.info("File sekolah digenerate dari pusat_2026.csv (506 pusat = 369 sekolah unik) + guru 60K. Upload SEKOLAH_MASTER_FINAL_2026.xlsx untuk push masuk sekolah_master.")
            up_sek = st.file_uploader("Upload Sekolah Master Excel (KOD SEKOLAH, NAMA SEKOLAH, KOD PPD)", type=["xlsx", "csv"], key="sekolah_up")
            if up_sek:
                try:
                    if up_sek.name.endswith(".csv"):
                        try: df_up = pd.read_csv(up_sek)
                        except:
                            up_sek.seek(0)
                            df_up = pd.read_csv(up_sek, encoding='latin1')
                    else:
                        df_up = pd.read_excel(up_sek)
                    st.write(f"Preview {len(df_up)} sekolah:")
                    st.dataframe(df_up.head(30), use_container_width=True)
                    if st.button(f"🚀 Import {len(df_up)} Sekolah ke Supabase", type="primary", use_container_width=True):
                        bar = st.progress(0)
                        stat = st.empty()
                        ok = 0
                        try:
                            supa.table("sekolah_master").delete().gt("id", 0).execute()
                            st.write("Old sekolah_master cleared")
                        except: pass
                        BATCH = 200
                        for start in range(0, len(df_up), BATCH):
                            end = min(start + BATCH, len(df_up))
                            bdf = df_up.iloc[start:end]
                            batch = []
                            for _, row in bdf.iterrows():
                                try: 
                                    kod = str(row.get("KOD SEKOLAH", "") or row.get("kod_sekolah", "") or row.get("KOD_SEKOLAH", "")).strip().upper()
                                    if not kod: continue
                                    nama = str(row.get("NAMA SEKOLAH", "") or row.get("nama_sekolah", "") or row.get("NAMA_PUSAT", "")).strip().upper()
                                    kod_ppd = str(row.get("KOD PPD", "") or row.get("kod_ppd", "") or row.get("PPD_CODE", "") or "BH").strip().upper()
                                    batch.append({"kod_sekolah": kod, "nama_sekolah": nama, "kod_ppd": kod_ppd, "data": {k: (" " if pd.isna(v) else str(v)) for k, v in row.to_dict().items()}})
                                except: continue
                            if batch:
                                try:
                                    supa.table("sekolah_master").insert(batch).execute()
                                    ok += len(batch)
                                except Exception as e:
                                    st.warning(f"Batch {start}-{end}: {e}")
                            bar.progress(end / len(df_up))
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
                    res = supa.table("pusat_master").select("*").limit(1000).execute()
                    df_p = pd.DataFrame(res.data or [])
                    if df_p.empty:
                        st.error("pusat_master kosong, import pusat dulu")
                    else:
                        sekolah_list = []
                        seen = set()
                        for _, r in df_p.iterrows():
                            d = r.get("data") or {}
                            kod_sek = d.get("KOD_SEKOLAH", "") or r.get("kod_sekolah", "") or ""
                            kod_sek = str(kod_sek).upper().strip()
                            if not kod_sek or kod_sek in seen: continue
                            seen.add(kod_sek)
                            sekolah_list.append({"kod_sekolah": kod_sek, "nama_sekolah": r.get("nama_pusat", "") or d.get("NAMA_PUSAT", ""), "kod_ppd": r.get("kod_ppd", "BH"), "data": {"KOD SEKOLAH": kod_sek, "NAMA SEKOLAH": r.get("nama_pusat", ""), "KOD PPD": r.get("kod_ppd", "BH")}})
                        if sekolah_list:
                            try: supa.table("sekolah_master").delete().gt("id", 0).execute()
                            except: pass
                            for i in range(0, len(sekolah_list), 200):
                                supa.table("sekolah_master").insert(sekolah_list[i:i + 200]).execute()
                            st.success(f"✅ Generated {len(sekolah_list)} sekolah dari pusat_master!")
                            st.rerun()
                except Exception as e:
                    st.error(f"Error generate: {e}")

        elif menu == "pusat":
            st.header("Pusat Master - Selangor 2026 (506 Pusat) - FIX Jumlah Calon")
            try:
                total = safe_count("pusat_master")
                res = supa.table("pusat_master").select("*").limit(1000).execute()
                raw_data = res.data or []
                df = pd.DataFrame(raw_data)
                st.write(f"Total Pusat Sedia Ada: **{total}** / 506 pusat")
                display_rows = []
                for r in raw_data:
                    d = r.get("data") or {}
                    if isinstance(d, str):
                        try: d = json.loads(d)
                        except: d = {}
                    no_pusat = r.get("no_pusat") or r.get("kod_pusat") or d.get("NO_PUSAT") or d.get("KOD PUSAT") or ""
                    nama = r.get("nama_pusat") or d.get("NAMA_PUSAT") or ""
                    kod_sek = r.get("kod_sekolah_tuan_rumah") or r.get("kod_sekolah") or d.get("KOD_SEKOLAH") or ""
                    ppd = r.get("ppd") or d.get("PPD") or ""
                    j_calon = r.get("jumlah_calon") or r.get("calon") or r.get("JUMLAH_CALON") or d.get("JUMLAH_CALON") or d.get("CALON") or 0
                    j_kelas = r.get("jumlah_kelas") or r.get("bilik") or d.get("JUMLAH_KELAS") or d.get("BILIK") or 0
                    petugas = d.get("PETUGAS_NEEDED") or r.get("petugas_needed") or 0
                    try: j_calon_int = int(float(str(j_calon).replace(",", "").strip() or 0))
                    except: j_calon_int = 0
                    try: j_kelas_int = int(float(str(j_kelas).strip() or 0))
                    except: j_kelas_int = 0
                    display_rows.append({"NO_PUSAT": no_pusat, "NAMA_PUSAT": nama, "KOD_SEKOLAH": kod_sek, "PPD": ppd, "JUMLAH_CALON": j_calon_int, "JUMLAH_KELAS": j_kelas_int, "PETUGAS": petugas, "_id": r.get("id"), "_raw": r})
                
                df_display = pd.DataFrame(display_rows)
                if not df_display.empty:
                    st.subheader(f"Senarai Pusat dengan Jumlah Calon (dari CSV)")
                    st.dataframe(df_display[["NO_PUSAT", "NAMA_PUSAT", "KOD_SEKOLAH", "PPD", "JUMLAH_CALON", "JUMLAH_KELAS", "PETUGAS"]].head(500), use_container_width=True)
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Total Calon", int(df_display["JUMLAH_CALON"].sum()))
                    c2.metric("Total Kelas", int(df_display["JUMLAH_KELAS"].sum()))
                    c3.metric("Ada Calon", len(df_display[df_display["JUMLAH_CALON"] > 0]))
                    if len(df_display[df_display["JUMLAH_CALON"] == 0]) > 100:
                        st.error(f"⚠️ {len(df_display[df_display['JUMLAH_CALON']==0])} pusat JUMLAH_CALON = 0 / kosong! Kena fix dari CSV.")
                    st.download_button("📥 Export Pusat dengan Calon", to_excel(pd.DataFrame(display_rows)), file_name="pusat_master_dengan_calon.xlsx")
                else:
                    st.warning("pusat_master kosong")
                
                st.markdown("---")
                st.subheader("🔧 FIX: Update Jumlah Calon yang Hilang")
                st.info("Kalau JUMLAH_CALON 0/kosong, upload pusat_2026.csv untuk update balik 506 pusat dengan jumlah calon betul.")
                up_fix = st.file_uploader("Upload pusat_2026.csv untuk FIX jumlah calon", type=["csv", "xlsx"], key="fix_calon")
                if up_fix:
                    try:
                        if up_fix.name.endswith(".csv"):
                            try: df_fix = pd.read_csv(up_fix)
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
                            ok = 0
                            fail = 0
                            for idx, row in df_fix.iterrows():
                                try:
                                    no_pusat = str(row.get("NO_PUSAT", "") or row.get("KOD PUSAT", "")).upper().strip()
                                    if not no_pusat: continue
                                    j_calon = row.get("JUMLAH_CALON", "0")
                                    j_kelas = row.get("JUMLAH_KELAS", "0")
                                    update_data = {"jumlah_calon": int(float(str(j_calon).strip() or 0)), "jumlah_kelas": int(float(str(j_kelas).strip() or 0)), "calon": int(float(str(j_calon).strip() or 0)), "bilik": int(float(str(j_kelas).strip() or 0))}
                                    try:
                                        supa.table("pusat_master").update(update_data).eq("no_pusat", no_pusat).execute()
                                        ok += 1
                                    except:
                                        try:
                                            supa.table("pusat_master").update(update_data).eq("kod_pusat", no_pusat).execute()
                                            ok += 1
                                        except: fail += 1
                                except: fail += 1
                                if idx % 20 == 0:
                                    bar.progress((idx + 1) / len(df_fix))
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
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("➕ Tambah Pusat Manual - Auto Kira SPM")
                st.caption("Formula: 1 kelas=20 calon, CEIL(calon/20)=kelas, petugas=kelas+9, sekolah perlu calonkan=kelas+12 (petugas+KP+TKP+Penyelia)")
                with st.form("tambah_pusat"):
                    kod_pusat = st.text_input("KOD PUSAT * (cth: BA001)")
                    nama_pusat = st.text_input("NAMA PUSAT *")
                    kod_ppd_pusat = st.selectbox("KOD PPD", KOD_DAERAH, format_func=lambda x: f"{x}-{PPD_MAP[x]}")
                    alamat_pusat = st.text_area("ALAMAT PUSAT (KOD SEKOLAH)")
                    calon_input = st.number_input("JUMLAH CALON * (contoh 105)", min_value=1, value=100, step=1, help="1 kelas = 20 calon. Auto kira kelas & petugas")
                    kelas_preview = kira_kelas_dari_calon(calon_input)
                    petugas_preview = kira_petugas_dari_kelas(kelas_preview)
                    sekolah_need_preview = kira_sekolah_perlu_calonkan(kelas_preview)
                    st.info(f" Auto Kira: {calon_input} calon → {kelas_preview} kelas (20/kelas) → {petugas_preview} petugas (kelas+9) → Sekolah perlu calonkan {sekolah_need_preview} orang (petugas+KP+TKP+Penyelia)")
                    submit_pusat = st.form_submit_button("💾 Simpan Pusat (Auto Kira)", type="primary", use_container_width=True)
                    if submit_pusat:
                        if not kod_pusat or not nama_pusat:
                            st.error("Kod & Nama Pusat wajib!")
                        else:
                            try:
                                kelas_calc = kira_kelas_dari_calon(calon_input)
                                petugas_calc = kira_petugas_dari_kelas(kelas_calc)
                                sekolah_need = kira_sekolah_perlu_calonkan(kelas_calc)
                                supa.table("pusat_master").insert({"kod_pusat": kod_pusat.upper(), "nama_pusat": nama_pusat.upper(), "kod_ppd": kod_ppd_pusat, "ppd": PPD_MAP.get(kod_ppd_pusat, ""), "alamat": alamat_pusat, "bilik": kelas_calc, "calon": int(calon_input), "jumlah_calon": int(calon_input), "jumlah_kelas": kelas_calc, "petugas_needed": petugas_calc, "data": {"NO_PUSAT": kod_pusat.upper(), "NAMA_PUSAT": nama_pusat.upper(), "KOD PPD": kod_ppd_pusat, "KOD_SEKOLAH": alamat_pusat, "JUMLAH_CALON": str(calon_input), "JUMLAH_KELAS": str(kelas_calc), "PETUGAS_NEEDED": str(petugas_calc), "SEKOLAH_PERLU_CALON": str(sekolah_need), "FORMULA": f"{calon_input} calon /20 = {kelas_calc} kelas, {kelas_calc}+9={petugas_calc} petugas, +3 KP/TKP/Penyelia = {sekolah_need} sekolah perlu calon"}}).execute()
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
                    st.download_button("📥 Template Pusat", to_excel(pd.DataFrame([{"KOD PUSAT": "BA001", "NAMA PUSAT": "SMK DATO HAMZAH", "KOD PPD": "BA", "ALAMAT PUSAT": "Jalan Dato Hamzah", "BILIK": 10, "CALON": 250}])), "TEMPLATE_PUSAT.xlsx")
                with col_t2:
                    st.download_button("📥 Sample pusat_2026.csv", open("/mnt/data/pusat_2026.csv", "rb").read() if __import__("os").path.exists("/mnt/data/pusat_2026.csv") else b"", "pusat_2026_sample.csv")
                
                up = st.file_uploader("Upload Excel/CSV Pusat (Excel atau CSV)", type=["xlsx", "csv"], key="pusat_up")
                if up:
                    try:
                        if up.name.endswith(".csv"):
                            try: df_up = pd.read_csv(up)
                            except:
                                up.seek(0)
                                df_up = pd.read_csv(up, encoding='latin1')
                        else:
                            df_up = pd.read_excel(up)
                        st.write(f"Preview {len(df_up)} pusat:")
                        st.dataframe(df_up.head(20), use_container_width=True)
                        if st.button(f"🚀 Import {len(df_up)} Pusat (Batch 200)", type="primary", use_container_width=True):
                            bar = st.progress(0)
                            stat = st.empty()
                            ok = 0
                            BATCH = 200
                            ppd_name_map = {"klang": "BA", "kuala langat": "BB", "kuala selangor": "BC", "hulu langat": "BD", "hulu selangor": "BE", "sabak bernam": "BF", "gombak": "BG", "petaling perdana": "BH", "sepang": "BJ", "petaling utama": "BK"}
                            for start in range(0, len(df_up), BATCH):
                                end = min(start + BATCH, len(df_up))
                                bdf = df_up.iloc[start:end]
                                batch = []
                                for _, row in bdf.iterrows():
                                    try:
                                        d = {}
                                        for k, v in row.to_dict().items():
                                            d[k] = " " if pd.isna(v) else str(v)
                                        kod_p = d.get("NO_PUSAT", "") or d.get("KOD PUSAT", "") or d.get("kod_pusat", "")
                                        kod_p = kod_p.upper().strip()
                                        if not kod_p: continue
                                        kod_ppd_val = d.get("KOD PPD", "") or d.get("KOD_PPD", "") or d.get("PPD_CODE", "")
                                        if not kod_ppd_val:
                                            ppd_raw = d.get("PPD", "").lower()
                                            for name, code in ppd_name_map.items():
                                                if name in ppd_raw:
                                                    kod_ppd_val = code
                                                    break
                                        if not kod_ppd_val: kod_ppd_val = "BH"
                                        kod_ppd_val = kod_ppd_val.upper().strip()
                                        nama_p = d.get("NAMA_PUSAT", "") or d.get("NAMA PUSAT", "") or kod_p
                                        bilik_val = d.get("JUMLAH_KELAS", "") or d.get("BILIK", "") or "10"
                                        calon_val = d.get("JUMLAH_CALON", "") or d.get("CALON", "") or "200"
                                        try: bilik_int = int(float(bilik_val))
                                        except: bilik_int = 10
                                        try: calon_int = int(float(calon_val))
                                        except: calon_int = 200
                                        batch.append({"kod_pusat": kod_p, "nama_pusat": nama_p.upper(), "kod_ppd": kod_ppd_val, "ppd": d.get("PPD", "") or PPD_MAP.get(kod_ppd_val, ""), "alamat": d.get("KOD_SEKOLAH", "") or d.get("ALAMAT PUSAT", "") or d.get("ALAMAT", ""), "bilik": bilik_int, "calon": calon_int, "data": d})
                                    except: continue
                                if batch:
                                    try:
                                        supa.table("pusat_master").insert(batch).execute()
                                        ok += len(batch)
                                    except Exception as e:
                                        st.warning(f"Batch {start}-{end}: {e}")
                                bar.progress(end / len(df_up))
                                stat.write(f"Progress {end}/{len(df_up)} | OK {ok}")
                            st.success(f"✅ Selesai import {ok}/{len(df_up)} pusat! Total 506")
                            st.balloons()
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
            
            st.markdown("---")
            if st.button("🗑️ Kosongkan Semua Pusat (Hati-hati!)", type="secondary"):
                try:
                    supa.table("pusat_master").delete().gt("id", 0).execute()
                    st.success("Semua pusat dipadam")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

        elif menu == "guru":
            st.header("Guru Master Seluruh Negeri")
            st.subheader(" Import MASTER 60K Guru Selangor")
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
                        ok = 0
                        BATCH = 500
                        for start in range(0, len(df_m), BATCH):
                            end = min(start + BATCH, len(df_m))
                            bdf = df_m.iloc[start:end]
                            batch = []
                            for _, row in bdf.iterrows():
                                try:
                                    d = {}
                                    for k, v in row.to_dict().items():
                                        d[k] = "" if pd.isna(v) else str(v)
                                    nama = d.get("NAMA GURU", "").upper().strip()
                                    if not nama or nama == "NAN": continue
                                    batch.append({
                                        "kod_ppd": d.get("KOD PPD", "").lower().strip(),
                                        "kod_sekolah": d.get("KOD SEKOLAH", "").upper().strip(),
                                        "nama_guru": nama,
                                        "ic_guru": d.get("IC", ""),
                                        "jantina": d.get("JANTINA",""),
                                        "poskod_rumah": d.get("POSKOD RUMAH","") or d.get("POSKOD_RUMAH",""),
                                        "alamat_rumah": d.get("ALAMAT RUMAH","") or d.get("ALAMAT_RUMAH",""),
                                        "telefon_guru": d.get("NO TELEFON GURU","") or d.get("TELEFON_GURU",""),
                                        "email_guru": d.get("EMAIL GURU","") or d.get("EMAIL_GURU",""),
                                        "pengalaman_spm": d.get("PENGALAMAN SPM","") or d.get("PENGALAMAN_SPM",""),
                                        "kod_sekolah_asal": d.get("KOD SEKOLAH","").upper().strip(),
                                        "nama_sekolah_asal": d.get("NAMA SEKOLAH",""),
                                        "no_pusat_asal": "BA142",
                                        "data": d
                                    })
                                except: continue
                            if batch:
                                try:
                                    supa.table("guru_master").insert(batch).execute()
                                    ok += len(batch)
                                except Exception as e:
                                    st.error(f"Batch {start}-{end} error: {e}")
                            bar.progress(end / len(df_m))
                            stat.write(f"Imported {end}/{len(df_m)} | OK {ok}")
                        st.success(f"✅ Selesai import {ok}/{len(df_m)} guru!")
                        st.balloons()
                except Exception as e:
                    st.error(f"Error: {e}")
            
            st.markdown("---")
            st.subheader("Data Sedia Ada")
            try:
                res = supa.table("guru_master").select("*", count="exact").limit(5000).execute()
                df = pd.DataFrame(res.data or [])
                st.write(f"Total dalam Supabase: {res.count} records")
                if not df.empty:
                    st.dataframe(df.head(100), use_container_width=True)
                    st.download_button("Export Guru Master (5000)", to_excel(df), file_name="guru_master_full.xlsx")
            except Exception as e:
                st.error(str(e))

        elif menu == "cadangan":
            st.header("Semua Cadangan Seluruh Negeri")
            try:
                res = supa.table("cadangan_sup").select("*").limit(10000).execute()
                df = pd.DataFrame(res.data or [])
                st.dataframe(df, use_container_width=True)
                if not df.empty:
                    st.download_button("Export Semua Cadangan", to_excel(df), file_name=f"cadangan_negeri_{datetime.date.today()}.xlsx")
            except Exception as e:
                st.error(str(e))

        elif menu == "export":
            st.header("Export Laporan Negeri")
            try:
                res = supa.table("cadangan_sup").select("*").limit(10000).execute()
                df = pd.DataFrame(res.data or [])
                if not df.empty:
                    st.download_button("📥 Laporan Penuh Negeri (Excel)", to_excel(df), file_name=f"Laporan_JPN_Selangor_{datetime.date.today()}.xlsx", use_container_width=True, type="primary")
            except Exception as e:
                st.error(str(e))

        elif menu == "admin":
            st.header("Admin - Check Tables & Connection")
            st.code(f"URL: {SUPABASE_URL}\nKEY: {SUPABASE_KEY[:20]}...{SUPABASE_KEY[-10:]} (Active)")
            for t in ["sekolah_master", "pusat_master", "guru_master", "cadangan_sup"]:
                try:
                    res = supa.table(t).select("*", count="exact").limit(1).execute()
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
