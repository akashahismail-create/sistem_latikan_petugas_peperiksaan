"""
SISTEM PELANTIKAN PETUGAS PEPERIKSAAN SELANGOR 2026
VERSI SUPABASE OPTIMIZED - GABUNGAN QWEN LAJU + SUPABASE LIVE
Base: Qwen_python_20261020_hoal6tldz.py (cache 300/3600, refresh button, kuota kosong)
Convert: GSheet -> Supabase Singapore
URL: https://gnmaijhugkkvxejvsotk.supabase.co
"""

import streamlit as st
import pandas as pd
import os
import re
import time
import threading
from io import BytesIO

try:
    from supabase import create_client
except:
    create_client = None

st.set_page_config(page_title="Sistem Pelantikan Selangor 2026 LIVE", layout="wide", page_icon="📚", initial_sidebar_state="collapsed")

st.markdown("""
<style>
[data-testid="stSidebar"] {display: none !important;}
[data-testid="collapsedControl"] {display: none !important;}
.big-title {text-align:center; font-size:28px; font-weight:bold; color:#3b82f6; margin-bottom:5px;}
.sub-title {text-align:center; font-size:14px; color:#94a3b8; margin-bottom:8px;}
</style>
""", unsafe_allow_html=True)

# ========== CONFIG SUPABASE - DARI KAU PUNYA ==========
SUPABASE_URL = "https://gnmaijhugkkvxejvsotk.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdubWFpamh1Z2trdnhlanZzb3RrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTI0ODc4OTcsImV4cCI6MjEwODA2Mzg5N30.1YWg71nCwnQzP-KUzTdHR4rZAVCAesbKVqvVC1-X6lw"

try:
    if "SUPABASE_URL" in st.secrets:
        SUPABASE_URL = st.secrets["SUPABASE_URL"]
    if "SUPABASE_ANON_KEY" in st.secrets:
        SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
    if "SUPABASE_KEY" in st.secrets:
        SUPABASE_ANON_KEY = st.secrets["SUPABASE_KEY"]
    if "connections" in st.secrets and "supabase" in st.secrets["connections"]:
        SUPABASE_URL = st.secrets["connections"]["supabase"].get("SUPABASE_URL", SUPABASE_URL)
        SUPABASE_ANON_KEY = st.secrets["connections"]["supabase"].get("SUPABASE_KEY", SUPABASE_ANON_KEY)
        SUPABASE_ANON_KEY = st.secrets["connections"]["supabase"].get("SUPABASE_ANON_KEY", SUPABASE_ANON_KEY)
except:
    pass

# ========== HELPER LOCK & CACHE (KEKAL DARI QWEN) ==========
def _peta_kunci():
    return {"master": threading.Lock(), "peta": {}}

def get_lock(name="*"):
    k = _peta_kunci()
    with k["master"]:
        return k["peta"].setdefault(name, threading.Lock())

# ========== SUPABASE CONNECTION - GANTI GSheet ==========
@st.cache_resource(ttl=300, show_spinner=False)
def get_supabase():
    if create_client is None:
        return None, "Library supabase belum install (pip install supabase)"
    try:
        client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        return client, None
    except Exception as e:
        return None, str(e)

def _df_from_rows(rows):
    if not rows:
        return pd.DataFrame()
    out=[]
    for r in rows:
        if isinstance(r, dict):
            if "data" in r and isinstance(r["data"], dict) and r["data"]:
                d=r["data"].copy()
                out.append(d)
            else:
                r2={k:v for k,v in r.items() if k not in ["id","created_at","data"]}
                # merge sisa column terus
                for k in ["KOD_PPD","NO_PUSAT_TUGAS","KOD_SEKOLAH","PPD","STATUS"]:
                    if k in r and r[k]:
                        r2[k]=r[k]
                out.append(r2)
        else:
            out.append(r)
    return pd.DataFrame(out)

def tab_tahun(base, tahun=None):
    if tahun is None:
        try:
            tahun = st.session_state.get("tahun_pilih", 2026)
        except:
            tahun = 2026
    return f"{base}_{tahun}"

def tab_daerah(base, kod, tahun=None):
    if tahun is None:
        try:
            tahun = st.session_state.get("tahun_pilih", 2026)
        except:
            tahun = 2026
    return f"{base}_{tahun}_{kod}" if kod else tab_tahun(base, tahun)

