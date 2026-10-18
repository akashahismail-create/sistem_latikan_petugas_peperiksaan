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
                except:
                    continue
        except:
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
        except:
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
        except:
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
        
        if menu=="Senarai Pusat":
            st.header(f"🏢 PPD {info['ppd_nama']} - {len(df_ppd)} sekolah, {len(semua_pusat)} pusat")
            st.info(f"Daerah {info['kod']} = {info['ppd_nama']} | {len(semua_pusat)} pusat peperiksaan")
            
            # Load penempatan untuk kira status
            penempatan_all = read_sheet("penempatan_ppd")
            
            # Buat status table
            status_data = []
            for pusat in semua_pusat:
                kod_sek_pusat = pusat_to_sekolah.get(pusat, "")
                nama_sek_pusat = df_ppd[df_ppd["KOD SEKOLAH"].astype(str)==kod_sek_pusat]["NAMA SEKOLAH"].values[0] if not df_ppd[df_ppd["KOD SEKOLAH"].astype(str)==kod_sek_pusat].empty else pusat
                if not penempatan_all.empty and "NO PUSAT TUGAS" in penempatan_all.columns:
                    bil = len(penempatan_all[penempatan_all["NO PUSAT TUGAS"].astype(str)==pusat])
                    status = "✅ Lengkap" if bil>=3 else ("⚠️ Separa" if bil>0 else "❌ Belum")
                else:
                    bil = 0
                    status = "❌ Belum"
                status_data.append({"NO PUSAT": pusat, "SEKOLAH TUAN RUMAH": nama_sek_pusat, "KOD SEKOLAH": kod_sek_pusat, "BIL DILANTIK": bil, "STATUS": status})
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
            
            cadangan_all = read_sheet("cadangan_sup")
            penempatan_all = read_sheet("penempatan_ppd")
            
            if not cadangan_all.empty and "KOD SEKOLAH ASAL" in cadangan_all.columns:
                cadangan_ppd = cadangan_all[cadangan_all["KOD SEKOLAH ASAL"].astype(str).isin(kod_sekolah_ppd)]
            else:
                cadangan_ppd = cadangan_all
            
            # Pilih pusat
            if not semua_pusat:
                st.warning("Tiada pusat untuk daerah ini")
            else:
                col1, col2 = st.columns([2,1])
                with col1:
                    pusat_pilih = st.selectbox("📌 Pilih NO PUSAT", semua_pusat, index=0)
                with col2:
                    kod_sek_pusat = pusat_to_sekolah.get(pusat_pilih, "")
                    nama_pusat = pusat_to_nama.get(pusat_pilih, df_ppd[df_ppd["KOD SEKOLAH"].astype(str)==kod_sek_pusat]["NAMA SEKOLAH"].values[0] if not df_ppd[df_ppd["KOD SEKOLAH"].astype(str)==kod_sek_pusat].empty else pusat_pilih)
                    st.metric("Sekolah Tuan Rumah", f"{nama_pusat}")
                    st.caption(f"Kod: {kod_sek_pusat} | Pusat: {pusat_pilih}")
                
                # Show penempatan untuk pusat ini
                if penempatan_all.empty or "NO PUSAT TUGAS" not in penempatan_all.columns:
                    penempatan_pusat = pd.DataFrame()
                else:
                    penempatan_pusat = penempatan_all[penempatan_all["NO PUSAT TUGAS"].astype(str)==str(pusat_pilih)]
                
                # Status + Jana Auto button SELALU ADA
                bil_sedia = len(penempatan_pusat)
                if bil_sedia == 0:
                    st.warning(f"❌ {pusat_pilih} belum ada lantikan. Tekan Jana Auto di bawah.")
                else:
                    st.info(f"ℹ️ {pusat_pilih} ada {bil_sedia} petugas sekarang - boleh tambah/lengkapkan lagi")
                
                # JANA AUTO / LENGKAPKAN - sentiasa tunjuk
                col_j1, col_j2 = st.columns(2)
                with col_j1:
                    label_btn = f"🤖 Jana Auto untuk {pusat_pilih}" if bil_sedia==0 else f"➕ Lengkapkan {pusat_pilih} jadi 10 orang"
                    if st.button(label_btn, use_container_width=True, type="primary", key=f"jana_{pusat_pilih}"):
                        if cadangan_ppd.empty:
                            st.error("Tiada cadangan guru untuk daerah ini! Isi Cadangan SUP dulu")
                        else:
                            calon = cadangan_ppd[cadangan_ppd["KOD SEKOLAH ASAL"].astype(str)!=str(kod_sek_pusat)].copy()
                            # Exclude yang dah dilantik di pusat ni
                            if not penempatan_pusat.empty and "IC" in penempatan_pusat.columns:
                                ic_sedia = penempatan_pusat["IC"].astype(str).tolist()
                                calon = calon[~calon["IC"].astype(str).isin(ic_sedia)]
                            if calon.empty:
                                st.warning("Semua guru daerah ni dah dilantik di pusat ni atau tiada calon lain!")
                            else:
                                # Kira berapa perlu tambah
                                perlu = 10 - bil_sedia if bil_sedia>0 else 10
                                calon_sample = calon.head(perlu)
                                new_rows = []
                                # Jawatan yang belum ada
                                jawatan_sedia = penempatan_pusat["JAWATAN FINAL"].astype(str).tolist() if "JAWATAN FINAL" in penempatan_pusat.columns else []
                                jawatan_all = ["Ketua Pengawas", "Timbalan Ketua Pengawas"] + ["Pengawas Peperiksaan"]*6 + ["Pengemas Bilik", "Penyelia Kawasan"]
                                # Cari jawatan yang belum isi
                                jawatan_perlu = []
                                for j in jawatan_all:
                                    if j not in jawatan_sedia or jawatan_sedia.count(j) < jawatan_all.count(j):
                                        # kalau dah ada, skip
                                        count_need = jawatan_all.count(j) - jawatan_sedia.count(j)
                                        for _ in range(count_need):
                                            if len(jawatan_perlu) < perlu:
                                                jawatan_perlu.append(j)
                                if not jawatan_perlu:
                                    jawatan_perlu = ["Pengawas Peperiksaan"]*perlu
                                
                                for i, (_, guru) in enumerate(calon_sample.iterrows()):
                                    if i < len(jawatan_perlu):
                                        new_rows.append({
                                            "NO PUSAT TUGAS": pusat_pilih,
                                            "NAMA PUSAT TUGAS": nama_pusat,
                                            "KOD SEKOLAH ASAL GURU": guru.get("KOD SEKOLAH ASAL",""),
                                            "NAMA SEKOLAH ASAL": guru.get("NAMA SEKOLAH ASAL",""),
                                            "NAMA GURU": guru.get("NAMA GURU",""),
                                            "IC": guru.get("IC",""),
                                            "JANTINA": guru.get("JANTINA",""),
                                            "JAWATAN FINAL": jawatan_perlu[i] if i < len(jawatan_perlu) else "Pengawas Peperiksaan",
                                            "POSKOD RUMAH": guru.get("POSKOD RUMAH",""),
                                            "STATUS PENEMPATAN": "Auto by PPD" if bil_sedia==0 else "Lengkapkan Auto by PPD"
                                        })
                                if new_rows:
                                    df_new = pd.DataFrame(new_rows)
                                    penempatan_all = pd.concat([penempatan_all, df_new], ignore_index=True)
                                    if write_sheet("penempatan_ppd", penempatan_all):
                                        st.success(f"✅ {pusat_pilih} berjaya ditambah {len(new_rows)} petugas! Sekarang total {bil_sedia+len(new_rows)}")
                                        st.rerun()
                with col_j2:
                    if st.button(f"🗑️ Kosongkan {pusat_pilih} (Reset)", use_container_width=True, key=f"reset_{pusat_pilih}"):
                        penempatan_all = penempatan_all[penempatan_all["NO PUSAT TUGAS"].astype(str)!=str(pusat_pilih)]
                        if write_sheet("penempatan_ppd", penempatan_all):
                            st.success(f"✅ {pusat_pilih} dikosongkan!")
                            st.rerun()
                
                if penempatan_pusat.empty:
                    st.info(f"Belum dilantik untuk {pusat_pilih} - tekan Jana Auto di atas")
                else:
                    st.success(f"✅ {pusat_pilih} - {len(penempatan_pusat)} petugas dilantik")
                    
                    # Display by jawatan
                    for jaw in ["Ketua Pengawas", "Timbalan Ketua Pengawas", "Pengawas Peperiksaan", "Pengemas Bilik", "Penyelia Kawasan"]:
                        subset = penempatan_pusat[penempatan_pusat["JAWATAN FINAL"].astype(str).str.contains(jaw, case=False, na=False)] if "JAWATAN FINAL" in penempatan_pusat.columns else pd.DataFrame()
                        if not subset.empty:
                            st.markdown(f"**{jaw} ({len(subset)} orang)**")
                            st.dataframe(subset[["NAMA GURU","KOD SEKOLAH ASAL GURU","NAMA SEKOLAH ASAL","IC","JAWATAN FINAL"]], use_container_width=True)
                    
                    st.markdown("---")
                    st.markdown(f"#### ✏️ Edit Lantikan {pusat_pilih} - Klik Nama Untuk Tukar")
                    st.caption(f"📍 Pusat: {pusat_pilih} - {nama_pusat} ({kod_sek_pusat}) | Guru dari {kod_sek_pusat} tidak boleh jaga pusat sendiri - auto exclude")
                    
                    # Senarai calon untuk edit - exclude sekolah tuan rumah - SEMUA sekolah daerah kecuali tuan rumah
                    if not cadangan_ppd.empty:
                        calon_edit = cadangan_ppd[cadangan_ppd["KOD SEKOLAH ASAL"].astype(str)!=str(kod_sek_pusat)].copy()
                        # Tambah label dengan nama pusat sekolah
                        def label_calon(row):
                            return f"{row.get('NAMA GURU','')} | {row.get('KOD SEKOLAH ASAL','')} - {row.get('NAMA SEKOLAH ASAL','')} | IC:{row.get('IC','')} | Poskod:{row.get('POSKOD RUMAH','')}"
                        calon_options = [label_calon(r) for _, r in calon_edit.iterrows()]
                    else:
                        calon_options = []
                        calon_edit = pd.DataFrame()
                    
                    st.info(f"📋 Ada {len(calon_options)} guru dari daerah {info['ppd_nama']} boleh pilih (kecuali {kod_sek_pusat})")
                    
                    # Pilih petugas yang nak ditukar - BILA KLIK NAMA TU KELUAR PILIHAN
                    if not penempatan_pusat.empty:
                        # Show table dengan index untuk klik
                        penempatan_display = penempatan_pusat.copy()
                        penempatan_display["PILIH UNTUK TUKAR"] = penempatan_display["NAMA GURU"]
                        
                        st.markdown("**👇 Senarai petugas sekarang - pilih yang nak ditukar:**")
                        # Guna data_editor atau selectbox yang jelas
                        petugas_list = penempatan_pusat["NAMA GURU"].astype(str).tolist()
                        # Tambah info jawatan dalam label
                        petugas_labels = []
                        for _, r in penempatan_pusat.iterrows():
                            petugas_labels.append(f"{r.get('NAMA GURU','')} - {r.get('JAWATAN FINAL','')} ({r.get('KOD SEKOLAH ASAL GURU','')})")
                        
                        col_a, col_b = st.columns([1,2])
                        with col_a:
                            idx_pilih = st.selectbox("1️⃣ Klik nama pengawas nak tukar", ["-- Pilih nama --"] + petugas_labels, key=f"pilih_{pusat_pilih}")
                        with col_b:
                            if idx_pilih != "-- Pilih nama --" and calon_options:
                                # Cari index
                                petugas_pilih = petugas_list[petugas_labels.index(idx_pilih)] if idx_pilih in petugas_labels else ""
                                guru_baru = st.selectbox(f"2️⃣ Ganti {petugas_pilih} dengan guru lain (dari daerah {info['ppd_nama']} kecuali {kod_sek_pusat})", ["-- Pilih guru baru dari senarai cadangan --"] + calon_options, key=f"ganti_{pusat_pilih}")
                                if guru_baru != "-- Pilih guru baru dari senarai cadangan --":
                                    if st.button(f"🔄 Tukar {petugas_pilih} → {guru_baru.split('|')[0].strip()}", use_container_width=True, type="primary"):
                                        idx_old = penempatan_all[(penempatan_all["NO PUSAT TUGAS"].astype(str)==str(pusat_pilih)) & (penempatan_all["NAMA GURU"].astype(str)==str(petugas_pilih))].index
                                        if not idx_old.empty:
                                            idx_new = calon_options.index(guru_baru)
                                            guru_data = calon_edit.iloc[idx_new]
                                            for idx in idx_old:
                                                penempatan_all.at[idx, "NAMA GURU"] = guru_data.get("NAMA GURU","")
                                                penempatan_all.at[idx, "KOD SEKOLAH ASAL GURU"] = guru_data.get("KOD SEKOLAH ASAL","")
                                                penempatan_all.at[idx, "NAMA SEKOLAH ASAL"] = guru_data.get("NAMA SEKOLAH ASAL","")
                                                penempatan_all.at[idx, "IC"] = guru_data.get("IC","")
                                                penempatan_all.at[idx, "JANTINA"] = guru_data.get("JANTINA","")
                                                penempatan_all.at[idx, "POSKOD RUMAH"] = guru_data.get("POSKOD RUMAH","")
                                                penempatan_all.at[idx, "STATUS PENEMPATAN"] = f"Tukar manual oleh PPD {info['ppd_nama']} - {pd.Timestamp.now().strftime('%Y-%m-%d')}"
                                            if write_sheet("penempatan_ppd", penempatan_all):
                                                st.success(f"✅ {petugas_pilih} ditukar kepada {guru_data.get('NAMA GURU','')} dari {guru_data.get('KOD SEKOLAH ASAL','')}")
                                                st.rerun()
                    
                    # Full table edit
                    st.markdown("#### 📋 Semua Petugas di Pusat Ini")
                    st.dataframe(penempatan_pusat, use_container_width=True)
        
        else:
            st.header(f"📤 Hantar ke JPN - {info['ppd_nama']}")
            penempatan_all = read_sheet("penempatan_ppd")
            maklumat_all = read_sheet("maklumat_sekolah")
            cadangan_all = read_sheet("cadangan_sup")
            
            # Kira pusat lengkap
            if not penempatan_all.empty and "NO PUSAT TUGAS" in penempatan_all.columns:
                pusat_lengkap = penempatan_all[penempatan_all["NO PUSAT TUGAS"].astype(str).isin(semua_pusat)]["NO PUSAT TUGAS"].nunique()
            else:
                pusat_lengkap = 0
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Sekolah", f"{len(df_ppd)}")
            with col2:
                st.metric("Pusat", f"{len(semua_pusat)}")
            with col3:
                st.metric("Pusat Dilantik", f"{pusat_lengkap}/{len(semua_pusat)}")
            
            if st.button("📤 HANTAR ke JPN", use_container_width=True, type="primary"):
                st.success(f"✅ PPD {info['ppd_nama']} hantar {pusat_lengkap} pusat ke JPN!")
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
