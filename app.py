"""
SISTEM PELANTIKAN PETUGAS PEPERIKSAAN SELANGOR 2026
MUKA DEPAN BARU: SUP Pilih Daerah -> Pilih Sekolah -> Password (Tak perlu ID)
Total 369 sekolah termasuk persendirian, boleh tambah
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

# Hide sidebar
st.markdown("""
<style>
    [data-testid="stSidebar"] {display: none !important;}
    [data-testid="collapsedControl"] {display: none !important;}
    .big-title {text-align:center; font-size:30px; font-weight:bold; color:#0B5394; margin-top:10px;}
    .sub-title {text-align:center; font-size:15px; color:#666; margin-bottom:15px;}
    .login-box {background:#f0f7ff; padding:20px; border-radius:12px; border:1px solid #c2d8ff;}
    .left-panel {background:#f8fafc; padding:15px; border-radius:10px; border:1px solid #e2e8f0;}
</style>
""", unsafe_allow_html=True)

# --- LOAD MAPPING 369 SEKOLAH ---
@st.cache_data
def load_mapping():
    try:
        df = pd.read_excel("data/SENARAI_ID_SUP_BY_DAERAH.xlsx")
    except:
        try:
            df = pd.read_excel("/mnt/data/SENARAI_ID_SUP_BY_DAERAH.xlsx")
        except:
            # fallback dummy 10
            df = pd.DataFrame([
                {"ID":1,"PASSWORD":"1","KOD SEKOLAH":"BEB8653","NAMA SEKOLAH":"SMJK KATHOLIK","PPD":"Petaling Utama","KOD PPD":"BK","BIL PUSAT":3,"SENARAI PUSAT":"BK009,BK010,BK011"},
            ])
    return df

mapping_df = load_mapping()

# PPD users
PPD_LIST = [
    ("1", "a", "Klang", "BA"), ("2", "b", "Kuala Langat", "BB"),
    ("3", "c", "Kuala Selangor", "BC"), ("4", "d", "Hulu Langat", "BD"),
    ("5", "e", "Hulu Selangor", "BE"), ("6", "f", "Sabak Bernam", "BF"),
    ("7", "g", "Gombak", "BG"), ("8", "h", "Petaling Perdana", "BH"),
    ("9", "i", "Sepang", "BJ"), ("10", "j", "Petaling Utama", "BK"),
]
PPD_USERS = {f"{nama}": {"id": id_, "password": pwd, "nama": f"PPD {nama}", "ppd_nama": nama, "kod": kod} for id_, pwd, nama, kod in PPD_LIST}
PPD_BY_KOD = {kod: {"id": id_, "password": pwd, "nama": nama} for id_, pwd, nama, kod in PPD_LIST}

JPN_USERS = {"1": {"password": "a", "nama": "JPN Selangor", "role": "JPN"}}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ================= MUKA DEPAN =================
if not st.session_state.logged_in:
    st.markdown('<div class="big-title">📚 SISTEM PELANTIKAN PETUGAS PEPERIKSAAN</div>', unsafe_allow_html=True)
    st.markdown('<div class="big-title" style="font-size:22px;">SELANGOR 2026</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">369 Sekolah Termasuk Persendirian • Boleh Tambah Sekolah Baru<br>SPM Bertulis • Amali Sains • Mendengar • Bertutur</div>', unsafe_allow_html=True)

    left, center, right = st.columns([1,2,1])
    with center:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown("### 🔐 Log Masuk")
        
        peranan = st.selectbox("1️⃣ Pilih Peranan", ["-- Pilih --", "JPN Selangor", "PPD", "SUP Sekolah"])
        
        # JPN
        if peranan == "JPN Selangor":
            st.info("JPN Selangor: 1 pengguna")
            jpn_id = st.text_input("ID", value="1", disabled=True)
            jpn_pwd = st.text_input("Kata Laluan", type="password", placeholder="a")
            login_btn = st.button("🚀 Log Masuk JPN", use_container_width=True, type="primary")
            if login_btn:
                if jpn_id=="1" and jpn_pwd=="a":
                    st.session_state.logged_in=True
                    st.session_state.user_role="JPN"
                    st.session_state.user_info={"nama":"JPN Selangor","role":"JPN","id":"1"}
                    st.rerun()
                else:
                    st.error("❌ Password salah - JPN password a")
        
        # PPD - Pilih Daerah terus
        elif peranan == "PPD":
            st.markdown("#### 2️⃣ Pilih Daerah (PPD)")
            ppd_daerah = st.selectbox("Daerah", ["-- Pilih Daerah --", "Klang", "Kuala Langat", "Kuala Selangor", "Hulu Langat", "Hulu Selangor", "Sabak Bernam", "Gombak", "Petaling Perdana", "Sepang", "Petaling Utama"])
            
            if ppd_daerah != "-- Pilih Daerah --":
                ppd_info = PPD_USERS[ppd_daerah]
                st.success(f"PPD {ppd_daerah} - ID {ppd_info['id']} - Kod {ppd_info['kod']}")
                ppd_pwd = st.text_input(f"Kata Laluan PPD {ppd_daerah}", type="password", placeholder=f"Password {ppd_info['password']} (huruf {chr(96+int(ppd_info['id']))})")
                login_btn = st.button(f"🚀 Log Masuk {ppd_daerah}", use_container_width=True, type="primary")
                if login_btn:
                    if ppd_pwd == ppd_info['password']:
                        st.session_state.logged_in=True
                        st.session_state.user_role="PPD"
                        st.session_state.user_info={"nama":f"PPD {ppd_daerah}","ppd_nama":ppd_daerah,"kod":ppd_info['kod'],"password":ppd_info['password'],"id":ppd_info['id'],"role":"PPD"}
                        st.rerun()
                    else:
                        st.error(f"❌ Password salah - Password PPD {ppd_daerah} adalah {ppd_info['password']}")
        
        # SUP - Pilih Daerah -> Pilih Sekolah -> Password sahaja (tak perlu ID)
        elif peranan == "SUP Sekolah":
            st.markdown("#### 2️⃣ Pilih Daerah")
            daerah_list = ["-- Pilih Daerah --"] + sorted(mapping_df["PPD"].unique().tolist())
            # Susun ikut turutan asal: Klang ... Petaling Utama
            order_daerah = ["Klang","Kuala Langat","Kuala Selangor","Hulu Langat","Hulu Selangor","Sabak Bernam","Gombak","Petaling Perdana","Sepang","Petaling Utama"]
            daerah_list_ordered = ["-- Pilih Daerah --"] + [d for d in order_daerah if d in mapping_df["PPD"].values]
            sup_daerah = st.selectbox("Daerah Sekolah Anda", daerah_list_ordered)
            
            if sup_daerah != "-- Pilih Daerah --":
                df_daerah = mapping_df[mapping_df["PPD"]==sup_daerah].sort_values("NAMA SEKOLAH")
                st.markdown(f"#### 3️⃣ Pilih Sekolah di {sup_daerah} ({len(df_daerah)} sekolah)")
                st.caption(f"Ada penambahan sekolah? PPD boleh tambah dalam Google Sheet. Contoh: SMJK KATHOLIK ada 3 pusat BK009,BK010,BK011 tapi 1 login sahaja")
                
                # Dropdown sekolah
                sekolah_options = [f"{row['NAMA SEKOLAH']} ({row['KOD SEKOLAH']}) - {row['BIL PUSAT']} pusat [{row['SENARAI PUSAT']}]" for _, row in df_daerah.iterrows()]
                sekolah_pilih = st.selectbox("Nama Sekolah", ["-- Pilih Sekolah --"] + sekolah_options)
                
                if sekolah_pilih != "-- Pilih Sekolah --":
                    idx = sekolah_options.index(sekolah_pilih)
                    row_sekolah = df_daerah.iloc[idx]
                    st.success(f"✅ {row_sekolah['NAMA SEKOLAH']} - Kod {row_sekolah['KOD SEKOLAH']} - {row_sekolah['BIL PUSAT']} pusat: {row_sekolah['SENARAI PUSAT']}")
                    
                    st.markdown("#### 4️⃣ Masukkan Password Sahaja (Tak perlu ID)")
                    st.caption(f"Password kekal ikut ID lama: ID {row_sekolah['ID']} → Password {row_sekolah['PASSWORD']}")
                    sup_pwd = st.text_input(f"Password untuk {row_sekolah['NAMA SEKOLAH']}", type="password", placeholder=f"Password {row_sekolah['PASSWORD']}")
                    
                    login_btn = st.button(f"🚀 Log Masuk {row_sekolah['NAMA SEKOLAH']}", use_container_width=True, type="primary")
                    if login_btn:
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
                            st.error(f"❌ Password salah - Password sekolah ini {row_sekolah['PASSWORD']}")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        with st.expander("ℹ️ Cara Login Baru (Tanpa ID untuk SUP)"):
            st.markdown("""
            **JPN:** Pilih JPN → ID 1 → Password a
            
            **PPD:** Pilih PPD → Pilih Daerah (Klang dll) → Password a-j
            
            **SUP Sekolah (Baru! Tak perlu ID):**
            1. Pilih SUP Sekolah
            2. Pilih Daerah (contoh Klang ada 49 sekolah ID 1-49, Petaling Utama ID 334-369)
            3. Pilih Sekolah (contoh SMJK KATHOLIK - 3 pusat BK009,10,11 tapi 1 login je)
            4. Masuk Password sahaja (Password kekal: ID 354 = Password 354)
            
            **Total 369 sekolah termasuk persendirian, PPD boleh tambah sekolah baru dalam Google Sheet.**
            """)
    
    st.markdown("---")
    st.caption("Sistem 369 Sekolah By Daerah | Tanpa Sidebar | SUP: Daerah → Sekolah → Password sahaja")
    st.stop()

# ================= DAH LOGIN =================
role = st.session_state.user_role
info = st.session_state.user_info

# Header
st.markdown(f"""
<div style="background:#0B5394; color:white; padding:12px 20px; border-radius:8px; display:flex; justify-content:space-between;">
    <div><b>📚 SPM 2026</b> | 👋 {info['nama']} | {role} | {info.get('ppd','')} {info.get('kod_sekolah','')} | ID {info.get('id')} | {info.get('bil_pusat','')} pusat</div>
    <div style="font-size:11px;">369 Sekolah By Daerah</div>
</div>
""", unsafe_allow_html=True)

col_kiri, col_kanan = st.columns([1, 3])

with col_kiri:
    st.markdown('<div class="left-panel">', unsafe_allow_html=True)
    st.markdown(f"### 👤 {info['nama']}")
    st.markdown(f"**Peranan:** {role}")
    if role=="SUP":
        st.markdown(f"**Kod:** {info['kod_sekolah']}")
        st.markdown(f"**PPD:** {info['ppd']} ({info['kod_ppd']})")
        st.markdown(f"**Pusat:** {info['bil_pusat']} pusat")
        st.markdown(f"`{info['senarai_pusat']}`")
        st.markdown(f"**Password:** {info['password']} (ID tak perlu)")
    elif role=="PPD":
        st.markdown(f"**PPD:** {info['ppd_nama']} ({info['kod']})")
        st.markdown(f"**ID:** {info['id']} | **Pwd:** {info['password']}")
    else:
        st.markdown(f"**JPN Selangor**")
    
    st.markdown("---")
    st.markdown("### 📝 Menu")
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
            return pd.read_excel("data/senarai_506_PLUS_calon2026_FINAL.xlsx")
        except:
            return pd.DataFrame({"NO PUSAT":["BK009"],"NAMA PUSAT":["SMJK KATHOLIK"]})
    pusat_master = load_master()
    
    try:
        from streamlit_gsheets import GSheetsConnection
        conn = st.connection("gsheets", type=GSheetsConnection)
        USE_GSHEET=True
    except:
        USE_GSHEET=False
    
    def read_sheet(name):
        if USE_GSHEET:
            try:
                return conn.read(worksheet=name, ttl=0)
            except:
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
            except:
                return pd.DataFrame()
    
    def write_sheet(name, df):
        if USE_GSHEET:
            try:
                conn.update(worksheet=name, data=df)
                return True
            except Exception as ex:
                st.error(f"Gagal {name}: {ex}")
                return False
        else:
            return True

    if role=="SUP":
        if menu=="Maklumat Sekolah":
            st.header(f"🏫 {info['nama']} - {info['senarai_pusat']}")
            st.info(f"Kod {info['kod_sekolah']} | {info['bil_pusat']} pusat ({info['senarai_pusat']}) | Formula: KP={info['bil_pusat']+1}, Pengawas=Bil Kelas+5 | Masuk ikut sekolah bukan pusat")
            maklumat = read_sheet("maklumat_sekolah")
            with st.form("sekolah"):
                c1,c2 = st.columns(2)
                with c1:
                    nama_sek = st.text_input("NAMA SEKOLAH", value=info['nama'])
                    email = st.text_input("EMAIL")
                    poskod_sek = st.number_input("POSKOD SEKOLAH",40000,49000,46000)
                    bil_pusat = st.number_input("BIL PUSAT",1,10,int(info['bil_pusat']))
                with c2:
                    senarai = st.text_input("SENARAI NO PUSAT", value=info['senarai_pusat'])
                    bil_kelas = st.number_input("BIL KELAS",1,30,12)
                    nama_sup = st.text_input("NAMA SUP", value=f"SUP {info['nama']}")
                if st.form_submit_button("💾 Simpan", use_container_width=True):
                    new = pd.DataFrame([{"KOD SEKOLAH": info['kod_sekolah'], "NAMA SEKOLAH": nama_sek, "BIL NO PUSAT": bil_pusat, "SENARAI NO PUSAT": senarai, "BIL KELAS DIGUNAKAN": bil_kelas}])
                    maklumat=pd.concat([maklumat,new],ignore_index=True)
                    write_sheet("maklumat_sekolah", maklumat)
                    st.success(f"Simpan! {info['nama']} {bil_pusat} pusat, KP={bil_pusat+1}")
            st.dataframe(maklumat.tail(5), use_container_width=True)
        elif menu=="Cadangan Petugas":
            st.header(f"👥 Cadangan Petugas - {info['nama']}")
            st.caption(f"{info['bil_pusat']} pusat: {info['senarai_pusat']} - Isi poskod rumah untuk nearest")
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
                    new_g = pd.DataFrame([{"KOD SEKOLAH ASAL": info['kod_sekolah'], "NAMA SEKOLAH ASAL": info['nama'], "JAWATAN CADANG": jaw, "NAMA GURU": nama_g, "IC": ic, "JANTINA": jantina, "POSKOD RUMAH": pos_rumah}])
                    cadangan=pd.concat([cadangan,new_g],ignore_index=True)
                    write_sheet("cadangan_sup", cadangan)
                    st.success(f"{nama_g} ditambah")
            st.dataframe(cadangan.tail(10), use_container_width=True)
        else:
            st.header("📤 Status")
            st.success("Data dah simpan dalam Google Sheet")
            st.dataframe(read_sheet("maklumat_sekolah").tail(5), use_container_width=True)
    
    elif role=="PPD":
        if menu=="Senarai Pusat":
            st.header(f"🏢 PPD {info['ppd_nama']} ({info['kod']}) - {len(mapping_df[mapping_df['KOD PPD']==info['kod']])} sekolah")
            pusat_ppd = pusat_master[pusat_master["NO PUSAT"].str.startswith(info['kod'])]
            st.dataframe(pusat_ppd[["NO PUSAT","NAMA PUSAT","KOD SEKOLAH"]], use_container_width=True)
        elif menu=="Cadangan SUP":
            st.header("📋 Cadangan SUP")
            st.dataframe(read_sheet("cadangan_sup"), use_container_width=True)
        elif menu=="Jana Penempatan":
            st.header("🤖 Jana Penempatan Ikut Poskod")
            if st.button("🤖 Jana Auto", use_container_width=True, type="primary"):
                st.success("Jana penempatan (demo) - ikut poskod nearest")
                st.dataframe(read_sheet("penempatan_ppd").tail(10), use_container_width=True)
        else:
            st.header("📤 Hantar ke JPN")
            if st.button("📤 HANTAR ke JPN", use_container_width=True, type="primary"):
                st.success(f"PPD {info['ppd_nama']} hantar ke JPN!")
                st.balloons()
    else:
        if menu=="Semua PPD":
            st.header("🏛️ Semua PPD - 369 Sekolah")
            st.dataframe(mapping_df, use_container_width=True)
            st.metric("Total Sekolah", len(mapping_df))
        elif menu=="Sahkan PPD":
            st.header("✅ Sahkan PPD")
            ppd_sah = st.selectbox("Pilih PPD", [f"{nama} ({kod}) - {len(mapping_df[mapping_df['KOD PPD']==kod])} sekolah" for _,_,nama,kod in PPD_LIST])
            if st.button("✅ SAHKAN", use_container_width=True, type="primary"):
                st.success(f"{ppd_sah} DISAHKAN!")
                st.balloons()
        else:
            st.header("📄 Jana Surat")
            penempatan_all = read_sheet("penempatan_ppd")
            if st.button("📄 Jana Surat", use_container_width=True, type="primary"):
                st.success("Surat dijana!")
                if not penempatan_all.empty:
                    st.download_button("⬇️ Download CSV", penempatan_all.to_csv(index=False), file_name="senarai.csv")
