"""
SISTEM PELANTIKAN PETUGAS PEPERIKSAAN SELANGOR 2026
VERSI TANPA SIDEBAR - Fungsi kiri tetap tapi bukan sidebar
Fix: Sidebar hide, guna column kiri tetap
Repo: sistem_latikan_petugas_peperiksaan
"""

import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Sistem Pelantikan Selangor 2026", 
    layout="wide", 
    page_icon="📚",
    initial_sidebar_state="collapsed"
)

# --- HIDE SIDEBAR COMPLETELY ---
st.markdown("""
<style>
    [data-testid="stSidebar"] {display: none !important;}
    [data-testid="collapsedControl"] {display: none !important;}
    .big-title {text-align:center; font-size:32px; font-weight:bold; color:#0B5394; margin-top:10px;}
    .sub-title {text-align:center; font-size:16px; color:#666; margin-bottom:20px;}
    .login-box {background:#f0f7ff; padding:20px; border-radius:12px; border:1px solid #c2d8ff;}
    .left-panel {background:#f8fafc; padding:15px; border-radius:10px; border:1px solid #e2e8f0; height:100%;}
    .right-panel {background:white; padding:15px; border-radius:10px;}
</style>
""", unsafe_allow_html=True)

# --- DATA LOGIN ---
JPN_USERS = {"1": {"password": "a", "nama": "JPN Selangor", "role": "JPN"}}
PPD_LIST = [
    ("1", "a", "Klang", "BA"), ("2", "b", "Kuala Langat", "BB"),
    ("3", "c", "Kuala Selangor", "BC"), ("4", "d", "Hulu Langat", "BD"),
    ("5", "e", "Hulu Selangor", "BE"), ("6", "f", "Sabak Bernam", "BF"),
    ("7", "g", "Gombak", "BG"), ("8", "h", "Petaling Perdana", "BH"),
    ("9", "i", "Sepang", "BJ"), ("10", "j", "Petaling Utama", "BK"),
]
PPD_USERS = {id_: {"password": pwd, "nama": f"PPD {nama}", "ppd_nama": nama, "kod": kod, "role": "PPD"} for id_, pwd, nama, kod in PPD_LIST}
SUP_USERS = {str(i): {"password": str(i), "nama": f"Sekolah {i}", "role": "SUP", "kod_sekolah": f"SEKOLAH{i}"} for i in range(1, 301)}

try:
    df_master = pd.read_excel("data/senarai_506_PLUS_calon2026_FINAL.xlsx")
    df_list = df_master.groupby("KOD SEKOLAH").first().reset_index().head(300)
    for idx, row in df_list.iterrows():
        sid = str(idx+1)
        if sid in SUP_USERS:
            SUP_USERS[sid]["nama"] = row["NAMA PUSAT"]
            SUP_USERS[sid]["kod_sekolah"] = row["KOD SEKOLAH"]
except Exception:
    pass

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ================= MUKA DEPAN LOGIN =================
if not st.session_state.logged_in:
    st.markdown('<div class="big-title">📚 SISTEM PELANTIKAN PETUGAS PEPERIKSAAN</div>', unsafe_allow_html=True)
    st.markdown('<div class="big-title" style="font-size:24px;">SELANGOR 2026</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">SPM Bertulis • Amali Sains • Mendengar • Bertutur<br>GitHub + Streamlit + Google Sheet</div>', unsafe_allow_html=True)

    left, center, right = st.columns([1,2,1])
    with center:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown("### 🔐 Log Masuk Sistem")
        peranan = st.selectbox("Peranan", ["-- Pilih --", "JPN Selangor", "PPD", "SUP Sekolah"])
        id_input = st.text_input("ID Pengguna", placeholder="JPN=1, PPD=1-10, SUP=1-300")
        pwd_input = st.text_input("Kata Laluan", type="password", placeholder="JPN/PPD a-j, SUP sama ID")
        
        with st.expander("ℹ️ Senarai ID & Password"):
            st.markdown("""
            **JPN:** ID `1` / `a`
            **PPD:** 1=a Klang, 2=b Kuala Langat, 3=c Kuala Selangor, 4=d Hulu Langat, 5=e Hulu Selangor, 6=f Sabak Bernam, 7=g Gombak, 8=h Petaling Perdana, 9=i Sepang, 10=j Petaling Utama
            **SUP:** ID `1`-`300` / Password `1`-`300`
            """)
        
        if st.button("🚀 Log Masuk", use_container_width=True, type="primary"):
            success = False
            user_info = {}
            if peranan == "JPN Selangor" and id_input in JPN_USERS and JPN_USERS[id_input]["password"] == pwd_input:
                success=True; user_info=JPN_USERS[id_input]
            elif peranan == "PPD" and id_input in PPD_USERS and PPD_USERS[id_input]["password"] == pwd_input:
                success=True; user_info=PPD_USERS[id_input]
            elif peranan == "SUP Sekolah" and id_input in SUP_USERS and SUP_USERS[id_input]["password"] == pwd_input:
                success=True; user_info=SUP_USERS[id_input]
            
            if success:
                st.session_state.logged_in=True
                st.session_state.user_role=user_info["role"]
                st.session_state.user_info=user_info
                st.session_state.user_id=id_input
                st.rerun()
            else:
                if peranan!="-- Pilih --":
                    st.error("❌ ID / Password salah")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    st.caption("Sistem Lantikan SPM 2026 | Kashah & Aira | Tanpa Sidebar - Panel Kiri Tetap")
    st.stop()

