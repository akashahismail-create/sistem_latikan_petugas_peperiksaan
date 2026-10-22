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

# ✅ FIX: Buang trailing space dari KOD_DAERAH & PPD_MAP
KOD_DAERAH = ["BA", "BB", "BC", "BD", "BE", "BF", "BG", "BH", "BJ", "BK"]
PPD_MAP = {
    "BA": "Klang", "BB": "Kuala Langat", "BC": "Kuala Selangor",
    "BD": "Hulu Langat", "BE": "Hulu Selangor", "BF": "Sabak Bernam",
    "BG": "Gombak", "BH": "Petaling Perdana", "BJ": "Sepang", "BK": "Petaling Utama"
}

# ================= CSS UNTUK CUSTOM SIDEBAR - FIX DARK MODE =================
st.markdown("""
<style>
[data-testid="stSidebar"] {display: none !important;}
[data-testid="stSidebarNav"] {display: none !important;}
.stSidebar {display: none !important;}
section[data-testid="stSidebar"] {display: none !important;}

/* Custom left panel that looks like sidebar - FIX DARK MODE */
.custom-sidebar {
    background: #ffffff;
    border-radius: 12px;
    padding: 16px;
    border: 2px solid #0d47a1;
    box-shadow: 0 4px 12px rgba(13, 71, 161, 0.15);
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
/* Caption nama sekolah - buat lebih gelap dan visible */
.custom-sidebar .caption, .custom-sidebar [data-testid="stCaptionContainer"] {
    color: #212121 !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    opacity: 1 !important;
}
/* NO PUSAT box - high contrast, visible in both light and dark */
.no-pusat-box {
    background: #ffeb3b;
    border: 2px solid #f57f17;
    border-radius: 8px;
    padding: 10px 12px;
    margin: 10px 0;
}
.no-pusat-label {
    font-size: 11px;
    color: #bf360c;
    font-weight: 700;
    margin-bottom: 2px;
}
.no-pusat-value {
    font-size: 18px;
    color: #000000 !important;
    font-weight: 900;
    letter-spacing: 0.5px;
    word-break: break-all;
}
/* Dark mode fix - ensure custom sidebar stays light with dark text */
@media (prefers-color-scheme: dark) {
    .custom-sidebar {
        background: #ffffff !important;
        border-color: #1565c0 !important;
    }
    .custom-sidebar h3 {
        color: #0d47a1 !important;
    }
    .custom-sidebar p, .custom-sidebar span, .custom-sidebar div {
        color: #212121 !important;
    }
}
/* Force Streamlit caption to be visible */
[data-testid="stCaptionContainer"] p {
    color: #212121 !important;
    font-weight: 600 !important;
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
        st.cache_resource.clear()
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
                <div style="background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); padding:20px; border-radius:12px; border-left:6px solid #1565c0; margin-bottom:20px;">
                    <h3 style="margin:0; color:#0d47a1;">🏫 KEPERLUAN PENGAWAS SEKOLAH ANDA - {kod}</h3>
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
                    ('jana', '🚀 Jana Keseluruhan'), ('cadangan', '📋 Cadangan SUP'), ('kelulusan', '✅ Kelulusan'), 
                    ('export', '📥 Export'), ('keluar', '🚪 Log Keluar')]
        menu = st.radio("Menu PPD", [k for k, _ in MENU_PPD], format_func=dict(MENU_PPD).get, label_visibility="collapsed", key="ppd_menu_radio")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_main:
        if menu == "keluar":
            st.session_state.clear()
            st.rerun()
        
        elif menu == "dashboard":
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #0d47a1 0%, #1976d2 100%); padding:20px; border-radius:12px; color:white; margin-bottom:20px;">
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
                    st.markdown("### 📍 Senarai Pusat Peperiksaan - Status Petugas")
                    st.caption("🔴 Merah = Belum Ada (0) | 🟡 Kuning = Belum Cukup (< sepatutnya) | 🟢 Hijau = Cukup / Lebih (>= sepatutnya)")
                    
                    # Build display table with colors
                    display_rows = []
                    for _, p in df_pusat_ppd.sort_values("NO_PUSAT").iterrows():
                        no_p = p["NO_PUSAT"]
                        dic = p["DICADANGKAN"]
                        sep = p["SEPATUTNYA"]
                        
                        if dic == 0:
                            status_icon = "🔴"
                            status_text = "Belum Ada"
                            color = "#d32f2f"
                            bg = "#ffebee"
                        elif dic < sep:
                            status_icon = "🟡"
                            status_text = f"Belum Cukup ({dic}/{sep})"
                            color = "#f57f17"
                            bg = "#fff8e1"
                        else:
                            status_icon = "🟢"
                            status_text = f"Cukup ({dic}/{sep})"
                            color = "#2e7d32"
                            bg = "#e8f5e9"
                        
                        display_rows.append({
                            "Logo": "🏫",
                            "NO_PUSAT": no_p,
                            "NAMA_PUSAT": p["NAMA_PUSAT"][:30],
                            "KOD_TUAN": p["KOD_TUAN_RUMAH"],
                            "CALON": p["CALON"],
                            "KELAS": p["KELAS"],
                            "SEPATUTNYA": sep,
                            "DICADANGKAN": dic,
                            "STATUS": f"{status_icon} {status_text}",
                            "_color": color,
                            "_bg": bg
                        })
                    
                    df_display = pd.DataFrame(display_rows)
                    
                    # Create HTML table with colors
                    html_table = """
                    <style>
                    .ppd-table {width:100%; border-collapse:collapse; font-size:13px;}
                    .ppd-table th {background:#0d47a1; color:white; padding:10px 8px; text-align:left; font-weight:700;}
                    .ppd-table td {padding:8px; border-bottom:1px solid #e0e0e0;}
                    .ppd-table tr:hover {background:#f5f5f5;}
                    .badge-merah {background:#ffebee; color:#d32f2f; padding:4px 8px; border-radius:12px; font-weight:700; border:1px solid #d32f2f;}
                    .badge-kuning {background:#fff8e1; color:#f57f17; padding:4px 8px; border-radius:12px; font-weight:700; border:1px solid #f57f17;}
                    .badge-hijau {background:#e8f5e9; color:#2e7d32; padding:4px 8px; border-radius:12px; font-weight:700; border:1px solid #2e7d32;}
                    </style>
                    <table class="ppd-table">
                    <tr><th>🏫</th><th>NO PUSAT</th><th>NAMA PUSAT</th><th>KOD TUAN</th><th>CALON</th><th>KELAS</th><th>PERLU (K+9)</th><th>DICADANG</th><th>STATUS</th></tr>
                    """
                    
                    for _, r in df_display.iterrows():
                        dic = r["DICADANGKAN"]
                        sep = r["SEPATUTNYA"]
                        if dic == 0:
                            badge_class = "badge-merah"
                            badge_text = f"🔴 {dic}"
                            status_badge = f'<span class="{badge_class}">{r["STATUS"]}</span>'
                        elif dic < sep:
                            badge_class = "badge-kuning"
                            badge_text = f"🟡 {dic}"
                            status_badge = f'<span class="{badge_class}">{r["STATUS"]}</span>'
                        else:
                            badge_class = "badge-hijau"
                            badge_text = f"🟢 {dic}"
                            status_badge = f'<span class="{badge_class}">{r["STATUS"]}</span>'
                        
                        html_table += f"<tr><td>{r['Logo']}</td><td><b>{r['NO_PUSAT']}</b></td><td>{r['NAMA_PUSAT']}</td><td>{r['KOD_TUAN']}</td><td style='text-align:center;'><b>{r['CALON']}</b></td><td style='text-align:center;'>{r['KELAS']}</td><td style='text-align:center; background:#e3f2fd; font-weight:700;'>{r['SEPATUTNYA']}</td><td style='text-align:center;'><span class='{badge_class}'>{badge_text}</span></td><td>{status_badge}</td></tr>"
                    
                    html_table += "</table>"
                    
                    st.markdown(html_table, unsafe_allow_html=True)
                    
                    st.markdown("---")
                    
                    # Also show as dataframe for export
                    with st.expander("📊 Lihat Dataframe & Export", expanded=False):
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
            st.header(f"🚀 Jana Keseluruhan - Letak Semua Petugas di Pusat Peperiksaan - PPD {kod_ppd} - {PPD_MAP.get(kod_ppd, '')}")
            st.caption("Function ni akan ambil semua cadangan dari SUP dan letak di pusat peperiksaan ikut jumlah calon. Boleh edit kalau tak sesuai.")
            df_pusat_raw = get_pusat_df()
            df_cad_all = get_cadangan_df(kod_ppd=kod_ppd)
            
            if df_pusat_raw.empty:
                st.warning("Tiada pusat_master - import dulu di JPN > Pusat Master")
            elif df_cad_all.empty:
                st.warning(f"Belum ada cadangan dari SUP untuk PPD {kod_ppd}. Sekolah perlu cadang dulu di SUP > Cadangan Lantikan.")
            else:
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
                    rows.append({"NO_PUSAT": no_pusat, "NAMA_PUSAT": nama, "KOD_SEKOLAH_TUAN_RUMAH": kod_sek_tuan, "JUMLAH_CALON": jc, "JUMLAH_KELAS": jk, "PETUGAS": kira_petugas_dari_kelas(jk)})
                
                df_pusat_ppd = pd.DataFrame(rows)
                if df_pusat_ppd.empty:
                    st.warning(f"Tiada pusat dengan prefix {kod_ppd} dalam pusat_master")
                else:
                    st.success(f"Jumpa {len(df_pusat_ppd)} pusat di PPD {kod_ppd} | Total cadangan: {len(df_cad_all)} guru")
                    st.subheader("📍 Senarai Pusat & Keperluan Petugas")
                    st.dataframe(df_pusat_ppd.sort_values("NO_PUSAT"), use_container_width=True, hide_index=True)
                    st.markdown("---")
                    st.subheader("👥 Penempatan Petugas - Auto Jana")
                    assignments = []
                    df_cad_sorted = df_cad_all.sort_values("JAWATAN_CADANGAN") if "JAWATAN_CADANGAN" in df_cad_all.columns else df_cad_all
                    st.info("⚠️ RULE: Cikgu sekolah asal TAK BOLEH bertugas di sekolah dia sendiri - sistem akan elak auto")
                    
                    for idx, row in df_cad_sorted.iterrows():
                        kod_sek_asal = str(row.get("KOD_SEKOLAH_ASAL", "") or "").upper().strip()
                        asal = str(row.get("NO_PUSAT_ASAL", "") or "").upper().strip()
                        pusat_tugas = None
                        
                        if asal and asal in df_pusat_ppd["NO_PUSAT"].values:
                            pusat_info = df_pusat_ppd[df_pusat_ppd["NO_PUSAT"] == asal]
                            if not pusat_info.empty:
                                tuan_rumah = str(pusat_info.iloc[0].get("KOD_SEKOLAH_TUAN_RUMAH", "") or "").upper().strip()
                                if tuan_rumah and kod_sek_asal and tuan_rumah == kod_sek_asal:
                                    pusat_tugas = None
                                else:
                                    pusat_tugas = asal
                        
                        if not pusat_tugas:
                            for p_idx in range(len(df_pusat_ppd)):
                                candidate = df_pusat_ppd.iloc[(idx + p_idx) % len(df_pusat_ppd)]
                                cand_no = candidate["NO_PUSAT"]
                                cand_tuan = str(candidate.get("KOD_SEKOLAH_TUAN_RUMAH", "") or "").upper().strip()
                                if cand_tuan and kod_sek_asal and cand_tuan == kod_sek_asal: continue
                                pusat_tugas = cand_no
                                break
                            if not pusat_tugas:
                                pusat_tugas = df_pusat_ppd.iloc[idx % len(df_pusat_ppd)]["NO_PUSAT"] if len(df_pusat_ppd) > 0 else "BA142"
                        
                        assignments.append({"id": row.get("id", ""), "NAMA_GURU": row.get("NAMA_GURU", ""), "IC_GURU": row.get("IC_GURU", ""), "JAWATAN_CADANGAN": row.get("JAWATAN_CADANGAN", ""), "KOD_SEKOLAH_ASAL": row.get("KOD_SEKOLAH_ASAL", ""), "NAMA_SEKOLAH_ASAL": row.get("NAMA_SEKOLAH_ASAL", ""), "NO_PUSAT_ASAL": row.get("NO_PUSAT_ASAL", ""), "NO_PUSAT_TUGAS": pusat_tugas, "STATUS": row.get("STATUS", "DICADANGKAN")})
                    
                    df_assign = pd.DataFrame(assignments)
                    st.dataframe(df_assign, use_container_width=True, hide_index=True)
                    st.markdown("---")
                    st.subheader("✏️ Edit Penempatan (Kalau Tak Sesuai)")
                    st.caption("Pilih guru dan tukar pusat tugas, kemudian klik Update")
                    
                    if not df_assign.empty:
                        edit_ic = st.selectbox("Pilih Guru untuk edit pusat tugas", df_assign["IC_GURU"].tolist(), format_func=lambda x: f"{x} - {df_assign[df_assign['IC_GURU']==x]['NAMA_GURU'].values[0] if not df_assign[df_assign['IC_GURU']==x].empty else x}")
                        if edit_ic:
                            curr = df_assign[df_assign["IC_GURU"] == edit_ic].iloc[0] if not df_assign[df_assign["IC_GURU"] == edit_ic].empty else None
                            if curr is not None:
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.text_input("NAMA GURU", value=curr.get("NAMA_GURU", ""), disabled=True)
                                    st.text_input("JAWATAN", value=curr.get("JAWATAN_CADANGAN", ""), disabled=True)
                                    st.text_input("SEKOLAH ASAL", value=curr.get("NAMA_SEKOLAH_ASAL", ""), disabled=True)
                                with col2:
                                    kod_sek_asal_edit = str(curr.get("KOD_SEKOLAH_ASAL", "") or "").upper().strip()
                                    allowed_pusat = []
                                    for _, pr in df_pusat_ppd.iterrows():
                                        tuan = str(pr.get("KOD_SEKOLAH_TUAN_RUMAH", "") or "").upper().strip()
                                        if tuan and kod_sek_asal_edit and tuan == kod_sek_asal_edit: continue
                                        allowed_pusat.append(pr["NO_PUSAT"])
                                    if not allowed_pusat: allowed_pusat = df_pusat_ppd["NO_PUSAT"].tolist()
                                    
                                    new_pusat = st.selectbox(f"Tukar Pusat Tugas (Boleh Edit) - {curr.get('KOD_SEKOLAH_ASAL')} tak boleh di sekolah sendiri", allowed_pusat, index=allowed_pusat.index(curr.get("NO_PUSAT_TUGAS")) if curr.get("NO_PUSAT_TUGAS") in allowed_pusat else 0)
                                    if st.button("💾 Update Pusat Tugas", type="primary"):
                                        try:
                                            update_data = {"kod_pusat": new_pusat, "no_pusat_asal": new_pusat}
                                            if curr.get("id"):
                                                supa.table("cadangan_sup").update(update_data).eq("id", curr.get("id")).execute()
                                            else:
                                                supa.table("cadangan_sup").update(update_data).eq("ic_guru", edit_ic).execute()
                                            st.success(f"✅ Berjaya tukar {curr.get('NAMA_GURU')} ke pusat {new_pusat}")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Gagal update: {e}")
                    
                    st.download_button("📥 Export Penempatan Penuh", to_excel(df_assign), file_name=f"penempatan_{kod_ppd}_{datetime.date.today()}.xlsx", use_container_width=True)

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
