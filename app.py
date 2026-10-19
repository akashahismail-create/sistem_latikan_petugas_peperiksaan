"""
SISTEM PELANTIKAN PETUGAS PEPERIKSAAN SELANGOR 2026
FIX FINAL - Baca apa saja nama file ID DAERAH, tak kisah - atau _ , besar kecil huruf
Total 369 sekolah
"""

import streamlit as st
import pandas as pd
import os
import glob
import re
import time
import threading

try:
    import gspread
    from google.oauth2.service_account import Credentials
except Exception:  # library belum dipasang - app tetap boleh buka
    gspread = None
    Credentials = None

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

@st.cache_data
def load_mapping():
    # Cara baru: scan semua file dalam data/ yang ada ID dan DAERAH, tak kisah nama
    data_folder = "data"
    candidates = []
    if os.path.exists(data_folder):
        for f in os.listdir(data_folder):
            low = f.lower()
            if "id" in low and "daerah" in low and (low.endswith(".xlsx") or low.endswith(".csv")):
                candidates.append(os.path.join(data_folder, f))
    
    # Cuba baca semua candidate, ambil yang paling banyak row
    best_df = pd.DataFrame()
    best_file = ""
    for path in candidates:
        try:
            if path.endswith(".xlsx"):
                df = pd.read_excel(path)
            else:
                df = pd.read_csv(path)
            # Check ada column PPD
            if "PPD" in df.columns and len(df) > len(best_df):
                best_df = df
                best_file = path
        except Exception as e:
            continue
    
    if not best_df.empty and len(best_df) > 10:
        return best_df, best_file
    
    # Fallback: cuba nama standard
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
    
    # Last fallback: generate dari master 506
    try:
        master_path = None
        for p in ["data/senarai_506_PLUS_calon2026_FINAL.xlsx", "data/senarai_506_PLUS_calon2026_FINAL.xlsx".lower(), "/mnt/data/senarai_506_PLUS_calon2026_FINAL.xlsx"]:
            # case insensitive search
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
                if "NO_PUSAT" in df.columns and len(df)>20:
                    return df
            except Exception:
                pass
    return pd.DataFrame()

df_calon_master = load_pusat_calon()

# ====== HELPER GSHEET & PENEMPATAN (mula) ======
GS_SPREADSHEET_ID_DEFAULT = "1dweem4yw6nKlo1wy5PA264prHEHpLoBPSu89jRFi484"


@st.cache_resource(ttl=300, show_spinner=False)
def get_gsheet():
    """Sambung ke Google Sheet sekali sahaja. Pulang (client, spreadsheet_id, ralat)."""
    if gspread is None:
        return None, None, "Library gspread/google-auth belum dipasang (pip install gspread google-auth)"
    try:
        try:
            sid = st.secrets["SPREADSHEET_ID"]
        except Exception:
            try:
                sid = st.secrets["connections"]["gsheets"]["spreadsheet"].split("/d/")[1].split("/")[0]
            except Exception:
                sid = GS_SPREADSHEET_ID_DEFAULT
        creds_dict = dict(st.secrets["gcp_service_account"])
        pk = creds_dict.get("private_key", "")
        if "\\n" in pk:
            creds_dict["private_key"] = pk.replace("\\n", "\n")
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds), sid, None
    except Exception as e:
        return None, None, str(e)


@st.cache_resource(show_spinner=False)
def get_lock():
    """Satu kunci untuk semua pengguna - elak 2 orang tulis serentak (baca-ubah-tulis)."""
    return threading.Lock()


def _retry(fn, tries=3):
    """Cuba semula bila Google beri ralat sementara (kuota / rangkaian)."""
    for i in range(tries):
        try:
            return fn()
        except gspread.exceptions.APIError:
            if i == tries - 1:
                raise
            time.sleep(1.5 * (i + 1))


def read_sheet_strict(name):
    """Baca sheet. Kalau GAGAL -> timbul ralat (JANGAN pulang kosong). Sheet tak wujud -> DataFrame kosong."""
    client, sid, err = get_gsheet()
    if client is None:
        raise RuntimeError(f"Google Sheet tidak connect: {err}")
    sh = _retry(lambda: client.open_by_key(sid))
    try:
        ws = sh.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        return pd.DataFrame()
    records = _retry(lambda: ws.get_all_records(numericise_ignore=["all"]))
    return pd.DataFrame(records)


@st.cache_data(ttl=15, show_spinner=False)
def _cached_read(name):
    return read_sheet_strict(name)


def read_sheet(name):
    """Untuk PAPARAN sahaja (cache 15 saat, kurangkan kuota Google). Jangan guna untuk simpan data."""
    client, _, _ = get_gsheet()
    if client is None:
        return pd.DataFrame()
    try:
        return _cached_read(name)
    except Exception as e:
        st.warning(f"⚠️ Gagal baca sheet '{name}' ({type(e).__name__}). Data di bawah mungkin tidak lengkap - cuba muat semula sebentar lagi.")
        return pd.DataFrame()


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


def _tulis_sheet(name, df):
    """Tulis df ke sheet TANPA clear dulu: tulis data baru, baru buang baki baris lebihan."""
    if len(df.columns) == 0:
        return
    client, sid, err = get_gsheet()
    if client is None:
        raise RuntimeError(f"Google Sheet tidak connect: {err}")
    sh = _retry(lambda: client.open_by_key(sid))
    try:
        ws = sh.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=name, rows=1000, cols=30)
    values = [[str(c) for c in df.columns]] + [[_cell(v) for v in row] for row in df.itertuples(index=False, name=None)]
    n_rows, n_cols = len(values), len(values[0])
    if ws.row_count < n_rows:
        ws.add_rows(n_rows - ws.row_count + 100)
    if ws.col_count < n_cols:
        ws.add_cols(n_cols - ws.col_count)
    _retry(lambda: ws.update(values=values, range_name="A1"))
    if ws.row_count > n_rows:
        akhir = gspread.utils.rowcol_to_a1(ws.row_count, ws.col_count)
        _retry(lambda: ws.batch_clear([f"A{n_rows + 1}:{akhir}"]))


def modify_sheet(name, modifier):
    """Cara SELAMAT ubah data: baca segar -> modifier(df) -> tulis, dalam satu kunci.
    - Kalau bacaan gagal, TIADA apa ditulis (data lama selamat).
    - modifier boleh `raise ValueError("mesej")` untuk batalkan; pulang None = tiada perubahan.
    Pulang True kalau berjaya."""
    try:
        with get_lock():
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
    """Simpan mesej supaya masih nampak selepas st.rerun()."""
    st.session_state.setdefault("_flash", []).append((level, msg))


def show_flash():
    for level, msg in st.session_state.pop("_flash", []):
        getattr(st, level)(msg)


def norm_ic(x):
    """Samakan format IC (buang '-', tambah sifar depan) supaya perbandingan tepat."""
    d = re.sub(r"\D", "", str(x))
    return d.zfill(12) if d else ""


def keperluan_pengawas(pusat, df_calon):
    """Bilangan Pengawas Peperiksaan untuk satu pusat (default 10). KP + TKP ditambah berasingan."""
    if df_calon is not None and not df_calon.empty and "NO_PUSAT" in df_calon.columns and "PETUGAS_NEEDED" in df_calon.columns:
        r = df_calon[df_calon["NO_PUSAT"].astype(str) == str(pusat)]
        if not r.empty:
            try:
                return int(r.iloc[0]["PETUGAS_NEEDED"])
            except (ValueError, TypeError):
                pass
    return 10


def jawatan_kosong(need_peng, jawatan_sedia):
    """Jawatan yang masih kosong: 1 Ketua + 1 Timbalan + need_peng Pengawas."""
    sasaran = {"Ketua Pengawas": 1, "Timbalan Ketua Pengawas": 1, "Pengawas Peperiksaan": need_peng}
    sedia = [str(j).strip() for j in jawatan_sedia]
    hasil = []
    for jaw, bil in sasaran.items():
        hasil += [jaw] * max(0, bil - sedia.count(jaw))
    return hasil