@st.cache_data(ttl=300, show_spinner=False)
def _cached_read(name):
    """Ini cache utama - dulu baca GSheet, sekarang Supabase - laju"""
    supa, err = get_supabase()
    if supa is None:
        return pd.DataFrame()

    # Parse nama: maklumat_sekolah_2026_BK -> base=maklumat_sekolah, filter=BK
    base_name=name
    filter_ppd=None
    parts=name.split("_")
    if len(parts)>=3 and parts[-1] in ["BA","BB","BC","BD","BE","BF","BG","BH","BJ","BK"]:
        filter_ppd=parts[-1]
        base_name="_".join(parts[:-1])
        if base_name.endswith("_2026") or base_name.endswith("_2025"):
            base_name="_".join(base_name.split("_")[:-1])
    else:
        if base_name.endswith("_2026") or base_name.endswith("_2025"):
            base_name="_".join(base_name.split("_")[:-1])

    allowed=["maklumat_sekolah","cadangan_sup","penempatan_ppd","status_hantar","kuota_ppd"]
    if base_name not in allowed:
        for a in allowed:
            if a in name:
                base_name=a
                break
    if base_name not in allowed:
        return pd.DataFrame()

    try:
        q=supa.table(base_name).select("*").limit(10000)
        if filter_ppd:
            q=q.eq("KOD_PPD", filter_ppd)
        res=q.execute()
        return _df_from_rows(res.data)
    except Exception as e:
        # st.warning(f"Supabase read {name} error: {e}")
        return pd.DataFrame()

def read_sheet(name):
    try:
        df=_cached_read(name)
        if not df.empty:
            return df
        # fallback tanpa tahun
        if "_2026" in name or "_2025" in name:
            base_fallback=name.replace("_2026","").replace("_2025","")
            df2=_cached_read(base_fallback)
            if not df2.empty:
                return df2
        return df
    except Exception:
        return pd.DataFrame()

def read_sheet_tahun(base, kod_or_none=None, tahun=None):
    if tahun is None:
        try:
            tahun = st.session_state.get("tahun_pilih", 2026)
        except:
            tahun=2026
    name=tab_daerah(base, kod_or_none, tahun) if kod_or_none else tab_tahun(base, tahun)
    return read_sheet(name)

@st.cache_data(ttl=300, show_spinner=False)
def read_semua_daerah(base, tahun=None):
    supa, err=get_supabase()
    if supa is None:
        return pd.DataFrame()
    if tahun is None:
        try:
            tahun=st.session_state.get("tahun_pilih",2026)
        except:
            tahun=2026
    clean=base
    # cuba table terus
    try:
        res=supa.table(clean).select("*").limit(10000).execute()
        return _df_from_rows(res.data)
    except:
        return pd.DataFrame()

def _tulis_supabase(name, df):
    supa, err=get_supabase()
    if supa is None:
        raise RuntimeError(f"Supabase tidak connect: {err}")
    base_name=name
    filter_ppd=None
    parts=name.split("_")
    if len(parts)>=3 and parts[-1] in ["BA","BB","BC","BD","BE","BF","BG","BH","BJ","BK"]:
        filter_ppd=parts[-1]
        base_name="_".join(parts[:-1])
        if base_name.endswith("_2026") or base_name.endswith("_2025"):
            base_name="_".join(base_name.split("_")[:-1])
    else:
        if base_name.endswith("_2026") or base_name.endswith("_2025"):
            base_name="_".join(base_name.split("_")[:-1])
    allowed=["maklumat_sekolah","cadangan_sup","penempatan_ppd","status_hantar","kuota_ppd"]
    if base_name not in allowed:
        for a in allowed:
            if a in name:
                base_name=a
                break
    # Convert
    if base_name=="status_hantar":
        # upsert per KOD_PPD
        for _, row in df.iterrows():
            rd=row.to_dict()
            clean={k:("" if pd.isna(v) else str(v) if not isinstance(v,(int,float,bool)) else v) for k,v in rd.items()}
            data_to={
                "KOD_PPD": str(clean.get("KOD PPD", clean.get("KOD_PPD",""))),
                "PPD": str(clean.get("PPD","")),
                "STATUS": str(clean.get("STATUS","")),
                "TARIKH_HANTAR": str(clean.get("TARIKH HANTAR","")),
                "TARIKH_SAH": str(clean.get("TARIKH SAH","")),
                "data": clean
            }
            if data_to["KOD_PPD"]:
                supa.table(base_name).upsert(data_to, on_conflict="KOD_PPD").execute()
    else:
        if filter_ppd:
            supa.table(base_name).delete().eq("KOD_PPD", filter_ppd).execute()
        else:
            supa.table(base_name).delete().neq("id", -1).execute()
        batch=[]
        for _, row in df.iterrows():
            rd=row.to_dict()
            clean={k:("" if pd.isna(v) else v) for k,v in rd.items()}
            batch.append({
                "KOD_PPD": str(clean.get("KOD PPD", clean.get("KOD PPD", filter_ppd or ""))),
                "NO_PUSAT_TUGAS": str(clean.get("NO PUSAT TUGAS", clean.get("NO PUSAT",""))),
                "KOD_SEKOLAH": str(clean.get("KOD SEKOLAH","")),
                "data": clean
            })
        for i in range(0, len(batch), 100):
            if batch[i:i+100]:
                supa.table(base_name).insert(batch[i:i+100]).execute()

