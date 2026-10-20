"""
APP MIGRASI ONE CLICK - FIXED VERSION 2
Fix untuk error: Service account info missing token_uri, client_email
"""
import streamlit as st
import pandas as pd
import json
from supabase import create_client
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="MIGRASI DATA FIX", layout="centered")
st.title("🚀 MIGRASI Google Sheet -> Supabase (FIXED)")
st.write("Versi fix untuk error token_uri / client_email")

# ===== SUPABASE =====
SUPABASE_URL = "https://gnmaijhugkkvxejvsotk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdubWFpam11Z2trdnhlanZzb3RrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjA0NTAwOTAsImV4cCI6MjA3NjAyNjA5MH0.1YWg71nCwnQzP-KUzTdHR4rZAVCAesbKVqvVC1-X6lw"
try:
    if "SUPABASE_URL" in st.secrets:
        SUPABASE_URL = st.secrets["SUPABASE_URL"]
    if "SUPABASE_ANON_KEY" in st.secrets:
        SUPABASE_KEY = st.secrets["SUPABASE_ANON_KEY"]
    if "SUPABASE_KEY" in st.secrets:
        SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except:
    pass

# ===== GSHEET - FIXED CRED PARSER =====
st.subheader("1. Sambung Google Sheet")

def get_creds_dict():
    # Cuba 5 tempat berbeza
    tries = []
    # 1. Direct gcp_service_account
    try:
        d = st.secrets["gcp_service_account"]
        tries.append(("gcp_service_account direct", d))
    except:
        pass
    # 2. connections gsheets
    try:
        d = st.secrets["connections"]["gsheets"]["service_account"]
        tries.append(("connections.gsheets.service_account", d))
    except:
        pass
    # 3. connections gcp
    try:
        d = st.secrets["connections"]["gcp_service_account"]
        tries.append(("connections.gcp_service_account", d))
    except:
        pass
    # 4. secrets as json string
    try:
        raw = st.secrets["gcp_service_account"]
        if isinstance(raw, str):
            d = json.loads(raw)
            tries.append(("gcp_service_account json string", d))
    except:
        pass

    for name, d in tries:
        try:
            # Convert to dict
            if hasattr(d, 'to_dict'):
                d = d.to_dict()
            creds_dict = dict(d)
            # Fix private_key \n
            pk = creds_dict.get("private_key", "")
            if pk:
                # Replace escaped \n
                creds_dict["private_key"] = pk.replace("\\n", "\n")
            # Check required fields
            required = ["type", "project_id", "private_key", "client_email", "token_uri"]
            missing = [k for k in required if k not in creds_dict or not creds_dict[k]]
            if missing:
                st.warning(f"Cuba {name} tapi missing {missing}")
                continue
            st.success(f"✅ Jumpa creds dari {name}")
            return creds_dict
        except Exception as e:
            st.warning(f"Cuba {name} gagal: {e}")
            continue
    return None

creds_dict = get_creds_dict()

if creds_dict is None:
    st.error("❌ Tak jumpa gcp_service_account yang lengkap. Sila check Secrets di Streamlit Cloud.")
    st.info("""
    Dalam Streamlit Cloud > Secrets, pastikan ada:

    [gcp_service_account]
    type = "service_account"
    project_id = "..."
    private_key_id = "..."
    private_key = "-----BEGIN PRIVATE KEY-----\\n....\\n-----END PRIVATE KEY-----\\n"
    client_email = "...@...iam.gserviceaccount.com"
    client_id = "..."
    auth_uri = "https://accounts.google.com/o/oauth2/auth"
    token_uri = "https://oauth2.googleapis.com/token"
    auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
    client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."

    Pastikan private_key guna \\n (bukan enter betul)
    """)
    st.stop()

try:
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
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
    st.exception(e)
    st.stop()

st.subheader("2. Sambung Supabase")
try:
    supa = create_client(SUPABASE_URL, SUPABASE_KEY)
    st.success(f"✅ Supabase OK")
except Exception as e:
    st.error(f"❌ Supabase gagal: {e}")
    st.stop()

tables = ["maklumat_sekolah", "cadangan_sup", "penempatan_ppd", "status_hantar"]

st.subheader("3. Klik untuk Migrasi")
if st.button("🚀 MULA MIGRASI SEMUA TABLE", type="primary", use_container_width=True):
    progress = st.progress(0)
    for idx, base in enumerate(tables):
        st.write(f"⏳ Memproses {base}...")
        try:
            df = pd.DataFrame()
            for try_name in [f"{base}_2026", base, f"{base}_2025"]:
                try:
                    ws = sh.worksheet(try_name)
                    records = ws.get_all_records()
                    df = pd.DataFrame(records)
                    if not df.empty:
                        st.write(f"Jumpa {len(df)} baris dari tab {try_name}")
                        break
                except Exception:
                    continue
            
            if df.empty:
                st.warning(f"{base} kosong, skip")
                continue
            
            supa.table(base).delete().neq("id", -1).execute()
            
            batch = []
            for _, row in df.iterrows():
                rd = row.to_dict()
                clean = {k: ("" if pd.isna(v) else v) for k,v in rd.items()}
                if base == "status_hantar":
                    batch.append({
                        "KOD_PPD": str(clean.get("KOD PPD", clean.get("KOD_PPD", ""))),
                        "PPD": str(clean.get("PPD", "")),
                        "STATUS": str(clean.get("STATUS", "")),
                        "TARIKH_HANTAR": str(clean.get("TARIKH HANTAR", "")),
                        "TARIKH_SAH": str(clean.get("TARIKH SAH", "")),
                        "data": clean
                    })
                else:
                    kod_ppd = str(clean.get("KOD PPD", clean.get("KOD PPD", "")))
                    if not kod_ppd and clean.get("NO PUSAT TUGAS"):
                        kod_ppd = str(clean.get("NO PUSAT TUGAS", ""))[:2]
                    batch.append({
                        "KOD_PPD": kod_ppd,
                        "NO_PUSAT_TUGAS": str(clean.get("NO PUSAT TUGAS", clean.get("NO PUSAT", ""))),
                        "KOD_SEKOLAH": str(clean.get("KOD SEKOLAH", "")),
                        "data": clean
                    })
            
            for i in range(0, len(batch), 100):
                if batch[i:i+100]:
                    supa.table(base).insert(batch[i:i+100]).execute()
            
            st.success(f"✅ {base}: {len(batch)} baris berjaya pindah")
        except Exception as e:
            st.error(f"❌ {base} gagal: {e}")
        
        progress.progress((idx+1)/len(tables))
    
    st.balloons()
    st.success("SELESAI! Pergi Supabase > Table Editor > Refresh, check data ada.")

st.divider()
st.caption("Lepas siap, delete migrate.py dan rename app_backup.py jadi app.py balik")
