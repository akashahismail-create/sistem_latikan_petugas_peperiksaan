"""
SISTEM PELANTIKAN PETUGAS PEPERIKSAAN SELANGOR 2026
Muka Depan + Login ID Password
JPN: 1 user | PPD: 10 user | SUP: 300 user
Repo: sistem_latikan_petugas_peperiksaan
Link GS: 11XotkvoHEiT-b1qtgXH1oGNDVlcXYtvg
"""

import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Sistem Pelantikan Selangor 2026", layout="centered", page_icon="📚")

# --- DATA LOGIN ---
# JPN
JPN_USERS = {
    "1": {"password": "a", "nama": "JPN Selangor", "role": "JPN"}
}

# PPD - 10 PPD
PPD_LIST = [
    ("1", "a", "Klang", "BA"),
    ("2", "b", "Kuala Langat", "BB"),
    ("3", "c", "Kuala Selangor", "BC"),
    ("4", "d", "Hulu Langat", "BD"),
    ("5", "e", "Hulu Selangor", "BE"),
    ("6", "f", "Sabak Bernam", "BF"),
    ("7", "g", "Gombak", "BG"),
    ("8", "h", "Petaling Perdana", "BH"),
    ("9", "i", "Sepang", "BJ"),
    ("10", "j", "Petaling Utama", "BK"),
]

PPD_USERS = {}
for id_, pwd, nama, kod in PPD_LIST:
    PPD_USERS[id_] = {"password": pwd, "nama": f"PPD {nama}", "ppd_nama": nama, "kod": kod, "role": "PPD"}

# SUP - 300 sekolah (dummy 1-300, ikut KOD SEKOLAH nanti)
# Untuk demo kita buat 1-300, password sama dengan id
SUP_USERS = {}
for i in range(1, 301):
    SUP_USERS[str(i)] = {"password": str(i), "nama": f"Sekolah {i}", "role": "SUP", "kod_sekolah": f"SEKOLAH{i}"}

# Kalau ada data master sekolah, override nama
try:
    df_sekolah_master = pd.read_excel("data/senarai_506_PLUS_calon2026_FINAL.xlsx")
    df_sekolah_list = df_sekolah_master.groupby("KOD SEKOLAH").first().reset_index().head(300)
    for idx, row in df_sekolah_list.iterrows():
        sid = str(idx+1)
        if sid in SUP_USERS:
            SUP_USERS[sid]["nama"] = row["NAMA PUSAT"]
            SUP_USERS[sid]["kod_sekolah"] = row["KOD SEKOLAH"]
except:
    pass

# --- SESSION ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "user_info" not in st.session_state:
    st.session_state.user_info = {}

