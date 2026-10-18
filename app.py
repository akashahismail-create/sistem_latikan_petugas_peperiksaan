
import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Sistem Lantikan SPM 2026", layout="wide")
st.title("Sistem Lantikan Petugas SPM Selangor 2026")

@st.cache_data
def load_pusat():
    # Check ALL possible locations - root and data folder
    possible_paths = [
        "pusat_2026.csv",  # root - sebelah app.py
        "data/pusat_2026.csv",  # dalam data folder
        "Pusat-SELANGOR-2026-FULL-GITHUB.csv",
        "data/Pusat-SELANGOR-2026-FULL-GITHUB.csv",
        "pusat_SELANGOR_2026_FULL_GITHUB.csv",
        "data/pusat_SELANGOR_2026_FULL_GITHUB.csv",
        "senarai_506_PLUS_calon2026_FINAL.xlsx",
        "data/senarai_506_PLUS_calon2026_FINAL.xlsx"
    ]
    for p in possible_paths:
        if os.path.exists(p):
            try:
                if p.endswith(".csv"):
                    df = pd.read_csv(p)
                else:
                    df = pd.read_excel(p)
                if "NO_PUSAT" in df.columns and len(df) > 10:
                    st.success(f"✅ Loaded {len(df)} pusat dari: {p}")
                    return df
            except Exception as e:
                st.warning(f"Gagal load {p}: {e}")
    
    # Try list files for debug
    st.write("Files di root:", os.listdir(".")[:20])
    if os.path.exists("data"):
        st.write("Files di data/:", os.listdir("data")[:20])
    return pd.DataFrame()

df = load_pusat()

if df.empty:
    st.error("❌ pusat_2026.csv tidak jumpa! Pastikan file ada di GitHub sebelah app.py ATAU dalam data/pusat_2026.csv")
    st.info("Push pusat_2026.csv ke root (sebelah app.py) - bukan dalam data folder sahaja!")
    st.stop()

PPD_CODE = {"Klang":"BA","Kuala Langat":"BB","Kuala Selangor":"BC","Hulu Langat":"BD","Hulu Selangor":"BE","Sabak Bernam":"BF","Gombak":"BG","Petaling Perdana":"BH","Sepang":"BJ","Petaling Utama":"BK"}

ppd = st.selectbox("Pilih PPD", list(PPD_CODE.keys()), index=9)
code_ppd = PPD_CODE[ppd]

df_ppd = df[df["NO_PUSAT"].astype(str).str.startswith(code_ppd)].copy()
df_ppd = df_ppd.sort_values("NO_PUSAT")

st.markdown(f"### Daerah {code_ppd} = {ppd} | {len(df_ppd)} pusat ada calon (dari pusat_2026.csv) - bukan 71 spare")

c1,c2,c3,c4 = st.columns(4)
c1.metric("Pusat", len(df_ppd))
c2.metric("Calon", int(df_ppd["JUMLAH_CALON"].sum()) if "JUMLAH_CALON" in df_ppd.columns else 0)
c3.metric("Kelas", int(df_ppd["JUMLAH_KELAS"].sum()) if "JUMLAH_KELAS" in df_ppd.columns else 0)
c4.metric("Petugas", int(df_ppd["PETUGAS_NEEDED"].sum()) if "PETUGAS_NEEDED" in df_ppd.columns else len(df_ppd)*10)

cols = [c for c in ["NO_PUSAT","NAMA_PUSAT","KOD_SEKOLAH","JUMLAH_CALON","JUMLAH_KELAS","PETUGAS_NEEDED"] if c in df_ppd.columns]
st.dataframe(df_ppd[cols], use_container_width=True, height=600)

st.success(f"✅ Hanya {len(df_ppd)} pusat yang ada dalam pusat_2026.csv dipaparkan. Pusat kosong spare tidak dipaparkan. Tahun depan tukar JUMLAH_CALON dalam CSV je!")
