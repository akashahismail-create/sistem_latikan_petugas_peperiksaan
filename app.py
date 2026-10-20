"""
MIGRASI BERSIH - HANYA BA..BK SAHAJA - BUANG BR, ZZ, BL
- Delete semua data lama dalam cadangan_sup
- Baca HANYA sheet cadangan_sup_BA, BB, BC, BD, BE, BF, BG, BH, BJ, BK
- KOD_PPD ikut nama sheet, bukan parse dari KOD SEKOLAH
"""
import streamlit as st
import pandas as pd
from supabase import create_client
import glob, os

st.set_page_config(page_title="MIGRASI BERSIH BA-BK", layout="centered")
st.title("🧹 MIGRASI BERSIH - BUANG BR, MASUK BA..BK")
st.write("Ini akan DELETE semua BR, ZZ dan masukkan data bersih BA, BB, BC, BD, BE, BF, BG, BH, BJ, BK sahaja")

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

# Cari file
candidates = glob.glob("*.xlsx")
excel_path = None
for p in candidates:
    if "Lantikan" in p:
        excel_path = p
        break
if not excel_path and candidates:
    excel_path = candidates[0]

if not excel_path:
    st.error("Tak jumpa Excel")
    st.stop()

st.write(f"✅ Guna file: {excel_path}")
xls = pd.ExcelFile(excel_path)
st.write(f"Sheet ada: {xls.sheet_names}")

# List PPD valid
PPD_VALID = ["BA","BB","BC","BD","BE","BF","BG","BH","BJ","BK"]

if st.button("🧹 DELETE BR & MASUKKAN BA..BK BERSIH", type="primary", use_container_width=True):
    # 1. Delete semua cadangan_sup
    st.write("⏳ Delete semua data lama cadangan_sup...")
    try:
        # Delete in batches because Supabase limit
        for _ in range(10):
            res = supa.table("cadangan_sup").select("id").limit(1000).execute()
            if not res.data:
                break
            ids = [r["id"] for r in res.data]
            supa.table("cadangan_sup").delete().in_("id", ids).execute()
            st.write(f"  Deleted {len(ids)} rows...")
        st.success("✅ Semua data lama cadangan_sup dah delete")
    except Exception as e:
        st.error(f"Delete error: {e}")
        # fallback delete all
        try:
            supa.table("cadangan_sup").delete().neq("id", 0).execute()
        except:
            pass

    # 2. Masukkan dari sheet BA..BK sahaja
    total_insert = 0
    for ppd_code in PPD_VALID:
        sheet_name = f"cadangan_sup_{ppd_code}"
        if sheet_name not in xls.sheet_names:
            st.warning(f"Sheet {sheet_name} tak jumpa, skip")
            continue
        st.write(f"⏳ Baca {sheet_name}...")
        try:
            df = pd.read_excel(excel_path, sheet_name=sheet_name)
            if df.empty:
                continue
            # Dedup
            if "NAMA GURU" in df.columns and "KOD SEKOLAH ASAL" in df.columns:
                df = df.drop_duplicates(subset=["NAMA GURU", "KOD SEKOLAH ASAL"], keep="last")
            
            batch=[]
            for _, row in df.iterrows():
                rd=row.to_dict()
                clean={k: ("" if pd.isna(v) else str(v).strip() if isinstance(v,str) else v) for k,v in rd.items()}
                # KOD_PPD paksa ikut sheet, bukan parse
                batch.append({"KOD_PPD": ppd_code, "data": clean, "KOD_SEKOLAH": str(clean.get("KOD SEKOLAH ASAL", "")[:10])})
            
            # Insert 100 batch
            for i in range(0, len(batch), 100):
                supa.table("cadangan_sup").insert(batch[i:i+100]).execute()
            st.success(f"✅ {ppd_code}: {len(batch)} baris masuk")
            total_insert += len(batch)
        except Exception as e:
            st.error(f"❌ {ppd_code} gagal: {e}")

    st.balloons()
    st.success(f"🎉 SELESAI! Total {total_insert} baris bersih BA..BK dah masuk. BR, ZZ dah hilang!")
    
    # Show summary
    try:
        res = supa.table("cadangan_sup").select("KOD_PPD").limit(10000).execute()
        from collections import Counter
        c = Counter([r["KOD_PPD"] for r in res.data])
        st.write("### Summary KOD_PPD sekarang:")
        st.json(dict(c))
        if "BR" in c or "ZZ" in c:
            st.error("Masih ada BR/ZZ - kena delete lagi")
        else:
            st.success("✅ Bersih! Hanya BA..BK sahaja")
    except Exception as e:
        st.write(f"Summary error: {e}")

    st.info("Lepas ni restore app.py jadi App-FINAL-QWEN-BASE-SUPABASE.py balik")