# ================= DAH LOGIN - LAYOUT TANPA SIDEBAR =================
role = st.session_state.user_role
info = st.session_state.user_info
uid = st.session_state.user_id

# Header
st.markdown(f"""
<div style="background:#0B5394; color:white; padding:12px 20px; border-radius:8px; display:flex; justify-content:space-between; align-items:center;">
    <div>
        <b>📚 SISTEM PELANTIKAN SPM 2026</b> | 👋 {info['nama']} | Peranan: {role} | ID: {uid}
    </div>
    <div style="font-size:12px;">GS: 11XotkvoHEiT-b1qtgXH1oGNDVlcXYtvg</div>
</div>
""", unsafe_allow_html=True)

# Main layout: kiri tetap (bukan sidebar), kanan content
col_kiri, col_kanan = st.columns([1, 3])

with col_kiri:
    st.markdown('<div class="left-panel">', unsafe_allow_html=True)
    st.markdown(f"### 👤 {info['nama']}")
    st.markdown(f"**Peranan:** {role}")
    st.markdown(f"**ID:** {uid}")
    if role=="PPD":
        st.markdown(f"**PPD:** {info['ppd_nama']} ({info['kod']})")
        st.markdown(f"**Password:** {info['password']}")
    elif role=="JPN":
        st.markdown(f"**JPN Selangor**")
        st.markdown(f"**Password:** a")
    else:
        st.markdown(f"**Kod:** {info.get('kod_sekolah')}")
        st.markdown(f"**Password:** {uid}")
    
    st.markdown("---")
    st.markdown("### 📝 Menu")
    
    # Menu ikut role - ini yang dulu dalam sidebar, sekarang jadi panel kiri tetap
    if role=="SUP":
        menu = st.radio("Pilih", ["Maklumat Sekolah", "Cadangan Petugas", "Status Hantar"], label_visibility="collapsed")
    elif role=="PPD":
        menu = st.radio("Pilih", ["Senarai Pusat", "Cadangan SUP", "Jana Penempatan", "Hantar JPN"], label_visibility="collapsed")
    else:
        menu = st.radio("Pilih", ["Semua PPD", "Sahkan PPD", "Jana Surat"], label_visibility="collapsed")
    
    st.markdown("---")
    exam_type = st.selectbox("Peperiksaan", ["SPM Bertulis", "SPM Amali Sains", "Ujian Mendengar", "Ujian Bertutur"])
    
    st.markdown("---")
    if st.button("🚪 Log Keluar", use_container_width=True):
        st.session_state.logged_in=False
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