def jana_penempatan(pusat_list, penempatan_df, cadangan_df, pusat_to_sekolah, pusat_to_nama, df_calon, label_status):
    """Satu logik untuk jana 1 pusat ATAU semua pusat.
    Peraturan: guru sekolah tuan rumah tak boleh jaga pusat sendiri; seorang guru HANYA satu pusat
    (tiada guru diulang). Kalau calon tak cukup, jawatan dibiarkan kosong & dilaporkan.
    Pulang (baris_baru, senarai_kurang[(pusat, bil_kurang)])."""
    ada_pen = (not penempatan_df.empty) and ("NO PUSAT TUGAS" in penempatan_df.columns)
    used_ic = set()
    if (not penempatan_df.empty) and "IC" in penempatan_df.columns:
        used_ic = {i for i in penempatan_df["IC"].map(norm_ic) if i}

    cad = cadangan_df.copy()
    cad["_IC"] = cad["IC"].map(norm_ic)
    cad = cad[cad["_IC"] != ""].drop_duplicates(subset="_IC")

    rows, kurang = [], []
    for p in pusat_list:
        p = str(p)
        kod_sek = str(pusat_to_sekolah.get(p, ""))
        need_peng = keperluan_pengawas(p, df_calon)
        sedia = []
        if ada_pen and "JAWATAN FINAL" in penempatan_df.columns:
            sedia = penempatan_df[penempatan_df["NO PUSAT TUGAS"].astype(str) == p]["JAWATAN FINAL"].tolist()
        perlu = jawatan_kosong(need_peng, sedia)
        if not perlu:
            continue
        calon = cad[(cad["KOD SEKOLAH ASAL"].astype(str) != kod_sek) & (~cad["_IC"].isin(used_ic))].head(len(perlu))
        if len(calon) < len(perlu):
            kurang.append((p, len(perlu) - len(calon)))
        for jaw, (_, guru) in zip(perlu, calon.iterrows()):
            rows.append({
                "NO PUSAT TUGAS": p,
                "NAMA PUSAT TUGAS": pusat_to_nama.get(p, p),
                "KOD SEKOLAH ASAL GURU": guru.get("KOD SEKOLAH ASAL", ""),
                "NAMA SEKOLAH ASAL": guru.get("NAMA SEKOLAH ASAL", ""),
                "NAMA GURU": guru.get("NAMA GURU", ""),
                "IC": guru.get("IC", ""),
                "JANTINA": guru.get("JANTINA", ""),
                "JAWATAN FINAL": jaw,
                "POSKOD RUMAH": guru.get("POSKOD RUMAH", ""),
                "ALAMAT RUMAH": guru.get("ALAMAT RUMAH", ""),
                "NO TELEFON GURU": guru.get("NO TELEFON GURU", ""),
                "EMAIL GURU": guru.get("EMAIL GURU", ""),
                "STATUS PENEMPATAN": label_status,
            })
            used_ic.add(guru["_IC"])
    return rows, kurang
# ====== HELPER GSHEET & PENEMPATAN (tamat) ======


# Debug info
# st.sidebar.write(f"File guna: {file_used}, total {len(mapping_df)}")

PPD_LIST = [
    ("1", "a", "Klang", "BA"), ("2", "b", "Kuala Langat", "BB"),
    ("3", "c", "Kuala Selangor", "BC"), ("4", "d", "Hulu Langat", "BD"),
    ("5", "e", "Hulu Selangor", "BE"), ("6", "f", "Sabak Bernam", "BF"),
    ("7", "g", "Gombak", "BG"), ("8", "h", "Petaling Perdana", "BH"),
    ("9", "i", "Sepang", "BJ"), ("10", "j", "Petaling Utama", "BK"),
]
PPD_USERS = {f"{nama}": {"id": id_, "password": pwd, "nama": f"PPD {nama}", "ppd_nama": nama, "kod": kod} for id_, pwd, nama, kod in PPD_LIST}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown('<div class="big-title">📚 SISTEM PELANTIKAN PETUGAS PEPERIKSAAN</div>', unsafe_allow_html=True)
    st.markdown('<div class="big-title" style="font-size:22px;">SELANGOR 2026</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-title">{len(mapping_df)} Sekolah Termasuk Persendirian • File: {os.path.basename(file_used)}<br>SPM Bertulis • Amali Sains • Mendengar • Bertutur</div>', unsafe_allow_html=True)

    # Debug visible
    with st.expander(f"🔍 Debug Data - File guna: {file_used} - {len(mapping_df)} sekolah", expanded=False):
        st.write(f"File yang dibaca: {file_used}")
        st.write(f"Jumlah sekolah: {len(mapping_df)}")
        if not mapping_df.empty:
            st.write("Daerah yang ada:", mapping_df["PPD"].value_counts().to_dict())
            st.dataframe(mapping_df.head(10))

    left, center, right = st.columns([1,2,1])
    with center:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown("### 🔐 Log Masuk")
        
        peranan = st.selectbox("1️⃣ Pilih Peranan", ["-- Pilih --", "JPN Selangor", "PPD", "SUP Sekolah"])
        
        if peranan == "JPN Selangor":
            st.info("JPN: ID 1 Password a")
            jpn_pwd = st.text_input("Kata Laluan JPN", type="password", placeholder="a")
            if st.button("🚀 Log Masuk JPN", use_container_width=True, type="primary"):
                if jpn_pwd=="a":
                    st.session_state.logged_in=True
                    st.session_state.user_role="JPN"
                    st.session_state.user_info={"nama":"JPN Selangor","role":"JPN","id":"1"}
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
                        st.session_state.logged_in=True
                        st.session_state.user_role="PPD"
                        st.session_state.user_info={"nama":f"PPD {ppd_daerah}","ppd_nama":ppd_daerah,"kod":ppd_info['kod'],"password":ppd_info['password'],"id":ppd_info['id'],"role":"PPD"}
                        st.rerun()
                    else:
                        st.error("Password salah")
        
        elif peranan == "SUP Sekolah":
            st.markdown("#### 2️⃣ Pilih Daerah")
            order_daerah = ["Klang","Kuala Langat","Kuala Selangor","Hulu Langat","Hulu Selangor","Sabak Bernam","Gombak","Petaling Perdana","Sepang","Petaling Utama"]
            # Guna yang ada dalam file, tapi ikut order
            if not mapping_df.empty:
                daerah_ada = mapping_df["PPD"].unique().tolist()
                daerah_list = [d for d in order_daerah if d in daerah_ada]
            else:
                daerah_list = order_daerah
            
            sup_daerah = st.selectbox("Daerah Sekolah Anda", ["-- Pilih Daerah --"] + daerah_list)
            
            if sup_daerah != "-- Pilih Daerah --":
                df_daerah = mapping_df[mapping_df["PPD"]==sup_daerah].sort_values("NAMA SEKOLAH") if not mapping_df.empty else pd.DataFrame()
                st.markdown(f"#### 3️⃣ Pilih Sekolah di {sup_daerah} ({len(df_daerah)} sekolah)")
                if len(df_daerah)==0:
                    st.warning("Senarai kosong! Check file dalam data/")
                else:
                    sekolah_options = [f"{row['NAMA SEKOLAH']} ({row['KOD SEKOLAH']}) - {row['BIL PUSAT']} pusat [{row['SENARAI PUSAT']}]" for _, row in df_daerah.iterrows()]
                    sekolah_pilih = st.selectbox("Nama Sekolah (Masuk ikut sekolah, bukan pusat)", ["-- Pilih Sekolah --"] + sekolah_options)
                    
                    if sekolah_pilih != "-- Pilih Sekolah --":
                        idx = sekolah_options.index(sekolah_pilih)
                        row_sekolah = df_daerah.iloc[idx]
                        st.success(f"✅ {row_sekolah['NAMA SEKOLAH']} - {row_sekolah['KOD SEKOLAH']} - {row_sekolah['BIL PUSAT']} pusat: {row_sekolah['SENARAI PUSAT']}")
                        st.markdown("#### 4️⃣ Password Sahaja")
                        sup_pwd = st.text_input(f"Password {row_sekolah['NAMA SEKOLAH']}", type="password", placeholder=f"{row_sekolah['PASSWORD']}")
                        if st.button(f"🚀 Log Masuk {row_sekolah['NAMA SEKOLAH']}", use_container_width=True, type="primary"):
                            if sup_pwd == str(row_sekolah['PASSWORD']):
                                st.session_state.logged_in=True
                                st.session_state.user_role="SUP"
                                st.session_state.user_info={
                                    "nama": row_sekolah['NAMA SEKOLAH'],
                                    "kod_sekolah": row_sekolah['KOD SEKOLAH'],
                                    "ppd": row_sekolah['PPD'],
                                    "kod_ppd": row_sekolah['KOD PPD'],
                                    "id": str(row_sekolah['ID']),
                                    "password": str(row_sekolah['PASSWORD']),
                                    "bil_pusat": row_sekolah['BIL PUSAT'],
                                    "senarai_pusat": row_sekolah['SENARAI PUSAT'],
                                    "role":"SUP"
                                }
                                st.rerun()
                            else:
                                st.error(f"Password salah")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        with st.expander("ℹ️ Di mana update data?"):
            st.markdown(f"""
            **File yang sedang guna:** `{file_used}` - {len(mapping_df)} sekolah
            
            **Senarai Sekolah 369:**
            - App akan cari apa saja file dalam `data/` yang ada perkataan ID dan DAERAH (tak kisah - atau _ , besar kecil)
            - Contoh nama valid: `SENARAI_ID_SUP_BY_DAERAH.xlsx`, `SENARAI_ID-SUP_BY_DAERAH.xlsx`, `senarai_id_sup_by_daerah.xlsx` semua boleh!
            - File yang Kashah upload: `SENARAI_ID-SUP_BY_DAERAH.xlsx` - sekarang app dah boleh baca walaupun ada hyphen!
            - Kalau tak ada, app auto generate dari `senarai_506_PLUS_calon2026_FINAL.xlsx`
            
            **Tambah sekolah baru:** Edit file Excel tu tambah row ID 370, push GitHub
            
            **Senarai PPD:** Edit `PPD_LIST` dalam `app.py`
            """)
    
    st.markdown("---")
    st.caption(f"Data: {len(mapping_df)} sekolah dari {os.path.basename(file_used)} | Tanpa Sidebar")
    st.stop()

