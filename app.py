"""
MIGRASI ULTIMATE FIX - Hanya guna KOD_PPD + data (jsonb)
Fix untuk error: Could not find NO_PUSAT_TUGAS column
"""
import streamlit as st
import pandas as pd
from supabase import create_client
import os, glob

st.set_page_config(page_title="MIGRASI FIX ULTIMATE", layout="centered")
st.title("🚀 MIGRASI FIX - KOD_PPD + data je")
st.write("Fix untuk error NO_PUSAT_TUGAS column not found")

SUPABASE_URL = "https://gnmaijhugkkvxejvsotk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdubWFpamh1Z2trdnhlanZzb3RrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTI0ODc4OTcsImV4cCI6MjEwODA2Mzg5N30.1YWg71nCwnQzP-KUzTdHR4rZAVCAesbKVqvVC1-X6lw"
try:
    if "SUPABASE_URL" in st.secrets:
        SUPABASE_URL = st.secrets["SUPABASE_URL"]
    if "SUPABASE_ANON_KEY" in st.secrets:
        SUPABASE_KEY = st.secrets["SUPABASE_ANON_KEY"]
except:
    pass

supa = create_client(SUPABASE_URL, SUPABASE_KEY)
st.success("✅ Supabase OK")

candidates = glob.glob("*.xlsx")
excel_path = None
for p in candidates:
    if "Lantikan" in p:
        excel_path = p
        break
if not excel_path and candidates:
    excel_path = candidates[0]

st.write(f"✅ Guna file: {excel_path}")
xls = pd.ExcelFile(excel_path)
st.write(f"Sheets: {xls.sheet_names}")

if st.button("🚀 MULA MIGRASI ULTIMATE FIX", type="primary", use_container_width=True):
    groups = {
        "maklumat_sekolah": [s for s in xls.sheet_names if "maklumat_sekolah" in s],
        "cadangan_sup": [s for s in xls.sheet_names if "cadangan_sup" in s],
        "penempatan_ppd": [s for s in xls.sheet_names if "penempatan_ppd" in s],
    }
    for table, sheets in groups.items():
        if not sheets:
            continue
        st.write(f"⏳ {table} dari {sheets}")
        dfs=[]
        for sh in sheets:
            try:
                df=pd.read_excel(excel_path, sheet_name=sh)
                if not df.empty:
                    dfs.append(df)
            except:
                pass
        if not dfs:
            continue
        combined=pd.concat(dfs, ignore_index=True)
        if table=="maklumat_sekolah" and "KOD SEKOLAH" in combined.columns:
            combined=combined.drop_duplicates(subset=["KOD SEKOLAH"])
        if table=="cadangan_sup":
            # gabung 8078 + 8078 jadi 16155, drop duplicate NAMA GURU + KOD SEKOLAH
            if "NAMA GURU" in combined.columns:
                combined=combined.drop_duplicates(subset=["NAMA GURU", "KOD SEKOLAH ASAL"], keep="last")
        if table=="penempatan_ppd" and "NAMA GURU" in combined.columns:
            combined=combined.drop_duplicates(subset=["NAMA GURU", "NO PUSAT TUGAS"], keep="last")

        st.write(f"Total {len(combined)} baris selepas dedup")

        # Delete old
        try:
            supa.table(table).delete().neq("id", 0).execute()
        except Exception as e:
            st.warning(f"Delete {table}: {e}")

        # Insert hanya KOD_PPD + data
        batch=[]
        for _, row in combined.iterrows():
            rd=row.to_dict()
            clean={k: ("" if pd.isna(v) else str(v).strip() if isinstance(v, str) else v) for k,v in rd.items()}
            kod_ppd=""
            for kk in ["KOD PPD", "KOD_PPD", "KOD SEKOLAH", "KOD SEKOLAH ASAL", "NO PUSAT TUGAS", "NO PUSAT"]:
                if kk in clean and clean[kk]:
                    v=str(clean[kk])
                    if len(v)>=2 and v[:2].isalpha():
                        kod_ppd=v[:2]
                        break
                    if kk.startswith("KOD"):
                        kod_ppd=v[:2] if len(v)>=2 else v
            if not kod_ppd:
                kod_ppd="BK"
            batch.append({"KOD_PPD": kod_ppd, "data": clean})

        # Insert 100 batch
        ok=0
        for i in range(0, len(batch), 100):
            try:
                supa.table(table).insert(batch[i:i+100]).execute()
                ok+=len(batch[i:i+100])
                st.write(f"  {table} {ok}/{len(batch)}")
            except Exception as e:
                st.error(f"Insert error {table} batch {i}: {e}")
                # Try one by one to find bad row
                for b in batch[i:i+100]:
                    try:
                        supa.table(table).insert(b).execute()
                    except Exception as ee:
                        pass
        st.success(f"✅ {table}: {ok} baris berjaya")
    st.balloons()
    st.success("SELESAI! Sekarang check Supabase - data dah ada")
    st.info("Lepas ni restore app.py jadi App-27-FULL-QWEN-SUPABASE.py")
