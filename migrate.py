"""
APP MIGRASI ONE CLICK - GOOGLE SHEET -> SUPABASE
Upload file ni sebagai migrate.py kat Streamlit Cloud, run sekali je.
"""
import streamlit as st
import pandas as pd
from supabase import create_client
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="MIGRASI DATA", layout="centered")
st.title("🚀 MIGRASI Google Sheet -> Supabase")
st.write("Klik butang bawah untuk pindah semua data lama ke Supabase LIVE")

# Config Supabase
SUPABASE_URL = "https://gnmaijhugkkvxejvsotk.supabase.co"
SUPABASE_KEY = st.secrets.get("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdubWFpamh1Z2trdnhlanZzb3RrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTI0ODc4OTcsImV4cCI6MjEwODA2Mzg5N30.1YWg71nCwnQzP-KUzTdHR4rZAVCAesbKVqvVC1-X6lw")
try:
    if "SUPABASE_URL" in st.secrets:
        SUPABASE_URL = st.secrets["SUPABASE_URL"]
    if "SUPABASE_ANON_KEY" in st.secrets:
        SUPABASE_KEY = st.secrets["SUPABASE_ANON_KEY"]
    if "SUPABASE_KEY" in st.secrets:
        SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    if "connections" in st.secrets and "supabase" in st.secrets["connections"]:
        SUPABASE_URL = st.secrets["connections"]["supabase"].get("SUPABASE_URL", SUPABASE_URL)
        SUPABASE_KEY = st.secrets["connections"]["supabase"].get("SUPABASE_KEY", SUPABASE_KEY)
        SUPABASE_KEY = st.secrets["connections"]["supabase"].get("SUPABASE_ANON_KEY", SUPABASE_KEY)
except:
    pass

# Connect GSheet
st.subheader("1. Sambung Google Sheet")
try:
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    client = gspread.authorize(creds)
    SPREADSHEET_ID = st.secrets.get("SPREADSHEET_ID", "1dweem4yw6nKlo1wy5PA264prHEHpLoBPSu89jRFi484")
    try:
        SPREADSHEET_ID = st.secrets["connections"]["gsheets"]["spreadsheet"].split("/d/")[1].split("/")[0]
    except:
        pass
    sh = client.open_by_key(SPREADSHEET_ID)
    st.success(f"✅ Google Sheet OK: {sh.title}")
except Exception as e:
    st.error(f"❌ Google Sheet gagal: {e}")
    st.stop()

st.subheader("2. Sambung Supabase")
try:
    supa = create_client(SUPABASE_URL, SUPABASE_KEY)
    st.success(f"✅ Supabase OK: {SUPABASE_URL}")
except Exception as e:
    st.error(f"❌ Supabase gagal: {e}")
    st.stop()

# List tables
tables = ["maklumat_sekolah", "cadangan_sup", "penempatan_ppd", "status_hantar"]

st.subheader("3. Klik untuk Migrasi")
st.warning("Ini akan PADAM data lama dalam Supabase dan ganti dengan data dari Google Sheet. Buat sekali je.")

if st.button("🚀 MULA MIGRASI SEMUA TABLE", type="primary", use_container_width=True):
    progress = st.progress(0)
    log = st.empty()
    
    for idx, base in enumerate(tables):
        log.info(f"Memproses {base}...")
        try:
            # Baca dari GSheet - cuba 3 nama
            df = pd.DataFrame()
            for try_name in [f"{base}_2026", base, f"{base}_2025"]:
                try:
                    ws = sh.worksheet(try_name)
                    records = ws.get_all_records()
                    df = pd.DataFrame(records)
                    if not df.empty:
                        st.write(f"Jumpa {len(df)} baris dari tab {try_name}")
                        break
                except:
                    continue
            
            if df.empty:
                st.warning(f"{base} kosong atau tak jumpa di GSheet, skip")
                continue
            
            # Delete lama di Supabase
            supa.table(base).delete().neq("id", -1).execute()
            
            # Prepare batch
            batch = []
            for _, row in df.iterrows():
                rd = row.to_dict()
                clean = {k: ("" if pd.isna(v) else v) for k,v in rd.items()}
                if base == "status_hantar":
                    batch.append({
                        "KOD_PPD": str(clean.get("KOD PPD", "")),
                        "PPD": str(clean.get("PPD", "")),
                        "STATUS": str(clean.get("STATUS", "")),
                        "TARIKH_HANTAR": str(clean.get("TARIKH HANTAR", "")),
                        "TARIKH_SAH": str(clean.get("TARIKH SAH", "")),
                        "data": clean
                    })
                else:
                    kod_ppd = str(clean.get("KOD PPD", clean.get("KOD_PPD", "")))
                    if not kod_ppd:
                        # cuba dapat dari NO PUSAT
                        for k in ["NO PUSAT", "NO PUSAT TUGAS", "NO_PUSAT", "NO PUSAT TUGAS"]:
                            if k in clean and clean[k]:
                                kod_ppd = str(clean[k])[:2]
                                break
                    batch.append({
                        "KOD_PPD": kod_ppd,
                        "NO_PUSAT_TUGAS": str(clean.get("NO PUSAT TUGAS", clean.get("NO PUSAT", ""))),
                        "KOD_SEKOLAH": str(clean.get("KOD SEKOLAH", "")),
                        "data": clean
                    })
            
            # Insert
            for i in range(0, len(batch), 100):
                supa.table(base).insert(batch[i:i+100]).execute()
            
            st.success(f"✅ {base}: {len(batch)} baris berjaya pindah")
        except Exception as e:
            st.error(f"❌ {base} gagal: {e}")
        
        progress.progress((idx+1)/len(tables))
    
    log.success("SELESAI SEMUA!")
    st.balloons()
    st.info("Pergi Supabase > Table Editor > Refresh. Table patut dah ada data, bukan 'This table is empty' lagi.")

st.divider()
st.caption("Lepas migrasi selesai, kau boleh delete file migrate.py ni dari GitHub.")