# Dah login
role = st.session_state.user_role
info = st.session_state.user_info

st.markdown(f"""
<div style="background:#0B5394; color:white; padding:10px 15px; border-radius:8px;">
    <b>📚 SPM 2026</b> | {info['nama']} | {role} | {info.get('ppd','')} {info.get('kod_sekolah','')} | {info.get('bil_pusat','')} pusat | File: {os.path.basename(file_used)}
</div>
""", unsafe_allow_html=True)

col_kiri, col_kanan = st.columns([1, 3])

with col_kiri:
    st.markdown('<div class="left-panel">', unsafe_allow_html=True)
    st.markdown(f"### 👤 {info['nama']}")
    if role=="SUP":
        st.markdown(f"**Kod:** {info['kod_sekolah']}")
        st.markdown(f"**PPD:** {info['ppd']} ({info['kod_ppd']})")
        st.markdown(f"**Pusat:** {info['bil_pusat']} pusat")
        st.code(info['senarai_pusat'])
    elif role=="PPD":
        st.markdown(f"**PPD:** {info['ppd_nama']} ({info['kod']}) - {len(mapping_df[mapping_df['KOD PPD']==info['kod']])} sekolah")
    st.markdown("---")
    if role=="SUP":
        menu = st.radio("Menu", ["Maklumat Sekolah", "Cadangan Petugas", "Status"], label_visibility="collapsed")
    elif role=="PPD":
        menu = st.radio("Menu", ["Senarai Pusat", "Cadangan SUP", "Jana Penempatan", "Hantar JPN"], label_visibility="collapsed")
    else:
        menu = st.radio("Menu", ["Semua PPD", "Sahkan PPD", "Jana Surat"], label_visibility="collapsed")
    st.markdown("---")
    exam_type = st.selectbox("Peperiksaan", ["SPM Bertulis", "SPM Amali Sains", "Ujian Mendengar", "Ujian Bertutur"])
    st.markdown("---")
    if st.button("🚪 Log Keluar", use_container_width=True):
        st.session_state.logged_in=False
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with col_kanan:
    @st.cache_data
    def load_master():
        try:
            # cari file 506
            if os.path.exists("data"):
                for f in os.listdir("data"):
                    if "506" in f:
                        return pd.read_excel(os.path.join("data", f))
            return pd.read_excel("data/senarai_506_PLUS_calon2026_FINAL.xlsx")
        except Exception:
            return pd.DataFrame({"NO PUSAT":["BK009"],"NAMA PUSAT":["SMJK KATHOLIK"]})
    pusat_master = load_master()
    
    gspread_client, SPREADSHEET_ID_FIX, GS_ERR = get_gsheet()
    USE_GSHEET = gspread_client is not None
    if not USE_GSHEET:
        st.warning(f"GSheet tidak connect - data TIDAK boleh disimpan: {GS_ERR}")
    show_flash()

    if role=="SUP":
        if menu=="Maklumat Sekolah":
            st.header(f"🏫 {info['nama']} - {info['senarai_pusat']}")
            st.info(f"Kod {info['kod_sekolah']} | {info['bil_pusat']} pusat | Masuk ikut sekolah bukan pusat")
            maklumat = read_sheet("maklumat_sekolah")
            # === AUTO-LOAD data sedia ada ===
            existing = pd.DataFrame()
            if not maklumat.empty and "KOD SEKOLAH" in maklumat.columns:
                existing = maklumat[maklumat["KOD SEKOLAH"].astype(str) == str(info['kod_sekolah'])]
            
            def_val_nama = info['nama']
            def_val_email = ""
            def_val_poskod = 46000
            def_val_bil_pusat = int(info['bil_pusat'])
            def_val_senarai = info['senarai_pusat']
            def_val_bil_kelas = 12
            def_val_nama_sup = f"SUP {info['nama']}"
            def_val_tel = ""
            def_val_pengetua = ""
            
            if not existing.empty:
                row = existing.iloc[-1]
                def_val_nama = str(row.get("NAMA SEKOLAH", def_val_nama))
                # Email
                for col in ["EMAIL SEKOLAH", "EMAIL"]:
                    if col in existing.columns and pd.notna(row.get(col)):
                        def_val_email = str(row.get(col, ""))
                        break
                # Telefon - ikut nama betul
                for col in ["NO TELEFON SEKOLAH", "TELEFON SEKOLAH", "NO TELEFON"]:
                    if col in existing.columns and pd.notna(row.get(col)):
                        def_val_tel = str(row.get(col, ""))
                        break
                # Poskod - ikut nama betul
                for col in ["NO POSKOD SEKOLAH", "POSKOD SEKOLAH", "POSKOD"]:
                    if col in existing.columns:
                        try:
                            v = str(row.get(col, "")).strip()
                            if v and v != "nan":
                                def_val_poskod = int(float(v))
                                break
                        except Exception:
                            pass
                # Pengetua
                for col in ["NAMA PENGETUA", "PENGETUA"]:
                    if col in existing.columns and pd.notna(row.get(col)):
                        def_val_pengetua = str(row.get(col, ""))
                        break
                for col in ["NAMA SUP"]:
                    if col in existing.columns and pd.notna(row.get(col)):
                        def_val_nama_sup = str(row.get(col, ""))
                        break
                for col in ["SENARAI NO PUSAT"]:
                    if col in existing.columns and pd.notna(row.get(col)):
                        def_val_senarai = str(row.get(col, ""))
                        break
                for col in ["BIL NO PUSAT"]:
                    if col in existing.columns:
                        try:
                            def_val_bil_pusat = int(float(str(row.get(col, def_val_bil_pusat)).strip() or def_val_bil_pusat))
                        except Exception:
                            pass
                        break
                for col in ["BIL KELAS DIGUNAKAN"]:
                    if col in existing.columns:
                        try:
                            def_val_bil_kelas = int(float(str(row.get(col, def_val_bil_kelas)).strip() or def_val_bil_kelas))
                        except Exception:
                            pass
                        break
            
            if not existing.empty:
                st.success(f"✅ Data {info['kod_sekolah']} dijumpai - auto isi")
            
            # Elak app crash kalau nilai lama dalam sheet di luar had
            def_val_poskod = max(40000, min(49000, def_val_poskod))
            def_val_bil_pusat = max(1, min(10, def_val_bil_pusat))
            def_val_bil_kelas = max(1, min(30, def_val_bil_kelas))

            with st.form("sekolah"):
                c1,c2 = st.columns(2)
                with c1:
                    nama_sek = st.text_input("NAMA SEKOLAH", value=def_val_nama)
                    email = st.text_input("EMAIL SEKOLAH", value=def_val_email, placeholder="bea8640@moe.edu.my")
                    no_tel = st.text_input("NO TELEFON SEKOLAH", value=def_val_tel, placeholder="03-XXXXXXX")
                    poskod_sek = st.number_input("NO POSKOD SEKOLAH",40000,49000,def_val_poskod)
                    bil_pusat = st.number_input("BIL PUSAT",1,10,def_val_bil_pusat)
                with c2:
                    senarai = st.text_input("SENARAI NO PUSAT", value=def_val_senarai)
                    bil_kelas = st.number_input("BIL KELAS DIGUNAKAN",1,30,def_val_bil_kelas)
                    nama_sup = st.text_input("NAMA SUP", value=def_val_nama_sup)
                    nama_pengetua = st.text_input("NAMA PENGETUA", value=def_val_pengetua)
                if st.form_submit_button("💾 Simpan", use_container_width=True):
                    # Data baru - semua field - ikut format sheet sedia ada
                    new_row = {
                        "KOD SEKOLAH": info['kod_sekolah'], 
                        "NAMA SEKOLAH": nama_sek, 
                        "EMAIL SEKOLAH": email,
                        "NO TELEFON SEKOLAH": no_tel,
                        "TELEFON SEKOLAH": no_tel,
                        "NAMA PENGETUA": nama_pengetua,
                        "NAMA SUP": nama_sup,
                        "NO POSKOD SEKOLAH": poskod_sek,
                        "POSKOD SEKOLAH": poskod_sek,
                        "BIL NO PUSAT": bil_pusat, 
                        "SENARAI NO PUSAT": senarai, 
                        "BIL KELAS DIGUNAKAN": bil_kelas,
                        "TARIKH KEMASKINI": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    def _simpan_maklumat(df):
                        if not df.empty and "KOD SEKOLAH" not in df.columns:
                            raise ValueError("Format sheet maklumat_sekolah tidak dijangka - hubungi admin")
                        if not df.empty:
                            # Satu rekod sahaja setiap sekolah (buang rekod lama sekolah ini)
                            df = df[df["KOD SEKOLAH"].astype(str) != str(info['kod_sekolah'])]
                        return pd.concat([df, pd.DataFrame([new_row])], ignore_index=True) if not df.empty else pd.DataFrame([new_row])

                    if modify_sheet("maklumat_sekolah", _simpan_maklumat):
                        flash("success", f"✅ {nama_sek} berjaya dikemaskini! (Satu rekod sahaja untuk {info['kod_sekolah']})")
                        st.rerun()
            # === FIX: Hanya papar sekolah sendiri sahaja ===
            if not maklumat.empty and "KOD SEKOLAH" in maklumat.columns:
                maklumat_sendiri = maklumat[maklumat["KOD SEKOLAH"].astype(str) == str(info['kod_sekolah'])]
                if not maklumat_sendiri.empty:
                    st.markdown("#### 📋 Rekod Sekolah Anda (dari Google Sheet)")
                    st.dataframe(maklumat_sendiri, use_container_width=True)
                else:
                    st.info("Belum ada rekod untuk sekolah ini dalam Google Sheet")
            
        elif menu=="Cadangan Petugas":
            st.header(f"👥 Cadangan - {info['nama']}")
            cadangan = read_sheet("cadangan_sup")
            with st.form("guru"):
                c1,c2,c3 = st.columns(3)
                with c1:
                    jaw = st.selectbox("JAWATAN", ["Ketua Pengawas","Timbalan Ketua Pengawas","Pengawas Peperiksaan","Pengemas Bilik","Penyelia Kawasan"])
                    nama_g = st.text_input("NAMA GURU *")
                with c2:
                    ic = st.text_input("IC *")
                    jantina = st.selectbox("JANTINA", ["L","P"])
                with c3:
                    pos_rumah = st.number_input("POSKOD RUMAH *",40000,49000,46000)
                if st.form_submit_button("➕ Tambah", use_container_width=True):
                    ic_digit = re.sub(r"\D", "", ic)
                    if not nama_g.strip() or not ic.strip():
                        st.error("Nama Guru dan IC wajib isi!")
                    elif len(ic_digit) != 12:
                        st.error("IC mesti 12 digit (contoh: 900101-10-1234)")
                    else:
                        ic_norm = norm_ic(ic)
                        new_g_row = {"KOD SEKOLAH ASAL": info['kod_sekolah'], "NAMA SEKOLAH ASAL": info['nama'], "JAWATAN CADANG": jaw, "NAMA GURU": nama_g.strip(), "IC": ic.strip(), "JANTINA": jantina, "POSKOD RUMAH": pos_rumah, "TARIKH": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")}

                        def _tambah_guru(df):
                            if not df.empty and ("IC" not in df.columns or "KOD SEKOLAH ASAL" not in df.columns):
                                raise ValueError("Format sheet cadangan_sup tidak dijangka - hubungi admin")
                            if df.empty:
                                return pd.DataFrame([new_g_row])
                            sama = df["IC"].map(norm_ic) == ic_norm
                            lain = sama & (df["KOD SEKOLAH ASAL"].astype(str) != str(info['kod_sekolah']))
                            if lain.any():
                                r = df[lain].iloc[0]
                                raise ValueError(f"IC ini sudah dicadangkan oleh {r.get('NAMA SEKOLAH ASAL', r['KOD SEKOLAH ASAL'])}. Seorang guru hanya boleh dicadang oleh satu sekolah - hubungi PPD jika guru ini baru bertukar.")
                            # IC sama dalam sekolah SENDIRI sahaja yang diganti (kemaskini)
                            df = df[~sama]
                            return pd.concat([df, pd.DataFrame([new_g_row])], ignore_index=True) if not df.empty else pd.DataFrame([new_g_row])

                        if modify_sheet("cadangan_sup", _tambah_guru):
                            flash("success", f"✅ {nama_g} ditambah / dikemaskini! - Hanya untuk {info['kod_sekolah']}")
                            st.rerun()
            # === FIX: Hanya papar cadangan sekolah sendiri ===
            if not cadangan.empty and "KOD SEKOLAH ASAL" in cadangan.columns:
                cadangan_sendiri = cadangan[cadangan["KOD SEKOLAH ASAL"].astype(str) == str(info['kod_sekolah'])]
                if not cadangan_sendiri.empty:
                    st.markdown(f"#### 👥 Senarai Cadangan Anda - {info['kod_sekolah']} ({len(cadangan_sendiri)} orang)")
                    st.dataframe(cadangan_sendiri, use_container_width=True)
                else:
                    st.info(f"Belum ada cadangan untuk {info['kod_sekolah']}")
            else:
                st.info("Belum ada cadangan")
        else:
            st.header("📤 Status")
            maklumat_s = read_sheet("maklumat_sekolah")
            cadangan_s = read_sheet("cadangan_sup")
            kod_ini = str(info['kod_sekolah'])
            own_m = maklumat_s[maklumat_s["KOD SEKOLAH"].astype(str) == kod_ini] if (not maklumat_s.empty and "KOD SEKOLAH" in maklumat_s.columns) else pd.DataFrame()
            own_c = cadangan_s[cadangan_s["KOD SEKOLAH ASAL"].astype(str) == kod_ini] if (not cadangan_s.empty and "KOD SEKOLAH ASAL" in cadangan_s.columns) else pd.DataFrame()
            if own_m.empty:
                st.warning("❌ Maklumat Sekolah: belum diisi")
            else:
                st.success("✅ Maklumat Sekolah: sudah diisi")
                st.dataframe(own_m, use_container_width=True)
            if own_c.empty:
                st.warning("❌ Cadangan Petugas: belum ada")
            else:
                st.success(f"✅ Cadangan Petugas: {len(own_c)} orang")
    elif role=="PPD":
        # Senarai kod sekolah bawah PPD ini
        df_ppd = mapping_df[mapping_df["KOD PPD"]==info['kod']]
        kod_sekolah_ppd = df_ppd["KOD SEKOLAH"].astype(str).tolist()
        
        # Build list pusat under PPD - DARI MASTER + ID_SUP
        semua_pusat = []
        pusat_to_sekolah = {}
        pusat_to_nama = {}  # BK069 -> SMK TROPICANA
        
        # 1. Dari ID_SUP file (df_ppd)
        for _, r in df_ppd.iterrows():
            senarai = str(r.get("SENARAI PUSAT","")).split(",")
            for p in senarai:
                p = p.strip()
                if p:
                    semua_pusat.append(p)
                    pusat_to_sekolah[p] = str(r["KOD SEKOLAH"])
                    pusat_to_nama[p] = str(r["NAMA SEKOLAH"])
        
        # 2. Dari master 506 file - cari semua NO PUSAT ikut kod daerah (BA, BK etc)
        try:
            master_files = []
            if os.path.exists("data"):
                for f in os.listdir("data"):
                    if "506" in f and "calon" in f.lower():
                        master_files.append(os.path.join("data", f))
            for mf in master_files:
                try:
                    df_m = pd.read_excel(mf)
                    if "NO PUSAT" in df_m.columns and "KOD SEKOLAH" in df_m.columns:
                        # Filter NO PUSAT yang start dengan kod PPD ni (BK, BA dll)
                        mask = df_m["NO PUSAT"].astype(str).str.startswith(info['kod'])
                        df_m_ppd = df_m[mask]
                        for _, rm in df_m_ppd.iterrows():
                            p = str(rm["NO PUSAT"]).strip()
                            if p and p not in semua_pusat:
                                semua_pusat.append(p)
                            if p not in pusat_to_sekolah:
                                pusat_to_sekolah[p] = str(rm["KOD SEKOLAH"])
                            if p not in pusat_to_nama:
                                # Cari nama pusat dari df_m kalau ada NAMA PUSAT
                                nama_p = str(rm.get("NAMA PUSAT", rm.get("NAMA SEKOLAH", p)))
                                pusat_to_nama[p] = nama_p
                except Exception:
                    continue
        except Exception:
            pass
        
        # 3. Dari Google Sheet sah_jpn - ada NO PUSAT + NAMA PUSAT penuh!
        try:
            sah_tmp = read_sheet("sah_jpn")
            if not sah_tmp.empty and "NO PUSAT" in sah_tmp.columns:
                for _, rs in sah_tmp.iterrows():
                    p = str(rs.get("NO PUSAT","")).strip()
                    if p.startswith(info['kod']):
                        if p not in semua_pusat:
                            semua_pusat.append(p)
                        # Nama penuh pusat
                        nama_pusat = str(rs.get("NAMA PUSAT","")).strip()
                        if nama_pusat and nama_pusat.lower()!="nan":
                            pusat_to_nama[p] = nama_pusat
        except Exception:
            pass
        
        # 4. Dari penempatan_ppd sheet juga
        try:
            pen_tmp = read_sheet("penempatan_ppd")
            if not pen_tmp.empty and "NO PUSAT TUGAS" in pen_tmp.columns:
                for _, rp in pen_tmp.iterrows():
                    p = str(rp.get("NO PUSAT TUGAS","")).strip()
                    if p.startswith(info['kod']):
                        if p not in semua_pusat:
                            semua_pusat.append(p)
                        nama_p = str(rp.get("NAMA PUSAT TUGAS","")).strip()
                        if nama_p and nama_p.lower()!="nan" and p not in pusat_to_nama:
                            pusat_to_nama[p] = nama_p
        except Exception:
            pass
        
        # 5. Pastikan semua pusat ada nama - kalau takde, guna sekolah tuan rumah
        for p in semua_pusat:
            if p not in pusat_to_nama or not pusat_to_nama[p]:
                kod_sek = pusat_to_sekolah.get(p, "")
                if kod_sek:
                    # cari nama sekolah
                    row = df_ppd[df_ppd["KOD SEKOLAH"].astype(str)==kod_sek]
                    if not row.empty:
                        pusat_to_nama[p] = str(row.iloc[0]["NAMA SEKOLAH"])
                    else:
                        pusat_to_nama[p] = p
                else:
                    pusat_to_nama[p] = p
        
        semua_pusat = sorted(list(set(semua_pusat)))
        # FIX 43 bukan 71 - filter ikut pusat_2026.csv
        if not df_calon_master.empty and "NO_PUSAT" in df_calon_master.columns:
            calon_set = set(df_calon_master[df_calon_master["NO_PUSAT"].astype(str).str.startswith(info['kod'])]["NO_PUSAT"].astype(str).tolist())
            if calon_set:
                semua_pusat = sorted(list((set(semua_pusat) & calon_set) | calon_set))
                for _, rc in df_calon_master[df_calon_master["NO_PUSAT"].astype(str).str.startswith(info['kod'])].iterrows():
                    p = str(rc["NO_PUSAT"]).strip()
                    pusat_to_nama[p] = str(rc.get("NAMA_PUSAT", pusat_to_nama.get(p, p)))
                    if p not in pusat_to_sekolah:
                        pusat_to_sekolah[p] = str(rc.get("KOD_SEKOLAH", ""))
        
        if menu=="Senarai Pusat":
            if not df_calon_master.empty:
                dppd = df_calon_master[df_calon_master["NO_PUSAT"].astype(str).str.startswith(info['kod'])]
                tc = int(dppd["JUMLAH_CALON"].sum()) if not dppd.empty else 0
                tk = int(dppd["JUMLAH_KELAS"].sum()) if not dppd.empty else 0
                tp = int(dppd["PETUGAS_NEEDED"].sum()) if not dppd.empty else 0
                tt = tp + len(dppd)*2
                st.header(f"🏢 PPD {info['ppd_nama']} - {len(df_ppd)} sekolah, {len(semua_pusat)} pusat")
                st.info(f"Daerah {info['kod']} = {info['ppd_nama']} | {len(semua_pusat)} pusat ada calon (bukan 71 spare) | 📊 {tc} calon, {tk} kelas, {tp} pengawas + {len(dppd)*2} KP/TKP = {tt} petugas di pusat | Penyelia Kawasan exclude (Bilik Kebal)")
            else:
                st.header(f"🏢 PPD {info['ppd_nama']} - {len(df_ppd)} sekolah, {len(semua_pusat)} pusat")
    
            
            # Load penempatan untuk kira status
            penempatan_all = read_sheet("penempatan_ppd")
            
            # Buat status table - KASHAH: 11 kelas = 17 pengawas +1 KP +1 TKP =19 total, Penyelia exclude
            status_data = []
            for pusat in semua_pusat:
                kod_sek_pusat = pusat_to_sekolah.get(pusat, "")
                nr = df_ppd[df_ppd["KOD SEKOLAH"].astype(str)==kod_sek_pusat]
                nama_sek_pusat = nr["NAMA SEKOLAH"].values[0] if not nr.empty else pusat_to_nama.get(pusat, pusat)
                
                calon_c = 0
                kelas_c = 0
                pengawas_c = 10
                total_c = 12
                if not df_calon_master.empty:
                    rc = df_calon_master[df_calon_master["NO_PUSAT"].astype(str)==pusat]
                    if not rc.empty:
                        calon_c = int(rc.iloc[0].get("JUMLAH_CALON",0))
                        kelas_c = int(rc.iloc[0].get("JUMLAH_KELAS",0))
                        pengawas_c = int(rc.iloc[0].get("PETUGAS_NEEDED",10))
                        total_c = pengawas_c + 2
                
                if not penempatan_all.empty and "NO PUSAT TUGAS" in penempatan_all.columns:
                    bil = len(penempatan_all[penempatan_all["NO PUSAT TUGAS"].astype(str)==pusat])
                    if bil >= total_c:
                        status = f"✅ Lengkap ({bil}/{total_c})"
                    elif bil>0:
                        status = f"⚠️ Separa ({bil}/{total_c})"
                    else:
                        status = f"❌ Belum (0/{total_c})"
                else:
                    bil = 0
                    status = f"❌ Belum (0/{total_c})"
                
                status_data.append({"NO PUSAT": pusat, "SEKOLAH TUAN RUMAH": nama_sek_pusat, "KOD SEKOLAH": kod_sek_pusat, "JUMLAH CALON": calon_c, "KELAS": kelas_c, "PENGAWAS": pengawas_c, "TOTAL DI PUSAT": total_c, "BIL DILANTIK": bil, "STATUS": status})
            status_df = pd.DataFrame(status_data)
            st.dataframe(status_df, use_container_width=True)
            
            # Summary
            lengkap = len([s for s in status_data if "Lengkap" in s["STATUS"]])
            st.metric("Pusat Lengkap Dilantik", f"{lengkap}/{len(semua_pusat)}")
            
            # Detail maklumat sekolah
            maklumat_all = read_sheet("maklumat_sekolah")
            if not maklumat_all.empty and "KOD SEKOLAH" in maklumat_all.columns:
                maklumat_ppd = maklumat_all[maklumat_all["KOD SEKOLAH"].astype(str).isin(kod_sekolah_ppd)]
                st.markdown(f"#### 📊 Maklumat Sekolah - {info['ppd_nama']}: {len(maklumat_ppd)}/{len(df_ppd)} dah isi")
                belum = df_ppd[~df_ppd["KOD SEKOLAH"].astype(str).isin(maklumat_all["KOD SEKOLAH"].astype(str) if not maklumat_all.empty else [])]
                if not belum.empty:
                    st.warning(f"⚠️ {len(belum)} sekolah belum isi")
                    st.dataframe(belum[["KOD SEKOLAH","NAMA SEKOLAH"]], use_container_width=True)
        
        elif menu=="Cadangan SUP":
            st.header(f"📋 Cadangan SUP - {info['ppd_nama']} ({len(kod_sekolah_ppd)} sekolah)")
            cadangan_all = read_sheet("cadangan_sup")
            if not cadangan_all.empty and "KOD SEKOLAH ASAL" in cadangan_all.columns:
                cadangan_ppd = cadangan_all[cadangan_all["KOD SEKOLAH ASAL"].astype(str).isin(kod_sekolah_ppd)].copy()
                # Tambah NAMA PUSAT untuk setiap sekolah asal
                def get_nama_pusat(kod):
                    # cari nama sekolah dari df_ppd
                    row = df_ppd[df_ppd["KOD SEKOLAH"].astype(str)==str(kod)]
                    if not row.empty:
                        return str(row.iloc[0]["NAMA SEKOLAH"])
                    return str(kod)
                
                # Add NAMA PUSAT column kalau tak ada
                if "NAMA PUSAT SEKOLAH" not in cadangan_ppd.columns:
                    cadangan_ppd["NAMA PUSAT SEKOLAH"] = cadangan_ppd["KOD SEKOLAH ASAL"].apply(get_nama_pusat)
                
                st.success(f"✅ {len(cadangan_ppd)} guru dicadang dari {info['ppd_nama']}")
                if not cadangan_ppd.empty:
                    # DUA TAPIS: Sekolah dan Pusat
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        sekolah_opts = sorted(cadangan_ppd["KOD SEKOLAH ASAL"].astype(str).unique().tolist())
                        def label_sek(k):
                            nama = get_nama_pusat(k)
                            bil = len(cadangan_ppd[cadangan_ppd["KOD SEKOLAH ASAL"].astype(str)==k])
                            return f"{k} - {nama} ({bil} guru)"
                        pilih_sek = st.selectbox("🏫 Tapis ikut Sekolah Asal", ["SEMUA SEKOLAH"] + sekolah_opts, format_func=lambda x: "SEMUA SEKOLAH" if x=="SEMUA SEKOLAH" else label_sek(x))
                        if pilih_sek != "SEMUA SEKOLAH":
                            cadangan_ppd = cadangan_ppd[cadangan_ppd["KOD SEKOLAH ASAL"].astype(str)==pilih_sek]
                    with col_f2:
                        if "NO PUSAT ASAL" in cadangan_ppd.columns and not cadangan_ppd["NO PUSAT ASAL"].astype(str).str.strip().eq("").all():
                            pusat_options = sorted(cadangan_ppd["NO PUSAT ASAL"].dropna().astype(str).unique().tolist())
                            def label_pusat(p):
                                sek_kod = pusat_to_sekolah.get(p, "")
                                nama = pusat_to_nama.get(p, sek_kod)
                                return f"{p} - {nama}"
                            pilih_pusat = st.selectbox("📌 Tapis ikut Pusat Asal (NO PUSAT)", ["SEMUA PUSAT"] + pusat_options, format_func=lambda x: "SEMUA PUSAT" if x=="SEMUA PUSAT" else label_pusat(x))
                            if pilih_pusat != "SEMUA PUSAT":
                                cadangan_ppd = cadangan_ppd[cadangan_ppd["NO PUSAT ASAL"].astype(str)==str(pilih_pusat)]
                        else:
                            st.selectbox("📌 Tapis ikut Pusat", ["Tiada data NO PUSAT ASAL - guna tapis sekolah"], disabled=True)
                    
                    # Show dengan NAMA PUSAT
                    cols_show = []
                    for c in ["NO PUSAT ASAL", "KOD SEKOLAH ASAL", "NAMA SEKOLAH ASAL", "NAMA PUSAT SEKOLAH", "NAMA GURU", "JAWATAN CADANG", "IC", "JANTINA", "POSKOD RUMAH", "ALAMAT RUMAH", "NO TELEFON GURU", "EMAIL GURU"]:
                        if c in cadangan_ppd.columns:
                            cols_show.append(c)
                    if cols_show:
                        st.dataframe(cadangan_ppd[cols_show], use_container_width=True)
                    else:
                        st.dataframe(cadangan_ppd, use_container_width=True)
                    
                    st.markdown("#### Ringkasan ikut PUSAT")
                    if "NO PUSAT ASAL" in cadangan_ppd.columns:
                        st.dataframe(cadangan_ppd.groupby("NO PUSAT ASAL").size().reset_index(name="BIL GURU"), use_container_width=True)
                    else:
                        st.dataframe(cadangan_ppd.groupby("KOD SEKOLAH ASAL").size().reset_index(name="BIL GURU"), use_container_width=True)
                else:
                    st.info(f"Belum ada cadangan untuk {info['ppd_nama']}")
            else:
                st.info("Belum ada cadangan")
        
        elif menu=="Jana Penempatan":
            st.header(f"🎯 Lantikan Ikut Pusat - {info['ppd_nama']}")
            st.markdown("PPD pilih pusat, terus nampak siapa Ketua, Timbalan, Pengawas yang sistem tempatkan. Boleh edit terus!")
            st.caption("Susunan: 1 Ketua Pengawas + 1 Timbalan + Pengawas ikut keperluan pusat. Penyelia Kawasan exclude (Bilik Kebal). Seorang guru hanya dilantik di SATU pusat; guru sekolah tuan rumah tak jaga pusat sendiri.")

            cadangan_all = read_sheet("cadangan_sup")
            penempatan_all = read_sheet("penempatan_ppd")
            ada_pen = (not penempatan_all.empty) and ("NO PUSAT TUGAS" in penempatan_all.columns)

            if not cadangan_all.empty and "KOD SEKOLAH ASAL" in cadangan_all.columns:
                cadangan_ppd = cadangan_all[cadangan_all["KOD SEKOLAH ASAL"].astype(str).isin(kod_sekolah_ppd)]
            else:
                cadangan_ppd = pd.DataFrame()

            def jalankan_jana(senarai_pusat, label_status):
                """Jana untuk 1 atau banyak pusat - satu logik, simpan selamat."""
                if cadangan_ppd.empty or "IC" not in cadangan_ppd.columns:
                    st.error("Tiada cadangan guru! Isi Cadangan SUP dulu (setiap guru mesti ada IC).")
                    return
                hasil = {}

                def _ubah(df_pen):
                    rows, kurang = jana_penempatan(senarai_pusat, df_pen, cadangan_ppd, pusat_to_sekolah, pusat_to_nama, df_calon_master, label_status)
                    hasil["rows"], hasil["kurang"] = rows, kurang
                    if not rows:
                        return None
                    baru = pd.DataFrame(rows)
                    return pd.concat([df_pen, baru], ignore_index=True) if not df_pen.empty else baru

                with st.spinner("Menjana penempatan..."):
                    ok = modify_sheet("penempatan_ppd", _ubah)
                if not ok:
                    return
                if hasil["rows"]:
                    bil_p = len({r["NO PUSAT TUGAS"] for r in hasil["rows"]})
                    flash("success", f"✅ {len(hasil['rows'])} petugas ditambah di {bil_p} pusat.")
                else:
                    flash("info", "Tiada perubahan - semua pusat dah lengkap atau tiada calon yang sesuai.")
                if hasil["kurang"]:
                    flash("warning", "⚠️ Calon tak cukup (jawatan dibiar kosong): " + ", ".join(f"{p} (kurang {n})" for p, n in hasil["kurang"]) + ". Minta SUP tambah cadangan guru.")
                st.rerun()

            tot_peng = sum(keperluan_pengawas(p, df_calon_master) for p in semua_pusat)
            tot_tot = tot_peng + len(semua_pusat) * 2
            curr = int(penempatan_all["NO PUSAT TUGAS"].astype(str).isin(semua_pusat).sum()) if ada_pen else 0

            st.markdown("### 🚀 Jana Semua Pusat")
            st.info(f"{len(semua_pusat)} pusat = {tot_peng} Pengawas + {len(semua_pusat)*2} KP/TKP = {tot_tot} petugas | {len(cadangan_ppd)} guru dicadangkan")
            if len(cadangan_ppd) < tot_tot - curr:
                st.warning(f"⚠️ Cadangan guru ({len(cadangan_ppd)}) kurang daripada jawatan kosong ({tot_tot - curr}). Sebahagian pusat akan kekal tak lengkap.")
            st.metric("Total Dilantik Sekarang", f"{curr}/{tot_tot}")

            col_bulk1, col_bulk2, col_bulk3 = st.columns(3)
            with col_bulk1:
                if st.button(f"🚀 JANA SEMUA {len(semua_pusat)} PUSAT SEKARANG", use_container_width=True, type="primary", key="jana_all"):
                    jalankan_jana(semua_pusat, "Auto Jana Semua PPD")
            with col_bulk2:
                sahkan_kosong = st.checkbox("Ya, saya pasti nak kosongkan", key="sahkan_reset_all")
                if st.button("🗑️ Kosongkan SEMUA Pusat Daerah Ini", use_container_width=True, key="reset_all", disabled=not sahkan_kosong):
                    def _kosong_semua(df_pen):
                        if df_pen.empty or "NO PUSAT TUGAS" not in df_pen.columns:
                            return None
                        return df_pen[~df_pen["NO PUSAT TUGAS"].astype(str).isin(semua_pusat)]
                    if modify_sheet("penempatan_ppd", _kosong_semua):
                        flash("success", f"✅ Semua {len(semua_pusat)} pusat daerah {info['ppd_nama']} dikosongkan!")
                        st.rerun()
            with col_bulk3:
                pusat_ada = penempatan_all[penempatan_all["NO PUSAT TUGAS"].astype(str).isin(semua_pusat)]["NO PUSAT TUGAS"].nunique() if ada_pen else 0
                st.metric("Pusat Ada Lantikan", f"{pusat_ada}/{len(semua_pusat)}")

            st.markdown("---")

            # Pilih pusat
            if not semua_pusat:
                st.warning("Tiada pusat untuk daerah ini")
            else:
                col1, col2 = st.columns([2, 1])
                with col1:
                    pusat_pilih = st.selectbox("📌 Pilih NO PUSAT (untuk tengok/edit satu-satu)", semua_pusat, index=0)
                with col2:
                    kod_sek_pusat = pusat_to_sekolah.get(pusat_pilih, "")
                    nama_pusat = pusat_to_nama.get(pusat_pilih, pusat_pilih)
                    st.metric("Sekolah Tuan Rumah", f"{nama_pusat}")
                    st.caption(f"Kod: {kod_sek_pusat} | Pusat: {pusat_pilih}")

                if ada_pen:
                    penempatan_pusat = penempatan_all[penempatan_all["NO PUSAT TUGAS"].astype(str) == str(pusat_pilih)]
                else:
                    penempatan_pusat = pd.DataFrame()

                bil_sedia = len(penempatan_pusat)
                need_peng_single = keperluan_pengawas(pusat_pilih, df_calon_master)
                need_tot_single = need_peng_single + 2
                if bil_sedia == 0:
                    st.warning(f"❌ {pusat_pilih} belum ada lantikan. Tekan Jana Auto di bawah.")
                else:
                    st.info(f"ℹ️ {pusat_pilih} ada {bil_sedia}/{need_tot_single} petugas sekarang")

                col_j1, col_j2 = st.columns(2)
                with col_j1:
                    label_btn = f"🤖 Jana Auto untuk {pusat_pilih} ({need_tot_single} orang: 1 KP+1 TKP+{need_peng_single} Pengawas)" if bil_sedia == 0 else f"➕ Lengkapkan {pusat_pilih} jadi {need_tot_single} orang (1 KP+1 TKP+{need_peng_single} Pengawas)"
                    if st.button(label_btn, use_container_width=True, type="primary", key=f"jana_{pusat_pilih}"):
                        jalankan_jana([pusat_pilih], "Auto by PPD" if bil_sedia == 0 else "Lengkapkan Auto by PPD")
                with col_j2:
                    if st.button(f"🗑️ Kosongkan {pusat_pilih} (Reset)", use_container_width=True, key=f"reset_{pusat_pilih}"):
                        def _kosong_satu(df_pen):
                            if df_pen.empty or "NO PUSAT TUGAS" not in df_pen.columns:
                                return None
                            return df_pen[df_pen["NO PUSAT TUGAS"].astype(str) != str(pusat_pilih)]
                        if modify_sheet("penempatan_ppd", _kosong_satu):
                            flash("success", f"✅ {pusat_pilih} dikosongkan!")
                            st.rerun()

                if penempatan_pusat.empty:
                    st.info(f"Belum dilantik untuk {pusat_pilih} - tekan Jana Auto di atas")
                else:
                    st.success(f"✅ {pusat_pilih} - {len(penempatan_pusat)} petugas dilantik")

                    lajur_papar = ["NAMA GURU", "KOD SEKOLAH ASAL GURU", "NAMA SEKOLAH ASAL", "IC", "JAWATAN FINAL"]
                    for jaw in ["Ketua Pengawas", "Timbalan Ketua Pengawas", "Pengawas Peperiksaan", "Pengemas Bilik", "Penyelia Kawasan"]:
                        subset = penempatan_pusat[penempatan_pusat["JAWATAN FINAL"].astype(str) == jaw] if "JAWATAN FINAL" in penempatan_pusat.columns else pd.DataFrame()
                        if not subset.empty:
                            st.markdown(f"**{jaw} ({len(subset)} orang)**")
                            st.dataframe(subset[[c for c in lajur_papar if c in subset.columns]], use_container_width=True)

                    st.markdown("---")
                    st.markdown(f"#### ✏️ Edit Lantikan {pusat_pilih} - Klik Nama Untuk Tukar")
                    st.caption(f"📍 Pusat: {pusat_pilih} - {nama_pusat} ({kod_sek_pusat}) | Guru dari {kod_sek_pusat} tidak boleh jaga pusat sendiri - auto exclude")

                    # Calon ganti: bukan tuan rumah, dan belum dilantik di mana-mana pusat
                    if not cadangan_ppd.empty and "IC" in cadangan_ppd.columns:
                        calon_edit = cadangan_ppd[cadangan_ppd["KOD SEKOLAH ASAL"].astype(str) != str(kod_sek_pusat)].copy()
                        if "IC" in penempatan_all.columns:
                            ic_terpakai = {i for i in penempatan_all["IC"].map(norm_ic) if i}
                            calon_edit = calon_edit[~calon_edit["IC"].map(norm_ic).isin(ic_terpakai)]
                        calon_edit = calon_edit.reset_index(drop=True)

                        def label_calon(row):
                            return f"{row.get('NAMA GURU','')} | {row.get('KOD SEKOLAH ASAL','')} - {row.get('NAMA SEKOLAH ASAL','')} | IC:{row.get('IC','')} | Poskod:{row.get('POSKOD RUMAH','')}"
                        calon_options = [label_calon(r) for _, r in calon_edit.iterrows()]
                    else:
                        calon_options = []
                        calon_edit = pd.DataFrame()

                    st.info(f"📋 Ada {len(calon_options)} guru dari daerah {info['ppd_nama']} yang belum dilantik dan boleh dipilih (kecuali {kod_sek_pusat})")

                    petugas_labels = []
                    for _, r in penempatan_pusat.iterrows():
                        petugas_labels.append(f"{r.get('NAMA GURU','')} - {r.get('JAWATAN FINAL','')} ({r.get('KOD SEKOLAH ASAL GURU','')})")

                    col_a, col_b = st.columns([1, 2])
                    with col_a:
                        idx_pilih = st.selectbox("1️⃣ Klik nama pengawas nak tukar", ["-- Pilih nama --"] + petugas_labels, key=f"pilih_{pusat_pilih}")
                    with col_b:
                        if idx_pilih != "-- Pilih nama --" and calon_options:
                            pos_lama = petugas_labels.index(idx_pilih)
                            baris_lama = penempatan_pusat.iloc[pos_lama]
                            petugas_pilih = str(baris_lama.get("NAMA GURU", ""))
                            ic_lama = norm_ic(baris_lama.get("IC", ""))
                            guru_baru = st.selectbox(f"2️⃣ Ganti {petugas_pilih} dengan guru lain (dari daerah {info['ppd_nama']} kecuali {kod_sek_pusat})", ["-- Pilih guru baru dari senarai cadangan --"] + calon_options, key=f"ganti_{pusat_pilih}")
                            if guru_baru != "-- Pilih guru baru dari senarai cadangan --":
                                if st.button(f"🔄 Tukar {petugas_pilih} → {guru_baru.split('|')[0].strip()}", use_container_width=True, type="primary", key=f"tukar_{pusat_pilih}"):
                                    guru_data = calon_edit.iloc[calon_options.index(guru_baru)]
                                    ic_baru = norm_ic(guru_data.get("IC", ""))

                                    def _tukar(df_pen):
                                        if df_pen.empty or "NO PUSAT TUGAS" not in df_pen.columns or "NAMA GURU" not in df_pen.columns:
                                            raise ValueError("Data penempatan tidak lengkap - muat semula halaman")
                                        if "IC" in df_pen.columns and ic_baru and ic_baru in set(df_pen["IC"].map(norm_ic)):
                                            raise ValueError(f"{guru_data.get('NAMA GURU','Guru ini')} sudah dilantik di pusat lain - pilih guru lain.")
                                        mask = df_pen["NO PUSAT TUGAS"].astype(str) == str(pusat_pilih)
                                        if ic_lama and "IC" in df_pen.columns:
                                            mask = mask & (df_pen["IC"].map(norm_ic) == ic_lama)
                                        else:
                                            mask = mask & (df_pen["NAMA GURU"].astype(str) == petugas_pilih)
                                        if not mask.any():
                                            raise ValueError("Petugas asal tak dijumpai (mungkin sudah diubah orang lain) - muat semula halaman")
                                        df_pen = df_pen.copy()
                                        df_pen.loc[mask, "NAMA GURU"] = guru_data.get("NAMA GURU", "")
                                        df_pen.loc[mask, "KOD SEKOLAH ASAL GURU"] = guru_data.get("KOD SEKOLAH ASAL", "")
                                        df_pen.loc[mask, "NAMA SEKOLAH ASAL"] = guru_data.get("NAMA SEKOLAH ASAL", "")
                                        df_pen.loc[mask, "IC"] = guru_data.get("IC", "")
                                        df_pen.loc[mask, "JANTINA"] = guru_data.get("JANTINA", "")
                                        df_pen.loc[mask, "POSKOD RUMAH"] = guru_data.get("POSKOD RUMAH", "")
                                        df_pen.loc[mask, "STATUS PENEMPATAN"] = f"Tukar manual oleh PPD {info['ppd_nama']} - {pd.Timestamp.now().strftime('%Y-%m-%d')}"
                                        return df_pen

                                    if modify_sheet("penempatan_ppd", _tukar):
                                        flash("success", f"✅ {petugas_pilih} ditukar kepada {guru_data.get('NAMA GURU','')} dari {guru_data.get('KOD SEKOLAH ASAL','')}")
                                        st.rerun()

                    st.markdown("#### 📋 Semua Petugas di Pusat Ini")
                    st.dataframe(penempatan_pusat, use_container_width=True)

        else:
            st.header(f"📤 Hantar ke JPN - {info['ppd_nama']}")
            penempatan_all = read_sheet("penempatan_ppd")
            status_all = read_sheet("status_hantar")

            bil_petugas = 0
            bil_pusat_ada = 0
            bil_pusat_lengkap = 0
            if (not penempatan_all.empty) and ("NO PUSAT TUGAS" in penempatan_all.columns):
                pen_ppd = penempatan_all[penempatan_all["NO PUSAT TUGAS"].astype(str).isin(semua_pusat)]
                bil_petugas = len(pen_ppd)
                kiraan = pen_ppd["NO PUSAT TUGAS"].astype(str).value_counts()
                bil_pusat_ada = len(kiraan)
                bil_pusat_lengkap = sum(1 for p in semua_pusat if kiraan.get(p, 0) >= keperluan_pengawas(p, df_calon_master) + 2)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Sekolah", f"{len(df_ppd)}")
            with col2:
                st.metric("Pusat", f"{len(semua_pusat)}")
            with col3:
                st.metric("Pusat Ada Lantikan", f"{bil_pusat_ada}/{len(semua_pusat)}")
            with col4:
                st.metric("Pusat Lengkap", f"{bil_pusat_lengkap}/{len(semua_pusat)}")

            if (not status_all.empty) and ("KOD PPD" in status_all.columns):
                rekod = status_all[status_all["KOD PPD"].astype(str) == str(info['kod'])]
                if not rekod.empty:
                    r = rekod.iloc[-1]
                    st.info(f"Status terakhir: {r.get('STATUS','')} | Dihantar: {r.get('TARIKH HANTAR','')} | Disahkan: {r.get('TARIKH SAH','') or '-'}")

            if bil_pusat_lengkap < len(semua_pusat):
                st.warning(f"⚠️ {len(semua_pusat) - bil_pusat_lengkap} pusat belum lengkap. Anda masih boleh hantar, tapi JPN akan nampak status tak lengkap.")

            if st.button("📤 HANTAR ke JPN", use_container_width=True, type="primary"):
                if bil_petugas == 0:
                    st.error("Belum ada petugas dilantik. Jana Penempatan dulu.")
                else:
                    baris_hantar = {
                        "KOD PPD": info['kod'], "PPD": info['ppd_nama'],
                        "TARIKH HANTAR": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "BIL PUSAT": len(semua_pusat), "PUSAT ADA LANTIKAN": bil_pusat_ada,
                        "PUSAT LENGKAP": bil_pusat_lengkap, "BIL PETUGAS": bil_petugas,
                        "STATUS": "Dihantar", "TARIKH SAH": "",
                    }

                    def _hantar(df):
                        if not df.empty and "KOD PPD" not in df.columns:
                            raise ValueError("Format sheet status_hantar tidak dijangka - hubungi admin")
                        if df.empty:
                            return pd.DataFrame([baris_hantar])
                        df = df[df["KOD PPD"].astype(str) != str(info['kod'])]
                        return pd.concat([df, pd.DataFrame([baris_hantar])], ignore_index=True) if not df.empty else pd.DataFrame([baris_hantar])

                    if modify_sheet("status_hantar", _hantar):
                        flash("success", f"✅ PPD {info['ppd_nama']} berjaya hantar {bil_pusat_ada} pusat ({bil_petugas} petugas) ke JPN!")
                        st.rerun()
    else:
        if menu=="Semua PPD":
            st.header(f"🏛️ Semua PPD - {len(mapping_df)} Sekolah - File: {os.path.basename(file_used)}")
            st.dataframe(mapping_df, use_container_width=True)
        elif menu=="Sahkan PPD":
            st.header("✅ Sahkan PPD")
            status_all = read_sheet("status_hantar")
            if status_all.empty:
                st.info("Belum ada PPD yang hantar ke JPN.")
            else:
                st.dataframe(status_all, use_container_width=True)
            label_ppd = {kod: f"{nama} ({kod}) - {len(mapping_df[mapping_df['KOD PPD']==kod])} sekolah" for _, _, nama, kod in PPD_LIST}
            kod_sah = st.selectbox("Pilih PPD", list(label_ppd.keys()), format_func=lambda k: label_ppd[k])
            if st.button("✅ SAHKAN", use_container_width=True, type="primary"):
                def _sahkan(df):
                    if df.empty or "KOD PPD" not in df.columns or not (df["KOD PPD"].astype(str) == kod_sah).any():
                        raise ValueError(f"{label_ppd[kod_sah]} belum hantar ke JPN - tak boleh disahkan lagi.")
                    df = df.copy()
                    mask = df["KOD PPD"].astype(str) == kod_sah
                    df.loc[mask, "STATUS"] = "Disahkan"
                    df.loc[mask, "TARIKH SAH"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                    return df
                if modify_sheet("status_hantar", _sahkan):
                    flash("success", f"✅ {label_ppd[kod_sah]} DISAHKAN!")
                    st.rerun()
        else:
            st.header("📄 Jana Surat")
            st.info("Fungsi jana surat belum dibina (templat surat belum ditetapkan). Buat masa ini, muat turun senarai penempatan dalam CSV.")
            penempatan_all = read_sheet("penempatan_ppd")
            if penempatan_all.empty:
                st.warning("Belum ada data penempatan.")
            else:
                st.download_button("⬇️ Muat turun penempatan (CSV)", data=penempatan_all.to_csv(index=False).encode("utf-8-sig"), file_name="penempatan_ppd.csv", mime="text/csv", use_container_width=True)
