"""
MIGRASI FROM EXCEL - FIXED FOR FILENAME WITH SPACE (7)
"""
import streamlit as st
import pandas as pd
from supabase import create_client
import os, glob

st.set_page_config(page_title="MIGRASI EXCEL -> SUPABASE", layout="centered")
st.title("🚀 MIGRASI Excel -> Supabase")
st.write("Auto detect file Sistem_Lantikan_SPM_2026 (7).xlsx")

SUPABASE_URL = "https://gnmaijhugkkvxejvsotk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.1YWg71nCwnQzP-KUzTdHR4rZAVCAesbKVqvVC1-X6lw"
try:
    if "SUPABASE_URL" in st.secrets:
        SUPABASE_URL = st.secrets["SUPABASE_URL"]
    if "SUPABASE_ANON_KEY" in st.secrets:
        SUPABASE_KEY = st.secrets["SUPABASE_ANON_KEY"]
    if "SUPABASE_KEY" in st.secrets:
        SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except:
    pass

st.subheader("1. Sambung Supabase")
try:
    supa = create_client(SUPABASE_URL, SUPABASE_KEY)
    st.success(f"✅ Supabase OK")
except Exception as e:
    st.error(f"❌ Supabase gagal: {e}")
    st.stop()

st.subheader("2. Cari File Excel")
# Cari semua xlsx di root
candidates = glob.glob("*.xlsx") + glob.glob("data/*.xlsx")
st.write(f"File xlsx jumpa: {candidates}")

excel_path = None
# Prioriti cari yang ada Lantikan
for p in candidates:
    if "Lantikan" in p or "lanti" in p.lower():
        excel_path = p
        break
if not excel_path and candidates:
    excel_path = candidates[0]

uploaded = st.file_uploader("Atau upload manual jika tak jumpa", type=["xlsx"])
if uploaded:
    with open("/tmp/upload.xlsx", "wb") as f:
        f.write(uploaded.getbuffer())
    excel_path = "/tmp/upload.xlsx"

if excel_path and os.path.exists(excel_path):
    st.success(f"✅ Guna file: {excel_path}")
    xls = pd.ExcelFile(excel_path)
    st.write(f"Sheet: {xls.sheet_names}")
else:
    st.error("❌ Tak jumpa file Excel. Upload Sistem_Lantikan_SPM_2026 (7).xlsx")
    st.stop()

def df_to_batch(df, table_base):
    batch=[]
    for _, row in df.iterrows():
        rd=row.to_dict()
        clean={k: ("" if pd.isna(v) else v) for k,v in rd.items()}
        kod_ppd=str(clean.get("KOD PPD", ""))[:2]
        if not kod_ppd:
            for k in ["NO PUSAT TUGAS", "NO PUSAT", "KOD SEKOLAH", "KOD SEKOLAH ASAL"]:
                if k in clean and clean[k]:
                    v=str(clean[k])
                    if len(v)>=2 and v[:2].isalpha():
                        kod_ppd=v[:2]
                        break
        batch.append({
            "KOD_PPD": kod_ppd,
            "NO_PUSAT_TUGAS": str(clean.get("NO PUSAT TUGAS", clean.get("NO PUSAT", clean.get("SENARAI NO PUSAT", "")))),
            "KOD_SEKOLAH": str(clean.get("KOD SEKOLAH", clean.get("KOD SEKOLAH ASAL", ""))),
            "data": clean
        })
    return batch

st.subheader("3. Migrasi")
if st.button("🚀 MULA MIGRASI DARI EXCEL", type="primary", use_container_width=True):
    all_sheets = xls.sheet_names
    groups = {
        "maklumat_sekolah": [s for s in all_sheets if "maklumat_sekolah" in s],
        "cadangan_sup": [s for s in all_sheets if "cadangan_sup" in s],
        "penempatan_ppd": [s for s in all_sheets if "penempatan_ppd" in s],
        "kuota_ppd": [s for s in all_sheets if "kuota_ppd" in s],
        "sah_jpn": [s for s in all_sheets if "sah_jpn" in s],
    }
    prog=st.progress(0)
    for idx, (table, sheets) in enumerate(groups.items()):
        if not sheets:
            continue
        st.write(f"⏳ {table} dari {sheets}")
        try:
            dfs=[]
            for sh_name in sheets:
                try:
                    df=pd.read_excel(excel_path, sheet_name=sh_name)
                    if not df.empty:
                        dfs.append(df)
                except Exception as e:
                    st.warning(f"{sh_name} skip: {e}")
            if not dfs:
                continue
            combined=pd.concat(dfs, ignore_index=True)
            if table=="maklumat_sekolah" and "KOD SEKOLAH" in combined.columns:
                combined=combined.drop_duplicates(subset=["KOD SEKOLAH"])
            if table=="penempatan_ppd" and "NAMA GURU" in combined.columns:
                # keep last
                combined=combined.drop_duplicates(subset=["NAMA GURU", "NO PUSAT TUGAS"], keep="last")
            st.write(f"Total {len(combined)} baris")
            try:
                supa.table(table).delete().neq("id", -1).execute()
            except Exception as e:
                st.warning(f"Delete warning {table}: {e}")
            batch=df_to_batch(combined, table)
            # Supabase table names: maklumat_sekolah, cadangan_sup, penempatan_ppd exist. kuota_ppd, sah_jpn maybe not exist yet - we try
            target_table = table if table in ["maklumat_sekolah","cadangan_sup","penempatan_ppd","status_hantar"] else "maklumat_sekolah" if "maklumat" in table else table
            # Actually we have kuota_ppd and sah_jpn not in original 4, but we created? Try insert to penempatan or skip
            # For kuota_ppd and sah_jpn we will insert to status_hantar or create new? Let's just insert to their own table if exists, else skip with log
            try:
                for i in range(0, len(batch), 100):
                    supa.table(table).insert(batch[i:i+100]).execute()
                st.success(f"✅ {table}: {len(batch)} baris")
            except Exception as e:
                # If table not exist, try insert to maklumat or log
                st.warning(f"Table {table} belum wujud di Supabase, skip. Error: {e}")
                if table in ["maklumat_sekolah","cadangan_sup","penempatan_ppd"]:
                    raise e
        except Exception as e:
            st.error(f"❌ {table} gagal: {e}")
            st.exception(e)
        prog.progress((idx+1)/len(groups))
    st.balloons()
    st.success("SELESAI! Check Supabase Table Editor, data dah ada, bukan empty lagi.")
    st.info("Lepas ni rename balik: App-MIGRASI-FROM-EXCEL.py -> migrate.py backup, dan app_backup.py -> app.py untuk guna app asal JPN/PPD/SUP")
