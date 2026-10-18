
import streamlit as st
import pandas as pd
import os, math
st.set_page_config(page_title="Sistem Lantikan SPM 2026", layout="wide")

st.title("Sistem Lantikan Petugas SPM Selangor 2026")

@st.cache_data
def load_pusat():
    paths = ["pusat_2026.csv", "Pusat-SELANGOR-2026-FULL-GITHUB.csv", "pusat_SELANGOR_2026_FULL_GITHUB.csv"]
    for p in paths:
        if os.path.exists(p):
            try:
                return pd.read_csv(p)
            except:
                pass
    # fallback to /mnt/data
    try:
        return pd.read_csv("/mnt/data/pusat_2026.csv")
    except:
        return pd.DataFrame()

df = load_pusat()
if df.empty:
    st.error("pusat_2026.csv tidak jumpa! Pastikan file ada di GitHub sebelah app.py")
    st.stop()

PPD_CODE = {"Klang":"BA","Kuala Langat":"BB","Kuala Selangor":"BC","Hulu Langat":"BD","Hulu Selangor":"BE","Sabak Bernam":"BF","Gombak":"BG","Petaling Perdana":"BH","Sepang":"BJ","Petaling Utama":"BK"}
PPD_LIST = list(PPD_CODE.keys())

ppd = st.selectbox("Pilih PPD", PPD_LIST, index=9)
code = PPD_CODE[ppd]

df_ppd = df[df["NO_PUSAT"].astype(str).str.startswith(code)].copy()
df_ppd = df_ppd.sort_values("NO_PUSAT")

st.markdown(f"### Daerah {code} = {ppd} | {len(df_ppd)} pusat ada calon (dari pusat_2026.csv) - bukan 71 spare")

# Metrics
c1,c2,c3,c4 = st.columns(4)
c1.metric("Pusat Ada Calon", len(df_ppd))
c2.metric("Jumlah Calon", int(df_ppd["JUMLAH_CALON"].sum()))
c3.metric("Jumlah Kelas", int(df_ppd["JUMLAH_KELAS"].sum()))
c4.metric("Petugas Diperlukan", int(df_ppd["PETUGAS_NEEDED"].sum()))

st.markdown(f"**Formula:** 1 kelas = 20 calon, Petugas = 10 + max(0, kelas-4). Contoh: 10 kelas = 16 petugas")

# Table with calon data
st.dataframe(df_ppd[["NO_PUSAT","NAMA_PUSAT","KOD_SEKOLAH","JUMLAH_CALON","JUMLAH_KELAS","PETUGAS_NEEDED"]], use_container_width=True, height=600)

st.info("✅ Hanya pusat yang ada dalam pusat_2026.csv dipaparkan. Pusat spare kosong (BK003, BK004 dll tanpa calon) tidak dipaparkan. Tahun depan kalau calon ramai, tambah dalam CSV je!")

# Simulate penempatan table (dummy)
st.markdown("---")
st.markdown("### Senarai Pusat (untuk Jana Penempatan)")
# Create dummy status table like screenshot but only for 43
status_data = []
for _, row in df_ppd.iterrows():
    status_data.append({
        "NO PUSAT": row["NO_PUSAT"],
        "SEKOLAH TUAN RUMAH": row["NAMA_PUSAT"],
        "KOD SEKOLAH": row["KOD_SEKOLAH"],
        "JUMLAH CALON": row["JUMLAH_CALON"],
        "KELAS": row["JUMLAH_KELAS"],
        "PETUGAS DIPERLUKAN": row["PETUGAS_NEEDED"],
        "BIL DILANTIK": 0,
        "STATUS": "❌ Belum"
    })
st.dataframe(pd.DataFrame(status_data), use_container_width=True)

st.caption("Push app.py ini ke GitHub untuk fix paparan 71 pusat jadi 43 pusat sahaja!")