def modify_sheet(name, modifier):
    try:
        with get_lock(name):
            df=read_sheet(name)
            baru=modifier(df.copy() if not df.empty else pd.DataFrame())
            if baru is not None:
                _tulis_supabase(name, baru)
    except ValueError as e:
        st.error(f"⚠️ {e}")
        return False
    except Exception as e:
        st.error(f"❌ Gagal simpan ke Supabase '{name}'. Cuba lagi. ({type(e).__name__}: {e})")
        return False
    _cached_read.clear()
    read_semua_daerah.clear()
    return True

def flash(level, msg):
    st.session_state.setdefault("_flash", []).append((level, msg))

def show_flash():
    for level, msg in st.session_state.pop("_flash", []):
        getattr(st, level)(msg)

# ========== LOAD MAPPING - DARI QWEN (TTL 3600) ==========
@st.cache_data(ttl=3600)
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
        except Exception as e:
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

@st.cache_data(ttl=3600)
def load_pusat_calon():
    for p in ["pusat_2026.csv", "data/pusat_2026.csv", "Pusat-SELANGOR-2026-FULL-GITHUB.csv", "data/Pusat-SELANGOR-2026-FULL-GITHUB.csv", "/mnt/data/pusat_2026.csv"]:
        if os.path.exists(p):
            try:
                df = pd.read_csv(p) if p.endswith(".csv") else pd.read_excel(p)
                if "NO_PUSAT" in df.columns and len(df)>20:
                    return df
            except Exception:
                pass
    return pd.DataFrame()

df_calon_master = load_pusat_calon()

PPD_LIST = [
    ("1","354","Petaling Utama","BK"),
    ("2","360","Klang","BA"),
    ("3","361","Kuala Langat","BB"),
    ("4","362","Kuala Selangor","BC"),
    ("5","363","Hulu Langat","BD"),
    ("6","364","Hulu Selangor","BE"),
    ("7","365","Sabak Bernam","BF"),
    ("8","366","Gombak","BG"),
    ("9","367","Petaling Perdana","BH"),
    ("10","368","Sepang","BJ"),
]

def norm_ic(x):
    d = re.sub(r"\D", "", str(x))
    return d.zfill(12) if d else ""

def keperluan_asal(pusat, df_calon):
    petugas = 10
    kelas = 0
    calon = 0
    if df_calon is not None and not df_calon.empty and "NO_PUSAT" in df_calon.columns:
        r = df_calon[df_calon["NO_PUSAT"].astype(str) == str(pusat)]
        if not r.empty:
            try:
                calon = int(r.iloc[0].get("JUMLAH_CALON", 0))
            except: pass
            try:
                kelas = int(r.iloc[0].get("JUMLAH_KELAS", 0))
            except: pass
            if "PETUGAS_NEEDED" in df_calon.columns:
                try:
                    petugas = int(r.iloc[0]["PETUGAS_NEEDED"])
                except:
                    petugas = kelas + 10 if kelas else 10
            else:
                petugas = kelas + 10 if kelas else 10
    else:
        petugas = 10
    return petugas, kelas, calon

