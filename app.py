"""
SISTEM PELANTIKAN PETUGAS PEPERIKSAAN SELANGOR 2026
FIX FINAL - Baca apa saja nama file ID DAERAH, tak kisah - atau _ , besar kecil huruf
Total 369 sekolah
"""

import streamlit as st
import pandas as pd
import os
import glob
import re
import time
import threading
from io import BytesIO

try:
    import gspread
    from google.oauth2.service_account import Credentials
except Exception:  # library belum dipasang - app tetap boleh buka
    gspread = None
    Credentials = None

st.set_page_config(page_title="Sistem Pelantikan Selangor 2026", layout="wide", page_icon="📚", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    [data-testid="stSidebar"] {display: none !important;}
    [data-testid="collapsedControl"] {display: none !important;}
    .big-title {text-align:center; font-size:30px; font-weight:bold; color:#0B5394;}
    .sub-title {text-align:center; font-size:14px; color:#666; margin-bottom:15px;}
    .login-box {background:#f0f7ff; padding:20px; border-radius:12px; border:1px solid #c2d8ff;}
    .left-panel {background:#f8fafc; padding:15px; border-radius:10px; border:1px solid #e2e8f0;}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_mapping():
    # Cara baru: scan semua file dalam data/ yang ada ID dan DAERAH, tak kisah nama
    data_folder = "data"
    candidates = []
    if os.path.exists(data_folder):
        for f in os.listdir(data_folder):
            low = f.lower()
            if "id" in low and "daerah" in low and (low.endswith(".xlsx") or low.endswith(".csv")):
                candidates.append(os.path.join(data_folder, f))
    
    # Cuba baca semua candidate, ambil yang paling banyak row
    best_df = pd.DataFrame()
    best_file = ""
    for path in candidates:
        try:
            if path.endswith(".xlsx"):
                df = pd.read_excel(path)
            else:
                df = pd.read_csv(path)
            # Check ada column PPD
            if "PPD" in df.columns and len(df) > len(best_df):
                best_df = df
                best_file = path
        except Exception as e:
            continue
    
    if not best_df.empty and len(best_df) > 10:
        return best_df, best_file
    
    # Fallback: cuba nama standard
    standard_paths = [
        "data/SENARAI_ID_SUP_BY_DAERAH.xlsx",
        "data/SENARAI_ID-SUP_BY_DAERAH.xlsx",
        "data/SENARAI_ID_SUP_BY_DAERAH.csv",
        "/mnt/data/SENARAI_ID_SUP_BY_DAERAH.xlsx",
        "/mnt/data/SENARAI_ID_SUP_BY_DAERAH.csv",
    ]
    for path in standard_paths:
        try:
            if os.path.exists(path):
                if path.endswith(".xlsx"):
                    df = pd.read_excel(path)
                else:
                    df = pd.read_csv(path)
                if "PPD" in df.columns and len(df) > 10:
                    return df, path
        except Exception:
            continue
    
    # Last fallback: generate dari master 506
    try:
        master_path = None
        for p in ["data/senarai_506_PLUS_calon2026_FINAL.xlsx", "data/senarai_506_PLUS_calon2026_FINAL.xlsx".lower(), "/mnt/data/senarai_506_PLUS_calon2026_FINAL.xlsx"]:
            # case insensitive search
            if os.path.exists("data"):
                for f in os.listdir("data"):
                    if "506" in f and "calon" in f.lower():
                        master_path = os.path.join("data", f)
                        break
        if not master_path:
            master_path = "data/senarai_506_PLUS_calon2026_FINAL.xlsx"
        
        df_master = pd.read_excel(master_path)
        PPD_MAP = {"BA":"Klang","BB":"Kuala Langat","BC":"Kuala Selangor","BD":"Hulu Langat","BE":"Hulu Selangor","BF":"Sabak Bernam","BG":"Gombak","BH":"Petaling Perdana","BJ":"Sepang","BK":"Petaling Utama"}
        order = ["BA","BB","BC","BD","BE","BF","BG","BH","BJ","BK"]
        schools = df_master.groupby("KOD SEKOLAH").first().reset_index()
        schools["KOD PPD"] = schools["NO PUSAT"].str[:2]
        id_mapping = []
        current_id = 1
        for kod in order:
            subset = schools[schools["KOD PPD"]==kod].sort_values("KOD SEKOLAH")
            for _, row in subset.iterrows():
                bil_pusat = len(df_master[df_master["KOD SEKOLAH"]==row["KOD SEKOLAH"]])
                senarai = ",".join(df_master[df_master["KOD SEKOLAH"]==row["KOD SEKOLAH"]]["NO PUSAT"].tolist())
                id_mapping.append({
                    "ID": current_id, "PASSWORD": str(current_id), "KOD SEKOLAH": row["KOD SEKOLAH"],
                    "NAMA SEKOLAH": row["NAMA PUSAT"], "PPD": PPD_MAP.get(kod, kod), "KOD PPD": kod,
                    "BIL PUSAT": bil_pusat, "SENARAI PUSAT": senarai
                })
                current_id += 1
        return pd.DataFrame(id_mapping), f"Generated from {master_path} ({len(id_mapping)} sekolah)"
    except Exception as e:
        return pd.DataFrame([{"ID":354,"PASSWORD":"354","KOD SEKOLAH":"BEB8653","NAMA SEKOLAH":"SMJK KATHOLIK","PPD":"Petaling Utama","KOD PPD":"BK","BIL PUSAT":3,"SENARAI PUSAT":"BK009,BK010,BK011"}]), f"Fallback dummy error: {e}"

mapping_df, file_used = load_mapping()

@st.cache_data
def load_pusat_calon():
    for p in ["pusat_2026.csv", "data/pusat_2026.csv", "Pusat-SELANGOR-2026-FULL-GITHUB.csv", "data/Pusat-SELANGOR-2026-FULL-GITHUB.csv", "/mnt/data/pusat_2026.csv"]:
        if os.path.exists(p):
            try:
                df = pd.read_csv(p) if p.endswith(".csv") else pd.read_excel(p)
                if "NO_PUSAT" in df.columns and len(df)>20:
                    return df
            except Exception:
                pass
    return pd.DataFrame()

df_calon_master = load_pusat_calon()

# ====== HELPER GSHEET & PENEMPATAN (mula) ======
GS_SPREADSHEET_ID_DEFAULT = "1dweem4yw6nKlo1wy5PA264prHEHpLoBPSu89jRFi484"


@st.cache_resource(ttl=300, show_spinner=False)
def get_gsheet():
    """Sambung ke Google Sheet sekali sahaja. Pulang (client, spreadsheet_id, ralat)."""
    if gspread is None:
        return None, None, "Library gspread/google-auth belum dipasang (pip install gspread google-auth)"
    try:
        try:
            sid = st.secrets["SPREADSHEET_ID"]
        except Exception:
            try:
                sid = st.secrets["connections"]["gsheets"]["spreadsheet"].split("/d/")[1].split("/")[0]
            except Exception:
                sid = GS_SPREADSHEET_ID_DEFAULT
        creds_dict = dict(st.secrets["gcp_service_account"])
        pk = creds_dict.get("private_key", "")
        if "\\n" in pk:
            creds_dict["private_key"] = pk.replace("\\n", "\n")
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds), sid, None
    except Exception as e:
        return None, None, str(e)


@st.cache_resource(show_spinner=False)
def _peta_kunci():
    return {"master": threading.Lock(), "peta": {}}


def get_lock(name="*"):
    """Satu kunci SETIAP tab - elak 2 orang tulis tab yang sama serentak.
    Daerah berbeza guna tab berbeza, jadi tak perlu tunggu satu sama lain."""
    k = _peta_kunci()
    with k["master"]:
        return k["peta"].setdefault(name, threading.Lock())


def _retry(fn, tries=3):
    """Cuba semula bila Google beri ralat sementara (kuota / rangkaian)."""
    for i in range(tries):
        try:
            return fn()
        except gspread.exceptions.APIError:
            if i == tries - 1:
                raise
            time.sleep(1.5 * (i + 1))


def _normalize_sheet_name(s):
    import re
    s = str(s).lower().strip()
    s = re.sub(r"[\s\-_]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s

@st.cache_data(ttl=60, show_spinner=False)
def list_all_sheets():
    try:
        client, sid, err = get_gsheet()
        if client is None:
            return [], err
        sh = _retry(lambda: client.open_by_key(sid))
        sheets = _retry(lambda: sh.worksheets())
        return [ws.title for ws in sheets], None
    except Exception as e:
        return [], str(e)

def find_matching_sheet(target_name):
    try:
        all_sheets, err = list_all_sheets()
        if not all_sheets:
            return None
        target_norm = _normalize_sheet_name(target_name)
        target_lower = target_name.lower().strip()
        if target_name in all_sheets:
            return target_name
        for s in all_sheets:
            if s.lower() == target_lower:
                return s
        for s in all_sheets:
            if _normalize_sheet_name(s) == target_norm:
                return s
        target_parts = target_norm.split("_")
        for s in all_sheets:
            s_norm = _normalize_sheet_name(s)
            if all(part in s_norm for part in target_parts if len(part)>1):
                return s
            if target_norm in s_norm or s_norm in target_norm:
                return s
        import re
        target_no_year = re.sub(r"_?\d{4}$", "", target_name)
        target_no_year_norm = _normalize_sheet_name(target_no_year)
        for s in all_sheets:
            if _normalize_sheet_name(s) == target_no_year_norm:
                return s
            if target_no_year_norm in _normalize_sheet_name(s):
                return s
        return None
    except Exception:
        return None

def read_sheet_strict(name):
    client, sid, err = get_gsheet()
    if client is None:
        raise RuntimeError(f"Google Sheet tidak connect: {err}")
    sh = _retry(lambda: client.open_by_key(sid))
    try:
        ws = sh.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        matched = find_matching_sheet(name)
        if matched and matched != name:
            try:
                ws = sh.worksheet(matched)
            except gspread.exceptions.WorksheetNotFound:
                return pd.DataFrame()
        else:
            return pd.DataFrame()
    records = _retry(lambda: ws.get_all_records(numericise_ignore=["all"]))
    return pd.DataFrame(records)


@st.cache_data(ttl=15, show_spinner=False)
def _cached_read(name):
    return read_sheet_strict(name)


def read_sheet(name):
    """Baca sheet dengan fallback ke format lama tanpa tahun jika sheet tahun kosong."""
    try:
        df = read_sheet_strict(name)
        if not df.empty:
            return df
        if "_" in name:
            parts = name.rsplit("_", 1)
            if parts[1].isdigit() and len(parts[1])==4:
                fallback_name = parts[0]
                try:
                    df_old = read_sheet_strict(fallback_name)
                    if not df_old.empty:
                        return df_old
                except:
                    pass
        return df
    except Exception as e:
        try:
            if "_" in name:
                parts = name.rsplit("_", 1)
                if parts[1].isdigit() and len(parts[1])==4:
                    fallback_name = parts[0]
                    return read_sheet_strict(fallback_name)
        except:
            pass
        return pd.DataFrame()

def read_sheet_tahun(base, kod_or_none=None, tahun=None):
    if tahun is None:
        try:
            tahun = st.session_state.get("tahun_pilih", 2026)
        except:
            tahun = 2026
    if kod_or_none:
        name = tab_daerah(base, kod_or_none, tahun)
    else:
        name = tab_tahun(base, tahun)
    return read_sheet(name)



def _cell(v):
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except (TypeError, ValueError):
        pass
    if hasattr(v, "item"):
        v = v.item()
    if isinstance(v, pd.Timestamp):
        return str(v)
    return v


def _tulis_sheet(name, df):
    """Tulis df ke sheet TANPA clear dulu: tulis data baru, baru buang baki baris lebihan."""
    if len(df.columns) == 0:
        return
    client, sid, err = get_gsheet()
    if client is None:
        raise RuntimeError(f"Google Sheet tidak connect: {err}")
    sh = _retry(lambda: client.open_by_key(sid))
    try:
        ws = sh.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=name, rows=1000, cols=30)
    values = [[str(c) for c in df.columns]] + [[_cell(v) for v in row] for row in df.itertuples(index=False, name=None)]
    n_rows, n_cols = len(values), len(values[0])
    if ws.row_count < n_rows:
        ws.add_rows(n_rows - ws.row_count + 100)
    if ws.col_count < n_cols:
        ws.add_cols(n_cols - ws.col_count)
    _retry(lambda: ws.update(values=values, range_name="A1"))
    if ws.row_count > n_rows:
        akhir = gspread.utils.rowcol_to_a1(ws.row_count, ws.col_count)
        _retry(lambda: ws.batch_clear([f"A{n_rows + 1}:{akhir}"]))


def modify_sheet(name, modifier):
    """Cara SELAMAT ubah data: baca segar -> modifier(df) -> tulis, dalam satu kunci.
    - Kalau bacaan gagal, TIADA apa ditulis (data lama selamat).
    - modifier boleh `raise ValueError("mesej")` untuk batalkan; pulang None = tiada perubahan.
    Pulang True kalau berjaya."""
    try:
        with get_lock(name):
            df = read_sheet_strict(name)
            baru = modifier(df)
            if baru is not None:
                _tulis_sheet(name, baru)
    except ValueError as e:
        st.error(f"⚠️ {e}")
        return False
    except Exception as e:
        st.error(f"❌ Gagal simpan ke '{name}' - data lama tidak dipadam. Cuba lagi sebentar. ({type(e).__name__}: {e})")
        return False
    _cached_read.clear()
    return True


def flash(level, msg):
    """Simpan mesej supaya masih nampak selepas st.rerun()."""
    st.session_state.setdefault("_flash", []).append((level, msg))


def show_flash():
    for level, msg in st.session_state.pop("_flash", []):
        getattr(st, level)(msg)


def norm_ic(x):
    """Samakan format IC (buang '-', tambah sifar depan) supaya perbandingan tepat."""
    d = re.sub(r"\D", "", str(x))
    return d.zfill(12) if d else ""


def keperluan_asal(pusat, df_calon):
    """Data asal ikut formula - tidak diubah. Pulang (petugas_needed, kelas, calon)."""
    petugas = 10
    kelas = 0
    calon = 0
    if df_calon is not None and not df_calon.empty and "NO_PUSAT" in df_calon.columns:
        r = df_calon[df_calon["NO_PUSAT"].astype(str) == str(pusat)]
        if not r.empty:
            try:
                calon = int(r.iloc[0].get("JUMLAH_CALON", 0))
            except: pass
            try:
                kelas = int(r.iloc[0].get("JUMLAH_KELAS", 0))
            except: pass
            if "PETUGAS_NEEDED" in df_calon.columns:
                try:
                    petugas = int(r.iloc[0]["PETUGAS_NEEDED"])
                except:
                    petugas = kelas + 10 if kelas else 10
            else:
                petugas = kelas + 10 if kelas else 10
    else:
        petugas = 10
    return petugas, kelas, calon

def keperluan_pengawas(pusat, df_calon, df_kuota=None):
    """Bilangan Pengawas FINAL - check kuota_ppd dulu, kalau PPD edit guna yang edit, kalau tak guna asal."""
    # Auto load kuota jika tidak diberi (supaya semua fungsi auto berubah bila PPD edit)
    if df_kuota is None:
        try:
            df_kuota = read_sheet("kuota_ppd")
        except:
            df_kuota = pd.DataFrame()
    # 1. Check kuota override dari PPD
    if df_kuota is not None and not df_kuota.empty and "NO PUSAT" in df_kuota.columns:
        r = df_kuota[df_kuota["NO PUSAT"].astype(str) == str(pusat)]
        if not r.empty:
            last = r.iloc[-1]
            try:
                for col in ["KEPERLUAN EDIT", "KEPERLUAN_PENGAWAS", "JUMLAH_PENGAWAS", "PETUGAS_EDIT", "KEPERLUAN AKHIR"]:
                    if col in df_kuota.columns and str(last.get(col,"")).strip() != "" and str(last.get(col)).lower()!="nan":
                        return int(float(str(last.get(col)).strip()))
            except:
                pass
    asal, _, _ = keperluan_asal(pusat, df_calon)
    return asal

def get_kuota_info(pusat, df_calon, df_kuota=None):
    """Untuk paparan: asal vs edit vs formula"""
    if df_kuota is None:
        try:
            df_kuota = read_sheet("kuota_ppd")
        except:
            df_kuota = pd.DataFrame()
    asal, kelas, calon = keperluan_asal(pusat, df_calon)
    formula = (kelas + 10) if kelas else asal
    edit = None
    catatan = ""
    tarikh_edit = ""
    edited_by = ""
    if df_kuota is not None and not df_kuota.empty and "NO PUSAT" in df_kuota.columns:
        r = df_kuota[df_kuota["NO PUSAT"].astype(str) == str(pusat)]
        if not r.empty:
            last = r.iloc[-1]
            for col in ["KEPERLUAN EDIT", "KEPERLUAN_PENGAWAS", "JUMLAH_PENGAWAS", "PETUGAS_EDIT", "KEPERLUAN AKHIR"]:
                if col in df_kuota.columns:
                    try:
                        v = str(last.get(col,"")).strip()
                        if v and v.lower()!="nan":
                            edit = int(float(v))
                            break
                    except: pass
            for col in ["CATATAN", "ALASAN", "NOTA"]:
                if col in df_kuota.columns:
                    catatan = str(last.get(col,"") or "")
                    break
            for col in ["TARIKH EDIT", "TARIKH"]:
                if col in df_kuota.columns:
                    tarikh_edit = str(last.get(col,"") or "")
                    break
            for col in ["EDIT OLEH", "PPD"]:
                if col in df_kuota.columns:
                    edited_by = str(last.get(col,"") or "")
                    break
    final = edit if edit is not None else asal
    return {"asal": asal, "kelas": kelas, "calon": calon, "formula": formula, "edit": edit, "final": final, "catatan": catatan, "tarikh": tarikh_edit, "oleh": edited_by}



def jawatan_kosong(need_peng, jawatan_sedia):
    """Jawatan yang masih kosong: 1 Ketua + 1 Timbalan + need_peng Pengawas."""
    sasaran = {"Ketua Pengawas": 1, "Timbalan Ketua Pengawas": 1, "Pengawas Peperiksaan": need_peng}
    sedia = [str(j).strip() for j in jawatan_sedia]
    hasil = []
    for jaw, bil in sasaran.items():
        hasil += [jaw] * max(0, bil - sedia.count(jaw))
    return hasil


def _kunci_nama(nama, kod):
    n = re.sub(r"\s+", " ", str(nama)).strip().upper()
    if not n or n == "NAN":
        return ""
    return f"{n}|{str(kod).strip().upper()}"


def kunci_guru(ic, nama, kod_sekolah):
    """Kunci pengenalan seorang guru: IC, DAN nama+kod sekolah. Padan salah satu = guru yang sama."""
    ks = []
    i = norm_ic(ic)
    if i:
        ks.append("IC:" + i)
    nk = _kunci_nama(nama, kod_sekolah)
    if nk:
        ks.append("NS:" + nk)
    return ks


def peta_guru_pusat(df_pen, df_simp=None):
    """{kunci_guru: NO PUSAT} untuk guru yang sudah dilantik. Guru dalam senarai simpanan
    ditanda 'SIMPANAN' (dianggap tak tersedia untuk jana auto / lantik biasa)."""
    peta = {}
    if df_pen is not None and not df_pen.empty and "NO PUSAT TUGAS" in df_pen.columns:
        for _, r in df_pen.iterrows():
            for k in kunci_guru(r.get("IC", ""), r.get("NAMA GURU", ""), r.get("KOD SEKOLAH ASAL GURU", "")):
                peta.setdefault(k, str(r["NO PUSAT TUGAS"]))
    if df_simp is not None and not df_simp.empty:
        for _, r in df_simp.iterrows():
            for k in kunci_guru(r.get("IC", ""), r.get("NAMA GURU", ""), r.get("KOD SEKOLAH ASAL GURU", "")):
                peta.setdefault(k, "SIMPANAN")
    return peta


def huraian_pusat(p_):
    return "senarai Petugas Simpanan" if p_ == "SIMPANAN" else f"pusat {p_}"


def pusat_guru(peta, ic, nama, kod_sekolah):
    """Pulang NO PUSAT kalau guru ini sudah dilantik di mana-mana pusat, selain itu None."""
    for k in kunci_guru(ic, nama, kod_sekolah):
        if k in peta:
            return peta[k]
    return None


def jana_penempatan(pusat_list, penempatan_df, cadangan_df, pusat_to_sekolah, pusat_to_nama, df_calon, label_status, simpanan_df=None):
    """Satu logik untuk jana 1 pusat ATAU semua pusat.
    Peraturan: setiap pusat orang BERBEZA (padan IC / nama+sekolah); guru sekolah tuan rumah tak jaga
    pusat sendiri; calon tak cukup -> jawatan dibiar kosong & dilaporkan (tiada guru diulang).
    Pulang (baris_baru, senarai_kurang[(pusat, bil_kurang)])."""
    ada_pen = (not penempatan_df.empty) and ("NO PUSAT TUGAS" in penempatan_df.columns)
    peta = peta_guru_pusat(penempatan_df, simpanan_df)

    cad = cadangan_df.copy()
    cad["_IC"] = cad["IC"].map(norm_ic)
    cad = cad[cad["_IC"] != ""]
    # buang calon berulang dalam senarai cadangan sendiri (IC sama / nama+sekolah sama)
    lihat, baris_unik = set(), []
    for idx, g in cad.iterrows():
        ks = kunci_guru(g.get("IC", ""), g.get("NAMA GURU", ""), g.get("KOD SEKOLAH ASAL", ""))
        if any(k in lihat for k in ks):
            continue
        lihat.update(ks)
        baris_unik.append(idx)
    cad = cad.loc[baris_unik]

    rows, kurang = [], []
    for p in pusat_list:
        p = str(p)
        kod_sek = str(pusat_to_sekolah.get(p, ""))
        need_peng = keperluan_pengawas(p, df_calon)
        sedia = []
        if ada_pen and "JAWATAN FINAL" in penempatan_df.columns:
            sedia = penempatan_df[penempatan_df["NO PUSAT TUGAS"].astype(str) == p]["JAWATAN FINAL"].tolist()
        perlu = jawatan_kosong(need_peng, sedia)
        if not perlu:
            continue
        calon = []
        for _, g in cad.iterrows():
            if len(calon) >= len(perlu):
                break
            if str(g.get("KOD SEKOLAH ASAL", "")) == kod_sek:
                continue
            if pusat_guru(peta, g.get("IC", ""), g.get("NAMA GURU", ""), g.get("KOD SEKOLAH ASAL", "")) is not None:
                continue
            calon.append(g)
        if len(calon) < len(perlu):
            kurang.append((p, len(perlu) - len(calon)))
        for jaw, guru in zip(perlu, calon):
            rows.append({
                "NO PUSAT TUGAS": p,
                "NAMA PUSAT TUGAS": pusat_to_nama.get(p, p),
                "KOD SEKOLAH ASAL GURU": guru.get("KOD SEKOLAH ASAL", ""),
                "NAMA SEKOLAH ASAL": guru.get("NAMA SEKOLAH ASAL", ""),
                "NAMA GURU": guru.get("NAMA GURU", ""),
                "IC": guru.get("IC", ""),
                "JANTINA": guru.get("JANTINA", ""),
                "JAWATAN FINAL": jaw,
                "POSKOD RUMAH": guru.get("POSKOD RUMAH", ""),
                "ALAMAT RUMAH": guru.get("ALAMAT RUMAH", ""),
                "NO TELEFON GURU": guru.get("NO TELEFON GURU", ""),
                "EMAIL GURU": guru.get("EMAIL GURU", ""),
                "STATUS PENEMPATAN": label_status,
            })
            for k in kunci_guru(guru.get("IC", ""), guru.get("NAMA GURU", ""), guru.get("KOD SEKOLAH ASAL", "")):
                peta[k] = p
    return rows, kurang


def bersihkan_duplikasi(df_pen, pusat_ppd):
    """Cari guru yang dilantik di lebih daripada satu pusat (padan IC ATAU nama+sekolah).
    Rekod PERTAMA (ikut susunan sheet, mis. BK001 dulu) dikekalkan; yang lain dibuang.
    Pulang (df_baru, laporan[dict])."""
    if df_pen is None or df_pen.empty or "NO PUSAT TUGAS" not in df_pen.columns:
        return df_pen, []
    pset = {str(p) for p in pusat_ppd}
    luar = ~df_pen["NO PUSAT TUGAS"].astype(str).isin(pset)
    peta, buang, laporan = {}, [], []
    for _, r in df_pen[luar].iterrows():
        for k in kunci_guru(r.get("IC", ""), r.get("NAMA GURU", ""), r.get("KOD SEKOLAH ASAL GURU", "")):
            peta.setdefault(k, str(r["NO PUSAT TUGAS"]))
    for i, r in df_pen[~luar].iterrows():
        ks = kunci_guru(r.get("IC", ""), r.get("NAMA GURU", ""), r.get("KOD SEKOLAH ASAL GURU", ""))
        asal = next((peta[k] for k in ks if k in peta), None)
        if asal is not None:
            buang.append(i)
            laporan.append({"NAMA GURU": r.get("NAMA GURU", ""), "IC": r.get("IC", ""), "SEKOLAH ASAL": r.get("NAMA SEKOLAH ASAL", ""),
                            "KEKAL DI": asal, "DUPLIKAT DI (akan dibuang)": str(r["NO PUSAT TUGAS"])})
        else:
            for k in ks:
                peta[k] = str(r["NO PUSAT TUGAS"])
    if not buang:
        return df_pen, []
    return df_pen.drop(index=buang).reset_index(drop=True), laporan
def sah_telefon(t):
    """No telefon: 9-12 digit (abaikan '-' dan jarak)."""
    return 9 <= len(re.sub(r"\D", "", str(t))) <= 12


def sah_email(e):
    """Email boleh kosong; kalau diisi mesti format betul."""
    e = str(e).strip()
    return e == "" or re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", e) is not None


def normalkan_cadangan(df):
    """Samakan lajur lama 'JAWATAN CADANG' dengan header sheet 'JAWATAN CADANGAN'."""
    if "JAWATAN CADANG" not in df.columns:
        return df
    df = df.copy()
    if "JAWATAN CADANGAN" in df.columns:
        kosong = df["JAWATAN CADANGAN"].astype(str).str.strip().isin(["", "nan", "None"])
        df.loc[kosong, "JAWATAN CADANGAN"] = df.loc[kosong, "JAWATAN CADANG"]
        return df.drop(columns=["JAWATAN CADANG"])
    return df.rename(columns={"JAWATAN CADANG": "JAWATAN CADANGAN"})


def tab_daerah(base, kod_ppd, tahun=None):
    """Nama tab ikut daerah + tahun, contoh tab_daerah('cadangan_sup','BK',2026) -> 'cadangan_sup_BK_2026'."""
    if tahun is None:
        try:
            tahun = st.session_state.get("tahun_pilih", 2026)
        except:
            tahun = 2026
    kod = str(kod_ppd).strip().upper()
    th = str(tahun).strip()
    return f"{base}_{kod}_{th}"

def tab_daerah_base(base, kod_ppd):
    return f"{base}_{str(kod_ppd).strip().upper()}"

def tab_tahun(base, tahun=None):
    if tahun is None:
        try:
            tahun = st.session_state.get("tahun_pilih", 2026)
        except:
            tahun = 2026
    return f"{base}_{tahun}"


def read_semua_daerah(base, tahun=None):
    """Gabung tab 10 daerah ikut tahun (untuk JPN sahaja)."""
    if tahun is None:
        try:
            tahun = st.session_state.get("tahun_pilih", 2026)
        except:
            tahun = 2026
    bahagian = []
    for _, _, _, kod in PPD_LIST:
        d = read_sheet(tab_daerah(base, kod, tahun))
        if d.empty:
            d = read_sheet(tab_daerah_base(base, kod))
        if not d.empty:
            d = d.copy()
            d["KOD PPD"] = kod
            bahagian.append(d)
    return pd.concat(bahagian, ignore_index=True) if bahagian else pd.DataFrame()


def pecah_data_lama(mapping_df, jeda=4):
    """Salin data dalam tab lama (satu tab untuk semua daerah) ke tab setiap daerah.
    - Tab lama TIDAK diubah / dipadam.
    - Baris yang sudah ada dalam tab daerah dilangkau, jadi selamat dijalankan berulang kali.
    - Baris yang kod sekolahnya tiada dalam senarai dilaporkan dan dibiar di tab lama."""
    peta_sek = dict(zip(mapping_df["KOD SEKOLAH"].astype(str), mapping_df["KOD PPD"].astype(str)))

    def k_mak(r):
        return str(r.get("KOD SEKOLAH", "")).strip()

    def k_cad(r):
        return (kunci_guru(r.get("IC", ""), r.get("NAMA GURU", ""), r.get("KOD SEKOLAH ASAL", "")) or [""])[0]

    def k_pen(r):
        k = (kunci_guru(r.get("IC", ""), r.get("NAMA GURU", ""), r.get("KOD SEKOLAH ASAL GURU", "")) or [""])[0]
        return str(r.get("NO PUSAT TUGAS", "")).strip() + "|" + k

    senarai = [("maklumat_sekolah", "KOD SEKOLAH", k_mak),
               ("cadangan_sup", "KOD SEKOLAH ASAL", k_cad),
               ("penempatan_ppd", "KOD SEKOLAH ASAL GURU", k_pen)]
    laporan = []
    for base, kol, kunci in senarai:
        try:
            lama = read_sheet_strict(base)
        except Exception as e:
            laporan.append({"TAB LAMA": base, "DAERAH": "-", "BARIS": 0, "STATUS": f"Gagal baca ({type(e).__name__})"})
            continue
        if lama.empty or kol not in lama.columns:
            laporan.append({"TAB LAMA": base, "DAERAH": "-", "BARIS": 0, "STATUS": "Tiada data"})
            continue
        if base == "cadangan_sup":
            lama = normalkan_cadangan(lama)
        lama["_PPD"] = lama[kol].astype(str).map(peta_sek)
        tak = int(lama["_PPD"].isna().sum())
        if tak:
            laporan.append({"TAB LAMA": base, "DAERAH": "(tak dikenali)", "BARIS": tak, "STATUS": "Dibiar di tab lama - kod sekolah tiada dalam senarai"})
        for kod, grp in lama.dropna(subset=["_PPD"]).groupby("_PPD"):
            baru = grp.drop(columns=["_PPD"]).reset_index(drop=True)
            kiraan = {"n": 0}

            def _gabung(df, baru=baru, kunci=kunci, kiraan=kiraan):
                if df.empty:
                    kiraan["n"] = len(baru)
                    return baru
                ada = {kunci(r) for _, r in df.iterrows()}
                tambah = baru[[kunci(r) not in ada for _, r in baru.iterrows()]]
                kiraan["n"] = len(tambah)
                if tambah.empty:
                    return None
                return pd.concat([df, tambah], ignore_index=True)

            ok = modify_sheet(tab_daerah(base, kod), _gabung)
            if not ok:
                status = "GAGAL - jalankan semula"
            elif kiraan["n"] == 0:
                status = "Sudah ada (tiada perubahan)"
            else:
                status = "Disalin"
            laporan.append({"TAB LAMA": base, "DAERAH": kod, "BARIS": kiraan["n"], "STATUS": status})
            time.sleep(jeda)   # elak had kuota Google (60 permintaan/min)
    return laporan


# ====== SENARAI GURU & MUAT NAIK / MUAT TURUN (mula) ======
JAWATAN_CADANGAN_SAH = ["Ketua Pengawas", "Timbalan Ketua Pengawas", "Pengawas Peperiksaan", "Pengemas Bilik", "Penyelia Kawasan"]
JAWATAN_LAZIM = "Pengawas Peperiksaan"
LAJUR_GURU = ["KOD SEKOLAH ASAL", "NAMA SEKOLAH ASAL", "NAMA GURU", "IC", "JANTINA", "POSKOD RUMAH", "ALAMAT RUMAH",
              "NO TELEFON GURU", "EMAIL GURU", "PENGALAMAN SPM", "NO PUSAT ASAL", "JAWATAN CADANGAN"]
LAJUR_TEMPLAT = ["NAMA GURU", "IC", "JANTINA", "NO TELEFON GURU", "EMAIL GURU", "ALAMAT RUMAH", "POSKOD RUMAH",
                 "PENGALAMAN SPM", "NO PUSAT ASAL", "JAWATAN CADANGAN"]
_ALIAS_LAJUR = {
    "NAMA GURU": ["NAMA GURU", "NAMA"],
    "IC": ["IC", "NO IC", "NO. IC", "NO KP", "NO. KP", "NO KAD PENGENALAN"],
    "JANTINA": ["JANTINA"],
    "NO TELEFON GURU": ["NO TELEFON GURU", "NO TELEFON", "NO. TELEFON", "NO TEL", "TELEFON"],
    "EMAIL GURU": ["EMAIL GURU", "EMAIL", "E-MEL", "EMEL"],
    "ALAMAT RUMAH": ["ALAMAT RUMAH", "ALAMAT"],
    "POSKOD RUMAH": ["POSKOD RUMAH", "POSKOD"],
    "PENGALAMAN SPM": ["PENGALAMAN SPM", "PENGALAMAN"],
    "NO PUSAT ASAL": ["NO PUSAT ASAL", "NO PUSAT"],
    "JAWATAN CADANGAN": ["JAWATAN CADANGAN", "JAWATAN"],
}
MAKS_BARIS_MUAT_NAIK = 1000


def _teks(v):
    """Nilai sel -> teks bersih (NaN -> '', 900101.0 -> '900101')."""
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except (TypeError, ValueError):
        pass
    s = str(v).strip()
    if re.fullmatch(r"\d+\.0", s):
        s = s[:-2]
    return s


def _bersih_teks(s):
    """Rapikan jarak & buang aksara pembuka formula (=, +, -, @) supaya selamat bila dibuka dalam Excel."""
    s = re.sub(r"\s+", " ", _teks(s)).strip()
    return s.lstrip("=+-@ ").strip() if s[:1] in ("=", "+", "-", "@") else s


def format_ic(x):
    d = re.sub(r"\D", "", str(x)).zfill(12)
    return f"{d[:6]}-{d[6:8]}-{d[8:]}"


def norm_telefon(t):
    """012-345 6789 / 1234567890 / +60123456789 -> 0123456789 (Excel selalu buang sifar depan)."""
    d = re.sub(r"\D", "", str(t))
    if not d:
        return ""
    if d.startswith("60") and len(d) >= 10:
        d = "0" + d[2:]
    elif not d.startswith("0"):
        d = "0" + d
    return d


def _ke_int(v, lalai=None):
    s = _teks(v)
    if s == "":
        return lalai
    try:
        return int(float(s))
    except ValueError:
        return None


def validasi_guru(nama, ic, alamat, tel, email):
    """Pulang mesej ralat (str) atau '' kalau semua sah. Sama dengan peraturan borang Cadangan Petugas."""
    d = re.sub(r"\D", "", str(ic))
    if not str(nama).strip() or not str(ic).strip():
        return "Nama Guru dan IC wajib isi!"
    if not (11 <= len(d) <= 12):
        return "IC mesti 12 digit (contoh: 900101-10-1234)"
    if len(str(alamat).strip()) < 10:
        return "Alamat Rumah wajib isi penuh (no rumah, jalan, taman, bandar)."
    if not sah_telefon(norm_telefon(tel)):
        return "No Telefon Guru wajib isi dan mesti 9-12 digit (contoh: 012-3456789)."
    if not sah_email(email):
        return "Format Email Guru tidak betul (contoh: nama@moe.gov.my) atau biarkan kosong."
    return ""


def kekurangan_guru(r):
    """Senarai maklumat yang tak lengkap untuk seorang guru (untuk semak sebelum hantar)."""
    k = []
    if not _teks(r.get("NAMA GURU", "")):
        k.append("nama")
    if not (11 <= len(re.sub(r"\D", "", str(r.get("IC", "")))) <= 12):
        k.append("IC")
    if len(_teks(r.get("ALAMAT RUMAH", ""))) < 10:
        k.append("alamat")
    if not sah_telefon(norm_telefon(r.get("NO TELEFON GURU", ""))):
        k.append("telefon")
    return k


def baca_fail_guru(fail):
    """Baca fail muat naik (.xlsx / .csv) sebagai DataFrame teks."""
    nama = str(getattr(fail, "name", "")).lower()
    if nama.endswith(".csv"):
        try:
            return pd.read_csv(fail, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        except UnicodeDecodeError:
            fail.seek(0)
            return pd.read_csv(fail, dtype=str, keep_default_na=False, encoding="latin-1")
    if nama.endswith(".xlsx"):
        xl = pd.ExcelFile(fail, engine="openpyxl")
        helaian = "Senarai Guru" if "Senarai Guru" in xl.sheet_names else xl.sheet_names[0]
        return xl.parse(helaian, dtype=str).fillna("")
    raise ValueError("Format fail tidak disokong. Guna .xlsx (templat) atau .csv")


def proses_muat_naik(df_up, kod_sekolah, nama_sekolah, senarai_pusat):
    """Semak fail muat naik baris demi baris. Pulang (df_sah[LAJUR_GURU], ralat[list dict]).
    Baris bermasalah TIDAK dimasukkan; baris sah boleh terus diimport."""
    df = df_up.copy()
    df.columns = [re.sub(r"\s+", " ", str(c)).strip().upper() for c in df.columns]
    peta = {}
    for kanon, alias in _ALIAS_LAJUR.items():
        for a in alias:
            if a in df.columns:
                peta[kanon] = a
                break
    wajib = ["NAMA GURU", "IC", "ALAMAT RUMAH", "NO TELEFON GURU", "POSKOD RUMAH"]
    hilang = [w for w in wajib if w not in peta]
    if hilang:
        raise ValueError("Lajur wajib tiada dalam fail: " + ", ".join(hilang) + ". Sila guna templat Excel yang dimuat turun.")
    if len(df) > MAKS_BARIS_MUAT_NAIK:
        raise ValueError(f"Fail terlalu besar ({len(df)} baris). Maksimum {MAKS_BARIS_MUAT_NAIK} baris.")

    pusat_sah = [str(p).upper() for p in (senarai_pusat or [])]
    jaw_peta = {j.upper(): j for j in JAWATAN_CADANGAN_SAH}
    jaw_peta.update({"PENGAWAS": "Pengawas Peperiksaan", "KP": "Ketua Pengawas", "TKP": "Timbalan Ketua Pengawas"})
    baik, ralat, lihat = [], [], {}
    for i, (_, r) in enumerate(df.iterrows()):
        no = i + 2   # baris 1 = tajuk
        ambil = lambda k: _teks(r[peta[k]]) if k in peta else ""
        nama, ic_raw, jan_raw = _bersih_teks(ambil("NAMA GURU")), ambil("IC"), ambil("JANTINA")
        alamat, tel_raw, email = _bersih_teks(ambil("ALAMAT RUMAH")), ambil("NO TELEFON GURU"), ambil("EMAIL GURU").lower()
        pos_raw, peng_raw, pusat_raw, jaw_raw = ambil("POSKOD RUMAH"), ambil("PENGALAMAN SPM"), ambil("NO PUSAT ASAL"), ambil("JAWATAN CADANGAN")
        if not any([nama, ic_raw, alamat, tel_raw, email, pos_raw, jan_raw]):
            continue   # baris kosong
        m = []
        if not nama:
            m.append("nama kosong")
        d = re.sub(r"\D", "", ic_raw)
        if not (11 <= len(d) <= 12):
            m.append("IC mesti 12 digit")
            ic_fmt = ""
        else:
            ic_fmt = format_ic(d)
            k = norm_ic(d)
            if k in lihat:
                m.append(f"IC sama dengan baris {lihat[k]} dalam fail")
            else:
                lihat[k] = no
        jan = {"L": "L", "LELAKI": "L", "M": "L", "P": "P", "PEREMPUAN": "P", "F": "P"}.get(jan_raw.upper())
        if not jan:
            m.append("jantina mesti L atau P")
        pos = re.sub(r"\D", "", pos_raw)
        if len(pos) != 5:
            m.append("poskod mesti 5 digit")
        if len(alamat) < 10:
            m.append("alamat terlalu pendek / kosong")
        tel = norm_telefon(tel_raw)
        if not sah_telefon(tel):
            m.append("no telefon mesti 9-12 digit")
        if not sah_email(email):
            m.append("format email salah")
        peng = _ke_int(peng_raw, 0)
        if peng is None or not (0 <= peng <= 40):
            m.append("pengalaman SPM mesti nombor 0-40")
            peng = 0
        pusat = _bersih_teks(pusat_raw).upper()
        if not pusat and len(pusat_sah) == 1:
            pusat = pusat_sah[0]
        if pusat and pusat_sah and pusat not in pusat_sah:
            m.append(f"no pusat asal {pusat} bukan pusat sekolah ini ({', '.join(pusat_sah)})")
        jaw = ""
        if jaw_raw:
            jaw = jaw_peta.get(_bersih_teks(jaw_raw).upper(), "")
            if not jaw:
                m.append("jawatan tidak sah")
        if m:
            ralat.append({"BARIS": no, "NAMA GURU": nama, "MASALAH": "; ".join(m)})
            continue
        baik.append({"KOD SEKOLAH ASAL": str(kod_sekolah), "NAMA SEKOLAH ASAL": nama_sekolah, "NAMA GURU": nama, "IC": ic_fmt,
                     "JANTINA": jan, "POSKOD RUMAH": int(pos), "ALAMAT RUMAH": alamat, "NO TELEFON GURU": tel,
                     "EMAIL GURU": email, "PENGALAMAN SPM": int(peng), "NO PUSAT ASAL": pusat, "JAWATAN CADANGAN": jaw})
    return pd.DataFrame(baik, columns=LAJUR_GURU), ralat


def gabung_guru_sekolah(df_roster, df_baru, kod_sekolah, nama_sekolah):
    """Masukkan / kemaskini guru dalam Senarai Guru (padan IC dalam sekolah SAMA sahaja).
    Tidak pernah memadam sesiapa. Pulang (df, bil_baru, bil_kemaskini)."""
    kod = str(kod_sekolah)
    baru = df_baru.copy()
    for c in LAJUR_GURU:
        if c not in baru.columns:
            baru[c] = ""
    baru["KOD SEKOLAH ASAL"] = kod
    baru["NAMA SEKOLAH ASAL"] = nama_sekolah
    if df_roster is None or df_roster.empty:
        return baru[LAJUR_GURU].reset_index(drop=True), len(baru), 0
    if "IC" not in df_roster.columns or "KOD SEKOLAH ASAL" not in df_roster.columns:
        raise ValueError("Format sheet guru_sekolah tidak dijangka - hubungi admin")
    df = df_roster.copy().astype(object)
    for c in LAJUR_GURU:
        if c not in df.columns:
            df[c] = ""
    ada = {}
    for idx, r in df.iterrows():
        if str(r["KOD SEKOLAH ASAL"]) == kod and norm_ic(r["IC"]):
            ada.setdefault(norm_ic(r["IC"]), idx)
    tambah, n_baru, n_kemaskini = [], 0, 0
    lihat = set()
    for _, g in baru.iterrows():
        k = norm_ic(g["IC"])
        if not k or k in lihat:
            continue
        lihat.add(k)
        if k in ada:
            for c in LAJUR_GURU:
                v = g[c]
                if c == "JAWATAN CADANGAN" and not _teks(v):
                    continue   # kekalkan jawatan sedia ada kalau fail tak tulis
                df.at[ada[k], c] = v
            n_kemaskini += 1
        else:
            r = {c: g[c] for c in LAJUR_GURU}
            if not _teks(r["JAWATAN CADANGAN"]):
                r["JAWATAN CADANGAN"] = JAWATAN_LAZIM
            tambah.append(r)
            n_baru += 1
    if tambah:
        df = pd.concat([df, pd.DataFrame(tambah)], ignore_index=True)
    return df, n_baru, n_kemaskini


def senarai_guru_sekolah(df_roster, df_cad, kod_sekolah):
    """Semua guru sekolah ini: Senarai Guru + (cadangan lama yang belum ada dalam senarai).
    Lajur CADANGAN = True kalau guru itu sudah dihantar sebagai cadangan."""
    kod = str(kod_sekolah)

    def milik(df):
        if df is None or df.empty or "IC" not in df.columns or "KOD SEKOLAH ASAL" not in df.columns:
            return pd.DataFrame()
        return df[df["KOD SEKOLAH ASAL"].astype(str) == kod]

    r = milik(df_roster)
    c = milik(normalkan_cadangan(df_cad) if (df_cad is not None and not df_cad.empty) else df_cad)
    cad = {}
    for _, x in c.iterrows():
        k = norm_ic(x.get("IC", ""))
        if k:
            cad.setdefault(k, x)
    out, lihat = [], set()
    for _, x in r.iterrows():
        k = norm_ic(x.get("IC", ""))
        if not k or k in lihat:
            continue
        lihat.add(k)
        b = {col: x.get(col, "") for col in LAJUR_GURU}
        if k in cad:
            jc = _teks(cad[k].get("JAWATAN CADANGAN", ""))
            if jc:
                b["JAWATAN CADANGAN"] = jc
        b["CADANGAN"] = k in cad
        out.append(b)
    for k, x in cad.items():
        if k in lihat:
            continue
        b = {col: x.get(col, "") for col in LAJUR_GURU}
        b["CADANGAN"] = True
        out.append(b)
    df = pd.DataFrame(out, columns=LAJUR_GURU + ["CADANGAN"])
    if df.empty:
        return df
    df["JAWATAN CADANGAN"] = df["JAWATAN CADANGAN"].map(lambda v: _teks(v) if _teks(v) in JAWATAN_CADANGAN_SAH else JAWATAN_LAZIM)
    return df.sort_values("NAMA GURU", kind="stable").reset_index(drop=True)


def buang_guru_roster(df_roster, kod_sekolah, ic_dipilih, ic_cadangan):
    """Buang guru daripada Senarai Guru. Guru yang sedang jadi cadangan tak boleh dibuang (tarik balik dulu)."""
    if df_roster.empty or "IC" not in df_roster.columns or "KOD SEKOLAH ASAL" not in df_roster.columns:
        raise ValueError("Senarai Guru tidak dijumpai - muat semula halaman")
    pilih = {norm_ic(i) for i in ic_dipilih}
    if pilih & set(ic_cadangan):
        raise ValueError("Ada guru yang sedang dicadangkan - nyah-tick dan Hantar dahulu untuk menarik balik cadangan.")
    sasar = (df_roster["KOD SEKOLAH ASAL"].astype(str) == str(kod_sekolah)) & df_roster["IC"].map(norm_ic).isin(pilih)
    if not sasar.any():
        raise ValueError("Guru yang dipilih tak dijumpai (mungkin sudah dibuang) - muat semula halaman")
    return df_roster[~sasar].reset_index(drop=True), int(sasar.sum())


def hantar_cadangan(df_cad, kod_sekolah, nama_sekolah, ticked_df, df_pen, df_simp):
    """HANTAR: senarai cadangan sekolah ini jadi TEPAT guru yang di-tick (ia yang dilihat PPD).
    - Guru baru di-tick -> ditambah; yang sedia ada -> dikemaskini (status dikekalkan).
    - Guru yang dinyah-tick -> ditarik balik, KECUALI sudah dilantik / disimpan PPD (ditolak).
    - IC yang sudah dicadang sekolah lain -> ditolak.
    Pulang (df_baru, statistik)."""
    kod = str(kod_sekolah)
    ic_hantar = {norm_ic(x) for x in ticked_df["IC"] if norm_ic(x)}
    if not ic_hantar:
        raise ValueError("Tiada guru dipilih untuk dihantar")
    df = pd.DataFrame()
    if df_cad is not None and not df_cad.empty:
        if "IC" not in df_cad.columns or "KOD SEKOLAH ASAL" not in df_cad.columns:
            raise ValueError("Format sheet cadangan_sup tidak dijangka - hubungi admin")
        df = normalkan_cadangan(df_cad).astype(object)
    own, lain = pd.DataFrame(), pd.DataFrame()
    if not df.empty:
        m = df["KOD SEKOLAH ASAL"].astype(str) == kod
        own, lain = df[m], df[~m]
    if not lain.empty:
        bt = lain[lain["IC"].map(norm_ic).isin(ic_hantar)]
        if not bt.empty:
            r = bt.iloc[0]
            raise ValueError(f"{r.get('NAMA GURU', '')} sudah dicadangkan oleh {r.get('NAMA SEKOLAH ASAL', r['KOD SEKOLAH ASAL'])} - hubungi PPD jika guru ini baru bertukar.")
    own_map = {}
    for _, r in own.iterrows():
        k = norm_ic(r.get("IC", ""))
        if k:
            own_map.setdefault(k, r)
    tarik = [k for k in own_map if k not in ic_hantar]
    if tarik:
        peta = peta_guru_pusat(df_pen, df_simp)
        terkunci = []
        for k in tarik:
            r = own_map[k]
            p_ = pusat_guru(peta, r.get("IC", ""), r.get("NAMA GURU", ""), r.get("KOD SEKOLAH ASAL", ""))
            if p_ is not None:
                terkunci.append(f"{r.get('NAMA GURU', '')} ({'Simpanan' if p_ == 'SIMPANAN' else p_})")
        if terkunci:
            raise ValueError("Tak boleh ditarik balik kerana sudah dilantik / disimpan PPD: " + ", ".join(terkunci) + ". Tick semula guru itu, atau minta PPD kosongkan lantikan dahulu.")
    baris, lihat, n_baru, n_kemaskini = [], set(), 0, 0
    for _, g in ticked_df.iterrows():
        k = norm_ic(g.get("IC", ""))
        if not k or k in lihat:
            continue
        lihat.add(k)
        status = "Dicadang"
        if k in own_map:
            s = _teks(own_map[k].get("STATUS", ""))
            if s and s.lower() not in ("nan", "none"):
                status = s
            n_kemaskini += 1
        else:
            n_baru += 1
        pos, peng = _ke_int(g.get("POSKOD RUMAH", "")), _ke_int(g.get("PENGALAMAN SPM", ""), 0)
        baris.append({
            "KOD SEKOLAH ASAL": kod, "NAMA SEKOLAH ASAL": nama_sekolah, "NAMA GURU": g.get("NAMA GURU", ""), "IC": g.get("IC", ""),
            "JANTINA": g.get("JANTINA", ""), "POSKOD RUMAH": pos if pos is not None else g.get("POSKOD RUMAH", ""),
            "ALAMAT RUMAH": g.get("ALAMAT RUMAH", ""), "NO TELEFON GURU": g.get("NO TELEFON GURU", ""), "EMAIL GURU": g.get("EMAIL GURU", ""),
            "JAWATAN CADANGAN": _teks(g.get("JAWATAN CADANGAN", "")) or JAWATAN_LAZIM,
            "PENGALAMAN SPM": peng if peng is not None else 0, "NO PUSAT ASAL": g.get("NO PUSAT ASAL", ""), "STATUS": status,
        })
    hasil = pd.concat([lain, pd.DataFrame(baris)], ignore_index=True) if not lain.empty else pd.DataFrame(baris)
    return hasil, {"baru": n_baru, "kemaskini": n_kemaskini, "tarik": len(tarik), "jumlah": len(baris)}


def excel_bytes(df, nama_sheet="Data"):
    """DataFrame -> fail .xlsx (bytes). Teks tak akan jadi formula."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter
    wb = Workbook()
    ws = wb.active
    ws.title = nama_sheet[:31]
    ws.append([str(c) for c in df.columns])
    for row in df.itertuples(index=False, name=None):
        ws.append([_cell(v) for v in row])
    for r in ws.iter_rows(min_row=2):
        for c in r:
            if isinstance(c.value, str):
                c.data_type = "s"
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="0B5394")
    for i, col in enumerate(df.columns, start=1):
        panjang = max([len(str(col))] + [len(str(v)) for v in df[col].head(200)]) if len(df) else len(str(col))
        ws.column_dimensions[get_column_letter(i)].width = min(max(12, panjang + 2), 45)
    ws.freeze_panes = "A2"
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def templat_excel_bytes(senarai_pusat=None):
    """Templat muat naik Senarai Guru (dengan pilihan drop-down + helaian Panduan)."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation
    wb = Workbook()
    ws = wb.active
    ws.title = "Senarai Guru"
    ws.append(LAJUR_TEMPLAT)
    wajib = {"NAMA GURU", "IC", "JANTINA", "NO TELEFON GURU", "ALAMAT RUMAH", "POSKOD RUMAH"}
    for i, c in enumerate(ws[1], start=1):
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="C0392B" if LAJUR_TEMPLAT[i - 1] in wajib else "0B5394")
    lebar = {"NAMA GURU": 34, "IC": 18, "JANTINA": 10, "NO TELEFON GURU": 17, "EMAIL GURU": 28, "ALAMAT RUMAH": 50,
             "POSKOD RUMAH": 13, "PENGALAMAN SPM": 16, "NO PUSAT ASAL": 15, "JAWATAN CADANGAN": 26}
    for i, nama in enumerate(LAJUR_TEMPLAT, start=1):
        h = get_column_letter(i)
        ws.column_dimensions[h].width = lebar.get(nama, 18)
        if nama in ("IC", "NO TELEFON GURU", "POSKOD RUMAH", "NO PUSAT ASAL"):
            for r in range(2, 502):
                ws[f"{h}{r}"].number_format = "@"   # teks - sifar depan tak hilang
    col = {n: get_column_letter(i) for i, n in enumerate(LAJUR_TEMPLAT, start=1)}
    dv_j = DataValidation(type="list", formula1='"L,P"', allow_blank=True)
    dv_w = DataValidation(type="list", formula1='"' + ",".join(JAWATAN_CADANGAN_SAH) + '"', allow_blank=True)
    ws.add_data_validation(dv_j)
    ws.add_data_validation(dv_w)
    dv_j.add(f"{col['JANTINA']}2:{col['JANTINA']}501")
    dv_w.add(f"{col['JAWATAN CADANGAN']}2:{col['JAWATAN CADANGAN']}501")
    if senarai_pusat:
        teks = ",".join(str(p) for p in senarai_pusat)
        if len(teks) < 250:
            dv_p = DataValidation(type="list", formula1=f'"{teks}"', allow_blank=True)
            ws.add_data_validation(dv_p)
            dv_p.add(f"{col['NO PUSAT ASAL']}2:{col['NO PUSAT ASAL']}501")
    ws.freeze_panes = "A2"

    pg = wb.create_sheet("Panduan")
    baris = [
        ["PANDUAN ISI TEMPLAT SENARAI GURU"], [""],
        ["1. Isi di helaian 'Senarai Guru'. Satu baris = satu guru. Jangan ubah nama lajur (baris 1)."],
        ["2. Lajur bertanda MERAH wajib diisi: NAMA GURU, IC, JANTINA, NO TELEFON GURU, ALAMAT RUMAH, POSKOD RUMAH."],
        ["3. Kod sekolah & nama sekolah diisi automatik oleh sistem."],
        ["4. Selepas muat naik, TICK guru yang akan bertugas di menu 'Senarai Guru', kemudian tekan Hantar."], [""],
        ["LAJUR", "PERATURAN", "CONTOH"],
        ["NAMA GURU", "Wajib", "AHMAD BIN ALI"],
        ["IC", "Wajib, 12 digit (boleh ada '-')", "900101-10-1234"],
        ["JANTINA", "Wajib: L atau P", "L"],
        ["NO TELEFON GURU", "Wajib, 9-12 digit", "012-3456789"],
        ["EMAIL GURU", "Pilihan; format email yang betul", "ahmad@moe.gov.my"],
        ["ALAMAT RUMAH", "Wajib, alamat penuh", "No 5, Jalan Mawar 3, Taman Bunga, 47500 Subang Jaya"],
        ["POSKOD RUMAH", "Wajib, 5 digit", "47500"],
        ["PENGALAMAN SPM", "Pilihan; bil. kali bertugas (0-40)", "3"],
        ["NO PUSAT ASAL", "Pilihan; pusat milik sekolah anda" + (": " + ", ".join(str(p) for p in senarai_pusat) if senarai_pusat else ""), (str(senarai_pusat[0]) if senarai_pusat else "")],
        ["JAWATAN CADANGAN", "Pilihan; " + ", ".join(JAWATAN_CADANGAN_SAH) + " (kosong = Pengawas Peperiksaan)", "Pengawas Peperiksaan"],
        [""], ["Muat naik semula fail yang sama selamat: guru dengan IC sama akan dikemaskini, bukan berganda."],
    ]
    for b in baris:
        pg.append(b)
    pg["A1"].font = Font(bold=True, size=13)
    for c in pg[8]:
        c.font = Font(bold=True)
    pg.column_dimensions["A"].width = 24
    pg.column_dimensions["B"].width = 62
    pg.column_dimensions["C"].width = 52
    for r in pg.iter_rows():
        for c in r:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
# ====== SENARAI GURU & MUAT NAIK / MUAT TURUN (tamat) ======


def padam_cadangan_sekolah(df_cad, kod_sekolah, ic_dipilih, df_pen, df_simp=None):
    """Buang cadangan guru (ikut IC) HANYA milik sekolah ini. Pulang (df_baru, bil_dipadam).
    Tolak (ValueError) kalau guru sudah dilantik PPD di mana-mana pusat."""
    if df_cad.empty or "IC" not in df_cad.columns or "KOD SEKOLAH ASAL" not in df_cad.columns:
        raise ValueError("Data cadangan tidak dijumpai - muat semula halaman")
    milik = df_cad["KOD SEKOLAH ASAL"].astype(str) == str(kod_sekolah)
    sasar = milik & df_cad["IC"].map(norm_ic).isin({norm_ic(i) for i in ic_dipilih})
    if not sasar.any():
        raise ValueError("Guru yang dipilih tak dijumpai (mungkin sudah dipadam) - muat semula halaman")
    peta = peta_guru_pusat(df_pen, df_simp)
    terkunci = []
    for _, r in df_cad[sasar].iterrows():
        p_ = pusat_guru(peta, r.get("IC", ""), r.get("NAMA GURU", ""), r.get("KOD SEKOLAH ASAL", ""))
        if p_ is not None:
            terkunci.append(f"{r.get('NAMA GURU', '')} ({'Simpanan' if p_ == 'SIMPANAN' else p_})")
    if terkunci:
        raise ValueError("Tak boleh dipadam kerana sudah dilantik / disimpan PPD: " + ", ".join(terkunci) + ". Minta PPD kosongkan lantikan itu dahulu.")
    return df_cad[~sasar].reset_index(drop=True), int(sasar.sum())


def buang_guru_ic(df, ic, pusat=None, label="senarai"):
    """Buang baris guru ikut IC (dan NO PUSAT kalau diberi). ValueError kalau tak jumpa."""
    if df.empty or "IC" not in df.columns:
        raise ValueError(f"Guru tidak dijumpai dalam {label} - muat semula halaman")
    mask = df["IC"].map(norm_ic) == norm_ic(ic)
    if pusat is not None:
        if "NO PUSAT TUGAS" not in df.columns:
            raise ValueError(f"Guru tidak dijumpai dalam {label} - muat semula halaman")
        mask = mask & (df["NO PUSAT TUGAS"].astype(str) == str(pusat))
    if not mask.any():
        raise ValueError(f"Guru tidak dijumpai dalam {label} (mungkin sudah diubah oleh orang lain) - muat semula halaman")
    return df[~mask].reset_index(drop=True)


def baris_simpanan(baris_pen, sebab, ppd_nama):
    """Baris untuk tab petugas_simpanan, daripada satu baris penempatan yang dibatalkan."""
    return {
        "KOD SEKOLAH ASAL GURU": baris_pen.get("KOD SEKOLAH ASAL GURU", ""), "NAMA SEKOLAH ASAL": baris_pen.get("NAMA SEKOLAH ASAL", ""),
        "NAMA GURU": baris_pen.get("NAMA GURU", ""), "IC": baris_pen.get("IC", ""), "JANTINA": baris_pen.get("JANTINA", ""),
        "POSKOD RUMAH": baris_pen.get("POSKOD RUMAH", ""), "ALAMAT RUMAH": baris_pen.get("ALAMAT RUMAH", ""),
        "NO TELEFON GURU": baris_pen.get("NO TELEFON GURU", ""), "EMAIL GURU": baris_pen.get("EMAIL GURU", ""),
        "JAWATAN ASAL": baris_pen.get("JAWATAN FINAL", ""), "DIBATAL DARI PUSAT": baris_pen.get("NO PUSAT TUGAS", ""),
        "SEBAB": sebab, "TARIKH BATAL": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"), "DIBATAL OLEH": f"PPD {ppd_nama}",
    }


def tambah_simpanan(df, baris):
    """Tambah ke simpanan; kalau guru sama sudah ada, gantikan."""
    if df.empty:
        return pd.DataFrame([baris])
    if "IC" in df.columns:
        df = df[df["IC"].map(norm_ic) != norm_ic(baris.get("IC", ""))]
    return pd.concat([df, pd.DataFrame([baris])], ignore_index=True) if not df.empty else pd.DataFrame([baris])


def transaksi_dua_tab(tab1, fn1, tab2, fn2, undur_fn1):
    """Jalankan fn1 pada tab1 kemudian fn2 pada tab2. Kalau fn2 gagal, cuba UNDUR fn1
    supaya guru tak hilang / tak berganda. Pulang True kalau kedua-dua berjaya."""
    if not modify_sheet(tab1, fn1):
        return False
    if modify_sheet(tab2, fn2):
        return True
    if modify_sheet(tab1, undur_fn1):
        st.error("Operasi dibatalkan sepenuhnya - tiada perubahan dibuat. Cuba lagi sebentar.")
    else:
        st.error(f"⚠️ Operasi separuh siap dan tak dapat diundur automatik. Muat semula halaman dan semak tab '{tab1}' dan '{tab2}'.")
    return False


def senarai_semua_petugas(cad_df, pen_df, simp_df):
    """Satu senarai SEMUA petugas daerah (cadangan + penempatan + simpanan, tanpa berulang)
    dengan STATUS: Belum ditempatkan / Ditempatkan (PUSAT, JAWATAN SEMASA) / Simpanan."""
    baris = {}

    def tambah(df, kod_col):
        if df is None or df.empty:
            return
        for _, r in df.iterrows():
            nama, kod = r.get("NAMA GURU", ""), r.get(kod_col, "")
            key = norm_ic(r.get("IC", "")) or ("NS:" + _kunci_nama(nama, kod))
            if key in ("", "NS:") or key in baris:
                continue
            baris[key] = {"KOD SEKOLAH ASAL": kod, "NAMA SEKOLAH ASAL": r.get("NAMA SEKOLAH ASAL", ""), "NAMA GURU": nama,
                          "IC": r.get("IC", ""), "JANTINA": r.get("JANTINA", ""), "POSKOD RUMAH": r.get("POSKOD RUMAH", ""),
                          "ALAMAT RUMAH": r.get("ALAMAT RUMAH", ""), "NO TELEFON GURU": r.get("NO TELEFON GURU", ""),
                          "EMAIL GURU": r.get("EMAIL GURU", ""), "PENGALAMAN SPM": r.get("PENGALAMAN SPM", "")}

    tambah(cad_df, "KOD SEKOLAH ASAL")
    tambah(pen_df, "KOD SEKOLAH ASAL GURU")
    tambah(simp_df, "KOD SEKOLAH ASAL GURU")
    peta = peta_guru_pusat(pen_df, simp_df)
    jaw = {}
    if pen_df is not None and not pen_df.empty and "IC" in pen_df.columns:
        for _, r in pen_df.iterrows():
            jaw.setdefault(norm_ic(r.get("IC", "")), r.get("JAWATAN FINAL", ""))
    susun = {"Belum ditempatkan": 0, "Simpanan": 1, "Ditempatkan": 2}
    hasil = []
    for b in baris.values():
        p_ = pusat_guru(peta, b["IC"], b["NAMA GURU"], b["KOD SEKOLAH ASAL"])
        if p_ is None:
            b.update({"STATUS": "Belum ditempatkan", "PUSAT": "", "JAWATAN SEMASA": ""})
        elif p_ == "SIMPANAN":
            b.update({"STATUS": "Simpanan", "PUSAT": "", "JAWATAN SEMASA": ""})
        else:
            b.update({"STATUS": "Ditempatkan", "PUSAT": p_, "JAWATAN SEMASA": jaw.get(norm_ic(b["IC"]), "")})
        hasil.append(b)
    df = pd.DataFrame(hasil)
    if df.empty:
        return df
    df["_s"] = df["STATUS"].map(susun)
    return df.sort_values(["_s", "NAMA GURU"], kind="stable").drop(columns="_s").reset_index(drop=True)


def tempatkan_manual(df_pen, guru, pusat, jawatan, kod_sek_tuan, need_peng, nama_pusat, label_status, pindah=False):
    """Tempatkan seorang petugas ke pusat + jawatan pilihan PPD. Pulang df penempatan baru.
    pindah=True: petugas sedang ditempatkan -> kedudukan lama dibuang, kedudukan baru ditambah (satu tab, atomik).
    Disemak: ada IC; bukan guru sekolah tuan rumah; belum dilantik tempat lain; jawatan MASIH kosong."""
    ic = norm_ic(guru.get("IC", ""))
    if not ic:
        raise ValueError("Petugas ini tiada IC - tak boleh ditempatkan melalui sistem. Lengkapkan IC dalam cadangan SUP dahulu.")
    if str(guru.get("KOD SEKOLAH ASAL", "")) == str(kod_sek_tuan):
        raise ValueError(f"{guru.get('NAMA GURU', '')} dari sekolah tuan rumah pusat {pusat} - tak boleh jaga pusat sendiri.")
    df = df_pen.copy() if (df_pen is not None and not df_pen.empty) else pd.DataFrame()
    ada = (not df.empty) and ("NO PUSAT TUGAS" in df.columns) and ("IC" in df.columns)
    asal = ""
    if pindah:
        if not ada or not (df["IC"].map(norm_ic) == ic).any():
            raise ValueError("Petugas tak dijumpai dalam penempatan (mungkin sudah diubah orang lain) - muat semula halaman")
        mask = df["IC"].map(norm_ic) == ic
        asal = str(df[mask].iloc[0]["NO PUSAT TUGAS"])
        df = df[~mask].reset_index(drop=True)
    else:
        p_ = pusat_guru(peta_guru_pusat(df), guru.get("IC", ""), guru.get("NAMA GURU", ""), guru.get("KOD SEKOLAH ASAL", ""))
        if p_ is not None:
            raise ValueError(f"{guru.get('NAMA GURU', '')} sudah dilantik di {huraian_pusat(p_)} - muat semula halaman")
    sedia = []
    if (not df.empty) and ("NO PUSAT TUGAS" in df.columns) and ("JAWATAN FINAL" in df.columns):
        sedia = df[df["NO PUSAT TUGAS"].astype(str) == str(pusat)]["JAWATAN FINAL"].tolist()
    if jawatan_kosong(need_peng, sedia).count(jawatan) < 1:
        raise ValueError(f"Jawatan {jawatan} di {pusat} sudah penuh / diisi orang lain - muat semula halaman")
    baru = pd.DataFrame([{
        "NO PUSAT TUGAS": str(pusat), "NAMA PUSAT TUGAS": nama_pusat,
        "KOD SEKOLAH ASAL GURU": guru.get("KOD SEKOLAH ASAL", ""), "NAMA SEKOLAH ASAL": guru.get("NAMA SEKOLAH ASAL", ""),
        "NAMA GURU": guru.get("NAMA GURU", ""), "IC": guru.get("IC", ""), "JANTINA": guru.get("JANTINA", ""),
        "JAWATAN FINAL": jawatan, "POSKOD RUMAH": guru.get("POSKOD RUMAH", ""), "ALAMAT RUMAH": guru.get("ALAMAT RUMAH", ""),
        "NO TELEFON GURU": guru.get("NO TELEFON GURU", ""), "EMAIL GURU": guru.get("EMAIL GURU", ""),
        "STATUS PENEMPATAN": label_status + (f" (dipindah dari {asal})" if asal else ""),
    }])
    return pd.concat([df, baru], ignore_index=True) if not df.empty else baru


# ====== HELPER GSHEET & PENEMPATAN (tamat) ======


# Debug info
# st.sidebar.write(f"File guna: {file_used}, total {len(mapping_df)}")

PPD_LIST = [
    ("1", "a", "Klang", "BA"), ("2", "b", "Kuala Langat", "BB"),
    ("3", "c", "Kuala Selangor", "BC"), ("4", "d", "Hulu Langat", "BD"),
    ("5", "e", "Hulu Selangor", "BE"), ("6", "f", "Sabak Bernam", "BF"),
    ("7", "g", "Gombak", "BG"), ("8", "h", "Petaling Perdana", "BH"),
    ("9", "i", "Sepang", "BJ"), ("10", "j", "Petaling Utama", "BK"),
]
PPD_USERS = {f"{nama}": {"id": id_, "password": pwd, "nama": f"PPD {nama}", "ppd_nama": nama, "kod": kod} for id_, pwd, nama, kod in PPD_LIST}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown('<div class="big-title">📚 SISTEM PELANTIKAN PETUGAS PEPERIKSAAN</div>', unsafe_allow_html=True)
    st.markdown('<div class="big-title" style="font-size:22px;">SELANGOR 2026</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-title">{len(mapping_df)} Sekolah Termasuk Persendirian • File: {os.path.basename(file_used)}<br>SPM Bertulis • Amali Sains • Mendengar • Bertutur</div>', unsafe_allow_html=True)

    # Debug visible
    with st.expander(f"🔍 Debug Data - File guna: {file_used} - {len(mapping_df)} sekolah", expanded=False):
        st.write(f"File yang dibaca: {file_used}")
        st.write(f"Jumlah sekolah: {len(mapping_df)}")
        if not mapping_df.empty:
            st.write("Daerah yang ada:", mapping_df["PPD"].value_counts().to_dict())
            st.dataframe(mapping_df.head(10))

    left, center, right = st.columns([1,2,1])
    with center:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown("### 🔐 Log Masuk")
        
        peranan = st.selectbox("1️⃣ Pilih Peranan", ["-- Pilih --", "JPN Selangor", "PPD", "SUP Sekolah"])
        
        if peranan == "JPN Selangor":
            st.info("JPN: ID 1 Password a")
            jpn_pwd = st.text_input("Kata Laluan JPN", type="password", placeholder="a")
            if st.button("🚀 Log Masuk JPN", use_container_width=True, type="primary"):
                if jpn_pwd=="a":
                    st.session_state.logged_in=True
                    st.session_state.user_role="JPN"
                    st.session_state.user_info={"nama":"JPN Selangor","role":"JPN","id":"1"}
                    st.rerun()
                else:
                    st.error("Password salah")
        
        elif peranan == "PPD":
            st.markdown("#### 2️⃣ Pilih Daerah (PPD)")
            ppd_daerah = st.selectbox("Daerah", ["-- Pilih Daerah --"] + [nama for _,_,nama,_ in PPD_LIST])
            if ppd_daerah != "-- Pilih Daerah --":
                ppd_info = PPD_USERS[ppd_daerah]
                bil_sek = len(mapping_df[mapping_df["PPD"]==ppd_daerah]) if not mapping_df.empty else 0
                st.success(f"PPD {ppd_daerah} ({ppd_info['kod']}) - {bil_sek} sekolah - Password {ppd_info['password']}")
                ppd_pwd = st.text_input(f"Password PPD {ppd_daerah}", type="password")
                if st.button(f"🚀 Log Masuk {ppd_daerah}", use_container_width=True, type="primary"):
                    if ppd_pwd == ppd_info['password']:
                        st.session_state.logged_in=True
                        st.session_state.user_role="PPD"
                        st.session_state.user_info={"nama":f"PPD {ppd_daerah}","ppd_nama":ppd_daerah,"kod":ppd_info['kod'],"password":ppd_info['password'],"id":ppd_info['id'],"role":"PPD"}
                        st.rerun()
                    else:
                        st.error("Password salah")
        
        elif peranan == "SUP Sekolah":
            st.markdown("#### 2️⃣ Pilih Daerah")
            order_daerah = ["Klang","Kuala Langat","Kuala Selangor","Hulu Langat","Hulu Selangor","Sabak Bernam","Gombak","Petaling Perdana","Sepang","Petaling Utama"]
            # Guna yang ada dalam file, tapi ikut order
            if not mapping_df.empty:
                daerah_ada = mapping_df["PPD"].unique().tolist()
                daerah_list = [d for d in order_daerah if d in daerah_ada]
            else:
                daerah_list = order_daerah
            
            sup_daerah = st.selectbox("Daerah Sekolah Anda", ["-- Pilih Daerah --"] + daerah_list)
            
            if sup_daerah != "-- Pilih Daerah --":
                df_daerah = mapping_df[mapping_df["PPD"]==sup_daerah].sort_values("NAMA SEKOLAH") if not mapping_df.empty else pd.DataFrame()
                st.markdown(f"#### 3️⃣ Pilih Sekolah di {sup_daerah} ({len(df_daerah)} sekolah)")
                if len(df_daerah)==0:
                    st.warning("Senarai kosong! Check file dalam data/")
                else:
                    sekolah_options = [f"{row['NAMA SEKOLAH']} ({row['KOD SEKOLAH']}) - {row['BIL PUSAT']} pusat [{row['SENARAI PUSAT']}]" for _, row in df_daerah.iterrows()]
                    sekolah_pilih = st.selectbox("Nama Sekolah (Masuk ikut sekolah, bukan pusat)", ["-- Pilih Sekolah --"] + sekolah_options)
                    
                    if sekolah_pilih != "-- Pilih Sekolah --":
                        idx = sekolah_options.index(sekolah_pilih)
                        row_sekolah = df_daerah.iloc[idx]
                        st.success(f"✅ {row_sekolah['NAMA SEKOLAH']} - {row_sekolah['KOD SEKOLAH']} - {row_sekolah['BIL PUSAT']} pusat: {row_sekolah['SENARAI PUSAT']}")
                        st.markdown("#### 4️⃣ Password Sahaja")
                        sup_pwd = st.text_input(f"Password {row_sekolah['NAMA SEKOLAH']}", type="password", placeholder=f"{row_sekolah['PASSWORD']}")
                        if st.button(f"🚀 Log Masuk {row_sekolah['NAMA SEKOLAH']}", use_container_width=True, type="primary"):
                            if sup_pwd == str(row_sekolah['PASSWORD']):
                                st.session_state.logged_in=True
                                st.session_state.user_role="SUP"
                                st.session_state.user_info={
                                    "nama": row_sekolah['NAMA SEKOLAH'],
                                    "kod_sekolah": row_sekolah['KOD SEKOLAH'],
                                    "ppd": row_sekolah['PPD'],
                                    "kod_ppd": row_sekolah['KOD PPD'],
                                    "id": str(row_sekolah['ID']),
                                    "password": str(row_sekolah['PASSWORD']),
                                    "bil_pusat": row_sekolah['BIL PUSAT'],
                                    "senarai_pusat": row_sekolah['SENARAI PUSAT'],
                                    "role":"SUP"
                                }
                                st.rerun()
                            else:
                                st.error(f"Password salah")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        with st.expander("ℹ️ Di mana update data?"):
            st.markdown(f"""
            **File yang sedang guna:** `{file_used}` - {len(mapping_df)} sekolah
            
            **Senarai Sekolah 369:**
            - App akan cari apa saja file dalam `data/` yang ada perkataan ID dan DAERAH (tak kisah - atau _ , besar kecil)
            - Contoh nama valid: `SENARAI_ID_SUP_BY_DAERAH.xlsx`, `SENARAI_ID-SUP_BY_DAERAH.xlsx`, `senarai_id_sup_by_daerah.xlsx` semua boleh!
            - File yang Kashah upload: `SENARAI_ID-SUP_BY_DAERAH.xlsx` - sekarang app dah boleh baca walaupun ada hyphen!
            - Kalau tak ada, app auto generate dari `senarai_506_PLUS_calon2026_FINAL.xlsx`
            
            **Tambah sekolah baru:** Edit file Excel tu tambah row ID 370, push GitHub
            
            **Senarai PPD:** Edit `PPD_LIST` dalam `app.py`
            """)
    
    st.markdown("---")
    st.caption(f"Data: {len(mapping_df)} sekolah dari {os.path.basename(file_used)} | Tanpa Sidebar")
    st.stop()

# Dah login
role = st.session_state.user_role
info = st.session_state.user_info

st.markdown(f"""
<div style="background:#0B5394; color:white; padding:10px 15px; border-radius:8px;">
    <b>📚 SPM 2026</b> | {info['nama']} | {role} | {info.get('ppd','')} {info.get('kod_sekolah','')} | {info.get('bil_pusat','')} pusat | File: {os.path.basename(file_used)}
</div>
""", unsafe_allow_html=True)

col_kiri, col_kanan = st.columns([1, 3])

with col_kiri:
    st.markdown('<div class="left-panel">', unsafe_allow_html=True)
    st.markdown(f"### 👤 {info['nama']}")
    if role=="SUP":
        st.markdown(f"**Kod:** {info['kod_sekolah']}")
        st.markdown(f"**PPD:** {info['ppd']} ({info['kod_ppd']})")
        st.markdown(f"**Pusat:** {info['bil_pusat']} pusat")
        st.code(info['senarai_pusat'])
    elif role=="PPD":
        st.markdown(f"**PPD:** {info['ppd_nama']} ({info['kod']}) - {len(mapping_df[mapping_df['KOD PPD']==info['kod']])} sekolah")
    st.markdown("---")
    if role=="SUP":
        menu = st.radio("Menu", ["Maklumat Sekolah", "Senarai Guru", "Muat Naik / Muat Turun", "Cadangan Petugas", "Status"], label_visibility="collapsed")
    elif role=="PPD":
        menu = st.radio("Menu", ["Senarai Pusat", "Kuota Pusat", "Cadangan SUP", "Jana Penempatan", "Penempatan Manual", "Batal Penempatan", "Petugas Simpanan", "Hantar JPN"], label_visibility="collapsed")
    else:
        menu = st.radio("Menu", ["Semua PPD", "Sahkan PPD", "Jana Surat", "Pindah Data Daerah"], label_visibility="collapsed")
    st.markdown("---")
    tahun_list = [2026, 2027, 2028, 2029, 2030]
    if "tahun_pilih" not in st.session_state:
        st.session_state["tahun_pilih"] = 2026
    tahun_pilih = st.selectbox("📅 Tahun", tahun_list, index=tahun_list.index(st.session_state["tahun_pilih"]) if st.session_state["tahun_pilih"] in tahun_list else 0, key="tahun_selector")
    st.session_state["tahun_pilih"] = tahun_pilih
    st.caption(f"Sheet: *_{tahun_pilih}")
    st.markdown("---")
    exam_type = st.selectbox("Peperiksaan", ["SPM Bertulis", "SPM Amali Sains", "Ujian Mendengar", "Ujian Bertutur"])
    st.markdown("---")
    if st.button("🚪 Log Keluar", use_container_width=True):
        st.session_state.logged_in=False
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with col_kanan:
    @st.cache_data
    def load_master():
        try:
            # cari file 506
            if os.path.exists("data"):
                for f in os.listdir("data"):
                    if "506" in f:
                        return pd.read_excel(os.path.join("data", f))
            return pd.read_excel("data/senarai_506_PLUS_calon2026_FINAL.xlsx")
        except Exception:
            return pd.DataFrame({"NO PUSAT":["BK009"],"NAMA PUSAT":["SMJK KATHOLIK"]})
    pusat_master = load_master()
    
    gspread_client, SPREADSHEET_ID_FIX, GS_ERR = get_gsheet()
    USE_GSHEET = gspread_client is not None
    if not USE_GSHEET:
        st.warning(f"GSheet tidak connect - data TIDAK boleh disimpan: {GS_ERR}")
    show_flash()

    # Setiap daerah ada tab sendiri (contoh cadangan_sup_BK) - data daerah tak bercampur
    _kod_daerah = str(info.get("kod_ppd") or info.get("kod") or "").strip().upper()
    if role in ("SUP", "PPD") and _kod_daerah not in {t[3] for t in PPD_LIST}:
        st.error("Kod daerah tidak sah - sila log keluar dan log masuk semula.")
        st.stop()
    TAB_MAKLUMAT = tab_daerah("maklumat_sekolah", _kod_daerah)
    TAB_CADANGAN = tab_daerah("cadangan_sup", _kod_daerah)
    TAB_PENEMPATAN = tab_daerah("penempatan_ppd", _kod_daerah)
    TAB_SIMPANAN = tab_daerah("petugas_simpanan", _kod_daerah)
    TAB_GURU = tab_daerah("guru_sekolah", _kod_daerah)

    if role=="SUP":
        if menu=="Maklumat Sekolah":
            st.header(f"🏫 {info['nama']} - {info['senarai_pusat']}")
            st.info(f"Kod {info['kod_sekolah']} | {info['bil_pusat']} pusat | Masuk ikut sekolah bukan pusat")
            maklumat = read_sheet(TAB_MAKLUMAT)
            # === AUTO-LOAD data sedia ada ===
            existing = pd.DataFrame()
            if not maklumat.empty and "KOD SEKOLAH" in maklumat.columns:
                existing = maklumat[maklumat["KOD SEKOLAH"].astype(str) == str(info['kod_sekolah'])]
            
            def_val_nama = info['nama']
            def_val_email = ""
            def_val_poskod = 46000
            def_val_bil_pusat = int(info['bil_pusat'])
            def_val_senarai = info['senarai_pusat']
            def_val_bil_kelas = 12
            def_val_nama_sup = f"SUP {info['nama']}"
            def_val_tel = ""
            def_val_pengetua = ""
            
            if not existing.empty:
                row = existing.iloc[-1]
                def_val_nama = str(row.get("NAMA SEKOLAH", def_val_nama))
                # Email
                for col in ["EMAIL SEKOLAH", "EMAIL"]:
                    if col in existing.columns and pd.notna(row.get(col)):
                        def_val_email = str(row.get(col, ""))
                        break
                # Telefon - ikut nama betul
                for col in ["NO TELEFON SEKOLAH", "TELEFON SEKOLAH", "NO TELEFON"]:
                    if col in existing.columns and pd.notna(row.get(col)):
                        def_val_tel = str(row.get(col, ""))
                        break
                # Poskod - ikut nama betul
                for col in ["NO POSKOD SEKOLAH", "POSKOD SEKOLAH", "POSKOD"]:
                    if col in existing.columns:
                        try:
                            v = str(row.get(col, "")).strip()
                            if v and v != "nan":
                                def_val_poskod = int(float(v))
                                break
                        except Exception:
                            pass
                # Pengetua
                for col in ["NAMA PENGETUA", "PENGETUA"]:
                    if col in existing.columns and pd.notna(row.get(col)):
                        def_val_pengetua = str(row.get(col, ""))
                        break
                for col in ["NAMA SUP"]:
                    if col in existing.columns and pd.notna(row.get(col)):
                        def_val_nama_sup = str(row.get(col, ""))
                        break
                for col in ["SENARAI NO PUSAT"]:
                    if col in existing.columns and pd.notna(row.get(col)):
                        def_val_senarai = str(row.get(col, ""))
                        break
                for col in ["BIL NO PUSAT"]:
                    if col in existing.columns:
                        try:
                            def_val_bil_pusat = int(float(str(row.get(col, def_val_bil_pusat)).strip() or def_val_bil_pusat))
                        except Exception:
                            pass
                        break
                for col in ["BIL KELAS DIGUNAKAN"]:
                    if col in existing.columns:
                        try:
                            def_val_bil_kelas = int(float(str(row.get(col, def_val_bil_kelas)).strip() or def_val_bil_kelas))
                        except Exception:
                            pass
                        break
            
            if not existing.empty:
                st.success(f"✅ Data {info['kod_sekolah']} dijumpai - auto isi")
            
            # Elak app crash kalau nilai lama dalam sheet di luar had
            def_val_poskod = max(40000, min(49000, def_val_poskod))
            def_val_bil_pusat = max(1, min(10, def_val_bil_pusat))
            def_val_bil_kelas = max(1, min(30, def_val_bil_kelas))

            with st.form("sekolah"):
                c1,c2 = st.columns(2)
                with c1:
                    nama_sek = st.text_input("NAMA SEKOLAH", value=def_val_nama)
                    email = st.text_input("EMAIL SEKOLAH", value=def_val_email, placeholder="bea8640@moe.edu.my")
                    no_tel = st.text_input("NO TELEFON SEKOLAH", value=def_val_tel, placeholder="03-XXXXXXX")
                    poskod_sek = st.number_input("NO POSKOD SEKOLAH",40000,49000,def_val_poskod)
                    bil_pusat = st.number_input("BIL PUSAT",1,10,def_val_bil_pusat)
                with c2:
                    senarai = st.text_input("SENARAI NO PUSAT", value=def_val_senarai)
                    bil_kelas = st.number_input("BIL KELAS DIGUNAKAN",1,30,def_val_bil_kelas)
                    nama_sup = st.text_input("NAMA SUP", value=def_val_nama_sup)
                    nama_pengetua = st.text_input("NAMA PENGETUA", value=def_val_pengetua)
                if st.form_submit_button("💾 Simpan", use_container_width=True):
                    # Data baru - semua field - ikut format sheet sedia ada
                    new_row = {
                        "KOD SEKOLAH": info['kod_sekolah'], 
                        "NAMA SEKOLAH": nama_sek, 
                        "EMAIL SEKOLAH": email,
                        "NO TELEFON SEKOLAH": no_tel,
                        "TELEFON SEKOLAH": no_tel,
                        "NAMA PENGETUA": nama_pengetua,
                        "NAMA SUP": nama_sup,
                        "NO POSKOD SEKOLAH": poskod_sek,
                        "POSKOD SEKOLAH": poskod_sek,
                        "BIL NO PUSAT": bil_pusat, 
                        "SENARAI NO PUSAT": senarai, 
                        "BIL KELAS DIGUNAKAN": bil_kelas,
                        "TARIKH KEMASKINI": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    def _simpan_maklumat(df):
                        if not df.empty and "KOD SEKOLAH" not in df.columns:
                            raise ValueError("Format sheet maklumat_sekolah tidak dijangka - hubungi admin")
                        if not df.empty:
                            # Satu rekod sahaja setiap sekolah (buang rekod lama sekolah ini)
                            df = df[df["KOD SEKOLAH"].astype(str) != str(info['kod_sekolah'])]
                        return pd.concat([df, pd.DataFrame([new_row])], ignore_index=True) if not df.empty else pd.DataFrame([new_row])

                    if modify_sheet(TAB_MAKLUMAT, _simpan_maklumat):
                        flash("success", f"✅ {nama_sek} berjaya dikemaskini! (Satu rekod sahaja untuk {info['kod_sekolah']})")
                        st.rerun()
            # === FIX: Hanya papar sekolah sendiri sahaja ===
            if not maklumat.empty and "KOD SEKOLAH" in maklumat.columns:
                maklumat_sendiri = maklumat[maklumat["KOD SEKOLAH"].astype(str) == str(info['kod_sekolah'])]
                if not maklumat_sendiri.empty:
                    st.markdown("#### 📋 Rekod Sekolah Anda (dari Google Sheet)")
                    st.dataframe(maklumat_sendiri, use_container_width=True)
                else:
                    st.info("Belum ada rekod untuk sekolah ini dalam Google Sheet")
            
        elif menu=="Senarai Guru":
            st.header(f"🧑‍🏫 Senarai Guru - {info['nama']}")
            st.caption("Semua guru sekolah anda. TICK guru yang akan bertugas, pilih jawatan, kemudian tekan Hantar. Senarai yang dihantar terus masuk ke portal PPD (menu Cadangan SUP).")
            kod_s = str(info['kod_sekolah'])
            n_g = st.session_state.get("guru_n", 0)
            _pusat_g = []
            for _p in re.findall(r"[A-Za-z]+\d+", str(info.get("senarai_pusat", ""))):
                if _p.upper() not in _pusat_g:
                    _pusat_g.append(_p.upper())
            guru_roster = read_sheet(TAB_GURU)
            cadangan_g = read_sheet(TAB_CADANGAN)
            senarai_g = senarai_guru_sekolah(guru_roster, cadangan_g, kod_s)

            if senarai_g.empty:
                st.info("Belum ada guru. Muat naik fail Excel di menu **Muat Naik / Muat Turun**, atau tambah seorang guru di bawah.")
            else:
                peta_g = peta_guru_pusat(read_sheet(TAB_PENEMPATAN), read_sheet(TAB_SIMPANAN))
                status_ppd = []
                for _, r_ in senarai_g.iterrows():
                    p_ = pusat_guru(peta_g, r_["IC"], r_["NAMA GURU"], r_["KOD SEKOLAH ASAL"])
                    status_ppd.append("" if p_ is None else ("🅿️ Simpanan PPD" if p_ == "SIMPANAN" else f"🔒 Dilantik di {p_}"))
                senarai_g["STATUS PPD"] = status_ppd
                m1, m2, m3 = st.columns(3)
                with m1:
                    st.metric("Jumlah Guru", len(senarai_g))
                with m2:
                    st.metric("Sudah Dicadang (dihantar)", int(senarai_g["CADANGAN"].sum()))
                with m3:
                    st.metric("Dilantik PPD", int((senarai_g["STATUS PPD"] != "").sum()))

                lajur_edit = ["CADANGAN", "NAMA GURU", "IC", "JANTINA", "JAWATAN CADANGAN", "NO TELEFON GURU", "ALAMAT RUMAH", "PENGALAMAN SPM", "NO PUSAT ASAL", "STATUS PPD"]
                paparan = senarai_g[lajur_edit].copy()
                paparan["CADANGAN"] = paparan["CADANGAN"].astype(bool)
                diedit = st.data_editor(
                    paparan, hide_index=True, use_container_width=True, key=f"guru_edit_{n_g}",
                    disabled=[c for c in lajur_edit if c not in ("CADANGAN", "JAWATAN CADANGAN")],
                    column_config={
                        "CADANGAN": st.column_config.CheckboxColumn("✔ Cadangan", help="Tick guru yang akan bertugas"),
                        "JAWATAN CADANGAN": st.column_config.SelectboxColumn("Jawatan", options=JAWATAN_CADANGAN_SAH, required=True),
                    },
                )
                tick = diedit["CADANGAN"].fillna(False).astype(bool)
                ticked_df = senarai_g[tick.values].copy()
                ticked_df["JAWATAN CADANGAN"] = diedit.loc[tick, "JAWATAN CADANGAN"].map(lambda v: _teks(v) or JAWATAN_LAZIM).values
                dulu = senarai_g["CADANGAN"].astype(bool)
                n_tick = int(tick.sum())
                n_baru_t = int((tick & ~dulu).sum())
                n_tarik_t = int((~tick & dulu).sum())
                st.info(f"Dipilih: **{n_tick}** guru | Baharu: {n_baru_t} | Ditarik balik: {n_tarik_t}")
                if n_tarik_t:
                    st.warning(f"⚠️ {n_tarik_t} guru yang sebelum ini dicadangkan akan DITARIK BALIK daripada senarai PPD (kecuali yang sudah dilantik PPD - itu akan ditolak).")

                if st.button(f"📤 HANTAR {n_tick} CADANGAN KE PPD", use_container_width=True, type="primary", disabled=n_tick == 0, key=f"guru_hantar_{n_g}"):
                    sedia_cad = {norm_ic(x) for x in cadangan_g["IC"]} if (not cadangan_g.empty and "IC" in cadangan_g.columns) else set()
                    tak_lengkap = []
                    for _, r_ in ticked_df.iterrows():
                        if norm_ic(r_["IC"]) not in sedia_cad:
                            k_ = kekurangan_guru(r_)
                            if k_:
                                tak_lengkap.append(f"{r_['NAMA GURU']} ({', '.join(k_)})")
                    if tak_lengkap:
                        st.error("Maklumat belum lengkap, kemaskini dahulu: " + "; ".join(tak_lengkap))
                    else:
                        hasil_h = {}
                        # 1) pastikan semua guru yang dihantar ada dalam Senarai Guru (tak memadam apa-apa)
                        ok_r = modify_sheet(TAB_GURU, lambda dfr: gabung_guru_sekolah(dfr, ticked_df, kod_s, info['nama'])[0])
                        if ok_r:
                            def _sync_cad(df_cad):
                                baru_c, stat = hantar_cadangan(df_cad, kod_s, info['nama'], ticked_df, read_sheet_strict(TAB_PENEMPATAN), read_sheet_strict(TAB_SIMPANAN))
                                hasil_h.update(stat)
                                return baru_c
                            # 2) senarai cadangan sekolah ini jadi tepat guru yang di-tick
                            if modify_sheet(TAB_CADANGAN, _sync_cad):
                                flash("success", f"✅ {hasil_h['jumlah']} cadangan dihantar ke PPD (baharu {hasil_h['baru']}, dikemaskini {hasil_h['kemaskini']}, ditarik balik {hasil_h['tarik']}).")
                                st.session_state["guru_n"] = n_g + 1
                                st.rerun()

            # ----- Tambah seorang guru -----
            with st.expander("➕ Tambah / kemaskini seorang guru"):
                with st.form(f"form_guru_roster_{n_g}"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        jaw_f = st.selectbox("JAWATAN CADANGAN", JAWATAN_CADANGAN_SAH, index=JAWATAN_CADANGAN_SAH.index(JAWATAN_LAZIM))
                        jan_f = st.selectbox("JANTINA", ["L", "P"])
                    with c2:
                        nama_f = st.text_input("NAMA GURU *")
                        tel_f = st.text_input("NO TELEFON GURU *", placeholder="contoh: 012-3456789")
                    with c3:
                        ic_f = st.text_input("IC *", placeholder="contoh: 900101-10-1234")
                        email_f = st.text_input("EMAIL GURU", placeholder="contoh: nama@moe.gov.my")
                    alamat_f = st.text_area("ALAMAT RUMAH *", placeholder="No rumah, jalan, taman, poskod, bandar")
                    c4, c5, c6 = st.columns(3)
                    with c4:
                        pos_f = st.number_input("POSKOD RUMAH *", 10000, 99999, 46000)
                    with c5:
                        peng_f = st.number_input("PENGALAMAN SPM (bil. kali bertugas)", 0, 40, 0)
                    with c6:
                        pusat_f = st.selectbox("NO PUSAT ASAL", _pusat_g + ["-- Tiada --"])
                    if st.form_submit_button("💾 Simpan ke Senarai Guru", use_container_width=True):
                        masalah_f = validasi_guru(nama_f, ic_f, alamat_f, tel_f, email_f)
                        if masalah_f:
                            st.error(masalah_f)
                        else:
                            baris_f = pd.DataFrame([{
                                "NAMA GURU": _bersih_teks(nama_f), "IC": format_ic(ic_f), "JANTINA": jan_f, "POSKOD RUMAH": int(pos_f),
                                "ALAMAT RUMAH": _bersih_teks(alamat_f), "NO TELEFON GURU": norm_telefon(tel_f), "EMAIL GURU": email_f.strip().lower(),
                                "PENGALAMAN SPM": int(peng_f), "NO PUSAT ASAL": "" if pusat_f == "-- Tiada --" else pusat_f, "JAWATAN CADANGAN": jaw_f,
                            }])
                            hasil_f = {}

                            def _simpan_f(dfr):
                                df_n, nb, nk = gabung_guru_sekolah(dfr, baris_f, kod_s, info['nama'])
                                hasil_f.update(baru=nb, kemaskini=nk)
                                return df_n
                            if modify_sheet(TAB_GURU, _simpan_f):
                                flash("success", f"✅ {_bersih_teks(nama_f)} {'ditambah' if hasil_f['baru'] else 'dikemaskini'} dalam Senarai Guru. Tick di jadual untuk jadikan cadangan.")
                                st.session_state["guru_n"] = n_g + 1
                                st.rerun()

            # ----- Buang guru -----
            if not senarai_g.empty:
                with st.expander("🗑️ Buang guru daripada Senarai Guru"):
                    boleh_buang = senarai_g[~senarai_g["CADANGAN"].astype(bool)]
                    label_b = {norm_ic(r_["IC"]): f"{r_['NAMA GURU']} | IC: {r_['IC']}" for _, r_ in boleh_buang.iterrows() if norm_ic(r_["IC"])}
                    st.caption("Hanya guru yang TIDAK sedang dicadangkan boleh dibuang. Untuk buang guru yang dicadangkan: nyah-tick, Hantar, kemudian buang di sini.")
                    if not label_b:
                        st.info("Tiada guru yang boleh dibuang.")
                    else:
                        pilih_b = st.multiselect("Pilih guru", list(label_b.keys()), format_func=lambda k: label_b[k], key=f"guru_buang_{n_g}")
                        sah_b = st.checkbox("Ya, buang terus daripada Google Sheet (tidak boleh dipulihkan)", key=f"guru_buang_sah_{n_g}")
                        if st.button(f"🗑️ Buang {len(pilih_b)} guru", use_container_width=True, disabled=not (pilih_b and sah_b), key=f"guru_buang_btn_{n_g}"):
                            ic_cad_b = {norm_ic(x) for x in cadangan_g["IC"]} if (not cadangan_g.empty and "IC" in cadangan_g.columns) else set()
                            hasil_b = {}

                            def _buang_r(dfr):
                                baru_r, bil = buang_guru_roster(dfr, kod_s, pilih_b, ic_cad_b)
                                hasil_b["bil"] = bil
                                return baru_r
                            if modify_sheet(TAB_GURU, _buang_r):
                                flash("success", f"✅ {hasil_b['bil']} guru dibuang daripada Senarai Guru.")
                                st.session_state["guru_n"] = n_g + 1
                                st.rerun()
        elif menu=="Muat Naik / Muat Turun":
            st.header(f"📁 Muat Naik / Muat Turun - {info['nama']}")
            st.caption("1) Muat turun templat Excel  →  2) isi senarai guru sekolah  →  3) muat naik di sini  →  4) tick cadangan di menu **Senarai Guru** dan Hantar.")
            kod_s = str(info['kod_sekolah'])
            up_n = st.session_state.get("up_n", 0)
            _pusat_u = []
            for _p in re.findall(r"[A-Za-z]+\d+", str(info.get("senarai_pusat", ""))):
                if _p.upper() not in _pusat_u:
                    _pusat_u.append(_p.upper())

            st.markdown("### ⬇️ 1. Muat turun templat")
            st.download_button("⬇️ Muat turun Templat Excel (kosong)", data=templat_excel_bytes(_pusat_u), file_name=f"templat_senarai_guru_{kod_s}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="dl_templat")

            st.markdown("---")
            st.markdown("### ⬆️ 2. Muat naik senarai guru (terus ke Google Sheet)")
            fail_up = st.file_uploader("Pilih fail Excel (.xlsx) atau CSV", type=["xlsx", "csv"], key=f"up_guru_{up_n}")
            if fail_up is not None:
                try:
                    df_up = baca_fail_guru(fail_up)
                    df_sah, ralat_up = proses_muat_naik(df_up, kod_s, info['nama'], _pusat_u)
                except ValueError as e:
                    st.error(f"⚠️ {e}")
                    df_sah, ralat_up = None, []
                except Exception as e:
                    st.error(f"⚠️ Fail tak dapat dibaca ({type(e).__name__}). Pastikan fail Excel yang sah dan tidak berkata laluan.")
                    df_sah, ralat_up = None, []
                if df_sah is not None:
                    u1, u2, u3 = st.columns(3)
                    with u1:
                        st.metric("Baris dibaca", len(df_sah) + len(ralat_up))
                    with u2:
                        st.metric("Sah", len(df_sah))
                    with u3:
                        st.metric("Ada masalah", len(ralat_up))
                    if ralat_up:
                        st.error("Baris di bawah TIDAK akan diimport. Betulkan dalam fail dan muat naik semula (baris sah boleh diimport dahulu).")
                        st.dataframe(pd.DataFrame(ralat_up), use_container_width=True, hide_index=True)
                    if not df_sah.empty:
                        st.markdown("**Pratonton baris sah:**")
                        st.dataframe(df_sah[["NAMA GURU", "IC", "JANTINA", "NO TELEFON GURU", "ALAMAT RUMAH", "POSKOD RUMAH", "NO PUSAT ASAL", "JAWATAN CADANGAN"]], use_container_width=True, hide_index=True)
                        if st.button(f"📤 Import {len(df_sah)} guru ke Google Sheet", use_container_width=True, type="primary", key=f"up_btn_{up_n}"):
                            hasil_u = {}

                            def _import(dfr):
                                df_n, nb, nk = gabung_guru_sekolah(dfr, df_sah, kod_s, info['nama'])
                                hasil_u.update(baru=nb, kemaskini=nk)
                                return df_n
                            if modify_sheet(TAB_GURU, _import):
                                flash("success", f"✅ Muat naik berjaya: {hasil_u['baru']} guru baharu, {hasil_u['kemaskini']} dikemaskini" + (f", {len(ralat_up)} baris ditolak." if ralat_up else ".") + " Sila tick cadangan di menu Senarai Guru.")
                                st.session_state["up_n"] = up_n + 1
                                st.rerun()
                    else:
                        st.warning("Tiada baris sah untuk diimport.")

            st.markdown("---")
            st.markdown("### ⬇️ 3. Muat turun data")
            guru_dl = senarai_guru_sekolah(read_sheet(TAB_GURU), read_sheet(TAB_CADANGAN), kod_s)
            d1, d2 = st.columns(2)
            with d1:
                if guru_dl.empty:
                    st.info("Senarai Guru masih kosong.")
                else:
                    df_dl = guru_dl.copy()
                    df_dl["CADANGAN"] = df_dl["CADANGAN"].map(lambda b: "Ya" if b else "Tidak")
                    st.download_button(f"⬇️ Senarai Guru sekolah ({len(df_dl)} guru)", data=excel_bytes(df_dl, "Senarai Guru"), file_name=f"senarai_guru_{kod_s}_{st.session_state.get('tahun_pilih', 2026)}.xlsx",
                                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="dl_roster")
            with d2:
                cad_dl = guru_dl[guru_dl["CADANGAN"].astype(bool)] if not guru_dl.empty else guru_dl
                if cad_dl.empty:
                    st.info("Belum ada cadangan dihantar.")
                else:
                    st.download_button(f"⬇️ Senarai Cadangan dihantar ({len(cad_dl)} guru)", data=excel_bytes(cad_dl.drop(columns=["CADANGAN"]), "Cadangan"), file_name=f"cadangan_{kod_s}_{st.session_state.get('tahun_pilih', 2026)}.xlsx",
                                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="dl_cadangan")
        elif menu=="Cadangan Petugas":
            st.header(f"👥 Cadangan - {info['nama']}")
            cadangan = read_sheet(TAB_CADANGAN)
            # Pusat milik sekolah ini (untuk NO PUSAT ASAL)
            _senarai_p = []
            for _p in re.findall(r"[A-Za-z]+\d+", str(info.get("senarai_pusat", ""))):
                if _p.upper() not in _senarai_p:
                    _senarai_p.append(_p.upper())
            TIADA_PUSAT = "-- Tiada --"
            with st.form("guru"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    jaw = st.selectbox("JAWATAN CADANGAN", ["Ketua Pengawas", "Timbalan Ketua Pengawas", "Pengawas Peperiksaan", "Pengemas Bilik", "Penyelia Kawasan"])
                    jantina = st.selectbox("JANTINA", ["L", "P"])
                with c2:
                    nama_g = st.text_input("NAMA GURU *")
                    tel_g = st.text_input("NO TELEFON GURU *", placeholder="contoh: 012-3456789")
                with c3:
                    ic = st.text_input("IC *", placeholder="contoh: 900101-10-1234")
                    email_g = st.text_input("EMAIL GURU", placeholder="contoh: nama@moe.gov.my")
                alamat_g = st.text_area("ALAMAT RUMAH *", placeholder="No rumah, jalan, taman, poskod, bandar")
                c4, c5, c6 = st.columns(3)
                with c4:
                    pos_rumah = st.number_input("POSKOD RUMAH *", 40000, 49000, 46000)
                with c5:
                    pengalaman = st.number_input("PENGALAMAN SPM (bil. kali bertugas)", 0, 40, 0)
                with c6:
                    pusat_asal = st.selectbox("NO PUSAT ASAL (pusat sekolah anda)", _senarai_p + [TIADA_PUSAT])
                if st.form_submit_button("➕ Tambah", use_container_width=True):
                    ic_digit = re.sub(r"\D", "", ic)
                    if not nama_g.strip() or not ic.strip():
                        st.error("Nama Guru dan IC wajib isi!")
                    elif len(ic_digit) != 12:
                        st.error("IC mesti 12 digit (contoh: 900101-10-1234)")
                    elif len(alamat_g.strip()) < 10:
                        st.error("Alamat Rumah wajib isi penuh (no rumah, jalan, taman, bandar).")
                    elif not sah_telefon(tel_g):
                        st.error("No Telefon Guru wajib isi dan mesti 9-12 digit (contoh: 012-3456789).")
                    elif not sah_email(email_g):
                        st.error("Format Email Guru tidak betul (contoh: nama@moe.gov.my) atau biarkan kosong.")
                    else:
                        ic_norm = norm_ic(ic)
                        new_g_row = {
                            "KOD SEKOLAH ASAL": info['kod_sekolah'], "NAMA SEKOLAH ASAL": info['nama'],
                            "NAMA GURU": nama_g.strip(), "IC": ic.strip(), "JANTINA": jantina,
                            "POSKOD RUMAH": pos_rumah, "ALAMAT RUMAH": re.sub(r"\s+", " ", alamat_g).strip(),
                            "NO TELEFON GURU": tel_g.strip(), "EMAIL GURU": email_g.strip(),
                            "JAWATAN CADANGAN": jaw, "PENGALAMAN SPM": int(pengalaman),
                            "NO PUSAT ASAL": "" if pusat_asal == TIADA_PUSAT else pusat_asal,
                            "STATUS": "Dicadang",
                        }

                        def _tambah_guru(df):
                            if not df.empty and ("IC" not in df.columns or "KOD SEKOLAH ASAL" not in df.columns):
                                raise ValueError("Format sheet cadangan_sup tidak dijangka - hubungi admin")
                            if df.empty:
                                return pd.DataFrame([new_g_row])
                            df = normalkan_cadangan(df)
                            sama = df["IC"].map(norm_ic) == ic_norm
                            lain = sama & (df["KOD SEKOLAH ASAL"].astype(str) != str(info['kod_sekolah']))
                            if lain.any():
                                r = df[lain].iloc[0]
                                raise ValueError(f"IC ini sudah dicadangkan oleh {r.get('NAMA SEKOLAH ASAL', r['KOD SEKOLAH ASAL'])}. Seorang guru hanya boleh dicadang oleh satu sekolah - hubungi PPD jika guru ini baru bertukar.")
                            baris = dict(new_g_row)
                            if sama.any() and "STATUS" in df.columns:
                                s_lama = str(df[sama].iloc[0].get("STATUS", "")).strip()
                                if s_lama and s_lama.lower() not in ("nan", "none"):
                                    baris["STATUS"] = s_lama   # kekalkan status sedia ada
                            # IC sama dalam sekolah SENDIRI sahaja yang diganti (kemaskini)
                            df = df[~sama]
                            return pd.concat([df, pd.DataFrame([baris])], ignore_index=True) if not df.empty else pd.DataFrame([baris])

                        if modify_sheet(TAB_CADANGAN, _tambah_guru):
                            # pastikan guru ini juga ada dalam Senarai Guru sekolah
                            modify_sheet(TAB_GURU, lambda dfr: gabung_guru_sekolah(dfr, pd.DataFrame([new_g_row]), str(info['kod_sekolah']), info['nama'])[0])
                            flash("success", f"✅ {nama_g} ditambah / dikemaskini! - Hanya untuk {info['kod_sekolah']}")
                            st.rerun()
            # === FIX: Hanya papar cadangan sekolah sendiri ===
            if not cadangan.empty and "KOD SEKOLAH ASAL" in cadangan.columns:
                cadangan_sendiri = cadangan[cadangan["KOD SEKOLAH ASAL"].astype(str) == str(info['kod_sekolah'])]
                if not cadangan_sendiri.empty:
                    st.markdown(f"#### 👥 Senarai Cadangan Anda - {info['kod_sekolah']} ({len(cadangan_sendiri)} orang)")
                    st.dataframe(cadangan_sendiri, use_container_width=True)

                    # ===== PADAM CADANGAN =====
                    st.markdown("#### 🗑️ Padam Cadangan")
                    label_padam = {}
                    if "IC" in cadangan_sendiri.columns:
                        for _, r_ in cadangan_sendiri.iterrows():
                            k_ = norm_ic(r_.get("IC", ""))
                            if k_:
                                label_padam[k_] = f"{r_.get('NAMA GURU', '')} | IC: {r_.get('IC', '')} | {r_.get('JAWATAN CADANGAN', r_.get('JAWATAN CADANG', ''))}"
                    if not label_padam:
                        st.info("Tiada cadangan yang boleh dipadam.")
                    else:
                        pilih_padam = st.multiselect("Pilih guru yang nak dipadam", list(label_padam.keys()), format_func=lambda k: label_padam[k], key=f"padam_pilih_{st.session_state.get('padam_n', 0)}")
                        sahkan_padam = st.checkbox("Ya, padam terus daripada Google Sheet (tidak boleh dipulihkan)", key=f"padam_sahkan_{st.session_state.get('padam_n', 0)}")
                        if st.button(f"🗑️ Padam {len(pilih_padam)} guru", use_container_width=True, disabled=not (pilih_padam and sahkan_padam), key="padam_btn"):
                            hasil_padam = {}

                            def _padam(df):
                                # Semak lantikan dengan bacaan segar; kalau gagal baca -> batal (selamat)
                                df_pen = read_sheet_strict(TAB_PENEMPATAN)
                                baru, bil = padam_cadangan_sekolah(df, info['kod_sekolah'], pilih_padam, df_pen, read_sheet_strict(TAB_SIMPANAN))
                                hasil_padam["bil"] = bil
                                return baru

                            if modify_sheet(TAB_CADANGAN, _padam):
                                flash("success", f"✅ {hasil_padam['bil']} cadangan dipadam terus daripada Google Sheet.")
                                st.session_state["padam_n"] = st.session_state.get("padam_n", 0) + 1   # kosongkan pilihan
                                st.rerun()
                else:
                    st.info(f"Belum ada cadangan untuk {info['kod_sekolah']}")
            else:
                st.info("Belum ada cadangan")
        else:
            st.header("📤 Status")
            maklumat_s = read_sheet(TAB_MAKLUMAT)
            cadangan_s = read_sheet(TAB_CADANGAN)
            kod_ini = str(info['kod_sekolah'])
            own_m = maklumat_s[maklumat_s["KOD SEKOLAH"].astype(str) == kod_ini] if (not maklumat_s.empty and "KOD SEKOLAH" in maklumat_s.columns) else pd.DataFrame()
            own_c = cadangan_s[cadangan_s["KOD SEKOLAH ASAL"].astype(str) == kod_ini] if (not cadangan_s.empty and "KOD SEKOLAH ASAL" in cadangan_s.columns) else pd.DataFrame()
            if own_m.empty:
                st.warning("❌ Maklumat Sekolah: belum diisi")
            else:
                st.success("✅ Maklumat Sekolah: sudah diisi")
                st.dataframe(own_m, use_container_width=True)
            guru_st = read_sheet(TAB_GURU)
            own_g = guru_st[guru_st["KOD SEKOLAH ASAL"].astype(str) == kod_ini] if (not guru_st.empty and "KOD SEKOLAH ASAL" in guru_st.columns) else pd.DataFrame()
            if own_g.empty:
                st.warning("❌ Senarai Guru: belum diisi (muat naik fail Excel di menu Muat Naik / Muat Turun)")
            else:
                st.success(f"✅ Senarai Guru: {len(own_g)} guru")
            if own_c.empty:
                st.warning("❌ Cadangan Petugas: belum ada")
            else:
                st.success(f"✅ Cadangan Petugas: {len(own_c)} orang")
    elif role=="PPD":
        # Senarai kod sekolah bawah PPD ini
        df_ppd = mapping_df[mapping_df["KOD PPD"]==info['kod']]
        kod_sekolah_ppd = df_ppd["KOD SEKOLAH"].astype(str).tolist()
        
        # Build list pusat under PPD - DARI MASTER + ID_SUP
        semua_pusat = []
        pusat_to_sekolah = {}
        pusat_to_nama = {}  # BK069 -> SMK TROPICANA
        
        # 1. Dari ID_SUP file (df_ppd)
        for _, r in df_ppd.iterrows():
            senarai = str(r.get("SENARAI PUSAT","")).split(",")
            for p in senarai:
                p = p.strip()
                if p:
                    semua_pusat.append(p)
                    pusat_to_sekolah[p] = str(r["KOD SEKOLAH"])
                    pusat_to_nama[p] = str(r["NAMA SEKOLAH"])
        
        # 2. Dari master 506 file - cari semua NO PUSAT ikut kod daerah (BA, BK etc)
        try:
            master_files = []
            if os.path.exists("data"):
                for f in os.listdir("data"):
                    if "506" in f and "calon" in f.lower():
                        master_files.append(os.path.join("data", f))
            for mf in master_files:
                try:
                    df_m = pd.read_excel(mf)
                    if "NO PUSAT" in df_m.columns and "KOD SEKOLAH" in df_m.columns:
                        # Filter NO PUSAT yang start dengan kod PPD ni (BK, BA dll)
                        mask = df_m["NO PUSAT"].astype(str).str.startswith(info['kod'])
                        df_m_ppd = df_m[mask]
                        for _, rm in df_m_ppd.iterrows():
                            p = str(rm["NO PUSAT"]).strip()
                            if p and p not in semua_pusat:
                                semua_pusat.append(p)
                            if p not in pusat_to_sekolah:
                                pusat_to_sekolah[p] = str(rm["KOD SEKOLAH"])
                            if p not in pusat_to_nama:
                                # Cari nama pusat dari df_m kalau ada NAMA PUSAT
                                nama_p = str(rm.get("NAMA PUSAT", rm.get("NAMA SEKOLAH", p)))
                                pusat_to_nama[p] = nama_p
                except Exception:
                    continue
        except Exception:
            pass
        
        # 3. Dari Google Sheet sah_jpn - ada NO PUSAT + NAMA PUSAT penuh!
        try:
            sah_tmp = read_sheet("sah_jpn")
            if not sah_tmp.empty and "NO PUSAT" in sah_tmp.columns:
                for _, rs in sah_tmp.iterrows():
                    p = str(rs.get("NO PUSAT","")).strip()
                    if p.startswith(info['kod']):
                        if p not in semua_pusat:
                            semua_pusat.append(p)
                        # Nama penuh pusat
                        nama_pusat = str(rs.get("NAMA PUSAT","")).strip()
                        if nama_pusat and nama_pusat.lower()!="nan":
                            pusat_to_nama[p] = nama_pusat
        except Exception:
            pass
        
        # 4. Dari penempatan_ppd sheet juga
        try:
            pen_tmp = read_sheet(TAB_PENEMPATAN)
            if not pen_tmp.empty and "NO PUSAT TUGAS" in pen_tmp.columns:
                for _, rp in pen_tmp.iterrows():
                    p = str(rp.get("NO PUSAT TUGAS","")).strip()
                    if p.startswith(info['kod']):
                        if p not in semua_pusat:
                            semua_pusat.append(p)
                        nama_p = str(rp.get("NAMA PUSAT TUGAS","")).strip()
                        if nama_p and nama_p.lower()!="nan" and p not in pusat_to_nama:
                            pusat_to_nama[p] = nama_p
        except Exception:
            pass
        
        # 5. Pastikan semua pusat ada nama - kalau takde, guna sekolah tuan rumah
        for p in semua_pusat:
            if p not in pusat_to_nama or not pusat_to_nama[p]:
                kod_sek = pusat_to_sekolah.get(p, "")
                if kod_sek:
                    # cari nama sekolah
                    row = df_ppd[df_ppd["KOD SEKOLAH"].astype(str)==kod_sek]
                    if not row.empty:
                        pusat_to_nama[p] = str(row.iloc[0]["NAMA SEKOLAH"])
                    else:
                        pusat_to_nama[p] = p
                else:
                    pusat_to_nama[p] = p
        
        semua_pusat = sorted(list(set(semua_pusat)))
        # FIX 43 bukan 71 - filter ikut pusat_2026.csv
        if not df_calon_master.empty and "NO_PUSAT" in df_calon_master.columns:
            calon_set = set(df_calon_master[df_calon_master["NO_PUSAT"].astype(str).str.startswith(info['kod'])]["NO_PUSAT"].astype(str).tolist())
            if calon_set:
                semua_pusat = sorted(list((set(semua_pusat) & calon_set) | calon_set))
                for _, rc in df_calon_master[df_calon_master["NO_PUSAT"].astype(str).str.startswith(info['kod'])].iterrows():
                    p = str(rc["NO_PUSAT"]).strip()
                    pusat_to_nama[p] = str(rc.get("NAMA_PUSAT", pusat_to_nama.get(p, p)))
                    if p not in pusat_to_sekolah:
                        pusat_to_sekolah[p] = str(rc.get("KOD_SEKOLAH", ""))
        
        if menu=="Senarai Pusat":
            if not df_calon_master.empty:
                dppd = df_calon_master[df_calon_master["NO_PUSAT"].astype(str).str.startswith(info['kod'])]
                tc = int(dppd["JUMLAH_CALON"].sum()) if not dppd.empty else 0
                tk = int(dppd["JUMLAH_KELAS"].sum()) if not dppd.empty else 0
                # tp guna final kuota (kalau PPD edit)
                tp = 0
                if not dppd.empty:
                    for _, r in dppd.iterrows():
                        p = str(r.get("NO_PUSAT",""))
                        tp += keperluan_pengawas(p, df_calon_master)
                tt = tp + len(dppd)*2
                st.header(f"🏢 PPD {info['ppd_nama']} - {len(df_ppd)} sekolah, {len(semua_pusat)} pusat")
                st.info(f"Daerah {info['kod']} = {info['ppd_nama']} | {len(semua_pusat)} pusat ada calon (bukan 71 spare) | 📊 {tc} calon, {tk} kelas, {tp} pengawas + {len(dppd)*2} KP/TKP = {tt} petugas di pusat | Penyelia Kawasan exclude (Bilik Kebal)")
            else:
                st.header(f"🏢 PPD {info['ppd_nama']} - {len(df_ppd)} sekolah, {len(semua_pusat)} pusat")
    
            
            # Load penempatan untuk kira status
            penempatan_all = read_sheet(TAB_PENEMPATAN)
            
            # Buat status table - KASHAH: 11 kelas = 17 pengawas +1 KP +1 TKP =19 total, Penyelia exclude
            status_data = []
            for pusat in semua_pusat:
                kod_sek_pusat = pusat_to_sekolah.get(pusat, "")
                nr = df_ppd[df_ppd["KOD SEKOLAH"].astype(str)==kod_sek_pusat]
                nama_sek_pusat = nr["NAMA SEKOLAH"].values[0] if not nr.empty else pusat_to_nama.get(pusat, pusat)
                
                calon_c = 0
                kelas_c = 0
                pengawas_c = 10
                total_c = 12
                # Guna kuota final (PPD edit jika ada) - auto ubah semua fungsi
                info_k = get_kuota_info(pusat, df_calon_master)
                calon_c = info_k["calon"]
                kelas_c = info_k["kelas"]
                pengawas_c = info_k["final"]  # <-- FINAL yang diguna sistem (asal atau edit PPD)
                total_c = pengawas_c + 2
                # Fallback kalau info_k kosong, guna asal df
                if not df_calon_master.empty and calon_c==0 and kelas_c==0:
                    rc = df_calon_master[df_calon_master["NO_PUSAT"].astype(str)==pusat]
                    if not rc.empty:
                        calon_c = int(rc.iloc[0].get("JUMLAH_CALON",calon_c))
                        kelas_c = int(rc.iloc[0].get("JUMLAH_KELAS",kelas_c))
                        if pengawas_c==10 and "PETUGAS_NEEDED" in rc.columns:
                            try:
                                pengawas_c = int(rc.iloc[0].get("PETUGAS_NEEDED",pengawas_c))
                                total_c = pengawas_c + 2
                            except:
                                pass
                
                if not penempatan_all.empty and "NO PUSAT TUGAS" in penempatan_all.columns:
                    bil = len(penempatan_all[penempatan_all["NO PUSAT TUGAS"].astype(str)==pusat])
                    if bil >= total_c:
                        status = f"✅ Lengkap ({bil}/{total_c})"
                    elif bil>0:
                        status = f"⚠️ Separa ({bil}/{total_c})"
                    else:
                        status = f"❌ Belum (0/{total_c})"
                else:
                    bil = 0
                    status = f"❌ Belum (0/{total_c})"
                
                status_data.append({"NO PUSAT": pusat, "SEKOLAH TUAN RUMAH": nama_sek_pusat, "KOD SEKOLAH": kod_sek_pusat, "JUMLAH CALON": calon_c, "KELAS": kelas_c, "PENGAWAS": pengawas_c, "TOTAL DI PUSAT": total_c, "BIL DILANTIK": bil, "STATUS": status})
            status_df = pd.DataFrame(status_data)
            st.dataframe(status_df, use_container_width=True)
            
            # Summary
            lengkap = len([s for s in status_data if "Lengkap" in s["STATUS"]])
            st.metric("Pusat Lengkap Dilantik", f"{lengkap}/{len(semua_pusat)}")
            
            # Detail maklumat sekolah
            maklumat_all = read_sheet(TAB_MAKLUMAT)
            if not maklumat_all.empty and "KOD SEKOLAH" in maklumat_all.columns:
                maklumat_ppd = maklumat_all[maklumat_all["KOD SEKOLAH"].astype(str).isin(kod_sekolah_ppd)]
                st.markdown(f"#### 📊 Maklumat Sekolah - {info['ppd_nama']}: {len(maklumat_ppd)}/{len(df_ppd)} dah isi")
                belum = df_ppd[~df_ppd["KOD SEKOLAH"].astype(str).isin(maklumat_all["KOD SEKOLAH"].astype(str) if not maklumat_all.empty else [])]
                if not belum.empty:
                    st.warning(f"⚠️ {len(belum)} sekolah belum isi")
                    st.dataframe(belum[["KOD SEKOLAH","NAMA SEKOLAH"]], use_container_width=True)
        

        elif menu=="Kuota Pusat":
            st.header(f"⚙️ Kuota Pusat - PPD {info['ppd_nama']} ({info['kod']})")
            st.info("Data asal dikekalkan ikut formula KELAS + 10 / PETUGAS_NEEDED. PPD boleh edit KEPERLUAN EDIT ikut kesesuaian. Bila edit, semua fungsi (Senarai Pusat, Jana Penempatan, Hantar JPN) akan auto guna kuota baru.")
            
            # Load kuota sheet
            df_kuota_all = read_sheet("kuota_ppd")
            if df_kuota_all.empty:
                st.warning("Belum ada edit kuota - semua guna data asal.")
            else:
                st.caption(f"Ada {len(df_kuota_all)} rekod kuota dalam sheet")
            
            # Build table kuota
            kuota_data = []
            for pusat in semua_pusat:
                info_k = get_kuota_info(pusat, df_calon_master, df_kuota_all)
                kod_sek_pusat = pusat_to_sekolah.get(pusat, "")
                nama_pusat = pusat_to_nama.get(pusat, pusat)
                kuota_data.append({
                    "NO PUSAT": pusat,
                    "NAMA PUSAT": nama_pusat,
                    "KOD SEKOLAH TUAN RUMAH": kod_sek_pusat,
                    "JUMLAH CALON": info_k["calon"],
                    "BIL KELAS": info_k["kelas"],
                    "FORMULA (Kelas+10)": info_k["formula"],
                    "ASAL (PETUGAS_NEEDED)": info_k["asal"],
                    "KEPERLUAN EDIT": info_k["edit"] if info_k["edit"] is not None else "-",
                    "FINAL (Diguna Sistem)": info_k["final"],
                    "TOTAL + KP/TKP": info_k["final"] + 2,
                    "CATATAN": info_k["catatan"]
                })
            
            df_tunjuk = pd.DataFrame(kuota_data)
            st.dataframe(df_tunjuk, use_container_width=True, height=400)
            
            st.markdown("---")
            st.subheader("✏️ Edit Kuota Pusat")
            
            col1, col2 = st.columns([2,3])
            with col1:
                pusat_pilih = st.selectbox("Pilih Pusat untuk Edit", ["-- Pilih --"] + semua_pusat, format_func=lambda x: f"{x} - {pusat_to_nama.get(x,'')}" if x!="-- Pilih --" else x)
                
                if pusat_pilih != "-- Pilih --":
                    k_info = get_kuota_info(pusat_pilih, df_calon_master, df_kuota_all)
                    st.markdown(f"#### {pusat_pilih}")
                    c_a,c_b,c_c = st.columns(3)
                    with c_a:
                        st.metric("Asal", k_info["asal"])
                    with c_b:
                        st.metric("Kelas", k_info["kelas"])
                        st.caption(f"Formula Kelas+10 = {k_info['formula']}")
                    with c_c:
                        st.metric("Final Sekarang", k_info["final"])
                        if k_info["edit"] is not None:
                            st.success(f"Edited: {k_info['edit']}")
                        else:
                            st.info("Guna Asal")
                    
                    if k_info["catatan"]:
                        st.caption(f"Catatan lama: {k_info['catatan']}")
            
            with col2:
                if pusat_pilih != "-- Pilih --":
                    k_info = get_kuota_info(pusat_pilih, df_calon_master, df_kuota_all)
                    with st.form(f"edit_kuota_{pusat_pilih}"):
                        st.markdown(f"Edit Keperluan untuk **{pusat_pilih}**")
                        def_val = k_info["edit"] if k_info["edit"] is not None else k_info["asal"]
                        new_keperluan = st.number_input("KEPERLUAN EDIT (Bil Pengawas Sahaja, tidak termasuk KP/TKP)", 1, 50, int(def_val))
                        catatan = st.text_input("CATATAN / ALASAN EDIT", value=k_info["catatan"], placeholder="Contoh: Tambah 2 sebab dewan besar, kelas tumpang...")
                        
                        col_s1, col_s2 = st.columns(2)
                        with col_s1:
                            btn_simpan = st.form_submit_button("💾 Simpan Kuota", use_container_width=True, type="primary")
                        with col_s2:
                            btn_reset = st.form_submit_button("🔄 Reset ke Asal", use_container_width=True)
                        
                        if btn_simpan:
                            baris = {
                                "NO PUSAT": pusat_pilih,
                                "NAMA PUSAT": pusat_to_nama.get(pusat_pilih, pusat_pilih),
                                "KOD PPD": info['kod'],
                                "PPD": info['ppd_nama'],
                                "KOD SEKOLAH TUAN RUMAH": pusat_to_sekolah.get(pusat_pilih, ""),
                                "JUMLAH CALON": k_info["calon"],
                                "BIL KELAS": k_info["kelas"],
                                "FORMULA (Kelas+10)": k_info["formula"],
                                "ASAL (PETUGAS_NEEDED)": k_info["asal"],
                                "KEPERLUAN EDIT": int(new_keperluan),
                                "KEPERLUAN AKHIR": int(new_keperluan),
                                "FINAL DIGUNA": int(new_keperluan),
                                "CATATAN": catatan,
                                "TARIKH EDIT": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "EDIT OLEH": f"PPD {info['ppd_nama']} ({info['kod']})",
                                "TOTAL DENGAN KP/TKP": int(new_keperluan)+2
                            }
                            
                            def _simpan_kuota(df):
                                if df.empty:
                                    return pd.DataFrame([baris])
                                # Buang rekod lama pusat sama
                                df = df[df["NO PUSAT"].astype(str) != str(pusat_pilih)]
                                return pd.concat([df, pd.DataFrame([baris])], ignore_index=True)
                            
                            if modify_sheet("kuota_ppd", _simpan_kuota):
                                flash("success", f"✅ Kuota {pusat_pilih} diubah: Asal {k_info['asal']} -> Edit {new_keperluan}. Sistem akan auto guna kuota baru di semua fungsi!")
                                st.rerun()
                        
                        if btn_reset:
                            def _reset_kuota(df):
                                if df.empty:
                                    return df
                                return df[df["NO PUSAT"].astype(str) != str(pusat_pilih)]
                            
                            if modify_sheet("kuota_ppd", _reset_kuota):
                                flash("success", f"🔄 Kuota {pusat_pilih} direset ke asal ({k_info['asal']}) - Formula Kelas+10")
                                st.rerun()
            
            st.markdown("---")
            st.markdown("### 📥 Export / Import Kuota")
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                if not df_tunjuk.empty:
                    st.download_button("⬇️ Muat turun Kuota (CSV)", data=df_tunjuk.to_csv(index=False).encode("utf-8-sig"), file_name=f"kuota_{info['kod']}_{pd.Timestamp.now().strftime('%Y%m%d')}.csv", mime="text/csv", use_container_width=True)
            with col_e2:
                uploaded = st.file_uploader("Upload CSV Kuota (NO PUSAT, KEPERLUAN EDIT)", type=["csv","xlsx"])
                if uploaded and st.button("📤 Import Kuota Pukal"):
                    try:
                        if uploaded.name.endswith(".xlsx"):
                            df_up = pd.read_excel(uploaded)
                        else:
                            df_up = pd.read_csv(uploaded)
                        # Validate
                        if "NO PUSAT" not in df_up.columns or "KEPERLUAN EDIT" not in df_up.columns:
                            st.error("CSV mesti ada column NO PUSAT dan KEPERLUAN EDIT")
                        else:
                            count=0
                            for _, r in df_up.iterrows():
                                p = str(r["NO PUSAT"]).strip()
                                if p not in semua_pusat:
                                    continue
                                try:
                                    edit_val = int(float(r["KEPERLUAN EDIT"]))
                                except:
                                    continue
                                k_info = get_kuota_info(p, df_calon_master, df_kuota_all)
                                baris = {
                                    "NO PUSAT": p,
                                    "NAMA PUSAT": pusat_to_nama.get(p, p),
                                    "KOD PPD": info['kod'],
                                    "PPD": info['ppd_nama'],
                                    "JUMLAH CALON": k_info["calon"],
                                    "BIL KELAS": k_info["kelas"],
                                    "FORMULA (Kelas+10)": k_info["formula"],
                                    "ASAL (PETUGAS_NEEDED)": k_info["asal"],
                                    "KEPERLUAN EDIT": edit_val,
                                    "KEPERLUAN AKHIR": edit_val,
                                    "CATATAN": str(r.get("CATATAN","")),
                                    "TARIKH EDIT": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "EDIT OLEH": f"PPD {info['ppd_nama']} Import Pukal"
                                }
                                def _imp(df, b=baris, pp=p):
                                    if df.empty:
                                        return pd.DataFrame([b])
                                    df = df[df["NO PUSAT"].astype(str) != pp]
                                    return pd.concat([df, pd.DataFrame([b])], ignore_index=True)
                                modify_sheet("kuota_ppd", _imp)
                                count+=1
                            st.success(f"✅ {count} kuota diimport!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Gagal import: {e}")

        elif menu=="Cadangan SUP":
            st.header(f"📋 Cadangan SUP - {info['ppd_nama']} ({len(kod_sekolah_ppd)} sekolah)")
            st.caption("SUP boleh senaraikan lebih petugas. PPD PILIH JAWATAN DAHULU, kemudian TICK siapa akan bertugas. Yang di-tick sahaja akan masuk untuk Jana Penempatan. Selagi PPD tak tick, Simpanan kosong.")
            cadangan_all = read_sheet(TAB_CADANGAN)
            penempatan_all = read_sheet(TAB_PENEMPATAN)
            simpanan_all = read_sheet(TAB_SIMPANAN)
            TAB_PILIHAN = tab_daerah("pilihan_ppd", info['kod'])
            pilihan_all = read_sheet(TAB_PILIHAN)
            
            if not cadangan_all.empty and "KOD SEKOLAH ASAL" in cadangan_all.columns:
                cadangan_ppd = cadangan_all[cadangan_all["KOD SEKOLAH ASAL"].astype(str).isin(kod_sekolah_ppd)].copy()
                def get_nama_pusat(kod):
                    row = df_ppd[df_ppd["KOD SEKOLAH"].astype(str)==str(kod)]
                    if not row.empty:
                        return str(row.iloc[0]["NAMA SEKOLAH"])
                    return str(kod)
                
                if "NAMA PUSAT SEKOLAH" not in cadangan_ppd.columns:
                    cadangan_ppd["NAMA PUSAT SEKOLAH"] = cadangan_ppd["KOD SEKOLAH ASAL"].apply(get_nama_pusat)
                
                pilihan_map = {}
                if not pilihan_all.empty and "IC" in pilihan_all.columns:
                    for _, r in pilihan_all.iterrows():
                        ic_n = norm_ic(r.get("IC",""))
                        if ic_n:
                            pilihan_map[ic_n] = str(r.get("STATUS PILIHAN","")).upper()
                
                peta_pen = peta_guru_pusat(penempatan_all, simpanan_all)
                cadangan_ppd["_IC_NORM"] = cadangan_ppd["IC"].map(norm_ic)
                cadangan_ppd["_PUSAT_SEMASA"] = [pusat_guru(peta_pen, r.get("IC",""), r.get("NAMA GURU",""), r.get("KOD SEKOLAH ASAL","")) for _, r in cadangan_ppd.iterrows()]
                cadangan_ppd["_DIPILIH"] = cadangan_ppd["_IC_NORM"].apply(lambda x: pilihan_map.get(x, "BELUM PILIH"))
                
                def _status_label(p_):
                    if p_ is None:
                        return "✅ Belum Lantik"
                    if p_ == "SIMPANAN":
                        return "🅿️ Simpanan"
                    return f"🔒 Di {p_}"
                cadangan_ppd["_STATUS_LANTIK"] = cadangan_ppd["_PUSAT_SEMASA"].map(_status_label)
                
                total_cad = len(cadangan_ppd)
                sudah_pilih = len([v for v in pilihan_map.values() if "DIPILIH" in v and "TIDAK" not in v])
                belum_pilih = total_cad - len(pilihan_map)
                col_m1,col_m2,col_m3,col_m4 = st.columns(4)
                with col_m1:
                    st.metric("Total Cadangan SUP", total_cad)
                with col_m2:
                    st.metric("Sudah Dipilih PPD", sudah_pilih)
                with col_m3:
                    st.metric("Belum Pilih", belum_pilih)
                with col_m4:
                    dilantik = len([x for x in cadangan_ppd["_PUSAT_SEMASA"] if x is not None and x!="SIMPANAN"])
                    st.metric("Sudah Dilantik", dilantik)
                
                # Salin 2026 -> 2027
                tahun_semasa = st.session_state.get("tahun_pilih", 2026)
                if tahun_semasa >= 2027:
                    st.markdown("---")
                    col_salin1, col_salin2, col_salin3 = st.columns([2,1,1])
                    with col_salin1:
                        st.markdown(f"#### 📋 Salin Cadangan SUP {tahun_semasa-1} → {tahun_semasa}")
                        st.caption(f"File cadangan SUP {tahun_semasa-1} disalin ke {tahun_semasa}. SUP boleh semak balik dan tambah jika berubah. Tiada duplicate ikut IC.")
                    with col_salin2:
                        tahun_sumber = st.selectbox("Tahun Sumber", [tahun_semasa-1, tahun_semasa-2] if tahun_semasa-2>=2026 else [tahun_semasa-1], key="tahun_sumber_salin")
                    with col_salin3:
                        if st.button(f"📥 Salin dari {tahun_sumber} ke {tahun_semasa}", use_container_width=True, type="secondary", key="btn_salin_tahun"):
                            sheet_sumber = tab_daerah("cadangan_sup", info['kod'], tahun_sumber)
                            sheet_dest = tab_daerah("cadangan_sup", info['kod'], tahun_semasa)
                            df_sumber = read_sheet(sheet_sumber)
                            if df_sumber.empty:
                                df_sumber = read_sheet(tab_daerah_base("cadangan_sup", info['kod']))
                            if not df_sumber.empty:
                                if "KOD SEKOLAH ASAL" in df_sumber.columns:
                                    df_sumber_ppd = df_sumber[df_sumber["KOD SEKOLAH ASAL"].astype(str).isin(kod_sekolah_ppd)].copy()
                                else:
                                    df_sumber_ppd = df_sumber.copy()
                                if df_sumber_ppd.empty:
                                    st.error(f"Tiada cadangan PPD {info['ppd_nama']} di tahun {tahun_sumber}")
                                else:
                                    df_dest = read_sheet(sheet_dest)
                                    ic_dest = set(df_dest["IC"].map(norm_ic).tolist()) if not df_dest.empty and "IC" in df_dest.columns else set()
                                    df_baru = df_sumber_ppd[~df_sumber_ppd["IC"].map(norm_ic).isin(ic_dest)].copy() if ic_dest else df_sumber_ppd.copy()
                                    if df_baru.empty:
                                        st.info(f"Semua {len(df_sumber_ppd)} sudah ada di {tahun_semasa}")
                                    else:
                                        def _salin_tahun(df_old):
                                            if df_old.empty:
                                                return df_baru
                                            return pd.concat([df_old, df_baru], ignore_index=True)
                                        if modify_sheet(sheet_dest, _salin_tahun):
                                            flash("success", f"✅ {len(df_baru)} cadangan disalin dari {tahun_sumber} → {tahun_semasa}! SUP boleh semak dan tambah.")
                                            st.rerun()
                            else:
                                st.error(f"Tiada data di tahun {tahun_sumber}")
                    st.markdown("---")
                
                # Filter - PILIH JAWATAN DAHULU
                st.markdown("### 👔 Pilih Jawatan Dahulu - PPD Akan Pilih Ikut Jawatan")
                col_f1, col_f2, col_f3, col_f4 = st.columns(4)
                with col_f1:
                    jawatan_opts = ["SEMUA JAWATAN","Ketua Pengawas","Timbalan Ketua Pengawas","Pengawas Peperiksaan","Pengemas Bilik","Penyelia Kawasan"]
                    def label_jaw(j):
                        if j=="SEMUA JAWATAN":
                            return f"SEMUA JAWATAN ({len(cadangan_ppd)} orang)"
                        bil = 0
                        if "JAWATAN CADANGAN" in cadangan_ppd.columns:
                            bil = len(cadangan_ppd[cadangan_ppd["JAWATAN CADANGAN"].astype(str)==j])
                        if bil==0 and "JAWATAN CADANG" in cadangan_ppd.columns:
                            bil = len(cadangan_ppd[cadangan_ppd["JAWATAN CADANG"].astype(str)==j])
                        return f"{j} ({bil})"
                    pilih_jawatan = st.selectbox("👔 Jawatan", jawatan_opts, format_func=label_jaw, key="filter_jawatan_cad")
                    if pilih_jawatan != "SEMUA JAWATAN":
                        if "JAWATAN CADANGAN" in cadangan_ppd.columns:
                            cadangan_ppd = cadangan_ppd[cadangan_ppd["JAWATAN CADANGAN"].astype(str)==pilih_jawatan]
                        elif "JAWATAN CADANG" in cadangan_ppd.columns:
                            cadangan_ppd = cadangan_ppd[cadangan_ppd["JAWATAN CADANG"].astype(str)==pilih_jawatan]
                        st.info(f"📋 Menunjukkan {len(cadangan_ppd)} untuk **{pilih_jawatan}**")
                    else:
                        jaw_order = {"Ketua Pengawas":1, "Timbalan Ketua Pengawas":2, "Pengawas Peperiksaan":3, "Pengemas Bilik":4, "Penyelia Kawasan":5}
                        col_j = "JAWATAN CADANGAN" if "JAWATAN CADANGAN" in cadangan_ppd.columns else "JAWATAN CADANG"
                        if col_j in cadangan_ppd.columns:
                            cadangan_ppd["_JAW_ORDER"] = cadangan_ppd[col_j].map(lambda x: jaw_order.get(str(x), 99))
                            cadangan_ppd = cadangan_ppd.sort_values("_JAW_ORDER")
                
                with col_f2:
                    sekolah_opts = sorted(cadangan_ppd["KOD SEKOLAH ASAL"].astype(str).unique().tolist())
                    def label_sek(k):
                        nama = get_nama_pusat(k)
                        bil = len(cadangan_ppd[cadangan_ppd["KOD SEKOLAH ASAL"].astype(str)==k])
                        return f"{k} - {nama} ({bil})"
                    pilih_sek = st.selectbox("🏫 Sekolah", ["SEMUA SEKOLAH"] + sekolah_opts, format_func=lambda x: "SEMUA SEKOLAH" if x=="SEMUA SEKOLAH" else label_sek(x), key="filter_sek_cad")
                    if pilih_sek != "SEMUA SEKOLAH":
                        cadangan_ppd = cadangan_ppd[cadangan_ppd["KOD SEKOLAH ASAL"].astype(str)==pilih_sek]
                with col_f3:
                    status_opts = ["SEMUA","BELUM PILIH","DIPILIH","TIDAK DIPILIH"]
                    pilih_status = st.selectbox("📌 Status", status_opts, key="filter_status_cad")
                    if pilih_status != "SEMUA":
                        if pilih_status=="BELUM PILIH":
                            cadangan_ppd = cadangan_ppd[~cadangan_ppd["_IC_NORM"].isin(pilihan_map.keys())]
                        else:
                            cadangan_ppd = cadangan_ppd[cadangan_ppd["_DIPILIH"]==pilih_status]
                with col_f4:
                    search_nama = st.text_input("🔍 Cari", placeholder="ALI / 900101...", key="search_cad")
                    if search_nama.strip():
                        s = search_nama.strip().upper()
                        cadangan_ppd = cadangan_ppd[cadangan_ppd["NAMA GURU"].astype(str).str.contains(s, na=False) | cadangan_ppd["IC"].astype(str).str.contains(s, na=False)]
                
                st.markdown(f"#### ☑️ Tick Siapa Akan Bertugas - Jawatan: **{pilih_jawatan}**")
                st.caption("Tick = DIPILIH untuk Jana. Tak tick = kekal cadangan sahaja. Selagi PPD tak tick, Simpanan kosong.")
                
                df_editor = cadangan_ppd.copy()
                def is_dipilih(ic_n):
                    v = pilihan_map.get(ic_n,"")
                    return True if "DIPILIH" in v and "TIDAK" not in v else False
                df_editor["_TICK"] = df_editor["_IC_NORM"].apply(is_dipilih)
                
                cols_display = ["_TICK","NAMA GURU","IC","JAWATAN CADANGAN","JAWATAN CADANG","KOD SEKOLAH ASAL","NAMA SEKOLAH ASAL","JANTINA","NO TELEFON GURU","_DIPILIH","_STATUS_LANTIK"]
                cols_display = [c for c in cols_display if c in df_editor.columns]
                
                edited = st.data_editor(df_editor[cols_display], use_container_width=True, hide_index=True, 
                    column_config={
                        "_TICK": st.column_config.CheckboxColumn("✅ PILIH?"),
                        "_DIPILIH": st.column_config.TextColumn("Keputusan PPD"),
                        "_STATUS_LANTIK": st.column_config.TextColumn("Status Lantik")
                    }, key="editor_cadangan_ppd")
                
                col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
                with col_btn1:
                    if st.button("✅ Simpan Pilihan", use_container_width=True, type="primary"):
                        baris_pilihan = []
                        for _, r in edited.iterrows():
                            ic_val = str(r.get("IC","")).strip()
                            if not ic_val:
                                continue
                            status = "DIPILIH" if r.get("_TICK")==True else "TIDAK DIPILIH"
                            jaw_simpan = r.get("JAWATAN CADANGAN","") or r.get("JAWATAN CADANG","") or pilih_jawatan
                            baris_pilihan.append({
                                "IC": ic_val,
                                "NAMA GURU": r.get("NAMA GURU",""),
                                "KOD SEKOLAH ASAL": r.get("KOD SEKOLAH ASAL",""),
                                "JAWATAN DIPILIH": jaw_simpan,
                                "STATUS PILIHAN": status,
                                "TARIKH PILIH": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "DIPILIH OLEH": f"PPD {info['ppd_nama']}",
                                "NO PUSAT ASAL": r.get("NO PUSAT ASAL","") if "NO PUSAT ASAL" in r else ""
                            })
                        def _simpan_pilihan(df_old):
                            ic_list = [norm_ic(b["IC"]) for b in baris_pilihan]
                            if not df_old.empty and "IC" in df_old.columns:
                                df_old = df_old[~df_old["IC"].map(norm_ic).isin(ic_list)]
                                return pd.concat([df_old, pd.DataFrame(baris_pilihan)], ignore_index=True) if not df_old.empty else pd.DataFrame(baris_pilihan)
                            else:
                                return pd.DataFrame(baris_pilihan)
                        if modify_sheet(TAB_PILIHAN, _simpan_pilihan):
                            dipilh_count = len([b for b in baris_pilihan if b['STATUS PILIHAN']=='DIPILIH'])
                            flash("success", f"✅ {dipilh_count} DIPILIH untuk {pilih_jawatan}! Selagi tak tick, simpanan kosong. Yang tick akan masuk untuk Jana.")
                            st.rerun()
                with col_btn2:
                    if st.button("☑️ Pilih Semua", use_container_width=True):
                        all_ic = edited["IC"].tolist()
                        baris_pilihan = []
                        for ic_val in all_ic:
                            row = edited[edited["IC"]==ic_val].iloc[0] if not edited[edited["IC"]==ic_val].empty else None
                            if row is None:
                                continue
                            baris_pilihan.append({
                                "IC": str(row.get("IC","")),
                                "NAMA GURU": row.get("NAMA GURU",""),
                                "KOD SEKOLAH ASAL": row.get("KOD SEKOLAH ASAL",""),
                                "JAWATAN DIPILIH": row.get("JAWATAN CADANGAN","") or row.get("JAWATAN CADANG","") or pilih_jawatan,
                                "STATUS PILIHAN": "DIPILIH",
                                "TARIKH PILIH": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "DIPILIH OLEH": f"PPD {info['ppd_nama']} - Pilih Semua {pilih_jawatan}"
                            })
                        def _pilih_semua(df_old):
                            ic_list = [norm_ic(b["IC"]) for b in baris_pilihan]
                            if not df_old.empty and "IC" in df_old.columns:
                                df_old = df_old[~df_old["IC"].map(norm_ic).isin(ic_list)]
                                return pd.concat([df_old, pd.DataFrame(baris_pilihan)], ignore_index=True) if not df_old.empty else pd.DataFrame(baris_pilihan)
                            else:
                                return pd.DataFrame(baris_pilihan)
                        if modify_sheet(TAB_PILIHAN, _pilih_semua):
                            flash("success", f"✅ {len(baris_pilihan)} DIPILIH untuk {pilih_jawatan}!")
                            st.rerun()
                with col_btn3:
                    if st.button("❌ Nyah Pilih", use_container_width=True):
                        all_ic = edited["IC"].tolist()
                        def _nyah_semua(df_old):
                            if df_old.empty:
                                return df_old
                            return df_old[~df_old["IC"].map(norm_ic).isin([norm_ic(x) for x in all_ic])]
                        if modify_sheet(TAB_PILIHAN, _nyah_semua):
                            flash("success", "❌ Dinyahpilih")
                            st.rerun()
                with col_btn4:
                    st.caption(f"Jawatan: {pilih_jawatan}")
                
                st.markdown("---")
                st.markdown(f"#### 🎯 Ringkasan untuk Jana - Jawatan: {pilih_jawatan}")
                dipilh_df = cadangan_ppd[cadangan_ppd["_IC_NORM"].isin([k for k,v in pilihan_map.items() if "DIPILIH" in v and "TIDAK" not in v])]
                if dipilh_df.empty:
                    st.warning(f"⚠️ Belum ada yang DIPILIH untuk {pilih_jawatan}. Sila tick dan Simpan.")
                else:
                    if pilih_jawatan != "SEMUA JAWATAN":
                        col_j = "JAWATAN CADANGAN" if "JAWATAN CADANGAN" in dipilh_df.columns else "JAWATAN CADANG"
                        if col_j in dipilh_df.columns:
                            dipilh_show = dipilh_df[dipilh_df[col_j].astype(str)==pilih_jawatan]
                        else:
                            dipilh_show = dipilh_df
                    else:
                        dipilh_show = dipilh_df
                    st.success(f"✅ {len(dipilh_show)} DIPILIH untuk {pilih_jawatan}")
                    show_cols = ["NAMA GURU","IC","JAWATAN CADANGAN","JAWATAN CADANG","KOD SEKOLAH ASAL"]
                    show_cols = [c for c in show_cols if c in dipilh_show.columns]
                    st.dataframe(dipilh_show[show_cols], use_container_width=True)
            else:
                st.info("Belum ada cadangan SUP untuk daerah ini")




                st.markdown("---")
                st.markdown("### ❌ Batal Cadangan SUP (PPD Sahaja)")
                st.caption("Fungsi ini akan buang nama guru dari senarai Cadangan SUP PPD sahaja. Nama guru masih kekal dalam Senarai Guru SUP (master guru sekolah). Guna bila guru tidak layak, bertukar, atau cadangan salah.")
                
                if not cadangan_ppd.empty:
                    col_batal1, col_batal2 = st.columns([2,1])
                    with col_batal1:
                        opsi_batal = []
                        for _, r in cadangan_ppd.iterrows():
                            label = f"{r.get('NAMA GURU','')} - {r.get('IC','')} - {r.get('KOD SEKOLAH ASAL','')} - {r.get('JAWATAN CADANGAN','') or r.get('JAWATAN CADANG','')}"
                            opsi_batal.append(label)
                        pilih_batal = st.multiselect("Pilih guru untuk Batal dari Cadangan SUP PPD", opsi_batal, key="batal_cadangan_multiselect")
                    with col_batal2:
                        st.warning("⚠️ Batal hanya buang dari Cadangan SUP PPD, TIDAK buang dari Senarai Guru SUP")
                        sebab_batal = st.text_input("Sebab Batal (optional)", placeholder="Contoh: Bertukar sekolah, tidak layak", key="sebab_batal")
                    
                    if pilih_batal:
                        ic_batal = []
                        for label in pilih_batal:
                            try:
                                parts = label.split(" - ")
                                ic = parts[1].strip() if len(parts)>=2 else ""
                                if ic:
                                    ic_batal.append(ic)
                            except:
                                pass
                        
                        st.error(f"Anda akan batal {len(ic_batal)} guru dari Cadangan SUP PPD {info['kod']}. Nama masih kekal di Senarai Guru SUP.")
                        
                        col_batal_confirm1, col_batal_confirm2 = st.columns(2)
                        with col_batal_confirm1:
                            if st.button(f"❌ Sahkan Batal {len(ic_batal)} Guru dari PPD Sahaja", use_container_width=True, type="primary", key="btn_batal_ppd"):
                                log_batal = []
                                for ic in ic_batal:
                                    row = cadangan_ppd[cadangan_ppd["IC"].astype(str)==ic]
                                    nama = row["NAMA GURU"].values[0] if not row.empty else ""
                                    kod_sek = row["KOD SEKOLAH ASAL"].values[0] if not row.empty else ""
                                    log_batal.append({
                                        "IC": ic,
                                        "NAMA GURU": nama,
                                        "KOD SEKOLAH ASAL": kod_sek,
                                        "TARIKH BATAL": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "DIBATAL OLEH": f"PPD {info['ppd_nama']}",
                                        "SEBAB": sebab_batal,
                                        "STATUS": "BATAL DARI PPD - MASIH DALAM SENARAI GURU SUP"
                                    })
                                
                                def _batal_dari_cadangan(df_old):
                                    if df_old.empty:
                                        return df_old
                                    ic_norm_batal = [norm_ic(ic) for ic in ic_batal]
                                    mask_batal = df_old["IC"].map(norm_ic).isin(ic_norm_batal)
                                    if "KOD SEKOLAH ASAL" in df_old.columns:
                                        mask_batal = mask_batal & df_old["KOD SEKOLAH ASAL"].astype(str).isin(kod_sekolah_ppd)
                                    return df_old[~mask_batal].copy()
                                
                                def _batal_dari_pilihan(df_old):
                                    if df_old.empty:
                                        return df_old
                                    ic_norm_batal = [norm_ic(ic) for ic in ic_batal]
                                    return df_old[~df_old["IC"].map(norm_ic).isin(ic_norm_batal)].copy()
                                
                                ok1 = modify_sheet(TAB_CADANGAN, _batal_dari_cadangan)
                                ok2 = modify_sheet(TAB_PILIHAN, _batal_dari_pilihan)
                                
                                TAB_LOG_BATAL = tab_daerah("log_batal_ppd", info['kod'])
                                def _simpan_log(df_old):
                                    if df_old.empty:
                                        return pd.DataFrame(log_batal)
                                    return pd.concat([df_old, pd.DataFrame(log_batal)], ignore_index=True)
                                
                                ok3 = modify_sheet(TAB_LOG_BATAL, _simpan_log)
                                
                                if ok1:
                                    flash("success", f"✅ {len(ic_batal)} guru dibatal dari Cadangan SUP PPD {info['kod']}. Nama masih kekal dalam Senarai Guru SUP (master). Log disimpan di {TAB_LOG_BATAL}")
                                    st.rerun()
                        with col_batal_confirm2:
                            if st.button("Batalkan", use_container_width=True, key="btn_batal_cancel"):
                                st.info("Batal dibatalkan")
                else:
                    st.info("Tiada cadangan untuk dibatal")
                
                with st.expander("📜 Log Batal PPD (audit)"):
                    TAB_LOG_BATAL = tab_daerah("log_batal_ppd", info['kod'])
                    log_df = read_sheet(TAB_LOG_BATAL)
                    if log_df.empty:
                        st.info("Belum ada log batal")
                    else:
                        st.dataframe(log_df, use_container_width=True)
                        st.caption("Log ini untuk audit - guru yang dibatal dari PPD masih ada dalam Senarai Guru SUP")


        elif menu=="Jana Penempatan":
            st.header(f"🎯 Lantikan Ikut Pusat - {info['ppd_nama']}")
            st.markdown("PPD pilih pusat, terus nampak siapa Ketua, Timbalan, Pengawas yang sistem tempatkan. Boleh edit terus!")
            st.caption("Susunan: 1 Ketua Pengawas + 1 Timbalan + Pengawas ikut keperluan pusat. Penyelia Kawasan exclude (Bilik Kebal). Seorang guru hanya dilantik di SATU pusat; guru sekolah tuan rumah tak jaga pusat sendiri.")

            cadangan_all = read_sheet(TAB_CADANGAN)
            penempatan_all = read_sheet(TAB_PENEMPATAN)
            simpanan_all = read_sheet(TAB_SIMPANAN)
            ada_pen = (not penempatan_all.empty) and ("NO PUSAT TUGAS" in penempatan_all.columns)

            if not cadangan_all.empty and "KOD SEKOLAH ASAL" in cadangan_all.columns:
                cadangan_ppd = cadangan_all[cadangan_all["KOD SEKOLAH ASAL"].astype(str).isin(kod_sekolah_ppd)]
                TAB_PILIHAN_JANA = tab_daerah("pilihan_ppd", info['kod'])
                pilihan_jana = read_sheet(TAB_PILIHAN_JANA)
                if not pilihan_jana.empty and "IC" in pilihan_jana.columns and "STATUS PILIHAN" in pilihan_jana.columns:
                    ic_dipilih = pilihan_jana[pilihan_jana["STATUS PILIHAN"].astype(str).str.contains("DIPILIH") & ~pilihan_jana["STATUS PILIHAN"].astype(str).str.contains("TIDAK")]["IC"].map(norm_ic).tolist()
                    if ic_dipilih:
                        cadangan_ppd = cadangan_ppd[cadangan_ppd["IC"].map(norm_ic).isin(ic_dipilih)].copy()
                        st.info(f"🔍 Filter Pilihan PPD aktif: {len(ic_dipilih)} DIPILIH - hanya mereka akan dijana.")
            else:
                cadangan_ppd = pd.DataFrame()

            def jalankan_jana(senarai_pusat, label_status):
                """Jana untuk 1 atau banyak pusat - satu logik, simpan selamat."""
                if cadangan_ppd.empty or "IC" not in cadangan_ppd.columns:
                    st.error("Tiada cadangan guru! Isi Cadangan SUP dulu (setiap guru mesti ada IC).")
                    return
                hasil = {}

                def _ubah(df_pen):
                    rows, kurang = jana_penempatan(senarai_pusat, df_pen, cadangan_ppd, pusat_to_sekolah, pusat_to_nama, df_calon_master, label_status, read_sheet_strict(TAB_SIMPANAN))
                    hasil["rows"], hasil["kurang"] = rows, kurang
                    if not rows:
                        return None
                    baru = pd.DataFrame(rows)
                    return pd.concat([df_pen, baru], ignore_index=True) if not df_pen.empty else baru

                with st.spinner("Menjana penempatan..."):
                    ok = modify_sheet(TAB_PENEMPATAN, _ubah)
                if not ok:
                    return
                if hasil["rows"]:
                    bil_p = len({r["NO PUSAT TUGAS"] for r in hasil["rows"]})
                    flash("success", f"✅ {len(hasil['rows'])} petugas ditambah di {bil_p} pusat.")
                else:
                    flash("info", "Tiada perubahan - semua pusat dah lengkap atau tiada calon yang sesuai.")
                if hasil["kurang"]:
                    flash("warning", "⚠️ Calon tak cukup (jawatan dibiar kosong): " + ", ".join(f"{p} (kurang {n})" for p, n in hasil["kurang"]) + ". Minta SUP tambah cadangan guru.")
                st.rerun()

            tot_peng = sum(keperluan_pengawas(p, df_calon_master) for p in semua_pusat)
            tot_tot = tot_peng + len(semua_pusat) * 2
            curr = int(penempatan_all["NO PUSAT TUGAS"].astype(str).isin(semua_pusat).sum()) if ada_pen else 0

            # ===== SEMAK DUPLIKASI (guru sama di lebih daripada satu pusat) =====
            if ada_pen:
                _, dup = bersihkan_duplikasi(penempatan_all, semua_pusat)
            else:
                dup = []
            if dup:
                st.error(f"⚠️ {len(dup)} penempatan DUPLIKAT: guru yang sama dilantik di lebih daripada satu pusat (padan IC / nama+sekolah). Ini biasanya hasil janaan versi lama. Setiap pusat mesti orang berbeza.")
                with st.expander(f"Lihat {len(dup)} duplikasi"):
                    st.dataframe(pd.DataFrame(dup), use_container_width=True, hide_index=True)
                st.caption("Pembetulan: rekod pertama kekal (contoh BK001), rekod duplikat di pusat lain dibuang, kemudian jawatan kosong diisi semula dengan guru yang BERBEZA.")
                sahkan_betul = st.checkbox("Ya, buang duplikasi dan isi semula", key="sahkan_betul_dup")
                if st.button("🧹 Buang duplikasi & isi semula", use_container_width=True, type="primary", disabled=not sahkan_betul, key="betul_dup"):
                    hasil_b = {}

                    def _betul(df_pen):
                        df2, lap = bersihkan_duplikasi(df_pen, semua_pusat)
                        rows, kurang = [], []
                        if not cadangan_ppd.empty and "IC" in cadangan_ppd.columns:
                            rows, kurang = jana_penempatan(semua_pusat, df2, cadangan_ppd, pusat_to_sekolah, pusat_to_nama, df_calon_master, "Auto Jana Semua PPD (selepas bersih duplikasi)", read_sheet_strict(TAB_SIMPANAN))
                        hasil_b.update(buang=len(lap), rows=rows, kurang=kurang)
                        if rows:
                            return pd.concat([df2, pd.DataFrame(rows)], ignore_index=True) if not df2.empty else pd.DataFrame(rows)
                        return df2

                    with st.spinner("Membetulkan penempatan..."):
                        ok_b = modify_sheet(TAB_PENEMPATAN, _betul)
                    if ok_b:
                        flash("success", f"✅ {hasil_b['buang']} duplikasi dibuang, {len(hasil_b['rows'])} petugas BARU (berbeza) ditempatkan.")
                        if hasil_b["kurang"]:
                            flash("warning", "⚠️ Calon tak cukup untuk: " + ", ".join(f"{p} (kurang {n})" for p, n in hasil_b["kurang"]) + ". Minta SUP tambah cadangan guru.")
                        st.rerun()

            st.markdown("### 🚀 Jana Semua Pusat")
            st.info(f"{len(semua_pusat)} pusat = {tot_peng} Pengawas + {len(semua_pusat)*2} KP/TKP = {tot_tot} petugas | {len(cadangan_ppd)} guru dicadangkan")
            if len(cadangan_ppd) < tot_tot - curr:
                st.warning(f"⚠️ Cadangan guru ({len(cadangan_ppd)}) kurang daripada jawatan kosong ({tot_tot - curr}). Sebahagian pusat akan kekal tak lengkap.")
            st.metric("Total Dilantik Sekarang", f"{curr}/{tot_tot}")

            col_bulk1, col_bulk2, col_bulk3 = st.columns(3)
            with col_bulk1:
                if st.button(f"🚀 JANA SEMUA {len(semua_pusat)} PUSAT SEKARANG", use_container_width=True, type="primary", key="jana_all"):
                    jalankan_jana(semua_pusat, "Auto Jana Semua PPD")
            with col_bulk2:
                sahkan_kosong = st.checkbox("Ya, saya pasti nak kosongkan", key="sahkan_reset_all")
                if st.button("🗑️ Kosongkan SEMUA Pusat Daerah Ini", use_container_width=True, key="reset_all", disabled=not sahkan_kosong):
                    def _kosong_semua(df_pen):
                        if df_pen.empty or "NO PUSAT TUGAS" not in df_pen.columns:
                            return None
                        return df_pen[~df_pen["NO PUSAT TUGAS"].astype(str).isin(semua_pusat)]
                    if modify_sheet(TAB_PENEMPATAN, _kosong_semua):
                        flash("success", f"✅ Semua {len(semua_pusat)} pusat daerah {info['ppd_nama']} dikosongkan!")
                        st.rerun()
            with col_bulk3:
                pusat_ada = penempatan_all[penempatan_all["NO PUSAT TUGAS"].astype(str).isin(semua_pusat)]["NO PUSAT TUGAS"].nunique() if ada_pen else 0
                st.metric("Pusat Ada Lantikan", f"{pusat_ada}/{len(semua_pusat)}")

            st.markdown("---")

            # Pilih pusat
            if not semua_pusat:
                st.warning("Tiada pusat untuk daerah ini")
            else:
                col1, col2 = st.columns([2, 1])
                with col1:
                    pusat_pilih = st.selectbox("📌 Pilih NO PUSAT (untuk tengok/edit satu-satu)", semua_pusat, index=0)
                with col2:
                    kod_sek_pusat = pusat_to_sekolah.get(pusat_pilih, "")
                    nama_pusat = pusat_to_nama.get(pusat_pilih, pusat_pilih)
                    st.metric("Sekolah Tuan Rumah", f"{nama_pusat}")
                    st.caption(f"Kod: {kod_sek_pusat} | Pusat: {pusat_pilih}")

                if ada_pen:
                    penempatan_pusat = penempatan_all[penempatan_all["NO PUSAT TUGAS"].astype(str) == str(pusat_pilih)]
                else:
                    penempatan_pusat = pd.DataFrame()

                bil_sedia = len(penempatan_pusat)
                need_peng_single = keperluan_pengawas(pusat_pilih, df_calon_master)
                need_tot_single = need_peng_single + 2
                if bil_sedia == 0:
                    st.warning(f"❌ {pusat_pilih} belum ada lantikan. Tekan Jana Auto di bawah.")
                else:
                    st.info(f"ℹ️ {pusat_pilih} ada {bil_sedia}/{need_tot_single} petugas sekarang")

                col_j1, col_j2 = st.columns(2)
                with col_j1:
                    label_btn = f"🤖 Jana Auto untuk {pusat_pilih} ({need_tot_single} orang: 1 KP+1 TKP+{need_peng_single} Pengawas)" if bil_sedia == 0 else f"➕ Lengkapkan {pusat_pilih} jadi {need_tot_single} orang (1 KP+1 TKP+{need_peng_single} Pengawas)"
                    if st.button(label_btn, use_container_width=True, type="primary", key=f"jana_{pusat_pilih}"):
                        jalankan_jana([pusat_pilih], "Auto by PPD" if bil_sedia == 0 else "Lengkapkan Auto by PPD")
                with col_j2:
                    if st.button(f"🗑️ Kosongkan {pusat_pilih} (Reset)", use_container_width=True, key=f"reset_{pusat_pilih}"):
                        def _kosong_satu(df_pen):
                            if df_pen.empty or "NO PUSAT TUGAS" not in df_pen.columns:
                                return None
                            return df_pen[df_pen["NO PUSAT TUGAS"].astype(str) != str(pusat_pilih)]
                        if modify_sheet(TAB_PENEMPATAN, _kosong_satu):
                            flash("success", f"✅ {pusat_pilih} dikosongkan!")
                            st.rerun()

                # ===== SENARAI CADANGAN UNTUK PUSAT INI =====
                st.markdown("---")
                st.markdown(f"### 📋 Senarai Cadangan untuk {pusat_pilih}")

                def label_calon(row):
                    return f"{row.get('NAMA GURU','')} | {row.get('KOD SEKOLAH ASAL','')} - {row.get('NAMA SEKOLAH ASAL','')} | IC:{row.get('IC','')} | Poskod:{row.get('POSKOD RUMAH','')}"

                calon_edit = pd.DataFrame()
                calon_options = []
                if cadangan_ppd.empty or "IC" not in cadangan_ppd.columns:
                    st.info("Belum ada cadangan guru daripada sekolah-sekolah daerah ini.")
                else:
                    # Guru -> pusat tempat dia sudah dilantik (padan IC / nama+sekolah)
                    peta_pen = peta_guru_pusat(penempatan_all if ada_pen else None, simpanan_all)
                    senarai = cadangan_ppd.copy()
                    senarai["_IC"] = senarai["IC"].map(norm_ic)
                    senarai = senarai[senarai["_IC"] != ""].drop_duplicates(subset="_IC")
                    tuan = senarai["KOD SEKOLAH ASAL"].astype(str) == str(kod_sek_pusat)
                    bil_tuan = int(tuan.sum())
                    senarai = senarai[~tuan].copy()
                    senarai["_PUSAT"] = [pusat_guru(peta_pen, r.get("IC", ""), r.get("NAMA GURU", ""), r.get("KOD SEKOLAH ASAL", "")) for _, r in senarai.iterrows()]

                    def _status_calon(p_):
                        if p_ is None or (isinstance(p_, float) and pd.isna(p_)):
                            return "✅ Tersedia"
                        if p_ == "SIMPANAN":
                            return "🅿️ Petugas Simpanan"
                        if p_ == str(pusat_pilih):
                            return "📍 Sudah di pusat ini"
                        return f"🔒 Dilantik di {p_}"

                    senarai["STATUS"] = senarai["_PUSAT"].map(_status_calon)
                    senarai["_susun"] = senarai["STATUS"].map(lambda s: 0 if s.startswith("✅") else (1 if s.startswith("📍") else 2))
                    senarai = senarai.sort_values("_susun", kind="stable")
                    tersedia = senarai[senarai["STATUS"].str.startswith("✅")]
                    calon_edit = tersedia.drop(columns=["_IC", "_susun", "STATUS", "_PUSAT"]).reset_index(drop=True)
                    calon_options = [label_calon(r) for _, r in calon_edit.iterrows()]

                    bil_lain = int(senarai["STATUS"].str.startswith("🔒").sum())
                    bil_sini = int(senarai["STATUS"].str.startswith("📍").sum())
                    st.caption(f"✅ {len(calon_edit)} tersedia | 📍 {bil_sini} sudah di pusat ini | 🔒 {bil_lain} sudah dilantik di pusat lain (tak boleh dipilih) | {bil_tuan} guru sekolah tuan rumah ({kod_sek_pusat}) dikecualikan")
                    lajur_calon = [c for c in ["NAMA GURU", "KOD SEKOLAH ASAL", "NAMA SEKOLAH ASAL", "IC", "JANTINA", "POSKOD RUMAH", "NO TELEFON GURU", "PENGALAMAN SPM", "JAWATAN CADANGAN", "JAWATAN CADANG"] if c in senarai.columns]
                    st.dataframe(senarai[lajur_calon + ["STATUS"]], use_container_width=True, hide_index=True)

                    # Lantik manual dari senarai
                    sedia_jaw = penempatan_pusat["JAWATAN FINAL"].tolist() if (not penempatan_pusat.empty and "JAWATAN FINAL" in penempatan_pusat.columns) else []
                    jaw_kosong = jawatan_kosong(need_peng_single, sedia_jaw)
                    if not jaw_kosong:
                        st.success(f"✅ {pusat_pilih} sudah lengkap.")
                    elif not calon_options:
                        st.warning("Tiada calon tersedia untuk pusat ini - semua sudah dilantik / tuan rumah. Minta SUP tambah cadangan.")
                    else:
                        baki_jaw = {j: jaw_kosong.count(j) for j in dict.fromkeys(jaw_kosong)}
                        st.markdown("**➕ Lantik sendiri dari senarai ✅ Tersedia**")
                        pilih_jaw = st.selectbox("Jawatan", list(baki_jaw.keys()), format_func=lambda j: f"{j} (kosong {baki_jaw[j]})", key=f"manjaw_{pusat_pilih}")
                        pilih_guru = st.multiselect("Pilih guru", calon_options, key=f"manguru_{pusat_pilih}")
                        if st.button(f"✅ Lantik {len(pilih_guru)} guru ke {pusat_pilih}", use_container_width=True, type="primary", disabled=not pilih_guru, key=f"manlantik_{pusat_pilih}"):
                            if len(pilih_guru) > baki_jaw[pilih_jaw]:
                                st.error(f"Jawatan {pilih_jaw} hanya ada {baki_jaw[pilih_jaw]} kekosongan.")
                            else:
                                guru_dipilih = [calon_edit.iloc[calon_options.index(o)] for o in pilih_guru]

                                def _lantik(df_pen):
                                    ada = (not df_pen.empty) and ("IC" in df_pen.columns) and ("NO PUSAT TUGAS" in df_pen.columns)
                                    peta_x = peta_guru_pusat(df_pen, read_sheet_strict(TAB_SIMPANAN))
                                    for g in guru_dipilih:
                                        p_ = pusat_guru(peta_x, g.get("IC", ""), g.get("NAMA GURU", ""), g.get("KOD SEKOLAH ASAL", ""))
                                        if p_ is not None:
                                            raise ValueError(f"{g.get('NAMA GURU','')} sudah berada di {huraian_pusat(p_)} - seorang guru hanya boleh satu pusat.")
                                        if str(g.get("KOD SEKOLAH ASAL", "")) == str(kod_sek_pusat):
                                            raise ValueError(f"{g.get('NAMA GURU','')} dari sekolah tuan rumah - tak boleh jaga pusat sendiri.")
                                    sedia = df_pen[df_pen["NO PUSAT TUGAS"].astype(str) == str(pusat_pilih)]["JAWATAN FINAL"].tolist() if (ada and "JAWATAN FINAL" in df_pen.columns) else []
                                    if jawatan_kosong(need_peng_single, sedia).count(pilih_jaw) < len(guru_dipilih):
                                        raise ValueError(f"Jawatan {pilih_jaw} tak cukup kosong (mungkin sudah diisi orang lain) - muat semula halaman.")
                                    baru = pd.DataFrame([{
                                        "NO PUSAT TUGAS": str(pusat_pilih), "NAMA PUSAT TUGAS": nama_pusat,
                                        "KOD SEKOLAH ASAL GURU": g.get("KOD SEKOLAH ASAL", ""), "NAMA SEKOLAH ASAL": g.get("NAMA SEKOLAH ASAL", ""),
                                        "NAMA GURU": g.get("NAMA GURU", ""), "IC": g.get("IC", ""), "JANTINA": g.get("JANTINA", ""),
                                        "JAWATAN FINAL": pilih_jaw, "POSKOD RUMAH": g.get("POSKOD RUMAH", ""),
                                        "ALAMAT RUMAH": g.get("ALAMAT RUMAH", ""), "NO TELEFON GURU": g.get("NO TELEFON GURU", ""), "EMAIL GURU": g.get("EMAIL GURU", ""),
                                        "STATUS PENEMPATAN": f"Lantik manual oleh PPD {info['ppd_nama']} - {pd.Timestamp.now().strftime('%Y-%m-%d')}",
                                    } for g in guru_dipilih])
                                    return pd.concat([df_pen, baru], ignore_index=True) if not df_pen.empty else baru

                                if modify_sheet(TAB_PENEMPATAN, _lantik):
                                    flash("success", f"✅ {len(guru_dipilih)} guru dilantik sebagai {pilih_jaw} di {pusat_pilih}.")
                                    st.rerun()
                st.markdown("---")

                if penempatan_pusat.empty:
                    st.info(f"Belum dilantik untuk {pusat_pilih} - tekan Jana Auto di atas")
                else:
                    st.success(f"✅ {pusat_pilih} - {len(penempatan_pusat)} petugas dilantik")

                    lajur_papar = ["NAMA GURU", "KOD SEKOLAH ASAL GURU", "NAMA SEKOLAH ASAL", "IC", "JAWATAN FINAL"]
                    for jaw in ["Ketua Pengawas", "Timbalan Ketua Pengawas", "Pengawas Peperiksaan", "Pengemas Bilik", "Penyelia Kawasan"]:
                        subset = penempatan_pusat[penempatan_pusat["JAWATAN FINAL"].astype(str) == jaw] if "JAWATAN FINAL" in penempatan_pusat.columns else pd.DataFrame()
                        if not subset.empty:
                            st.markdown(f"**{jaw} ({len(subset)} orang)**")
                            st.dataframe(subset[[c for c in lajur_papar if c in subset.columns]], use_container_width=True)

                    st.markdown("---")
                    st.markdown(f"#### ✏️ Edit Lantikan {pusat_pilih} - Klik Nama Untuk Tukar")
                    st.caption(f"📍 Pusat: {pusat_pilih} - {nama_pusat} ({kod_sek_pusat}) | Guru dari {kod_sek_pusat} tidak boleh jaga pusat sendiri - auto exclude")


                    st.info(f"📋 Ada {len(calon_options)} guru dari daerah {info['ppd_nama']} yang belum dilantik dan boleh dipilih (kecuali {kod_sek_pusat})")

                    petugas_labels = []
                    for _, r in penempatan_pusat.iterrows():
                        petugas_labels.append(f"{r.get('NAMA GURU','')} - {r.get('JAWATAN FINAL','')} ({r.get('KOD SEKOLAH ASAL GURU','')})")

                    col_a, col_b = st.columns([1, 2])
                    with col_a:
                        idx_pilih = st.selectbox("1️⃣ Klik nama pengawas nak tukar", ["-- Pilih nama --"] + petugas_labels, key=f"pilih_{pusat_pilih}")
                    with col_b:
                        if idx_pilih != "-- Pilih nama --" and calon_options:
                            pos_lama = petugas_labels.index(idx_pilih)
                            baris_lama = penempatan_pusat.iloc[pos_lama]
                            petugas_pilih = str(baris_lama.get("NAMA GURU", ""))
                            ic_lama = norm_ic(baris_lama.get("IC", ""))
                            guru_baru = st.selectbox(f"2️⃣ Ganti {petugas_pilih} dengan guru lain (dari daerah {info['ppd_nama']} kecuali {kod_sek_pusat})", ["-- Pilih guru baru dari senarai cadangan --"] + calon_options, key=f"ganti_{pusat_pilih}")
                            if guru_baru != "-- Pilih guru baru dari senarai cadangan --":
                                if st.button(f"🔄 Tukar {petugas_pilih} → {guru_baru.split('|')[0].strip()}", use_container_width=True, type="primary", key=f"tukar_{pusat_pilih}"):
                                    guru_data = calon_edit.iloc[calon_options.index(guru_baru)]
                                    ic_baru = norm_ic(guru_data.get("IC", ""))

                                    def _tukar(df_pen):
                                        if df_pen.empty or "NO PUSAT TUGAS" not in df_pen.columns or "NAMA GURU" not in df_pen.columns:
                                            raise ValueError("Data penempatan tidak lengkap - muat semula halaman")
                                        p_lain = pusat_guru(peta_guru_pusat(df_pen, read_sheet_strict(TAB_SIMPANAN)), guru_data.get("IC", ""), guru_data.get("NAMA GURU", ""), guru_data.get("KOD SEKOLAH ASAL", ""))
                                        if p_lain is not None:
                                            raise ValueError(f"{guru_data.get('NAMA GURU','Guru ini')} sudah berada di {huraian_pusat(p_lain)} - pilih guru lain.")
                                        mask = df_pen["NO PUSAT TUGAS"].astype(str) == str(pusat_pilih)
                                        if ic_lama and "IC" in df_pen.columns:
                                            mask = mask & (df_pen["IC"].map(norm_ic) == ic_lama)
                                        else:
                                            mask = mask & (df_pen["NAMA GURU"].astype(str) == petugas_pilih)
                                        if not mask.any():
                                            raise ValueError("Petugas asal tak dijumpai (mungkin sudah diubah orang lain) - muat semula halaman")
                                        df_pen = df_pen.copy()
                                        df_pen.loc[mask, "NAMA GURU"] = guru_data.get("NAMA GURU", "")
                                        df_pen.loc[mask, "KOD SEKOLAH ASAL GURU"] = guru_data.get("KOD SEKOLAH ASAL", "")
                                        df_pen.loc[mask, "NAMA SEKOLAH ASAL"] = guru_data.get("NAMA SEKOLAH ASAL", "")
                                        df_pen.loc[mask, "IC"] = guru_data.get("IC", "")
                                        df_pen.loc[mask, "JANTINA"] = guru_data.get("JANTINA", "")
                                        df_pen.loc[mask, "POSKOD RUMAH"] = guru_data.get("POSKOD RUMAH", "")
                                        df_pen.loc[mask, "ALAMAT RUMAH"] = guru_data.get("ALAMAT RUMAH", "")
                                        df_pen.loc[mask, "NO TELEFON GURU"] = guru_data.get("NO TELEFON GURU", "")
                                        df_pen.loc[mask, "EMAIL GURU"] = guru_data.get("EMAIL GURU", "")
                                        df_pen.loc[mask, "STATUS PENEMPATAN"] = f"Tukar manual oleh PPD {info['ppd_nama']} - {pd.Timestamp.now().strftime('%Y-%m-%d')}"
                                        return df_pen

                                    if modify_sheet(TAB_PENEMPATAN, _tukar):
                                        flash("success", f"✅ {petugas_pilih} ditukar kepada {guru_data.get('NAMA GURU','')} dari {guru_data.get('KOD SEKOLAH ASAL','')}")
                                        st.rerun()

                    st.markdown("---")
                    st.markdown(f"#### ❌ Batalkan Penempatan {pusat_pilih} → Petugas Simpanan")
                    st.caption("Petugas yang dibatalkan dibuang daripada pusat ini dan masuk ke senarai Petugas Simpanan. Jana Auto tak akan pilih mereka semula; boleh ditempatkan semula melalui menu Petugas Simpanan.")
                    cb1, cb2 = st.columns([2, 1])
                    with cb1:
                        pilih_batal = st.selectbox("Pilih petugas yang nak dibatalkan", ["-- Pilih nama --"] + petugas_labels, key=f"batal_pilih_{pusat_pilih}_{st.session_state.get('ppd_n', 0)}")
                    with cb2:
                        sebab_batal = st.selectbox("Sebab", ["Sakit / tidak sihat", "Tarik diri", "Tidak sesuai", "Bertukar sekolah", "Lain-lain"], key=f"batal_sebab_{pusat_pilih}_{st.session_state.get('ppd_n', 0)}")
                    catatan_batal = st.text_input("Catatan (pilihan)", key=f"batal_catatan_{pusat_pilih}_{st.session_state.get('ppd_n', 0)}")
                    if pilih_batal != "-- Pilih nama --":
                        baris_b = penempatan_pusat.iloc[petugas_labels.index(pilih_batal)]
                        ic_b = norm_ic(baris_b.get("IC", ""))
                        nama_b = str(baris_b.get("NAMA GURU", ""))
                        sahkan_batal = st.checkbox(f"Ya, batalkan penempatan {nama_b}", key=f"batal_sahkan_{pusat_pilih}_{st.session_state.get('ppd_n', 0)}")
                        if st.button(f"❌ Batalkan {nama_b} dan masukkan ke Simpanan", use_container_width=True, disabled=not sahkan_batal, key=f"batal_btn_{pusat_pilih}"):
                            if not ic_b:
                                st.error("Petugas ini tiada IC dalam data - tak boleh dibatalkan melalui sistem. Edit terus dalam Google Sheet.")
                            else:
                                sebab_penuh = sebab_batal + (f": {catatan_batal.strip()}" if catatan_batal.strip() else "")
                                baris_simp = baris_simpanan(baris_b, sebab_penuh, info['ppd_nama'])
                                ok_batal = transaksi_dua_tab(
                                    TAB_SIMPANAN, lambda df: tambah_simpanan(df, baris_simp),
                                    TAB_PENEMPATAN, lambda df: buang_guru_ic(df, ic_b, pusat_pilih, "penempatan pusat ini"),
                                    lambda df: buang_guru_ic(df, ic_b, None, "senarai simpanan"),
                                )
                                if ok_batal:
                                    st.session_state["ppd_n"] = st.session_state.get("ppd_n", 0) + 1   # segarkan pilihan
                                    flash("success", f"✅ {nama_b} dibatalkan daripada {pusat_pilih} dan dimasukkan ke Petugas Simpanan. Jawatan {baris_b.get('JAWATAN FINAL','')} kini kosong.")
                                    st.rerun()
                    st.markdown("---")

                    st.markdown("#### 📋 Semua Petugas di Pusat Ini")
                    st.dataframe(penempatan_pusat, use_container_width=True)

        elif menu=="Penempatan Manual":
            st.header(f"✍️ Penempatan Manual - {info['ppd_nama']}")
            st.caption("Pilih petugas → pilih pusat → pilih jawatan → tempatkan. Boleh untuk petugas yang belum ditempatkan, yang sudah ditempatkan (dipindahkan) dan yang dalam simpanan.")
            cadangan_all = read_sheet(TAB_CADANGAN)
            penempatan_all = read_sheet(TAB_PENEMPATAN)
            simpanan_all = read_sheet(TAB_SIMPANAN)
            if not cadangan_all.empty and "KOD SEKOLAH ASAL" in cadangan_all.columns:
                cadangan_ppd = cadangan_all[cadangan_all["KOD SEKOLAH ASAL"].astype(str).isin(kod_sekolah_ppd)]
                TAB_PILIHAN_JANA = tab_daerah("pilihan_ppd", info['kod'])
                pilihan_jana = read_sheet(TAB_PILIHAN_JANA)
                if not pilihan_jana.empty and "IC" in pilihan_jana.columns and "STATUS PILIHAN" in pilihan_jana.columns:
                    ic_dipilih = pilihan_jana[pilihan_jana["STATUS PILIHAN"].astype(str).str.contains("DIPILIH") & ~pilihan_jana["STATUS PILIHAN"].astype(str).str.contains("TIDAK")]["IC"].map(norm_ic).tolist()
                    if ic_dipilih:
                        cadangan_ppd = cadangan_ppd[cadangan_ppd["IC"].map(norm_ic).isin(ic_dipilih)].copy()
                        st.info(f"🔍 Filter Pilihan PPD aktif: {len(ic_dipilih)} DIPILIH - hanya mereka akan dijana.")
            else:
                cadangan_ppd = pd.DataFrame()
            master = senarai_semua_petugas(cadangan_ppd, penempatan_all, simpanan_all)

            if master.empty:
                st.info("Belum ada petugas. Minta SUP isi Cadangan Petugas dahulu.")
            elif not semua_pusat:
                st.warning("Tiada pusat untuk daerah ini.")
            else:
                n_ = st.session_state.get("ppd_n", 0)
                m1, m2, m3, m4 = st.columns(4)
                with m1:
                    st.metric("Jumlah Petugas", len(master))
                with m2:
                    st.metric("Belum Ditempatkan", int((master["STATUS"] == "Belum ditempatkan").sum()))
                with m3:
                    st.metric("Ditempatkan", int((master["STATUS"] == "Ditempatkan").sum()))
                with m4:
                    st.metric("Simpanan", int((master["STATUS"] == "Simpanan").sum()))

                f1, f2, f3 = st.columns(3)
                with f1:
                    tapis_status = st.selectbox("Status", ["Semua", "Belum ditempatkan", "Ditempatkan", "Simpanan"], key=f"man_status_{n_}")
                with f2:
                    sek_opsyen = sorted({str(k) for k in master["KOD SEKOLAH ASAL"] if str(k).strip()})
                    nama_sek = {str(r_["KOD SEKOLAH ASAL"]): str(r_["NAMA SEKOLAH ASAL"]) for _, r_ in master.iterrows()}
                    tapis_sek = st.selectbox("Sekolah asal", ["Semua"] + sek_opsyen, format_func=lambda k: "Semua" if k == "Semua" else f"{k} - {nama_sek.get(k, '')}", key=f"man_sek_{n_}")
                with f3:
                    cari = st.text_input("Cari nama / IC", key=f"man_cari_{n_}")

                lihat = master.copy()
                if tapis_status != "Semua":
                    lihat = lihat[lihat["STATUS"] == tapis_status]
                if tapis_sek != "Semua":
                    lihat = lihat[lihat["KOD SEKOLAH ASAL"].astype(str) == tapis_sek]
                if cari.strip():
                    c_ = cari.strip().upper()
                    lihat = lihat[lihat["NAMA GURU"].astype(str).str.upper().str.contains(c_, regex=False) | lihat["IC"].astype(str).str.contains(c_, regex=False)]

                lajur_m = [c for c in ["NAMA GURU", "NAMA SEKOLAH ASAL", "KOD SEKOLAH ASAL", "IC", "JANTINA", "POSKOD RUMAH", "NO TELEFON GURU", "PENGALAMAN SPM", "STATUS", "PUSAT", "JAWATAN SEMASA"] if c in lihat.columns]
                st.dataframe(lihat[lajur_m], use_container_width=True, hide_index=True)

                st.markdown("---")
                st.markdown("### ✍️ Tempatkan Petugas")
                label_m = {}
                for _, r_ in lihat.iterrows():
                    k_ = norm_ic(r_.get("IC", ""))
                    if k_:
                        tambahan = f" → {r_['PUSAT']} ({r_['JAWATAN SEMASA']})" if r_["STATUS"] == "Ditempatkan" else ""
                        label_m[k_] = f"{r_['NAMA GURU']} | {r_['NAMA SEKOLAH ASAL']} | {r_['STATUS']}{tambahan}"
                if not label_m:
                    st.info("Tiada petugas (yang ada IC) dalam tapisan ini.")
                else:
                    pilih_m = st.selectbox("1️⃣ Pilih petugas", list(label_m.keys()), format_func=lambda k: label_m[k], key=f"man_guru_{n_}")
                    guru_m = master[master["IC"].map(norm_ic) == pilih_m].iloc[0]
                    status_m = guru_m["STATUS"]
                    pusat_kini = str(guru_m["PUSAT"])

                    kiraan_p = penempatan_all["NO PUSAT TUGAS"].astype(str).value_counts() if (not penempatan_all.empty and "NO PUSAT TUGAS" in penempatan_all.columns) else pd.Series(dtype=int)

                    def label_pusat_m(p):
                        return f"{p} - {pusat_to_nama.get(p, p)} ({int(kiraan_p.get(p, 0))}/{keperluan_pengawas(p, df_calon_master) + 2})"

                    idx_pusat = semua_pusat.index(pusat_kini) if pusat_kini in semua_pusat else 0
                    pusat_m = st.selectbox("2️⃣ Pilih pusat", semua_pusat, index=idx_pusat, format_func=label_pusat_m, key=f"man_pusat_{pilih_m}_{n_}")

                    sedia_m = penempatan_all[penempatan_all["NO PUSAT TUGAS"].astype(str) == str(pusat_m)]["JAWATAN FINAL"].astype(str).tolist() if (not penempatan_all.empty and "NO PUSAT TUGAS" in penempatan_all.columns and "JAWATAN FINAL" in penempatan_all.columns) else []
                    if status_m == "Ditempatkan" and pusat_m == pusat_kini and guru_m["JAWATAN SEMASA"] in sedia_m:
                        sedia_m.remove(guru_m["JAWATAN SEMASA"])   # kedudukan sendiri dikira kosong
                    need_m = keperluan_pengawas(pusat_m, df_calon_master)
                    kosong_m = jawatan_kosong(need_m, sedia_m)
                    kod_tuan_m = str(pusat_to_sekolah.get(pusat_m, ""))

                    if str(guru_m["KOD SEKOLAH ASAL"]) == kod_tuan_m:
                        st.error(f"❌ {guru_m['NAMA GURU']} dari sekolah tuan rumah {pusat_m} ({kod_tuan_m}) - tak boleh jaga pusat sendiri. Pilih pusat lain.")
                    elif not kosong_m:
                        st.warning(f"⚠️ {pusat_m} sudah penuh - tiada jawatan kosong. Pilih pusat lain.")
                    else:
                        jaw_m = st.selectbox("3️⃣ Pilih jawatan", list(dict.fromkeys(kosong_m)), format_func=lambda j: f"{j} (kosong {kosong_m.count(j)})", key=f"man_jaw_{pilih_m}_{pusat_m}_{n_}")
                        sama_je = status_m == "Ditempatkan" and pusat_m == pusat_kini and jaw_m == guru_m["JAWATAN SEMASA"]
                        if sama_je:
                            st.info("Petugas sudah berada di pusat dan jawatan ini.")
                        verb = {"Belum ditempatkan": "Tempatkan", "Simpanan": "Tempatkan dari simpanan", "Ditempatkan": "Pindahkan"}[status_m]
                        if st.button(f"✅ {verb} {guru_m['NAMA GURU']} → {pusat_m} sebagai {jaw_m}", use_container_width=True, type="primary", disabled=sama_je, key=f"man_btn_{pilih_m}_{n_}"):
                            label_status = f"Manual oleh PPD {info['ppd_nama']} - {pd.Timestamp.now().strftime('%Y-%m-%d')}"
                            nama_p = pusat_to_nama.get(pusat_m, pusat_m)

                            def _fn_pen(df_pen, pindah=(status_m == "Ditempatkan")):
                                return tempatkan_manual(df_pen, guru_m, pusat_m, jaw_m, kod_tuan_m, need_m, nama_p, label_status, pindah=pindah)

                            if status_m == "Simpanan":
                                ok_m = transaksi_dua_tab(
                                    TAB_PENEMPATAN, _fn_pen,
                                    TAB_SIMPANAN, lambda df: buang_guru_ic(df, pilih_m, None, "senarai simpanan"),
                                    lambda df: buang_guru_ic(df, pilih_m, pusat_m, "penempatan"),
                                )
                            else:
                                ok_m = modify_sheet(TAB_PENEMPATAN, _fn_pen)
                            if ok_m:
                                flash("success", f"✅ {guru_m['NAMA GURU']} {'dipindahkan' if status_m == 'Ditempatkan' else 'ditempatkan'} di {pusat_m} sebagai {jaw_m}.")
                                st.session_state["ppd_n"] = st.session_state.get("ppd_n", 0) + 1
                                st.rerun()

        elif menu=="Batal Penempatan":
            st.header(f"❌ Batal Penempatan - PPD {info['ppd_nama']}")
            st.caption("Batal penempatan ikut pusat atau keseluruhan daerah. Semua yang dibatalkan akan auto masuk ke Senarai Simpanan. SUP isi lebih petugas pun akan masuk simpanan. Sheet ikut tahun: {} - {}".format(tab_daerah("penempatan_ppd", info['kod']), st.session_state.get("tahun_pilih",2026)))
            
            penempatan_all = read_sheet(TAB_PENEMPATAN)
            simpanan_all = read_sheet(TAB_SIMPANAN)
            cadangan_all = read_sheet(TAB_CADANGAN)
            
            if not penempatan_all.empty and "NO PUSAT TUGAS" in penempatan_all.columns:
                pen_ppd = penempatan_all[penempatan_all["NO PUSAT TUGAS"].astype(str).isin(semua_pusat)].copy()
            else:
                pen_ppd = pd.DataFrame()
            
            st.markdown(f"#### 📊 Status Semasa - {len(semua_pusat)} pusat | {len(pen_ppd)} petugas dilantik | Tahun {st.session_state.get('tahun_pilih',2026)}")
            
            tab1, tab2, tab3 = st.tabs(["🏫 Batal Ikut Pusat", "🗺️ Batal Keseluruhan Daerah", "📦 Lebihan SUP ke Simpanan"])
            
            with tab1:
                st.subheader("Batal Ikut Pusat")
                if not semua_pusat:
                    st.warning("Tiada pusat")
                else:
                    pusat_batal = st.selectbox("Pilih Pusat untuk Batal", ["-- Pilih --"] + semua_pusat, format_func=lambda x: f"{x} - {pusat_to_nama.get(x,'')}" if x!="-- Pilih --" else x, key="batal_pusat_select")
                    if pusat_batal != "-- Pilih --":
                        if pen_ppd.empty:
                            st.info(f"Tiada petugas di {pusat_batal}")
                        else:
                            df_pusat = pen_ppd[pen_ppd["NO PUSAT TUGAS"].astype(str)==str(pusat_batal)].copy()
                            if df_pusat.empty:
                                st.info(f"Tiada petugas di {pusat_batal}")
                            else:
                                st.dataframe(df_pusat, use_container_width=True)
                                
                                df_pusat["_pilih"] = False
                                edited = st.data_editor(df_pusat[["_pilih","NAMA GURU","IC","JAWATAN FINAL","NAMA SEKOLAH ASAL"]], use_container_width=True, hide_index=True, column_config={"_pilih": st.column_config.CheckboxColumn("Batal?")}, key=f"edit_batal_{pusat_batal}")
                                
                                pilih_batal = edited[edited["_pilih"]==True]
                                
                                col_a, col_b = st.columns(2)
                                with col_a:
                                    sebab_batal = st.text_input("Sebab Batal", placeholder="Contoh: Pertukaran guru, cuti bersalin...", key=f"sebab_{pusat_batal}")
                                with col_b:
                                    st.write(f"Terpilih: {len(pilih_batal)} orang")
                                
                                c1,c2 = st.columns(2)
                                with c1:
                                    if st.button(f"❌ Batal {len(pilih_batal)} Terpilih di {pusat_batal}", use_container_width=True, type="primary", disabled=len(pilih_batal)==0, key="btn_batal_pilih"):
                                        baris_simpanan_list = []
                                        for _, r in df_pusat[df_pusat["IC"].isin(pilih_batal["IC"])].iterrows():
                                            baris_simpanan_list.append({
                                                "KOD SEKOLAH ASAL GURU": r.get("KOD SEKOLAH ASAL GURU",""),
                                                "NAMA SEKOLAH ASAL": r.get("NAMA SEKOLAH ASAL",""),
                                                "NAMA GURU": r.get("NAMA GURU",""),
                                                "IC": r.get("IC",""),
                                                "JANTINA": r.get("JANTINA",""),
                                                "POSKOD RUMAH": r.get("POSKOD RUMAH",""),
                                                "ALAMAT RUMAH": r.get("ALAMAT RUMAH",""),
                                                "NO TELEFON GURU": r.get("NO TELEFON GURU",""),
                                                "EMAIL GURU": r.get("EMAIL GURU",""),
                                                "JAWATAN ASAL": r.get("JAWATAN FINAL",""),
                                                "DIBATAL DARI PUSAT": str(pusat_batal),
                                                "NAMA PUSAT ASAL BATAL": pusat_to_nama.get(pusat_batal, pusat_batal),
                                                "TARIKH BATAL": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                                                "BATAL OLEH": f"PPD {info['ppd_nama']}",
                                                "SEBAB BATAL": sebab_batal,
                                                "STATUS SIMPANAN": "Dalam Simpanan"
                                            })
                                        
                                        def _batal_pusat(df_pen):
                                            mask = (df_pen["NO PUSAT TUGAS"].astype(str)==str(pusat_batal)) & (df_pen["IC"].isin(pilih_batal["IC"]))
                                            return df_pen[~mask].copy() if not df_pen.empty else df_pen
                                        
                                        def _masuk_simpanan(df_simp):
                                            if df_simp.empty:
                                                return pd.DataFrame(baris_simpanan_list)
                                            ic_baru = [b["IC"] for b in baris_simpanan_list]
                                            df_simp = df_simp[~df_simp["IC"].map(norm_ic).isin([norm_ic(x) for x in ic_baru])]
                                            return pd.concat([df_simp, pd.DataFrame(baris_simpanan_list)], ignore_index=True)
                                        
                                        ok1 = modify_sheet(TAB_PENEMPATAN, _batal_pusat)
                                        ok2 = modify_sheet(TAB_SIMPANAN, _masuk_simpanan)
                                        if ok1 and ok2:
                                            flash("success", f"✅ {len(pilih_batal)} petugas dari {pusat_batal} dibatalkan & masuk Simpanan!")
                                            st.rerun()
                                
                                with c2:
                                    if st.button(f"❌ Batal SEMUA di {pusat_batal} ({len(df_pusat)} orang)", use_container_width=True, key="btn_batal_semua_pusat"):
                                        baris_simpanan_list = []
                                        for _, r in df_pusat.iterrows():
                                            baris_simpanan_list.append({
                                                "KOD SEKOLAH ASAL GURU": r.get("KOD SEKOLAH ASAL GURU",""),
                                                "NAMA SEKOLAH ASAL": r.get("NAMA SEKOLAH ASAL",""),
                                                "NAMA GURU": r.get("NAMA GURU",""),
                                                "IC": r.get("IC",""),
                                                "JANTINA": r.get("JANTINA",""),
                                                "POSKOD RUMAH": r.get("POSKOD RUMAH",""),
                                                "ALAMAT RUMAH": r.get("ALAMAT RUMAH",""),
                                                "NO TELEFON GURU": r.get("NO TELEFON GURU",""),
                                                "EMAIL GURU": r.get("EMAIL GURU",""),
                                                "JAWATAN ASAL": r.get("JAWATAN FINAL",""),
                                                "DIBATAL DARI PUSAT": str(pusat_batal),
                                                "NAMA PUSAT ASAL BATAL": pusat_to_nama.get(pusat_batal, pusat_batal),
                                                "TARIKH BATAL": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                                                "BATAL OLEH": f"PPD {info['ppd_nama']}",
                                                "SEBAB BATAL": sebab_batal or "Batal semua pusat",
                                                "STATUS SIMPANAN": "Dalam Simpanan"
                                            })
                                        def _batal_all_pusat(df_pen):
                                            if df_pen.empty:
                                                return df_pen
                                            return df_pen[df_pen["NO PUSAT TUGAS"].astype(str)!=str(pusat_batal)].copy()
                                        def _masuk_simpanan_all(df_simp):
                                            if df_simp.empty:
                                                return pd.DataFrame(baris_simpanan_list)
                                            ic_baru = [b["IC"] for b in baris_simpanan_list]
                                            df_simp = df_simp[~df_simp["IC"].map(norm_ic).isin([norm_ic(x) for x in ic_baru])]
                                            return pd.concat([df_simp, pd.DataFrame(baris_simpanan_list)], ignore_index=True)
                                        ok1 = modify_sheet(TAB_PENEMPATAN, _batal_all_pusat)
                                        ok2 = modify_sheet(TAB_SIMPANAN, _masuk_simpanan_all)
                                        if ok1 and ok2:
                                            flash("success", f"✅ Semua {len(df_pusat)} petugas dari {pusat_batal} dibatalkan!")
                                            st.rerun()
            
            with tab2:
                st.subheader("Batal Keseluruhan Daerah")
                st.error(f"⚠️ Tindakan ini akan batal SEMUA {len(pen_ppd)} petugas di {len(semua_pusat)} pusat dalam PPD {info['ppd_nama']}!")
                if not pen_ppd.empty:
                    st.dataframe(pen_ppd, use_container_width=True)
                else:
                    st.info("Tiada penempatan")
                
                if not pen_ppd.empty:
                    sebab_all = st.text_input("Sebab Batal Keseluruhan", placeholder="Contoh: Penstrukturan semula, arahan JPN...", key="sebab_all")
                    confirm_text = st.text_input(f'Taip "BATAL {info["kod"]}" untuk sahkan', key="confirm_all")
                    
                    if st.button("💥 BATAL KESELURUHAN DAERAH", use_container_width=True, type="primary", disabled=confirm_text!=f"BATAL {info['kod']}"):
                        baris_simpanan_list = []
                        for _, r in pen_ppd.iterrows():
                            baris_simpanan_list.append({
                                "KOD SEKOLAH ASAL GURU": r.get("KOD SEKOLAH ASAL GURU",""),
                                "NAMA SEKOLAH ASAL": r.get("NAMA SEKOLAH ASAL",""),
                                "NAMA GURU": r.get("NAMA GURU",""),
                                "IC": r.get("IC",""),
                                "JANTINA": r.get("JANTINA",""),
                                "POSKOD RUMAH": r.get("POSKOD RUMAH",""),
                                "ALAMAT RUMAH": r.get("ALAMAT RUMAH",""),
                                "NO TELEFON GURU": r.get("NO TELEFON GURU",""),
                                "EMAIL GURU": r.get("EMAIL GURU",""),
                                "JAWATAN ASAL": r.get("JAWATAN FINAL",""),
                                "DIBATAL DARI PUSAT": str(r.get("NO PUSAT TUGAS","")),
                                "NAMA PUSAT ASAL BATAL": str(r.get("NAMA PUSAT TUGAS","")),
                                "TARIKH BATAL": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "BATAL OLEH": f"PPD {info['ppd_nama']} - KESELURUHAN",
                                "SEBAB BATAL": sebab_all or "Batal keseluruhan daerah",
                                "STATUS SIMPANAN": "Dalam Simpanan - Batal Keseluruhan"
                            })
                        
                        def _batal_keseluruhan(df_pen):
                            if df_pen.empty:
                                return df_pen
                            return df_pen[~df_pen["NO PUSAT TUGAS"].astype(str).isin(semua_pusat)].copy()
                        
                        def _masuk_simpanan_keseluruhan(df_simp):
                            if df_simp.empty:
                                return pd.DataFrame(baris_simpanan_list)
                            ic_baru = [b["IC"] for b in baris_simpanan_list]
                            df_simp = df_simp[~df_simp["IC"].map(norm_ic).isin([norm_ic(x) for x in ic_baru])]
                            return pd.concat([df_simp, pd.DataFrame(baris_simpanan_list)], ignore_index=True)
                        
                        ok1 = modify_sheet(TAB_PENEMPATAN, _batal_keseluruhan)
                        ok2 = modify_sheet(TAB_SIMPANAN, _masuk_simpanan_keseluruhan)
                        if ok1 and ok2:
                            flash("success", f"💥 Keseluruhan {len(pen_ppd)} petugas dibatalkan & masuk Simpanan!")
                            st.rerun()
            
            with tab3:
                st.subheader("Lebihan Cadangan SUP → Simpanan")
                st.caption("Jika SUP isi lebih petugas daripada keperluan, yang lebihan auto masuk simpanan.")
                
                if cadangan_all.empty:
                    st.info("Tiada cadangan SUP")
                else:
                    peta = peta_guru_pusat(pen_ppd)
                    belum_lantik = []
                    for _, r in cadangan_all.iterrows():
                        if pusat_guru(peta, r.get("IC",""), r.get("NAMA GURU",""), r.get("KOD SEKOLAH ASAL","")) is None:
                            belum_lantik.append(r)
                    
                    if not belum_lantik:
                        st.success("✅ Semua cadangan sudah dilantik - tiada lebihan")
                    else:
                        df_belum = pd.DataFrame(belum_lantik)
                        st.metric("Cadangan Belum Dilantik (Lebihan)", f"{len(df_belum)} orang")
                        st.dataframe(df_belum, use_container_width=True)
                        
                        df_belum["_pilih"] = False
                        edited_belum = st.data_editor(df_belum[["_pilih","NAMA GURU","IC","JAWATAN CADANGAN","NAMA SEKOLAH ASAL"]], use_container_width=True, hide_index=True, column_config={"_pilih": st.column_config.CheckboxColumn("Masuk Simpanan?")}, key="edit_lebihan")
                        pilih_lebihan = edited_belum[edited_belum["_pilih"]==True]
                        
                        if st.button(f"📦 Pindahkan {len(pilih_lebihan)} Lebihan ke Simpanan", use_container_width=True, disabled=len(pilih_lebihan)==0):
                            baris_simpanan_list = []
                            for _, r in df_belum[df_belum["IC"].isin(pilih_lebihan["IC"])].iterrows():
                                baris_simpanan_list.append({
                                    "KOD SEKOLAH ASAL GURU": r.get("KOD SEKOLAH ASAL",""),
                                    "NAMA SEKOLAH ASAL": r.get("NAMA SEKOLAH ASAL",""),
                                    "NAMA GURU": r.get("NAMA GURU",""),
                                    "IC": r.get("IC",""),
                                    "JANTINA": r.get("JANTINA",""),
                                    "POSKOD RUMAH": r.get("POSKOD RUMAH",""),
                                    "ALAMAT RUMAH": r.get("ALAMAT RUMAH",""),
                                    "NO TELEFON GURU": r.get("NO TELEFON GURU",""),
                                    "EMAIL GURU": r.get("EMAIL GURU",""),
                                    "JAWATAN ASAL": r.get("JAWATAN CADANGAN",""),
                                    "DIBATAL DARI PUSAT": "LEBIHAN CADANGAN SUP",
                                    "TARIKH BATAL": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "BATAL OLEH": f"PPD {info['ppd_nama']} - Lebihan",
                                    "SEBAB BATAL": "Lebihan cadangan SUP - melebihi kuota",
                                    "STATUS SIMPANAN": "Lebihan SUP"
                                })
                            def _masuk_lebihan(df_simp):
                                if df_simp.empty:
                                    return pd.DataFrame(baris_simpanan_list)
                                ic_baru = [b["IC"] for b in baris_simpanan_list]
                                df_simp = df_simp[~df_simp["IC"].map(norm_ic).isin([norm_ic(x) for x in ic_baru])]
                                return pd.concat([df_simp, pd.DataFrame(baris_simpanan_list)], ignore_index=True)
                            
                            if modify_sheet(TAB_SIMPANAN, _masuk_lebihan):
                                flash("success", f"📦 {len(pilih_lebihan)} lebihan cadangan dipindah ke Simpanan!")
                                st.rerun()

        elif menu=="Petugas Simpanan":

            st.header(f"🅿️ Petugas Simpanan - {info['ppd_nama']}")
            st.caption("Selagi PPD tak tick cadangan SUP, senarai ini kosong. Lepas PPD tick, yang di-tick akan masuk untuk Jana. Jika belum dijana / belum ditempatkan manual, mereka ada di sini sebagai backup.")
            simpanan_all = read_sheet(TAB_SIMPANAN)
            penempatan_all = read_sheet(TAB_PENEMPATAN)
            cadangan_all_s = read_sheet(TAB_CADANGAN)
            TAB_PILIHAN_S = tab_daerah("pilihan_ppd", info['kod'])
            pilihan_all_s = read_sheet(TAB_PILIHAN_S)
            
            tambahan_sedia = []
            if not pilihan_all_s.empty and not cadangan_all_s.empty:
                peta_s = peta_guru_pusat(penempatan_all, simpanan_all)
                ic_dipilih_s = pilihan_all_s[pilihan_all_s["STATUS PILIHAN"].astype(str).str.contains("DIPILIH") & ~pilihan_all_s["STATUS PILIHAN"].astype(str).str.contains("TIDAK")]["IC"].map(norm_ic).tolist() if "STATUS PILIHAN" in pilihan_all_s.columns else []
                for ic_n in ic_dipilih_s:
                    if pusat_guru(peta_s, ic_n, "", "") is None:
                        r_cad = cadangan_all_s[cadangan_all_s["IC"].map(norm_ic)==ic_n]
                        if not r_cad.empty:
                            r = r_cad.iloc[0]
                            tambahan_sedia.append({
                                "KOD SEKOLAH ASAL GURU": r.get("KOD SEKOLAH ASAL",""),
                                "NAMA SEKOLAH ASAL": r.get("NAMA SEKOLAH ASAL",""),
                                "NAMA GURU": r.get("NAMA GURU",""),
                                "IC": r.get("IC",""),
                                "JANTINA": r.get("JANTINA",""),
                                "POSKOD RUMAH": r.get("POSKOD RUMAH",""),
                                "ALAMAT RUMAH": r.get("ALAMAT RUMAH",""),
                                "NO TELEFON GURU": r.get("NO TELEFON GURU",""),
                                "EMAIL GURU": r.get("EMAIL GURU",""),
                                "JAWATAN ASAL": r.get("JAWATAN CADANGAN","") or r.get("JAWATAN CADANG",""),
                                "DIBATAL DARI PUSAT": "DIPILIH PPD - BELUM JANA",
                                "NAMA PUSAT ASAL BATAL": "",
                                "TARIKH BATAL": "",
                                "BATAL OLEH": f"PPD {info['ppd_nama']} - Dipilih",
                                "SEBAB BATAL": "Dipilih PPD tapi belum dijana / belum ditempatkan manual",
                                "STATUS SIMPANAN": "Sedia Dijana (Tick PPD)"
                            })
            if tambahan_sedia:
                df_tambahan = pd.DataFrame(tambahan_sedia)
                if simpanan_all.empty:
                    simpanan_all = df_tambahan
                else:
                    ic_exist = simpanan_all["IC"].map(norm_ic).tolist() if "IC" in simpanan_all.columns else []
                    df_tambahan = df_tambahan[~df_tambahan["IC"].map(norm_ic).isin(ic_exist)]
                    simpanan_all = pd.concat([simpanan_all, df_tambahan], ignore_index=True) if not df_tambahan.empty else simpanan_all
                st.info(f"ℹ️ Ada {len(tambahan_sedia)} yang DIPILIH PPD tapi belum dijana - dipaparkan sebagai Sedia Dijana")
            
            if simpanan_all.empty or "IC" not in simpanan_all.columns:
                st.info("📭 Simpanan kosong - selagi PPD tak tick cadangan SUP, tiada nama di sini. Sila tick di menu Cadangan SUP dahulu.")
            else:
                peta_p = peta_guru_pusat(penempatan_all)
                paparan = simpanan_all.copy()
                status_semasa, label_s = [], {}
                for _, r_ in paparan.iterrows():
                    p_ = pusat_guru(peta_p, r_.get("IC", ""), r_.get("NAMA GURU", ""), r_.get("KOD SEKOLAH ASAL GURU", ""))
                    status_semasa.append("🅿️ Simpanan" if p_ is None else f"⚠️ Sudah dilantik di {p_}")
                    k_ = norm_ic(r_.get("IC", ""))
                    if p_ is None and k_:
                        label_s[k_] = f"{r_.get('NAMA GURU', '')} | {r_.get('NAMA SEKOLAH ASAL', '')} | IC: {r_.get('IC', '')} | Asal: {r_.get('DIBATAL DARI PUSAT', '')} ({r_.get('JAWATAN ASAL', '')})"
                paparan["STATUS SEMASA"] = status_semasa
                st.metric("Bilangan Petugas Simpanan", f"{len(label_s)}")
                st.dataframe(paparan, use_container_width=True, hide_index=True)
                if any(s.startswith("⚠️") for s in status_semasa):
                    st.warning("Ada rekod bertanda ⚠️: guru itu sebenarnya sudah dilantik di pusat lain. Pilih 'Keluarkan daripada simpanan' untuk bersihkan rekod itu.")

                st.markdown("---")
                st.markdown("### ➕ Tempatkan Semula ke Pusat")
                if not label_s:
                    st.info("Tiada petugas simpanan yang boleh ditempatkan.")
                elif not semua_pusat:
                    st.warning("Tiada pusat untuk daerah ini.")
                else:
                    pilih_s = st.selectbox("Pilih petugas simpanan", list(label_s.keys()), format_func=lambda k: label_s[k], key=f"simp_pilih_{st.session_state.get('ppd_n', 0)}")
                    pusat_t = st.selectbox("Tempatkan ke pusat", semua_pusat, key="simp_pusat")
                    sedia_t = penempatan_all[penempatan_all["NO PUSAT TUGAS"].astype(str) == str(pusat_t)]["JAWATAN FINAL"].tolist() if (not penempatan_all.empty and "NO PUSAT TUGAS" in penempatan_all.columns and "JAWATAN FINAL" in penempatan_all.columns) else []
                    need_t = keperluan_pengawas(pusat_t, df_calon_master)
                    kosong_t = jawatan_kosong(need_t, sedia_t)
                    if not kosong_t:
                        st.success(f"✅ {pusat_t} sudah lengkap - tiada jawatan kosong.")
                    else:
                        jaw_t = st.selectbox("Jawatan", list(dict.fromkeys(kosong_t)), format_func=lambda j: f"{j} (kosong {kosong_t.count(j)})", key=f"simp_jaw_{st.session_state.get('ppd_n', 0)}")
                        if st.button(f"✅ Tempatkan ke {pusat_t} sebagai {jaw_t}", use_container_width=True, type="primary", key="simp_tempat"):
                            baris_s = simpanan_all[simpanan_all["IC"].map(norm_ic) == pilih_s].iloc[0]
                            baru_pen = {
                                "NO PUSAT TUGAS": str(pusat_t), "NAMA PUSAT TUGAS": pusat_to_nama.get(pusat_t, pusat_t),
                                "KOD SEKOLAH ASAL GURU": baris_s.get("KOD SEKOLAH ASAL GURU", ""), "NAMA SEKOLAH ASAL": baris_s.get("NAMA SEKOLAH ASAL", ""),
                                "NAMA GURU": baris_s.get("NAMA GURU", ""), "IC": baris_s.get("IC", ""), "JANTINA": baris_s.get("JANTINA", ""),
                                "JAWATAN FINAL": jaw_t, "POSKOD RUMAH": baris_s.get("POSKOD RUMAH", ""), "ALAMAT RUMAH": baris_s.get("ALAMAT RUMAH", ""),
                                "NO TELEFON GURU": baris_s.get("NO TELEFON GURU", ""), "EMAIL GURU": baris_s.get("EMAIL GURU", ""),
                                "STATUS PENEMPATAN": f"Dari simpanan oleh PPD {info['ppd_nama']} - {pd.Timestamp.now().strftime('%Y-%m-%d')}",
                            }
                            def _tambah_pen(df_pen):
                                if str(baru_pen["KOD SEKOLAH ASAL GURU"]) == str(pusat_to_sekolah.get(pusat_t, "")):
                                    raise ValueError("Guru dari sekolah tuan rumah - tak boleh jaga pusat sendiri.")
                                if pusat_guru(peta_guru_pusat(df_pen), baru_pen["IC"], baru_pen["NAMA GURU"], baru_pen["KOD SEKOLAH ASAL GURU"]) is not None:
                                    raise ValueError("Guru ini sudah dilantik di pusat lain.")
                                if df_pen.empty:
                                    return pd.DataFrame([baru_pen])
                                return pd.concat([df_pen, pd.DataFrame([baru_pen])], ignore_index=True)
                            def _buang_simpanan(df_simp):
                                return df_simp[df_simp["IC"].map(norm_ic) != pilih_s].copy() if not df_simp.empty else df_simp
                            ok1 = modify_sheet(TAB_PENEMPATAN, _tambah_pen)
                            ok2 = modify_sheet(TAB_SIMPANAN, _buang_simpanan)
                            if ok1 and ok2:
                                flash("success", f"✅ {baru_pen['NAMA GURU']} ditempatkan di {pusat_t} sebagai {jaw_t}.")
                                st.rerun()

                st.markdown("---")
                st.markdown("### ↩️ Keluarkan daripada Simpanan → Masuk Cadangan SUP")
                st.caption("Guru dikeluarkan akan kembali ke senarai cadangan biasa (BELUM PILIH) dan boleh di-tick semula di Cadangan SUP.")
                semua_label = {}
                for _, r_ in simpanan_all.iterrows():
                    k_ = norm_ic(r_.get("IC", ""))
                    if k_:
                        semua_label[k_] = f"{r_.get('NAMA GURU', '')} | IC: {r_.get('IC', '')} | {r_.get('JAWATAN ASAL','')}"
                pilih_keluar = st.multiselect("Pilih guru", list(semua_label.keys()), format_func=lambda k: semua_label[k], key=f"simp_keluar_{st.session_state.get('ppd_n', 0)}")
                if st.button(f"↩️ Keluarkan {len(pilih_keluar)} guru → Cadangan SUP", use_container_width=True, disabled=not pilih_keluar, key="simp_keluar_btn"):
                    def _keluar(df):
                        for k in pilih_keluar:
                            df = buang_guru_ic(df, k, None, "senarai simpanan")
                        return df
                    def _keluar_pilihan(df_pilihan):
                        if df_pilihan.empty:
                            return df_pilihan
                        return df_pilihan[~df_pilihan["IC"].map(norm_ic).isin(pilih_keluar)].copy()
                    TAB_PILIHAN_KELUAR = tab_daerah("pilihan_ppd", info['kod'])
                    ok1 = modify_sheet(TAB_SIMPANAN, _keluar)
                    ok2 = modify_sheet(TAB_PILIHAN_KELUAR, _keluar_pilihan)
                    if ok1:
                        st.session_state["ppd_n"] = st.session_state.get("ppd_n", 0) + 1
                        flash("success", f"✅ {len(pilih_keluar)} guru dikeluarkan → masuk semula ke Cadangan SUP sebagai BELUM PILIH.")
                        st.rerun()

                st.markdown("---")
                st.markdown("### 🗑️ Kosongkan Senarai Petugas Simpanan")
                st.caption("Semua petugas dalam simpanan akan dikosongkan dan masuk semula ke ruang Cadangan SUP sebagai BELUM PILIH. Selagi PPD tak tick semula, mereka tidak akan dijana.")
                
                if simpanan_all.empty:
                    st.info("Simpanan sudah kosong")
                else:
                    st.warning(f"⚠️ Tindakan ini akan kosongkan {len(simpanan_all)} petugas dari simpanan dan masukkan semula ke Cadangan SUP!")
                    col_k1, col_k2 = st.columns(2)
                    with col_k1:
                        sebab_kosong = st.text_input("Sebab Kosongkan Simpanan", placeholder="Contoh: Semak semula cadangan...", key="sebab_kosong_simpanan")
                    with col_k2:
                        confirm_kosong = st.text_input(f'Taip "KOSONGKAN {info["kod"]}" untuk sahkan', key="confirm_kosong")
                    
                    if st.button(f"🗑️ KOSONGKAN SEMUA {len(simpanan_all)} DARI SIMPANAN → MASUK CADANGAN SUP", use_container_width=True, type="primary", disabled=confirm_kosong!=f"KOSONGKAN {info['kod']}", key="btn_kosongkan_simpanan"):
                        ic_simpanan = simpanan_all["IC"].map(norm_ic).tolist() if "IC" in simpanan_all.columns else []
                        
                        def _kosongkan_simpanan(df):
                            if df.empty:
                                return df
                            return df.iloc[0:0].copy()
                        
                        def _kembalikan_ke_cadangan_pilihan(df_pilihan):
                            if df_pilihan.empty or "IC" not in df_pilihan.columns:
                                return df_pilihan
                            return df_pilihan[~df_pilihan["IC"].map(norm_ic).isin(ic_simpanan)].copy()
                        
                        def _log_kosong(df_log):
                            baris_log = []
                            for _, r in simpanan_all.iterrows():
                                baris_log.append({
                                    "IC": r.get("IC",""),
                                    "NAMA GURU": r.get("NAMA GURU",""),
                                    "KOD SEKOLAH ASAL": r.get("KOD SEKOLAH ASAL GURU","") or r.get("KOD SEKOLAH ASAL",""),
                                    "TINDAKAN": "KOSONGKAN SIMPANAN → CADANGAN SUP",
                                    "TARIKH": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "OLEH": f"PPD {info['ppd_nama']}",
                                    "SEBAB": sebab_kosong,
                                    "DARI": r.get("DIBATAL DARI PUSAT","") or r.get("STATUS SIMPANAN",""),
                                    "JAWATAN ASAL": r.get("JAWATAN ASAL","")
                                })
                            if not baris_log:
                                return df_log
                            df_baru = pd.DataFrame(baris_log)
                            if df_log.empty:
                                return df_baru
                            return pd.concat([df_log, df_baru], ignore_index=True)
                        
                        TAB_LOG = tab_daerah("log_simpanan", info['kod'])
                        TAB_PILIHAN_K = tab_daerah("pilihan_ppd", info['kod'])
                        
                        ok1 = modify_sheet(TAB_SIMPANAN, _kosongkan_simpanan)
                        ok2 = modify_sheet(TAB_PILIHAN_K, _kembalikan_ke_cadangan_pilihan)
                        try:
                            modify_sheet(TAB_LOG, _log_kosong)
                        except:
                            pass
                        
                        if ok1 and ok2:
                            flash("success", f"🗑️ {len(ic_simpanan)} petugas dikosongkan dari Simpanan dan masuk semula ke Cadangan SUP sebagai BELUM PILIH!")
                            st.rerun()


        elif menu=="Hantar JPN":
            st.header(f"📤 Hantar ke JPN - {info['ppd_nama']}")
            penempatan_all = read_sheet(TAB_PENEMPATAN)
            status_all = read_sheet(tab_tahun("status_hantar"))

            bil_petugas = 0
            bil_pusat_ada = 0
            bil_pusat_lengkap = 0
            if (not penempatan_all.empty) and ("NO PUSAT TUGAS" in penempatan_all.columns):
                pen_ppd = penempatan_all[penempatan_all["NO PUSAT TUGAS"].astype(str).isin(semua_pusat)]
                bil_petugas = len(pen_ppd)
                kiraan = pen_ppd["NO PUSAT TUGAS"].astype(str).value_counts()
                bil_pusat_ada = len(kiraan)
                bil_pusat_lengkap = sum(1 for p in semua_pusat if kiraan.get(p, 0) >= keperluan_pengawas(p, df_calon_master) + 2)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Sekolah", f"{len(df_ppd)}")
            with col2:
                st.metric("Pusat", f"{len(semua_pusat)}")
            with col3:
                st.metric("Pusat Ada Lantikan", f"{bil_pusat_ada}/{len(semua_pusat)}")
            with col4:
                st.metric("Pusat Lengkap", f"{bil_pusat_lengkap}/{len(semua_pusat)}")

            if (not status_all.empty) and ("KOD PPD" in status_all.columns):
                rekod = status_all[status_all["KOD PPD"].astype(str) == str(info['kod'])]
                if not rekod.empty:
                    r = rekod.iloc[-1]
                    st.info(f"Status terakhir: {r.get('STATUS','')} | Dihantar: {r.get('TARIKH HANTAR','')} | Disahkan: {r.get('TARIKH SAH','') or '-'}")

            if bil_pusat_lengkap < len(semua_pusat):
                st.warning(f"⚠️ {len(semua_pusat) - bil_pusat_lengkap} pusat belum lengkap. Anda masih boleh hantar, tapi JPN akan nampak status tak lengkap.")

            if st.button("📤 HANTAR ke JPN", use_container_width=True, type="primary"):
                if bil_petugas == 0:
                    st.error("Belum ada petugas dilantik. Jana Penempatan dulu.")
                else:
                    baris_hantar = {
                        "KOD PPD": info['kod'], "PPD": info['ppd_nama'],
                        "TARIKH HANTAR": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "BIL PUSAT": len(semua_pusat), "PUSAT ADA LANTIKAN": bil_pusat_ada,
                        "PUSAT LENGKAP": bil_pusat_lengkap, "BIL PETUGAS": bil_petugas,
                        "STATUS": "Dihantar", "TARIKH SAH": "",
                    }

                    def _hantar(df):
                        if not df.empty and "KOD PPD" not in df.columns:
                            raise ValueError("Format sheet status_hantar tidak dijangka - hubungi admin")
                        if df.empty:
                            return pd.DataFrame([baris_hantar])
                        df = df[df["KOD PPD"].astype(str) != str(info['kod'])]
                        return pd.concat([df, pd.DataFrame([baris_hantar])], ignore_index=True) if not df.empty else pd.DataFrame([baris_hantar])

                    if modify_sheet("status_hantar", _hantar):
                        flash("success", f"✅ PPD {info['ppd_nama']} berjaya hantar {bil_pusat_ada} pusat ({bil_petugas} petugas) ke JPN!")
                        st.rerun()
    else:
        if menu=="Semua PPD":
            st.header(f"🏛️ Semua PPD - {len(mapping_df)} Sekolah - File: {os.path.basename(file_used)}")
            st.dataframe(mapping_df, use_container_width=True)
        elif menu=="Sahkan PPD":
            st.header("✅ Sahkan PPD")
            status_all = read_sheet(tab_tahun("status_hantar"))
            if status_all.empty:
                st.info("Belum ada PPD yang hantar ke JPN.")
            else:
                st.dataframe(status_all, use_container_width=True)
            label_ppd = {kod: f"{nama} ({kod}) - {len(mapping_df[mapping_df['KOD PPD']==kod])} sekolah" for _, _, nama, kod in PPD_LIST}
            kod_sah = st.selectbox("Pilih PPD", list(label_ppd.keys()), format_func=lambda k: label_ppd[k])
            if st.button("✅ SAHKAN", use_container_width=True, type="primary"):
                def _sahkan(df):
                    if df.empty or "KOD PPD" not in df.columns or not (df["KOD PPD"].astype(str) == kod_sah).any():
                        raise ValueError(f"{label_ppd[kod_sah]} belum hantar ke JPN - tak boleh disahkan lagi.")
                    df = df.copy()
                    mask = df["KOD PPD"].astype(str) == kod_sah
                    df.loc[mask, "STATUS"] = "Disahkan"
                    df.loc[mask, "TARIKH SAH"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                    return df
                if modify_sheet("status_hantar", _sahkan):
                    flash("success", f"✅ {label_ppd[kod_sah]} DISAHKAN!")
                    st.rerun()
        elif menu=="Pindah Data Daerah":
            st.header("🗂️ Pindah Data Lama ke Tab Setiap Daerah")
            st.info("Data dalam tab lama `maklumat_sekolah`, `cadangan_sup` dan `penempatan_ppd` akan disalin ke tab setiap daerah, contohnya `cadangan_sup_BK`. Tab lama TIDAK dipadam atau diubah (jadi ada salinan keselamatan). Selamat dijalankan berulang kali - baris yang dah ada akan dilangkau.")
            st.caption("Tab daerah: " + ", ".join(f"{k} ({n})" for _, _, n, k in PPD_LIST))
            st.warning("Proses ini mengambil beberapa minit (ada jeda untuk elak had kuota Google). Jangan tutup halaman sehingga jadual keputusan keluar.")
            sahkan_pindah = st.checkbox("Saya faham, teruskan pemindahan", key="sahkan_pindah")
            if st.button("🚚 Mulakan Pemindahan", use_container_width=True, type="primary", disabled=not sahkan_pindah):
                with st.spinner("Memindahkan data ikut daerah... (beberapa minit)"):
                    hasil_pindah = pecah_data_lama(mapping_df)
                st.dataframe(pd.DataFrame(hasil_pindah), use_container_width=True, hide_index=True)
                if any(str(h["STATUS"]).startswith("GAGAL") or str(h["STATUS"]).startswith("Gagal") for h in hasil_pindah):
                    st.warning("Sebahagian gagal (biasanya had kuota Google). Tunggu seminit dan tekan Mulakan semula - yang dah siap akan dilangkau.")
                else:
                    st.success("✅ Selesai. App kini baca/tulis ikut tab daerah.")
        else:
            st.header("📄 Jana Surat")
            st.info("Fungsi jana surat belum dibina (templat surat belum ditetapkan). Buat masa ini, muat turun senarai penempatan dalam CSV.")
            penempatan_all = read_semua_daerah("penempatan_ppd")
            if penempatan_all.empty:
                st.warning("Belum ada data penempatan.")
            else:
                st.download_button("⬇️ Muat turun penempatan (CSV)", data=penempatan_all.to_csv(index=False).encode("utf-8-sig"), file_name="penempatan_ppd.csv", mime="text/csv", use_container_width=True)
