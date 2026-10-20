"""
MIGRASI FROM EXCEL - FIXED KEY
"""
import streamlit as st
import pandas as pd
from supabase import create_client
import os, glob

st.set_page_config(page_title="MIGRASI EXCEL -> SUPABASE", layout="centered")
st.title("🚀 MIGRASI Excel -> Supabase")
st.write("Versi FIXED KEY - Guna anon key penuh")

SUPABASE_URL = "https://gnmaijhugkkvxejvsotk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdubWFpamh1Z2trdnhlanZzb3RrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTI0ODc4OTcsImV4cCI6MjEwODA2Mzg5N30.1YWg71nCwnQzP-KUzTdHR4rZAVCAesbKVqvVC1-X6lw"
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
st.code(f"URL: {SUPABASE_URL}\nKEY: {SUPABASE_KEY[:20]}...{SUPABASE_KEY[-10:]}")
try:
    supa = create_client(SUPABASE_URL, SUPABASE_KEY)
    # Test query
    supa.table("maklumat_sekolah").select("id").limit(1).execute()
    st.success(f"✅ Supabase OK - Key sah")
except Exception as e:
    st.error(f"❌ Supabase gagal: {e}")
    st.stop()

st.subheader("2. Cari File Excel")
candidates = glob.glob("*.xlsx") + glob.glob("data/*.xlsx")
st.write(f"File jumpa: {candidates}")
excel_path = None
for p in candidates:
    if "Lantikan" in p or "lanti" in p.lower():
        excel_path = p
        break
if not excel_path and candidates:
    excel_path = candidates[0]

uploaded = st.file_uploader("Upload manual", type=["xlsx"])
if uploaded:
    with open("/tmp/upload.xlsx", "wb") as f:
        f.write(uploaded.getbuffer())
    excel_path = "/tmp/upload.xlsx"

if excel_path and os.path.exists(excel_path):
    st.success(f"✅ Guna file: {excel_path}")
    xls = pd.ExcelFile(excel_path)
    st.write(f"Sheet: {xls.sheet_names}")
else:
    st.error("❌ Tak jumpa Excel")
    st.stop()

def df_to_batch(df):
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
                except:
                    pass
            if not dfs:
                continue
            combined=pd.concat(dfs, ignore_index=True)
            if table=="maklumat_sekolah" and "KOD SEKOLAH" in combined.columns:
                combined=combined.drop_duplicates(subset=["KOD SEKOLAH"])
            if table=="penempatan_ppd" and "NAMA GURU" in combined.columns:
                combined=combined.drop_duplicates(subset=["NAMA GURU", "NO PUSAT TUGAS"], keep="last")
            st.write(f"Total {len(combined)} baris")
            try:
                supa.table(table).delete().neq("id", -1).execute()
            except Exception as e:
                st.warning(f"Delete {table}: {e}")
            batch=df_to_batch(combined)
            for i in range(0, len(batch), 100):
                supa.table(table).insert(batch[i:i+100]).execute()
                st.write(f"  Insert {i+len(batch[i:i+100])}/{len(batch)}")
            st.success(f"✅ {table}: {len(batch)} baris")
        except Exception as e:
            st.error(f"❌ {table} gagal: {e}")
            st.exception(e)
        prog.progress((idx+1)/len(groups))
    st.balloons()
    st.success("SELESAI! Check Supabase Table Editor")
