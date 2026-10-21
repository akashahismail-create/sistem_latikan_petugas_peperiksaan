import streamlit as st
from supabase import create_client
st.set_page_config(layout="wide")
SUPABASE_URL = "https://gnmaijhugkkvxejvsotk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdubWFpamh1Z2trdnhlanZzb3RrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTI0ODc4OTcsImV4cCI6MjEwODA2Mzg5N30.1YWg71nCwnQzP-KUzTdHR4rZAVCAesbKVqvVC1-X6lw"
supa = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("DEBUG - Check DB")

if st.button("Check guru_master"):
    try:
        res = supa.table("guru_master").select("*", count="exact").limit(1).execute()
        st.write(f"Count: {res.count}")
        res2 = supa.table("guru_master").select("kod_sekolah, nama_guru, ic_guru").limit(20).execute()
        st.write("20 rows sample:", res2.data)
    except Exception as e:
        st.error(f"Error: {e}")

if st.button("Check BFT0003"):
    try:
        res = supa.table("guru_master").select("*").eq("kod_sekolah", "BFT0003").limit(10).execute()
        st.write(f"BFT0003: {len(res.data)} rows")
        st.write(res.data)
    except Exception as e:
        st.error(f"Error: {e}")

if st.button("Check cadangan_sup"):
    try:
        res = supa.table("cadangan_sup").select("*", count="exact").limit(1).execute()
        st.write(f"cadangan_sup count: {res.count}")
        res2 = supa.table("cadangan_sup").select("*").limit(10).execute()
        st.write(res2.data)
    except Exception as e:
        st.error(f"Error: {e}")

if st.button("Import balik 60K dari Excel (jika kosong)"):
    import pandas as pd
    import glob
    files = glob.glob("*.xlsx")
    st.write(f"Files: {files}")
    path = None
    for f in files:
        if "MASTER" in f.upper() or "GURU" in f.upper():
            path=f
            break
    if not path and files:
        path=files[0]
    if path:
        st.write(f"Guna {path}")
        df=pd.read_excel(path, sheet_name=0)
        st.write(f"{len(df)} rows, cols {list(df.columns)}")
        st.dataframe(df.head(5))
        if st.button("Mula Import 60K (500 batch)"):
            import math
            BATCH=500
            ok=0
            bar=st.progress(0)
            for start in range(0, len(df), BATCH):
                end=min(start+BATCH, len(df))
                bdf=df.iloc[start:end]
                batch=[]
                for _,row in bdf.iterrows():
                    d={k: ("" if pd.isna(v) else str(v)) for k,v in row.to_dict().items()}
                    nama=d.get("NAMA GURU","").upper().strip()
                    if not nama or nama=="NAN": continue
                    batch.append({
                        "kod_ppd": d.get("KOD PPD","").lower().strip(),
                        "kod_sekolah": d.get("KOD SEKOLAH","").upper().strip(),
                        "nama_guru": nama,
                        "ic_guru": d.get("IC",""),
                        "jantina": d.get("JANTINA",""),
                        "poskod_rumah": d.get("POSKOD RUMAH","") or d.get("POSKOD_RUMAH",""),
                        "alamat_rumah": d.get("ALAMAT RUMAH","") or d.get("ALAMAT_RUMAH",""),
                        "telefon_guru": d.get("NO TELEFON GURU","") or d.get("TELEFON_GURU",""),
                        "email_guru": d.get("EMAIL GURU","") or d.get("EMAIL_GURU",""),
                        "kod_sekolah_asal": d.get("KOD SEKOLAH","").upper().strip(),
                        "nama_sekolah_asal": d.get("NAMA SEKOLAH",""),
                        "data": d
                    })
                if batch:
                    try:
                        supa.table("guru_master").insert(batch).execute()
                        ok+=len(batch)
                    except Exception as e:
                        st.error(f"Batch {start}: {e}")
                bar.progress(end/len(df))
            st.success(f"Import selesai {ok}")