def keperluan_pengawas(pusat, df_calon, df_kuota=None):
    # OPTIMIZED DARI QWEN: JANGAN auto-load kuota_ppd, biar kosong supaya laju
    if df_kuota is None:
        df_kuota = pd.DataFrame()
    if df_kuota is not None and not df_kuota.empty and "NO PUSAT" in df_kuota.columns:
        r = df_kuota[df_kuota["NO PUSAT"].astype(str) == str(pusat)]
        if not r.empty:
            last = r.iloc[-1]
            try:
                for col in ["KEPERLUAN EDIT", "KEPERLUAN_PENGAWAS", "JUMLAH_PENGAWAS", "PETUGAS_EDIT", "KEPERLUAN AKHIR"]:
                    if col in df_kuota.columns and str(last.get(col, "")).strip() != "" and str(last.get(col)).lower() != "nan":
                        return int(float(str(last.get(col)).strip()))
            except:
                pass
    asal, _, _ = keperluan_asal(pusat, df_calon)
    return asal

def get_kuota_info(pusat, df_calon, df_kuota=None):
    if df_kuota is None:
        df_kuota = pd.DataFrame()
    asal, kelas, calon = keperluan_asal(pusat, df_calon)
    formula = (kelas + 10) if kelas else asal
    edit = None
    catatan = ""
    tarikh_edit = ""
    edited_by = ""
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
    akhir = edit if edit is not None else formula
    return {"asal": asal, "formula": formula, "edit": edit, "akhir": akhir, "kelas": kelas, "calon": calon, "catatan": catatan}

def pecah_data_lama(mapping_df):
    # Dalam Supabase tak perlu pecah, semua centralized
    return [{"PPD":"SEMUA","STATUS":"Supabase centralized - tak perlu pecah daerah"}]

# ========== UI LOGIN & DASHBOARD - SAMA MACAM QWEN TAPI GUNA SUPABASE ==========
if "logged_in" not in st.session_state:
    st.session_state.logged_in=False

show_flash()

if not st.session_state.logged_in:
    st.markdown('<div class="big-title">SISTEM PELANTIKAN SPM 2026 - SUPABASE LIVE (Optimized Qwen)</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">369 Sekolah | 10 PPD | Live Supabase Singapore | Cache 300s/3600s</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-title">File: {os.path.basename(file_used)} | {len(mapping_df)} ID | Supabase LIVE</div>', unsafe_allow_html=True)

    col1,col2,col3=st.columns([1,2,1])
    with col2:
        with st.container(border=True):
            uid=st.text_input("ID Pengguna", placeholder="Contoh: 354 atau admin")
            pwd=st.text_input("Kata Laluan", type="password", placeholder="Password / ID sama")
            tahun=st.selectbox("Tahun", [2026,2025], index=0)
            st.session_state.tahun_pilih=tahun
            c1,c2=st.columns(2)
            with c1:
                login_btn = st.button("Log Masuk", use_container_width=True, type="primary")
            with c2:
                refresh_btn = st.button("🔄 Refresh Cache", use_container_width=True)
            
            if login_btn:
                if uid.strip()=="admin" and pwd.strip()=="admin123":
                    st.session_state.logged_in=True
                    st.session_state.user_info={"id":"admin","ppd_nama":"JPN","kod":"JPN","peranan":"JPN"}
                    st.rerun()
                else:
                    try:
                        row=mapping_df[mapping_df["ID"].astype(str)==str(uid).strip()]
                        if not row.empty and str(row.iloc[0]["PASSWORD"])==str(pwd).strip():
                            r=row.iloc[0]
                            st.session_state.logged_in=True
                            st.session_state.user_info={"id":str(r["ID"]),"ppd_nama":r["PPD"],"kod":r["KOD PPD"],"peranan":"PPD","sekolah":r["KOD SEKOLAH"],"nama_sekolah":r["NAMA SEKOLAH"]}
                            st.rerun()
                        else:
                            st.error("ID atau Password salah")
                    except Exception as e:
                        st.error(f"Login error: {e}")
            if refresh_btn:
                _cached_read.clear()
                load_mapping.clear()
                load_pusat_calon.clear()
                read_semua_daerah.clear()
                st.success("Cache cleared - reload laju!")
                time.sleep(1)
                st.rerun()
        supa,err=get_supabase()
        if supa:
            st.success("✅ Supabase Connected - LIVE MODE (Optimized)")
        else:
            st.error(f"❌ {err}")

