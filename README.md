# Sistem Lantikan SPM 2026 Selangor - GitHub + Streamlit + Google Sheet

**Link Google Sheet:** https://docs.google.com/spreadsheets/d/11XotkvoHEiT-b1qtgXH1oGNDVlcXYtvg/edit

## Setup GitHub + Streamlit (Full Free, Tak Perlu Hosting Berbayar)

### 1. Repo GitHub
Buat repo baru `sistem-lantikan-spm2026`, upload:
- app_lantikan_2026_gsheet.py (rename jadi app.py atau streamlit_app.py)
- requirements.txt
- folder data/ (5 file master)

### 2. Folder data/
Letak dalam folder data/:
- senarai_506_PLUS_calon2026_FINAL.xlsx
- rujukan_poskod_selangor_PPD.xlsx
- TEMPLATE_1_MAKLUMAT_SEKOLAH_SUP.xlsx
- TEMPLATE_2_CADANGAN_PETUGAS_SUP.xlsx
- TEMPLATE_3_PENEMPATAN_AUTO_POSKOD.xlsx

### 3. Streamlit Cloud
- Pergi share.streamlit.io -> New app -> Pilih repo -> File app_lantikan_2026_gsheet.py
- Settings -> Secrets -> Paste isi dari secrets.toml.template
  ```
  [connections.gsheets]
  spreadsheet = "https://docs.google.com/spreadsheets/d/11XotkvoHEiT-b1qtgXH1oGNDVlcXYtvg/edit"
  ```
- Share Google Sheet -> Anyone with link Editor (penting!)
- Deploy!

### 4. Guna
- SUP isi borang -> masuk Google Sheet tab cadangan_sup
- PPD login -> Jana auto ikut poskod nearest -> masuk tab penempatan_ppd
- JPN sahkan -> Jana surat

## Formula
- KP = Bil Pusat + 1
- Pengawas = Bil Kelas + 5
- PK = 1
- Pengemas = Bil Pusat (boleh sekolah sendiri)
- Penyelia Kawasan = 1

## Rule
1. Tak boleh jaga sekolah sendiri kecuali Pengemas
2. Ikut PPD (BA=Klang, BK=Petaling Utama etc)
3. Nearest ikut poskod (40170 Shah Alam dekat dengan 40160)
4. Agih Lelaki