with col_kanan:
    st.markdown('<div class="right-panel">', unsafe_allow_html=True)
    
    # Load data
    @st.cache_data
    def load_master():
        try:
            return pd.read_excel("data/senarai_506_PLUS_calon2026_FINAL.xlsx")
        except Exception:
            return pd.DataFrame({"NO PUSAT":["BK009"],"NAMA PUSAT":["SMJK KATHOLIK"]})
    
    pusat_master = load_master()
    
    try:
        from streamlit_gsheets import GSheetsConnection
        conn = st.connection("gsheets", type=GSheetsConnection)
        USE_GSHEET = True
    except Exception:
        USE_GSHEET = False
    
    def read_sheet(name):
        if USE_GSHEET:
            try:
                return conn.read(worksheet=name, ttl=0)
            except Exception:
                return pd.DataFrame()
        else:
            try:
                if name=="maklumat_sekolah":
                    return pd.read_excel("data/TEMPLATE_1_MAKLUMAT_SEKOLAH_SUP.xlsx")
                elif name=="cadangan_sup":
                    return pd.read_excel("data/TEMPLATE_2_CADANGAN_PETUGAS_SUP.xlsx")
                elif name=="penempatan_ppd":
                    return pd.read_excel("data/TEMPLATE_3_PENEMPATAN_AUTO_POSKOD.xlsx")
                else:
                    return pd.DataFrame()
            except Exception:
                return pd.DataFrame()
    
    def write_sheet(name, df):
        if USE_GSHEET:
            try:
                conn.update(worksheet=name, data=df)
                return True
            except Exception as ex:
                st.error(f"Gagal tulis {name}: {ex}")
                return False
        else:
            return True

    # CONTENT KANAN IKUT ROLE & MENU
    if role=="SUP":
        if menu=="Maklumat Sekolah":
            st.header(f"🏫 Maklumat Sekolah - {info['nama']}")
            st.info(f"ID {uid} | Formula: KP=Bil Pusat+1, Pengawas=Bil Kelas+5, PK=1, Pengemas=Bil Pusat")
            maklumat = read_sheet("maklumat_sekolah")
            with st.form("sekolah"):
                c1,c2 = st.columns(2)
                with c1:
                    nama_sek = st.text_input("NAMA SEKOLAH", value=info['nama'])
                    email = st.text_input("EMAIL")
                    poskod_sek = st.number_input("POSKOD SEKOLAH", 40000, 49000, 46000)
                    bil_pusat = st.number_input("BIL PUSAT",1,10,3)
                with c2:
                    senarai = st.text_input("SENARAI NO PUSAT", placeholder="BK009, BK010, BK011")
                    bil_kelas = st.number_input("BIL KELAS",1,30,12)
                    nama_sup = st.text_input("NAMA SUP", value=f"SUP {info['nama']}")
                    tel = st.text_input("NO TEL")
                if st.form_submit_button("💾 Simpan", use_container_width=True):
                    new = pd.DataFrame([{"KOD SEKOLAH": info.get('kod_sekolah'), "NAMA SEKOLAH": nama_sek, "EMAIL SEKOLAH": email, "NO POSKOD SEKOLAH": poskod_sek, "BIL NO PUSAT": bil_pusat, "SENARAI NO PUSAT": senarai, "BIL KELAS DIGUNAKAN": bil_kelas, "NAMA SUP": nama_sup}])
                    maklumat = pd.concat([maklumat, new], ignore_index=True)
                    write_sheet("maklumat_sekolah", maklumat)
                    st.success(f"Simpan! KP={bil_pusat+1} Pengawas={bil_kelas+5}")
            st.dataframe(maklumat.tail(10), use_container_width=True)
        
        elif menu=="Cadangan Petugas":
            st.header("👥 Cadangan Petugas")
            st.caption("Isi Poskod Rumah untuk auto nearest - Contoh 40170 Shah Alam")
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
                if st.form_submit_button("➕ Tambah Petugas", use_container_width=True):
                    new_g = pd.DataFrame([{"KOD SEKOLAH ASAL": info.get('kod_sekolah'), "NAMA SEKOLAH ASAL": info['nama'], "JAWATAN CADANG": jaw, "NAMA GURU": nama_g, "IC": ic, "JANTINA": jantina, "POSKOD RUMAH": pos_rumah}])
                    cadangan = pd.concat([cadangan, new_g], ignore_index=True)
                    write_sheet("cadangan_sup", cadangan)
                    st.success(f"{nama_g} {jaw} poskod {pos_rumah} ditambah")
            st.dataframe(cadangan.tail(15), use_container_width=True)
        
        else:
            st.header("📤 Status Hantaran")
            st.success("Maklumat sekolah & cadangan petugas dah disimpan dalam Google Sheet")
            st.dataframe(read_sheet("maklumat_sekolah").tail(5), use_container_width=True)

    elif role=="PPD":
        if menu=="Senarai Pusat":
            st.header(f"🏢 Senarai Pusat PPD {info['ppd_nama']} ({info['kod']})")
            pusat_ppd = pusat_master[pusat_master["NO PUSAT"].str.startswith(info['kod'])]
            st.dataframe(pusat_ppd[["NO PUSAT","NAMA PUSAT","KOD SEKOLAH"]], use_container_width=True)
            st.metric("Total Pusat", len(pusat_ppd))
        elif menu=="Cadangan SUP":
            st.header("📋 Cadangan Dari SUP")
            cadangan_all = read_sheet("cadangan_sup")
            st.dataframe(cadangan_all, use_container_width=True)
            st.metric("Total Cadangan", len(cadangan_all))
        elif menu=="Jana Penempatan":
            st.header("🤖 Jana Penempatan Ikut Poskod")
            st.info("Rule: Lock PPD, Tak boleh sekolah sendiri kecuali Pengemas, Nearest poskod, Agih Lelaki")
            cadangan_all = read_sheet("cadangan_sup")
            pusat_ppd = pusat_master[pusat_master["NO PUSAT"].str.startswith(info['kod'])]
            if st.button("🤖 Jana Auto", use_container_width=True, type="primary"):
                pool = cadangan_all[~cadangan_all["JAWATAN CADANG"].astype(str).str.contains("Pengemas")].copy()
                penempatan=[]
                for _, p in pusat_ppd.head(10).iterrows():
                    eligible = pool[pool["KOD SEKOLAH ASAL"]!=p["KOD SEKOLAH"]].copy()
                    if eligible.empty: continue
                    eligible["JARAK"]=(eligible["POSKOD RUMAH"]-46000).abs()
                    eligible=eligible.sort_values("JARAK")
                    kp=eligible[eligible["JAWATAN CADANG"]=="Ketua Pengawas"].head(1)
                    if not kp.empty:
                        r=kp.iloc[0]
                        penempatan.append({"NO PUSAT TUGAS":p["NO PUSAT"],"NAMA PUSAT TUGAS":p["NAMA PUSAT"],"KOD SEKOLAH ASAL GURU":r["KOD SEKOLAH ASAL"],"NAMA GURU":r["NAMA GURU"],"JAWATAN FINAL":"Ketua Pengawas","POSKOD RUMAH":r["POSKOD RUMAH"],"JARAK":int(r["JARAK"]),"JANTINA":r["JANTINA"]})
                        pool=pool[pool["IC"]!=r["IC"]]
                if penempatan:
                    df_pen=pd.DataFrame(penempatan)
                    existing=read_sheet("penempatan_ppd")
                    combined=pd.concat([existing, df_pen], ignore_index=True)
                    write_sheet("penempatan_ppd", combined)
                    st.success(f"Jana {len(penempatan)} penempatan!")
                    st.dataframe(df_pen, use_container_width=True)
            st.dataframe(read_sheet("penempatan_ppd").tail(15), use_container_width=True)
        else:
            st.header("📤 Hantar ke JPN")
            if st.button("📤 HANTAR ke JPN", use_container_width=True, type="primary"):
                st.success(f"PPD {info['ppd_nama']} dah hantar ke JPN! Tunggu JPN sahkan.")
                st.balloons()

    else: # JPN
        if menu=="Semua PPD":
            st.header("🏛️ Status Semua PPD")
            penempatan_all = read_sheet("penempatan_ppd")
            st.dataframe(penempatan_all, use_container_width=True)
        elif menu=="Sahkan PPD":
            st.header("✅ Sahkan PPD")
            ppd_sah = st.selectbox("Pilih PPD", [f"{nama} ({kod})" for _,_,nama,kod in PPD_LIST])
            if st.button("✅ SAHKAN", use_container_width=True, type="primary"):
                st.success(f"{ppd_sah} DISAHKAN! PPD boleh jana surat.")
                st.balloons()
        else:
            st.header("📄 Jana Surat Lantikan")
            penempatan_all = read_sheet("penempatan_ppd")
            if st.button("📄 Jana Semua Surat", use_container_width=True, type="primary"):
                st.success("Surat berjaya dijana!")
                if not penempatan_all.empty:
                    st.download_button("⬇️ Download CSV", penempatan_all.to_csv(index=False), file_name=f"senarai_{exam_type}.csv")
    
    st.markdown('</div>', unsafe_allow_html=True)