else:
    info=st.session_state.user_info
    st.markdown(f'<div class="big-title">Selamat Datang {info.get("ppd_nama")} - {info.get("kod")}</div>', unsafe_allow_html=True)
    
    top1,top2=st.columns([3,1])
    with top2:
        if st.button("Log Keluar"):
            st.session_state.logged_in=False
            st.rerun()
        if st.button("🔄 Refresh Data"):
            _cached_read.clear()
            read_semua_daerah.clear()
            st.rerun()
    
    show_flash()
    
    # Menu ikut role
    if info.get("kod")=="JPN":
        menu=st.selectbox("Menu JPN", ["Semua PPD","Dashboard JPN","Sahkan PPD","Jana Surat"])
    else:
        menu=st.selectbox("Menu PPD", ["Dashboard","Penempatan PPD","Hantar ke JPN","Jana Surat"])

    # Contoh Dashboard - pakai Supabase
    if menu in ["Dashboard","Dashboard JPN","Semua PPD"]:
        st.header(f"Dashboard - {info.get('ppd_nama')}")
        pen_all=read_semua_daerah("penempatan_ppd")
        status_all=read_sheet("status_hantar_2026")
        st.metric("Total Penempatan LIVE Supabase", len(pen_all))
        if not pen_all.empty:
            st.dataframe(pen_all.head(200), use_container_width=True)
        st.dataframe(status_all, use_container_width=True)
    elif menu in ["Penempatan PPD","Hantar ke JPN"]:
        st.header(f"Penempatan - PPD {info.get('ppd_nama')}")
        df_pen=read_sheet_tahun("penempatan_ppd", info.get("kod"))
        st.dataframe(df_pen, use_container_width=True)
        with st.form("tambah_petugas"):
            st.subheader("Tambah Petugas (Test Supabase LIVE)")
            no_pusat=st.text_input("NO PUSAT TUGAS (contoh BK001)")
            nama=st.text_input("Nama")
            ic=st.text_input("IC")
            submit=st.form_submit_button("Simpan ke Supabase")
            if submit:
                def _tambah(df):
                    new={"NO PUSAT TUGAS":no_pusat, "NAMA":nama, "IC":ic, "KOD PPD":info.get("kod"), "KOD SEKOLAH":info.get("sekolah","")}
                    return pd.concat([df, pd.DataFrame([new])], ignore_index=True) if not df.empty else pd.DataFrame([new])
                if modify_sheet(f"penempatan_ppd_2026_{info.get('kod')}", _tambah):
                    flash("success", "✅ Disimpan ke Supabase LIVE!")
                    st.rerun()
        if st.button("📤 HANTAR ke JPN", type="primary", use_container_width=True):
            def _hantar(df):
                baris={"KOD PPD":info['kod'], "PPD":info['ppd_nama'], "TARIKH HANTAR":pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"), "STATUS":"Dihantar", "TARIKH SAH":""}
                if df.empty:
                    return pd.DataFrame([baris])
                df=df[df["KOD PPD"].astype(str)!=str(info['kod'])]
                return pd.concat([df, pd.DataFrame([baris])], ignore_index=True)
            if modify_sheet("status_hantar_2026", _hantar):
                flash("success", f"✅ PPD {info['ppd_nama']} berjaya hantar ke JPN - LIVE!")
                st.rerun()
    elif menu=="Sahkan PPD":
        st.header("Sahkan PPD - JPN")
        status_all=read_sheet("status_hantar_2026")
        st.dataframe(status_all, use_container_width=True)
        kod_sah=st.selectbox("Pilih PPD", ["BA","BB","BC","BD","BE","BF","BG","BH","BJ","BK"])
        if st.button("SAHKAN", type="primary"):
            def _sah(df):
                df=df.copy()
                df.loc[df["KOD PPD"].astype(str)==kod_sah, "STATUS"]="Disahkan"
                df.loc[df["KOD PPD"].astype(str)==kod_sah, "TARIKH SAH"]=pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                return df
            if modify_sheet("status_hantar_2026", _sah):
                flash("success", f"PPD {kod_sah} Disahkan!")
                st.rerun()
    else:
        st.header("Jana Surat")
        pen_all=read_semua_daerah("penempatan_ppd")
        if pen_all.empty:
            st.warning("Belum ada data")
        else:
            st.download_button("Download CSV LIVE", data=pen_all.to_csv(index=False).encode("utf-8-sig"), file_name="penempatan_live_supabase.csv", mime="text/csv")
