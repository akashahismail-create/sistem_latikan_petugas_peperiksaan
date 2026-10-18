
"""
SISTEM LANTIKAN SPM 2026 - SELANGOR - FULL GITHUB + STREAMLIT + GOOGLE SHEET
Link Google Sheet: https://docs.google.com/spreadsheets/d/11XotkvoHEiT-b1qtgXH1oGNDVlcXYtvg/edit
Cara connect: Streamlit Cloud -> Settings -> Secrets -> Paste isi secrets.toml.template
"""

import streamlit as st
import pandas as pd
import math
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Sistem Lantikan SPM 2026 Selangor", layout="wide", page_icon="📚")

st.title("📚 Sistem Lantikan SPM 2026 - Selangor")
st.caption("Full GitHub + Streamlit + Google Sheet | Link: 11XotkvoHEiT-b1qtgXH1oGNDVlcXYtvg")

# --- CONNECT GOOGLE SHEET ---
# Try GSheets connection, fallback to session_state if fail (for local test)
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    USE_GSHEET = True
    st.sidebar.success("✅ Connected Google Sheet")
except Exception as e:
    USE_GSHEET = False
    st.sidebar.warning(f"⚠️ Guna Dummy Local (Google Sheet belum connect): {e}")

def read_sheet(sheet_name):
    if USE_GSHEET:
        try:
            df = conn.read(worksheet=sheet_name, ttl=0)
            return df
        except:
            return pd.DataFrame()
    else:
        # fallback local
        try:
            if sheet_name=="maklumat_sekolah":
                return pd.read_excel("data/TEMPLATE_1_MAKLUMAT_SEKOLAH_SUP.xlsx")
            elif sheet_name=="cadangan_sup":
                return pd.read_excel("data/TEMPLATE_2_CADANGAN_PETUGAS_SUP.xlsx")
            elif sheet_name=="penempatan_ppd":
                return pd.read_excel("data/TEMPLATE_3_PENEMPATAN_AUTO_POSKOD.xlsx")
            else:
                return pd.DataFrame()
        except:
            return pd.DataFrame()

def write_sheet(sheet_name, df):
    if USE_GSHEET:
        try:
            conn.update(worksheet=sheet_name, data=df)
            return True
        except Exception as e:
            st.error(f"Gagal tulis ke Google Sheet {sheet_name}: {e}")
            return False
    else:
        # save to session
        if sheet_name=="maklumat_sekolah":
            st.session_state.maklumat_sekolah = df
        elif sheet_name=="cadangan_sup":
            st.session_state.cadangan_sup = df
        elif sheet_name=="penempatan_ppd":
            st.session_state.penempatan_ppd = df
        return True

# Init session if not using gsheet
if "maklumat_sekolah" not in st.session_state:
    st.session_state.maklumat_sekolah = read_sheet("maklumat_sekolah")
if "cadangan_sup" not in st.session_state:
    st.session_state.cadangan_sup = read_sheet("cadangan_sup")
if "penempatan_ppd" not in st.session_state:
    st.session_state.penempatan_ppd = read_sheet("penempatan_ppd")

# Load master
@st.cache_data
def load_master():
    try:
        pusat = pd.read_excel("data/senarai_506_PLUS_calon2026_FINAL.xlsx")
    except:
        pusat = pd.DataFrame({"NO PUSAT":["BK009","BK010"],"NAMA PUSAT":["SMJK KATHOLIK","SMJK KATHOLIK"],"PPD":["Petaling Utama","Petaling Utama"]})
    return pusat

pusat_master = load_master()

PPD_MAP = {"BA":"Klang","BB":"Kuala Langat","BC":"Kuala Selangor","BD":"Hulu Langat","BE":"Hulu Selangor","BF":"Sabak Bernam","BG":"Gombak","BH":"Petaling Perdana","BJ":"Sepang","BK":"Petaling Utama"}

