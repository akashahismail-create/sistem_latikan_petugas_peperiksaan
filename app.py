"""
SISTEM PELANTIKAN PETUGAS PEPERIKSAAN SELANGOR 2026
FIX FINAL - Baca apa saja nama file ID DAERAH, tak kisah - atau _ , besar kecil huruf
Total 369 sekolah
"""

import streamlit as st
import pandas as pd
import os
import glob

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
        except:
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
        except:
            return pd.DataFrame({"NO PUSAT":["BK009"],"NAMA PUSAT":["SMJK KATHOLIK"]})
    pusat_master = load_master()
    
    # === FIXED: Guna gspread direct dengan Service Account (bukan GSheetsConnection) ===
    USE_GSHEET = False
    gspread_client = None
    SPREADSHEET_ID_FIX = None
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        # Ambil ID dari secrets
        try:
            SPREADSHEET_ID_FIX = st.secrets["SPREADSHEET_ID"]
        except:
            try:
                SPREADSHEET_ID_FIX = st.secrets["connections"]["gsheets"]["spreadsheet"].split("/d/")[1].split("/")[0]
            except:
                SPREADSHEET_ID_FIX = "1dweem4yw6nKlo1wy5PA264prHEHpLoBPSu89jRFi484"
        
        creds_dict = dict(st.secrets["gcp_service_account"])
        # Fix private_key newlines
        if "\\n" in creds_dict.get("private_key",""):
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        gspread_client = gspread.authorize(creds)
        USE_GSHEET = True
    except Exception as e:
        st.warning(f"GSheet init warning (akan guna memory sahaja): {e}")
        USE_GSHEET = False
    
    def read_sheet(name):
        if USE_GSHEET and gspread_client:
            try:
                sh = gspread_client.open_by_key(SPREADSHEET_ID_FIX)
                try:
                    ws = sh.worksheet(name)
                except:
                    # Worksheet tak wujud lagi, return kosong
                    return pd.DataFrame()
                records = ws.get_all_records()
                return pd.DataFrame(records)
            except Exception as e:
                # st.error(f"Read {name} gagal: {e}")
                return pd.DataFrame()
        else:
            return pd.DataFrame()
    
    def write_sheet(name, df):
        if USE_GSHEET and gspread_client:
            try:
                sh = gspread_client.open_by_key(SPREADSHEET_ID_FIX)
                try:
                    ws = sh.worksheet(name)
                except:
                    # Create worksheet kalau tak ada
                    ws = sh.add_worksheet(title=name, rows=1000, cols=30)
                
                # Clear dan tulis baru
                ws.clear()
                if not df.empty:
                    # Tukar NaN ke ""
                    df_fill = df.fillna("")
                    ws.update([df_fill.columns.values.tolist()] + df_fill.values.tolist())
                else:
                    # Kalau kosong, tulis header sahaja kalau ada
                    pass
                return True
            except Exception as ex:
                st.error(f"Gagal {name}: {ex}")
                return False
        else:
            st.error("Gsheet tidak connect - check Secrets")
            return False
    

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
                        except:
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
                        except:
                            pass
                        break
                for col in ["BIL KELAS DIGUNAKAN"]:
                    if col in existing.columns:
                        try:
                            def_val_bil_kelas = int(float(str(row.get(col, def_val_bil_kelas)).strip() or def_val_bil_kelas))
                        except:
                            pass
                        break
            
            if not existing.empty:
                st.success(f"✅ Data {info['kod_sekolah']} dijumpai - auto isi")
            
            with st.form("sekolah"):
                c1,c2 = st.columns(2)
                with c1:
                    nama_sek = st.text_input("NAMA SEKOLAH", value=def_val_nama)
                    email = st.text_input("EMAIL SEKOLAH", value=def_val_email, placeholder="bea8640@moe.edu.my")
                    no_tel = st.text_input("NO TELEFON SEKOLAH", value=def_val_tel, placeholder="03-XXXXXXX")
                    poskod_sek = st.number_input("POSKOD SEKOLAH",40000,49000,def_val_poskod)
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
                        "NAMA PENGETUA": nama_pengetua,
                        "NAMA SUP": nama_sup,
                        "NO POSKOD SEKOLAH": poskod_sek,
                        "BIL NO PUSAT": bil_pusat, 
                        "SENARAI NO PUSAT": senarai, 
                        "BIL KELAS DIGUNAKAN": bil_kelas,
                        "TARIKH KEMASKINI": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    # === LOGIK ANTI-DUPLICATE ===
                    if not maklumat.empty and "KOD SEKOLAH" in maklumat.columns:
                        # Buang baris lama kalau KOD SEKOLAH sama
                        maklumat = maklumat[maklumat["KOD SEKOLAH"].astype(str) != str(info['kod_sekolah'])]
                    
                    new_df = pd.DataFrame([new_row])
                    maklumat = pd.concat([maklumat, new_df], ignore_index=True)
                    # Buang duplicate kalau ada (keep last)
                    if "KOD SEKOLAH" in maklumat.columns:
                        maklumat = maklumat.drop_duplicates(subset=["KOD SEKOLAH"], keep="last")
                    
                    if write_sheet("maklumat_sekolah", maklumat):
                        st.success(f"✅ {nama_sek} berjaya dikemaskini! (Satu rekod sahaja untuk {info['kod_sekolah']})")
                        st.rerun()
                    else:
                        st.error("Gagal simpan")
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
                    if not nama_g or not ic:
                        st.error("Nama Guru dan IC wajib isi!")
                    else:
                        new_g_row = {"KOD SEKOLAH ASAL": info['kod_sekolah'], "NAMA SEKOLAH ASAL": info['nama'], "JAWATAN CADANG": jaw, "NAMA GURU": nama_g.strip(), "IC": ic.strip(), "JANTINA": jantina, "POSKOD RUMAH": pos_rumah, "TARIKH": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")}
                        # Anti-duplicate IC dalam sekolah yang sama
                        if not cadangan.empty and "IC" in cadangan.columns:
                            cadangan = cadangan[cadangan["IC"].astype(str) != str(ic.strip())]
                        new_g = pd.DataFrame([new_g_row])
                        cadangan = pd.concat([cadangan,new_g],ignore_index=True)
                        if write_sheet("cadangan_sup", cadangan):
                            st.success(f"✅ {nama_g} ditambah / dikemaskini! - Hanya untuk {info['kod_sekolah']}")
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
            st.success("Data simpan dalam Google Sheet")
            st.dataframe(read_sheet("maklumat_sekolah").tail(5), use_container_width=True)
    elif role=="PPD":
        if menu=="Senarai Pusat":
            st.header(f"🏢 PPD {info['ppd_nama']} - {len(mapping_df[mapping_df['KOD PPD']==info['kod']])} sekolah")
            st.info(f"File: {file_used} | Update: data/SENARAI_ID_SUP_BY_DAERAH.xlsx (apa saja nama ada ID+DAERAH)")
            df_ppd = mapping_df[mapping_df["KOD PPD"]==info['kod']]
            st.dataframe(df_ppd[["ID","KOD SEKOLAH","NAMA SEKOLAH","BIL PUSAT","SENARAI PUSAT"]], use_container_width=True)
        elif menu=="Cadangan SUP":
            st.header("📋 Cadangan SUP")
            st.dataframe(read_sheet("cadangan_sup"), use_container_width=True)
        elif menu=="Jana Penempatan":
            st.header("🤖 Jana Penempatan")
            if st.button("🤖 Jana Auto", use_container_width=True, type="primary"):
                st.success("Jana penempatan (demo)")
                st.dataframe(read_sheet("penempatan_ppd").tail(10), use_container_width=True)
        else:
            st.header("📤 Hantar ke JPN")
            if st.button("📤 HANTAR ke JPN", use_container_width=True, type="primary"):
                st.success(f"PPD {info['ppd_nama']} hantar ke JPN!")
                st.balloons()
    else:
        if menu=="Semua PPD":
            st.header(f"🏛️ Semua PPD - {len(mapping_df)} Sekolah - File: {os.path.basename(file_used)}")
            st.dataframe(mapping_df, use_container_width=True)
        elif menu=="Sahkan PPD":
            st.header("✅ Sahkan PPD")
            ppd_sah = st.selectbox("Pilih PPD", [f"{nama} ({kod}) - {len(mapping_df[mapping_df['KOD PPD']==kod])} sekolah" for _,_,nama,kod in PPD_LIST])
            if st.button("✅ SAHKAN", use_container_width=True, type="primary"):
                st.success(f"{ppd_sah} DISAHKAN!")
        else:
            st.header("📄 Jana Surat")
            penempatan_all = read_sheet("penempatan_ppd")
            if st.button("📄 Jana Surat", use_container_width=True, type="primary"):
                st.success("Surat dijana!")