# --- MUKA DEPAN ---
if not st.session_state.logged_in:
    st.markdown("""
    <style>
    .big-title {text-align:center; font-size:32px; font-weight:bold; color:#0B5394; margin-top:20px;}
    .sub-title {text-align:center; font-size:18px; color:#666; margin-bottom:30px;}
    .login-box {background:#f0f7ff; padding:25px; border-radius:15px; border:1px solid #c2d8ff;}
    </style>
    <div class="big-title">📚 SISTEM PELANTIKAN PETUGAS PEPERIKSAAN</div>
    <div class="big-title" style="font-size:24px; margin-top:5px;">SELANGOR 2026</div>
    <div class="sub-title">SPM Bertulis • Ujian Amali Sains • Ujian Mendengar • Ujian Bertutur<br>GitHub + Streamlit + Google Sheet</div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🔐 Sila Log Masuk")
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.container():
            st.markdown('<div class="login-box">', unsafe_allow_html=True)
            
            peranan = st.selectbox("Pilih Peranan", ["-- Pilih --", "JPN Selangor", "PPD", "SUP Sekolah"], index=0)
            
            id_input = st.text_input("ID Pengguna", placeholder="Contoh: JPN=1, PPD=1-10, SUP=1-300")
            pwd_input = st.text_input("Kata Laluan", type="password", placeholder="JPN/PPD: a-j, SUP: sama dengan ID")
            
            # Info bantuan
            with st.expander("ℹ️ Lihat Senarai ID & Password"):
                st.markdown("""
                **JPN Selangor (1 pengguna):**
                - ID: `1` | Password: `a`

                **PPD (10 pengguna):**
                - ID: `1` Password: `a` → PPD Klang (BA)
                - ID: `2` Password: `b` → PPD Kuala Langat (BB)
                - ID: `3` Password: `c` → PPD Kuala Selangor (BC)
                - ID: `4` Password: `d` → PPD Hulu Langat (BD)
                - ID: `5` Password: `e` → PPD Hulu Selangor (BE)
                - ID: `6` Password: `f` → PPD Sabak Bernam (BF)
                - ID: `7` Password: `g` → PPD Gombak (BG)
                - ID: `8` Password: `h` → PPD Petaling Perdana (BH)
                - ID: `9` Password: `i` → PPD Sepang (BJ)
                - ID: `10` Password: `j` → PPD Petaling Utama (BK)

                **SUP Sekolah (300 pengguna):**
                - ID: `1` Password: `1` → Sekolah 1
                - ID: `2` Password: `2` → Sekolah 2
                - ...
                - ID: `300` Password: `300` → Sekolah 300
                """)
            
            login_btn = st.button("🚀 Log Masuk", use_container_width=True, type="primary")
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    if login_btn:
        success = False
        user_info = {}
        
        if peranan == "JPN Selangor":
            if id_input in JPN_USERS and JPN_USERS[id_input]["password"] == pwd_input:
                success = True
                user_info = JPN_USERS[id_input]
        elif peranan == "PPD":
            if id_input in PPD_USERS and PPD_USERS[id_input]["password"] == pwd_input:
                success = True
                user_info = PPD_USERS[id_input]
        elif peranan == "SUP Sekolah":
            if id_input in SUP_USERS and SUP_USERS[id_input]["password"] == pwd_input:
                success = True
                user_info = SUP_USERS[id_input]
        else:
            st.error("Sila pilih peranan dulu")
        
        if success:
            st.session_state.logged_in = True
            st.session_state.user_role = user_info["role"]
            st.session_state.user_info = user_info
            st.session_state.user_id = id_input
            st.success(f"✅ Berjaya log masuk sebagai {user_info['nama']}")
            st.rerun()
        else:
            if peranan != "-- Pilih --":
                st.error("❌ ID atau Kata Laluan salah! Sila rujuk senarai ID.")
    
    st.markdown("---")
    st.caption("Sistem Pelantikan SPM 2026 | Kashah & Aira | Repo: sistem_latikan_petugas_peperiksaan | GS ID: 11XotkvoHEiT-b1qtgXH1oGNDVlcXYtvg")
    st.stop()

# --- JIKA DAH LOGIN ---
# Header logged in
role = st.session_state.user_role
info = st.session_state.user_info
uid = st.session_state.user_id

col_head1, col_head2 = st.columns([3,1])
with col_head1:
    st.markdown(f"### 👋 Selamat Datang, {info['nama']}")
    st.caption(f"Peranan: {role} | ID: {uid} | Kod: {info.get('kod','-')} | {info.get('kod_sekolah','')}")
with col_head2:
    if st.button("🚪 Log Keluar"):
        st.session_state.logged_in = False
        st.session_state.user_role = None
        st.session_state.user_info = {}
        st.rerun()

# --- LOAD DATA ---
@st.cache_data
def load_master():
    try:
        pusat = pd.read_excel("data/senarai_506_PLUS_calon2026_FINAL.xlsx")
    except:
        pusat = pd.DataFrame({"NO PUSAT":["BK009"],"NAMA PUSAT":["SMJK KATHOLIK"],"PPD":["Petaling Utama"]})
    return pusat

pusat_master = load_master()

# Try GSheets
try:
    from streamlit_gsheets import GSheetsConnection
    conn = st.connection("gsheets", type=GSheetsConnection)
    USE_GSHEET = True
except:
    USE_GSHEET = False

def read_sheet(name):
    if USE_GSHEET:
        try:
            return conn.read(worksheet=name, ttl=0)
        except:
            return pd.DataFrame()
    else:
        # fallback local
        try:
            if name=="maklumat_sekolah":
                return pd.read_excel("data/TEMPLATE_1_MAKLUMAT_SEKOLAH_SUP.xlsx")
            elif name=="cadangan_sup":
                return pd.read_excel("data/TEMPLATE_2_CADANGAN_PETUGAS_SUP.xlsx")
            elif name=="penempatan_ppd":
                return pd.read_excel("data/TEMPLATE_3_PENEMPATAN_AUTO_POSKOD.xlsx")
            else:
                return pd.DataFrame()
        except:
            return pd.DataFrame()

def write_sheet(name, df):
    if USE_GSHEET:
        try:
            conn.update(worksheet=name, data=df)
            return True
        except as e:
            st.error(f"Gagal tulis {name}: {e}")
            return False
    else:
        return True

# --- CONTENT IKUT ROLE ---
exam_type = st.selectbox("Pilih Jenis Peperiksaan", ["SPM Bertulis", "SPM Ujian Amali Sains", "Ujian Mendengar", "Ujian Bertutur"])

if role == "SUP":
    st.header(f"🏫 SUP Sekolah - {info['nama']} ({exam_type})")
    st.info(f"Kod Sekolah: {info.get('kod_sekolah')} | ID SUP: {uid} | Password: {uid} | Formula: KP=Bil Pusat+1, Pengawas=Bil Kelas+5")
    
    maklumat = read_sheet("maklumat_sekolah")
    
    with st.form("form_sekolah"):
        col_a, col_b = st.columns(2)
        with col_a:
            nama_sek = st.text_input("NAMA SEKOLAH", value=info['nama'])
            email = st.text_input("EMAIL SEKOLAH")
            poskod_sek = st.number_input("POSKOD SEKOLAH *", 40000, 49000, 46000)
            bil_pusat = st.number_input("BIL PUSAT *", 1, 10, 3)
        with col_b:
            senarai_pusat = st.text_input("SENARAI NO PUSAT *", placeholder="BK009, BK010, BK011")
            bil_kelas = st.number_input("BIL KELAS *", 1, 30, 12)
            nama_sup = st.text_input("NAMA SUP", value=f"SUP {info['nama']}")
            tel = st.text_input("NO TEL SEKOLAH")
        
        if st.form_submit_button("💾 Simpan Maklumat Sekolah"):
            new = pd.DataFrame([{"KOD SEKOLAH": info.get('kod_sekolah'), "NAMA SEKOLAH": nama_sek, "EMAIL SEKOLAH": email, "NO POSKOD SEKOLAH": poskod_sek, "BIL NO PUSAT": bil_pusat, "SENARAI NO PUSAT": senarai_pusat, "BIL KELAS DIGUNAKAN": bil_kelas, "NAMA SUP": nama_sup}])
            maklumat = pd.concat([maklumat, new], ignore_index=True)
            write_sheet("maklumat_sekolah", maklumat)
            st.success(f"Simpan! KP={bil_pusat+1} Pengawas={bil_kelas+5}")
    
    st.subheader("Cadangan Petugas (Isi Poskod Rumah Untuk Nearest)")
    cadangan = read_sheet("cadangan_sup")
    with st.form("form_guru"):
        c1,c2,c3 = st.columns(3)
        with c1:
            jaw = st.selectbox("JAWATAN", ["Ketua Pengawas","Timbalan Ketua Pengawas","Pengawas Peperiksaan","Pengemas Bilik","Penyelia Kawasan"])
            nama_g = st.text_input("NAMA GURU *")
        with c2:
            ic = st.text_input("IC *")
            jantina = st.selectbox("JANTINA", ["L","P"])
        with c3:
            pos_rumah = st.number_input("POSKOD RUMAH *", 40000, 49000, 46000, help="Contoh 40170 Shah Alam")
            if st.form_submit_button("Tambah"):
                new_g = pd.DataFrame([{"KOD SEKOLAH ASAL": info.get('kod_sekolah'), "NAMA SEKOLAH ASAL": nama_sek, "JAWATAN CADANG": jaw, "NAMA GURU": nama_g, "IC": ic, "JANTINA": jantina, "POSKOD RUMAH": pos_rumah}])
                cadangan = pd.concat([cadangan, new_g], ignore_index=True)
                write_sheet("cadangan_sup", cadangan)
                st.success(f"{nama_g} {jaw} poskod {pos_rumah} ditambah")
    
    st.dataframe(cadangan.tail(10), use_container_width=True)

elif role == "PPD":
    st.header(f"🏢 PPD {info['ppd_nama']} ({info['kod']}) - {exam_type}")
    st.info(f"ID: {uid} | Password: {info['password']} | Kod PPD: {info['kod']} | Rule: Lock {info['kod']}, Tak boleh sekolah sendiri, Nearest poskod, Agih Lelaki")
    
    pusat_ppd = pusat_master[pusat_master["NO PUSAT"].str.startswith(info['kod'])]
    st.dataframe(pusat_ppd[["NO PUSAT","NAMA PUSAT"]].head(20), use_container_width=True)
    
    cadangan_all = read_sheet("cadangan_sup")
    st.subheader(f"Cadangan SUP ({len(cadangan_all)} orang)")
    st.dataframe(cadangan_all.head(20), use_container_width=True)
    
    if st.button("🤖 Jana Auto Penempatan Ikut Poskod"):
        # simple auto nearest
        pool = cadangan_all[~cadangan_all["JAWATAN CADANG"].astype(str).str.contains("Pengemas")].copy()
        penempatan = []
        for _, p in pusat_ppd.head(10).iterrows():
            no = p["NO PUSAT"]
            kod_sek_pusat = p["KOD SEKOLAH"]
            eligible = pool[pool["KOD SEKOLAH ASAL"]!=kod_sek_pusat].copy()
            if eligible.empty: continue
            # assume poskod pusat 46000 for demo, real need mapping
            eligible["JARAK"] = (eligible["POSKOD RUMAH"]-46000).abs()
            eligible = eligible.sort_values("JARAK")
            kp = eligible[eligible["JAWATAN CADANG"]=="Ketua Pengawas"].head(1)
            if not kp.empty:
                r=kp.iloc[0]
                penempatan.append({"NO PUSAT TUGAS":no,"NAMA PUSAT TUGAS":p["NAMA PUSAT"],"KOD SEKOLAH ASAL GURU":r["KOD SEKOLAH ASAL"],"NAMA GURU":r["NAMA GURU"],"JAWATAN FINAL":"Ketua Pengawas","POSKOD RUMAH":r["POSKOD RUMAH"],"JARAK":int(r["JARAK"]),"JANTINA":r["JANTINA"]})
                pool=pool[pool["IC"]!=r["IC"]]
        
        if penempatan:
            df_pen = pd.DataFrame(penempatan)
            existing = read_sheet("penempatan_ppd")
            combined = pd.concat([existing, df_pen], ignore_index=True)
            write_sheet("penempatan_ppd", combined)
            st.success(f"Jana {len(penempatan)} penempatan!")
            st.dataframe(df_pen, use_container_width=True)
    
    if st.button("📤 HANTAR ke JPN"):
        st.success(f"PPD {info['ppd_nama']} hantar ke JPN! JPN boleh sahkan.")

elif role == "JPN":
    st.header(f"🏛️ JPN Selangor - {exam_type}")
    st.info("ID: 1 | Password: a | Kuasa: Sahkan semua PPD & Jana Surat")
    
    penempatan_all = read_sheet("penempatan_ppd")
    st.dataframe(penempatan_all.head(30), use_container_width=True)
    
    col1, col2 = st.columns(2)
    with col1:
        ppd_sah = st.selectbox("Pilih PPD untuk SAH", [f"{nama} ({kod})" for _,_,nama,kod in PPD_LIST])
        if st.button("✅ SAHKAN PPD"):
            st.success(f"{ppd_sah} DISAHKAN! PPD boleh jana surat sekarang.")
    with col2:
        if st.button("📄 Jana Surat Lantikan (Semua PPD)"):
            st.success("Surat berjaya dijana! (Demo)")
            if not penempatan_all.empty:
                st.download_button("⬇️ Download CSV", penempatan_all.to_csv(index=False), file_name=f"senarai_{exam_type}.csv")

st.markdown("---")
st.caption(f"Login sebagai {info['nama']} | ID {uid} | Repo: sistem_latikan_petugas_peperiksaan | GS: 11XotkvoHEiT-b1qtgXH1oGNDVlcXYtvg")