# Sidebar login
role = st.sidebar.selectbox("Peranan", ["SUP Sekolah","PPD","JPN Selangor"])
exam_type = st.sidebar.selectbox("Peperiksaan", ["SPM Bertulis","SPM Amali Sains","Ujian Mendengar","Ujian Bertutur"])
ppd_pilih = None
kod_ppd_pilih = None
if role=="PPD":
    ppd_pilih = st.sidebar.selectbox("PPD", list(PPD_MAP.values()))
    kod_ppd_pilih = [k for k,v in PPD_MAP.items() if v==ppd_pilih][0]

st.sidebar.markdown(f"**Google Sheet ID:** `11XotkvoHEiT-b1qtgXH1oGNDVlcXYtvg`")

tab_sup, tab_ppd, tab_jpn = st.tabs(["🏫 SUP","🏢 PPD","🏛️ JPN"])

with tab_sup:
    st.header(f"SUP - {exam_type}")
    maklumat = read_sheet("maklumat_sekolah") if USE_GSHEET else st.session_state.maklumat_sekolah
    cadangan = read_sheet("cadangan_sup") if USE_GSHEET else st.session_state.cadangan_sup
    
    col1, col2 = st.columns(2)
    with col1:
        with st.form("sekolah"):
            kod = st.text_input("KOD SEKOLAH *")
            nama = st.text_input("NAMA SEKOLAH *")
            email = st.text_input("EMAIL")
            poskod = st.number_input("POSKOD SEKOLAH *", 40000, 49000, 46000)
            bil_pusat = st.number_input("BIL PUSAT *",1,10,3)
            senarai = st.text_input("SENARAI PUSAT *", placeholder="BK009, BK010, BK011")
            bil_kelas = st.number_input("BIL KELAS *",1,30,12)
            sup_name = st.text_input("NAMA SUP *")
            if st.form_submit_button("Simpan Sekolah"):
                new = pd.DataFrame([{"KOD SEKOLAH":kod.upper(),"NAMA SEKOLAH":nama.upper(),"EMAIL SEKOLAH":email,"NO POSKOD SEKOLAH":poskod,"BIL NO PUSAT":bil_pusat,"SENARAI NO PUSAT":senarai.upper(),"BIL KELAS DIGUNAKAN":bil_kelas,"NAMA SUP":sup_name}])
                maklumat = pd.concat([maklumat, new], ignore_index=True)
                write_sheet("maklumat_sekolah", maklumat)
                st.success(f"Simpan! Formula KP={bil_pusat+1} Pengawas={bil_kelas+5}")
    
    with col2:
        if bil_pusat and bil_kelas:
            st.info(f"KP: {bil_pusat+1} | Pengawas: {bil_kelas+5} | PK:1 | Pengemas:{bil_pusat} | Penyelia:1 | Total: {bil_pusat+1+bil_kelas+5+1+bil_pusat+1}")
    
    st.subheader("Borang Cadangan Petugas")
    with st.form("guru"):
        c1,c2,c3 = st.columns(3)
        with c1:
            kod_asal = st.text_input("KOD SEKOLAH ASAL *")
            jaw = st.selectbox("JAWATAN *",["Ketua Pengawas","Timbalan Ketua Pengawas","Pengawas Peperiksaan","Pengemas Bilik","Penyelia Kawasan"])
        with c2:
            nama_g = st.text_input("NAMA GURU *")
            ic = st.text_input("IC *")
            jant = st.selectbox("JANTINA",["L","P"])
        with c3:
            pos_rumah = st.number_input("POSKOD RUMAH *",40000,49000,46000, help="40170 Shah Alam untuk nearest")
            tel = st.text_input("NO TEL")
        if st.form_submit_button("Tambah Petugas"):
            new_g = pd.DataFrame([{"KOD SEKOLAH ASAL":kod_asal.upper(),"JAWATAN CADANG":jaw,"NAMA GURU":nama_g.upper(),"IC":ic,"JANTINA":jant,"POSKOD RUMAH":pos_rumah,"NO TELEFON GURU":tel}])
            cadangan = pd.concat([cadangan, new_g], ignore_index=True)
            write_sheet("cadangan_sup", cadangan)
            st.success(f"{nama_g} {jaw} poskod {pos_rumah} ditambah!")
    
    st.dataframe(cadangan.tail(20), use_container_width=True)

