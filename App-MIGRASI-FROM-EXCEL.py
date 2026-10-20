"""
MIGRASI DARI EXCEL - Sistem_Lantikan_SPM_2026_7.xlsx -> Supabase
Upload file ni sebagai migrate.py
Tak perlu Google Sheet / gcp_service_account
"""
import streamlit as st
import pandas as pd
from supabase import create_client
import os

st.set_page_config(page_title="MIGRASI EXCEL -> SUPABASE", layout="centered")
st.title("🚀 MIGRASI Excel -> Supabase")
st.write("Import terus dari file Sistem_Lantikan_SPM_2026_7.xlsx - Tak perlu Google Sheet")

# Supabase
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
    st.success(f"✅ Supabase OK: {SUPABASE_URL}")
except Exception as e:
    st.error(f"❌ Supabase gagal: {e}")
    st.stop()

# Cari file Excel
st.subheader("2. Cari File Excel")
possible_paths = [
    "Sistem_Lantikan_SPM_2026_7.xlsx",
    "data/Sistem_Lantikan_SPM_2026_7.xlsx",
    "/mnt/data/Sistem_Lantikan_SPM_2026_7.xlsx",
    "Sistem_Lantikan_SPM_2026_6.xlsx",
    "data/Sistem_Lantikan_SPM_2026_6.xlsx"
]

excel_path = None
for p in possible_paths:
    if os.path.exists(p):
        excel_path = p
        break

uploaded = st.file_uploader("Atau upload file Sistem_Lantikan_SPM_2026_7.xlsx di sini", type=["xlsx"])
if uploaded:
    with open("/tmp/upload.xlsx", "wb") as f:
        f.write(uploaded.getbuffer())
    excel_path = "/tmp/upload.xlsx"

if excel_path:
    st.success(f"✅ Jumpa Excel: {excel_path}")
    xls = pd.ExcelFile(excel_path)
    st.write(f"Sheet ada: {xls.sheet_names}")
else:
    st.warning("❌ File Excel tak jumpa. Sila upload file Sistem_Lantikan_SPM_2026_7.xlsx")
    st.stop()

# Mapping sheet -> table supabase
# maklumat_sekolah, cadangan_sup, penempatan_ppd, status_hantar, kuota_ppd, sah_jpn

st.subheader("3. Klik Migrasi")

def df_to_batch(df, table_base):
    batch=[]
    for _, row in df.iterrows():
        rd=row.to_dict()
        clean={k: ("" if pd.isna(v) else v) for k,v in rd.items()}
        if table_base=="status_hantar" or table_base=="sah_jpn":
            batch.append({
                "KOD_PPD": str(clean.get("KOD PPD", clean.get("KOD_PPD", clean.get("KOD SEKOLAH", "")[:2] if "KOD SEKOLAH" in clean else ""))),
                "PPD": str(clean.get("PPD", clean.get("NO PUSAT", ""))),
                "STATUS": str(clean.get("STATUS", clean.get("STATUS SAH JPN", ""))),
                "TARIKH_HANTAR": str(clean.get("TARIKH HANTAR", "")),
                "TARIKH_SAH": str(clean.get("TARIKH SAH", "")),
                "data": clean
            })
        else:
            kod_ppd=str(clean.get("KOD PPD", clean.get("KOD_PPD", "")))
            if not kod_ppd:
                # Cuba dari NO PUSAT
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

if st.button("🚀 MULA MIGRASI DARI EXCEL", type="primary", use_container_width=True):
    # Kita migrasi sheet utama + sheet bahagi PPD
    # Gabungkan semua maklumat_sekolah_B* ke dalam maklumat_sekolah
    # Sama untuk cadangan_sup_B* -> cadangan_sup
    # penempatan_ppd_B* -> penempatan_ppd

    all_sheets = xls.sheet_names
    groups = {
        "maklumat_sekolah": [s for s in all_sheets if s.startswith("maklumat_sekolah")],
        "cadangan_sup": [s for s in all_sheets if s.startswith("cadangan_sup")],
        "penempatan_ppd": [s for s in all_sheets if s.startswith("penempatan_ppd")],
        "status_hantar": [s for s in all_sheets if "sah_jpn" in s or "status_hantar" in s],
        "kuota_ppd": [s for s in all_sheets if "kuota_ppd" in s],
    }

    progress = st.progress(0)
    total = len(groups)
    for idx, (table, sheets) in enumerate(groups.items()):
        if not sheets:
            continue
        st.write(f"⏳ Proses {table} dari sheet {sheets}")
        try:
            # Gabung semua df dari sheets dalam group
            dfs=[]
            for sh_name in sheets:
                try:
                    df=pd.read_excel(excel_path, sheet_name=sh_name)
                    if not df.empty:
                        dfs.append(df)
                except:
                    pass
            if not dfs:
                st.warning(f"{table} kosong")
                continue
            combined=pd.concat(dfs, ignore_index=True)
            # Drop duplicate based on KOD SEKOLAH or NAMA GURU etc
            # Untuk maklumat_sekolah drop dup KOD SEKOLAH
            if table=="maklumat_sekolah" and "KOD SEKOLAH" in combined.columns:
                combined=combined.drop_duplicates(subset=["KOD SEKOLAH"])
            if table=="penempatan_ppd" and "NAMA GURU" in combined.columns and "NO PUSAT TUGAS" in combined.columns:
                combined=combined.drop_duplicates(subset=["NAMA GURU", "NO PUSAT TUGAS"])

            st.write(f"Total {len(combined)} baris untuk {table}")

            # Delete lama
            try:
                supa.table(table).delete().neq("id", -1).execute()
            except Exception as e:
                st.warning(f"Delete {table} warning: {e} - cuba terus insert")

            batch=df_to_batch(combined, table)

            for i in range(0, len(batch), 100):
                supa.table(table).insert(batch[i:i+100]).execute()

            st.success(f"✅ {table}: {len(batch)} baris berjaya pindah dari {sheets}")

        except Exception as e:
            st.error(f"❌ {table} gagal: {e}")
            st.exception(e)

        progress.progress((idx+1)/total)

    st.balloons()
    st.success("SELESAI! Pergi Supabase > Table Editor > Refresh, check data ada.")
    st.info("Lepas siap, rename app_backup.py jadi app.py balik untuk guna app asal JPN/PPD/SUP")