with tab_ppd:
    st.header(f"PPD - {exam_type}")
    if kod_ppd_pilih:
        st.info(f"PPD {ppd_pilih} ({kod_ppd_pilih}) - Lock PPD, Tak boleh sekolah sendiri kecuali Pengemas, Nearest ikut poskod, Agih Lelaki")
        pusat_ppd = pusat_master[pusat_master["NO PUSAT"].str.startswith(kod_ppd_pilih)]
    else:
        pusat_ppd = pusat_master[pusat_master["NO PUSAT"].str.startswith("BK")]
        kod_ppd_pilih="BK"
    
    st.dataframe(pusat_ppd[["NO PUSAT","NAMA PUSAT","KOD SEKOLAH"]].head(20), use_container_width=True)
    
    cadangan_all = read_sheet("cadangan_sup") if USE_GSHEET else st.session_state.cadangan_sup
    st.subheader(f"Cadangan SUP ({len(cadangan_all)} orang)")
    st.dataframe(cadangan_all.head(20), use_container_width=True)
    
    if st.button("🤖 Jana Auto Penempatan Ikut Poskod"):
        # simple auto
        kawasan_poskod = {"CB85":46000,"CB86":46300,"CB87":46000,"CB89":47810,"CB90":52200,"CB01":41000}
        pusat_ppd["POSKOD_PUSAT"] = pusat_ppd["KOD KAWASAN"].map(kawasan_poskod).fillna(46000) if "KOD KAWASAN" in pusat_ppd.columns else 46000
        
        pool = cadangan_all[~cadangan_all["JAWATAN CADANG"].astype(str).str.contains("Pengemas")].copy()
        penempatan = []
        for _, p in pusat_ppd.head(10).iterrows():
            no = p["NO PUSAT"]
            kod_sek_pusat = p["KOD SEKOLAH"]
            pos_pusat = p["POSKOD_PUSAT"] if "POSKOD_PUSAT" in p else 46000
            eligible = pool[pool["KOD SEKOLAH ASAL"]!=kod_sek_pusat].copy()
            if eligible.empty: continue
            eligible["JARAK"] = (eligible["POSKOD RUMAH"]-pos_pusat).abs()
            eligible = eligible.sort_values("JARAK")
            kp = eligible[eligible["JAWATAN CADANG"]=="Ketua Pengawas"].head(1)
            if not kp.empty:
                r=kp.iloc[0]
                penempatan.append({"NO PUSAT TUGAS":no,"NAMA PUSAT TUGAS":p["NAMA PUSAT"],"KOD SEKOLAH ASAL GURU":r["KOD SEKOLAH ASAL"],"NAMA GURU":r["NAMA GURU"],"JAWATAN FINAL":"Ketua Pengawas","POSKOD RUMAH":r["POSKOD RUMAH"],"POSKOD PUSAT":pos_pusat,"JARAK":int(r["JARAK"]),"JANTINA":r["JANTINA"]})
                pool=pool[pool["IC"]!=r["IC"]]
        
        if penempatan:
            df_pen = pd.DataFrame(penempatan)
            existing = read_sheet("penempatan_ppd") if USE_GSHEET else st.session_state.penempatan_ppd
            combined = pd.concat([existing, df_pen], ignore_index=True)
            write_sheet("penempatan_ppd", combined)
            st.success(f"Jana {len(penempatan)} penempatan!")
            st.dataframe(df_pen, use_container_width=True)

with tab_jpn:
    st.header("JPN - Sahkan")
    penempatan_all = read_sheet("penempatan_ppd") if USE_GSHEET else st.session_state.penempatan_ppd
    st.dataframe(penempatan_all.head(20), use_container_width=True)
    if st.button("✅ SAHKAN PPD"):
        st.success("PPD Disahkan! PPD boleh jana surat.")
