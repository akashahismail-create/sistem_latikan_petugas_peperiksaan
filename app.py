"""
VERSION V37 - SERAGAM WARNA BIRU PEKAT & PUTIH SAHAJA (tajuk besar/kecil, menu, sub menu, SUP/PPD/JPN)
  - Logik / fungsi / pangkalan data TIDAK diubah (hanya warna)
VERSION V36 - FLYOUT SUB MENU UNTUK SEMUA (SUP / PPD / JPN) - BUTANG PETAK BIRU, TULISAN PUTIH
  - Menu utama & sub menu = butang petak biru/tulisan putih (butang aktif biru tua + jalur kuning)
  - Menu yang ada banyak bahagian/tab sekarang papar satu bahagian sahaja ikut pilihan flyout
  - Logik / fungsi / query pangkalan data TIDAK diubah (hanya cara paparan)
VERSION BARU - APP_33 - SISTEM LANTIKAN PETUGAS SPM 2026 - JPN TEMPLATE + ZIP PUKAL + SEKOLAH ASAL
Tarikh: 2026-10-23 23:59 - UPGRADE dari app_32.py LOCKED VERSION
Status: NEW FEATURE - TEMPLATE JPN SELARAS + ZIP + HANTAR SEKOLAH ASAL

UPGRADE V33:
1. ✅ Template surat lantikan ambil dari function JPN surat_templates_jpn (get_jpn_template_for_jawatan + render_jpn_template_html)
   - PPD punya akan diganti dengan template JPN jika JPN sudah cipta
   - Guna placeholder {{NAMA}}, {{IC}}, {{JAWATAN}}, {{SEKOLAH_ASAL}}, {{PUSAT}}, {{NO_SURAT}}, {{PPD}}, {{TARIKH}}
2. ✅ Bila PPD Jana Surat - keluar 2 button terus: PDF Kolektif (Pukal) + ZIP Individu Pukal (1000 PDF dalam 1 ZIP)
   - Guna create_zip_pukal_dari_JPN + generate_surat_kolektif_pdf_bytes_JPN
3. ✅ Surat yang dijana auto sampai ke sekolah asal petugas
   - Function hantar_surat_ke_sekolah_asal_bulk() update status SURAT_SAMPAI_SEKOLAH_ASAL
   - SUP boleh nampak di dashboard tab Surat Sampai Sekolah Asal
4. ✅ Semua tab (Keseluruhan, Ikut Pusat, Ikut Sekolah Asal) upgrade guna Template JPN + ZIP

BASE: app_32.py LOCKED VERSION OK
"""

import streamlit as st
import pandas as pd
from supabase import create_client
from io import BytesIO
import datetime
import math
import json
import re
import logging

_log = logging.getLogger("spm2026")

# ================= V38 - PILIHAN TAHUN (2026 - 2030) =================
TAHUN_PILIHAN = [2026, 2027, 2028, 2029, 2030]
# Jadual yang datanya berasingan ikut tahun (lajur `tahun` perlu wujud - lihat SQL di JPN > Admin > Urus Tahun)
TAHUN_TABLES = {"cadangan_sup", "guru_master", "pusat_master", "bilik_kebal_master", "surat_hantar_sekolah_asal"}

def default_tahun():
    y = datetime.date.today().year
    if y in TAHUN_PILIHAN:
        return y
    return TAHUN_PILIHAN[0] if y < TAHUN_PILIHAN[0] else TAHUN_PILIHAN[-1]

def tahun_aktif():
    """Tahun peperiksaan yang sedang dipilih pengguna (default: tahun semasa dalam julat pilihan)."""
    try:
        t = int(st.session_state.get("_tahun", default_tahun()))
        return t if t in TAHUN_PILIHAN else default_tahun()
    except Exception:
        return default_tahun()

def reset_sesi_kekal_tahun():
    """Log keluar: kosongkan sesi tetapi kekalkan pilihan tahun."""
    t = st.session_state.get("_tahun")
    st.session_state.clear()
    if t:
        st.session_state["_tahun"] = t
# ================= END V38 CORE =================

# ================= CONFIGURATION =================
st.set_page_config(page_title="Pelantikan SPM Selangor", layout="wide", page_icon="📚", initial_sidebar_state="collapsed")


# ===== HIDE FORK & GITHUB CAT BUTTON (PPD MINTA BUANG) =====
def hide_fork_github():
    try:
        import streamlit as st
        st.markdown("""
        <style>
        /* Hide Fork button and GitHub cat */
        header {visibility: hidden !important;}
        header * {visibility: hidden !important;}
        [data-testid="stHeader"] {display: none !important; visibility: hidden !important;}
        [data-testid="stToolbar"] {display: none !important;}
        [data-testid="stDecoration"] {display: none !important;}
        .stAppDeployButton {display: none !important; visibility: hidden !important;}
        /* Hide GitHub icon / Fork */
        a[href*="github"] {display: none !important;}
        button[kind="header"] {display: none !important;}
        /* Hide top right menu - Fork, Share etc */
        #MainMenu {visibility: hidden !important;}
        footer {visibility: hidden !important;}
        /* Extra: hide any element containing Fork text */
        div:has(> button:has-text("Fork")) {display: none !important;}

        /* ===== TAMBAHAN HIDE FORK GITHUB - CONFIRM HILANG ===== */
        header[data-testid="stHeader"] {display: none !important;}
        .viewerBadge_container__1QSob {display: none !important;}
        .styles_viewerBadge__1yB5_ {display: none !important;}
        a.viewerBadge_link__1S137 {display: none !important;}
        /* Streamlit Cloud Fork button */
        [data-testid="stAppViewContainer"] > header {display: none !important;}
        iframe[title="streamlitApp"] {display: none !important;}

        </style>
        """, unsafe_allow_html=True)
    except:
        pass

try:
    hide_fork_github()
except:
    pass

# ================= TEMA CANTIK =================
def apply_pretty_theme():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"], .stApp { font-family: 'Inter', 'Segoe UI', Arial, sans-serif !important; }
    .stApp { background: linear-gradient(180deg, #eef3fb 0%, #f8fafd 40%, #ffffff 100%); }
    .block-container { padding-top: 1.6rem !important; padding-bottom: 3rem !important; max-width: 1400px; }

    h1, h2, h3, h4 { color: #0d47a1; letter-spacing: -0.3px; font-weight: 700 !important; }

    /* Butang */
    .stButton > button, .stDownloadButton > button {
        border-radius: 12px !important; font-weight: 600 !important;
        border: 1px solid #cfd8e8 !important; transition: all .18s ease !important;
        box-shadow: 0 1px 2px rgba(13,71,161,.06);
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        transform: translateY(-1px); box-shadow: 0 6px 16px rgba(13,71,161,.18) !important;
        border-color: #1565c0 !important;
    }
    .stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
        background: linear-gradient(135deg, #1565c0 0%, #0d47a1 100%) !important;
        color: #fff !important; border: none !important;
    }

    /* Tab */
    .stTabs [data-baseweb="tab-list"] { gap: 6px; background: #e8eef8; padding: 6px; border-radius: 14px; }
    .stTabs [data-baseweb="tab"] { border-radius: 10px; padding: 8px 18px; font-weight: 600; color: #0d47a1; }
    .stTabs [aria-selected="true"] { background: #ffffff !important; color: #0d47a1 !important; box-shadow: 0 2px 8px rgba(13,71,161,.15); }
    .stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }

    /* Kad metrik */
    [data-testid="stMetric"] {
        background: #ffffff; border: 1px solid #e1e8f5; border-radius: 16px;
        padding: 14px 18px; box-shadow: 0 2px 10px rgba(13,71,161,.07);
    }
    [data-testid="stMetricValue"] { color: #0d47a1; font-weight: 800; }
    [data-testid="stMetricLabel"] { color: #0d47a1; font-weight: 600; }

    /* Container bersempadan, expander, jadual */
    [data-testid="stVerticalBlockBorderWrapper"] { border-radius: 16px !important; }
    [data-testid="stExpander"] { border: 1px solid #e1e8f5 !important; border-radius: 14px !important; background: #fff; overflow: hidden; }
    [data-testid="stDataFrame"] { border-radius: 14px; overflow: hidden; border: 1px solid #e1e8f5; }

    /* Input */
    .stTextInput input, .stNumberInput input, .stTextArea textarea, [data-baseweb="select"] > div { border-radius: 10px !important; }

    /* Alert */
    [data-testid="stAlert"] { border-radius: 12px; }

    /* Sidebar */
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #0d47a1 0%, #1565c0 100%); }
    [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] label, [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] h4, [data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: #ffffff !important; }
    [data-testid="stSidebar"] .stButton > button { background: rgba(255,255,255,.12) !important; border: 1px solid rgba(255,255,255,.25) !important; color: #fff !important; }

    /* Hero log masuk */
    .hero-login {
        background: linear-gradient(135deg, #0d47a1 0%, #1976d2 60%, #42a5f5 100%);
        color: #fff; border-radius: 22px; padding: 30px 24px; text-align: center; margin-bottom: 20px;
        box-shadow: 0 12px 32px rgba(13,71,161,.28);
    }
    .hero-login h1 { color: #fff !important; font-size: 1.7rem; margin: 0 0 6px 0; }
    .hero-login p { margin: 0; opacity: .92; font-size: .98rem; }
    .hero-stats { display: flex; justify-content: center; gap: 12px; flex-wrap: wrap; margin-top: 16px; }
    .hero-stats span { background: rgba(255,255,255,.16); border: 1px solid rgba(255,255,255,.28); padding: 6px 16px; border-radius: 999px; font-weight: 600; font-size: .9rem; }
    .app-footer { text-align: center; color: #0d47a1; font-size: .82rem; margin-top: 36px; padding-top: 14px; border-top: 1px solid #e1e8f5; }
    </style>
    """, unsafe_allow_html=True)

apply_pretty_theme()

# ================= TAMBAHAN TEMA JPN SERAGAM - BIRU TUA PUTIH - TAK UBAH FUNGSI =================
JPN_COLORS = {
    "biru_tua": "#0D47A1",
    "biru_sederhana": "#1565C0",
    "biru_muda": "#E3F2FD",
    "biru_cair": "#EEF3FB",
    "biru_border": "#CFDBF0",
    "putih": "#FFFFFF",
    "hitam_teks": "#0D47A1",
    "kelabu_teks": "#0D47A1",
    "hijau_lulus": "#0D47A1",
    "hijau_bg": "#FFFFFF",
    "kuning_pending": "#0D47A1",
    "kuning_bg": "#E3F2FD",
    "merah_gagal": "#0D47A1",
    "merah_bg": "#BBDEFB",
    "jingga_need": "#0D47A1",
}

def _apply_jpn_kad_css():
    st.markdown(f'''
    <style>
    .jpn-kad {{
        background: {JPN_COLORS["putih"]};
        border: 1.5px solid {JPN_COLORS["biru_border"]};
        border-radius: 14px;
        padding: 18px 20px;
        box-shadow: 0 2px 10px rgba(13,71,161,.06);
        margin-bottom: 16px;
    }}
    .jpn-kad-biru {{
        background: linear-gradient(135deg, {JPN_COLORS["putih"]} 0%, {JPN_COLORS["biru_cair"]} 100%);
        border: 2px solid {JPN_COLORS["biru_tua"]};
        border-radius: 14px;
        padding: 20px;
        box-shadow: 0 4px 14px rgba(13,71,161,.12);
        margin-bottom: 18px;
    }}
    .jpn-badge {{ display:inline-block; padding:4px 12px; border-radius:999px; font-weight:800; font-size:0.78rem; }}
    .jpn-badge-biru {{ background: {JPN_COLORS["biru_muda"]}; color: {JPN_COLORS["biru_tua"]}; border:1px solid {JPN_COLORS["biru_border"]}; }}
    .jpn-badge-hijau {{ background: {JPN_COLORS["hijau_bg"]}; color: {JPN_COLORS["hijau_lulus"]}; border:1px solid #FFFFFF; }}
    .jpn-badge-kuning {{ background: {JPN_COLORS["kuning_bg"]}; color: {JPN_COLORS["kuning_pending"]}; border:1px solid #E3F2FD; }}
    .jpn-no-pusat-box {{ background: {JPN_COLORS["kuning_bg"]}; border-left:4px solid {JPN_COLORS["kuning_pending"]}; padding:12px 16px; border-radius:8px; margin:12px 0; }}
    .jpn-no-pusat-label {{ font-size:0.82rem; color:{JPN_COLORS["kuning_pending"]}; font-weight:800; text-transform:uppercase; }}
    .jpn-no-pusat-value {{ font-size:1.35rem; font-weight:900; color:#0D47A1; letter-spacing:0.8px; word-spacing:6px; }}
    .surat-box img, .surat-container img, .tandatangan img {{ display:block !important; visibility:visible !important; }}
    </style>
    ''', unsafe_allow_html=True)

_apply_jpn_kad_css()

def jpn_kad_pusat(no_pusat_list_str, total_kelas, total_petugas, total_perlu, kod_sekolah=""):
    return f'''
    <div class="jpn-kad-biru">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
            <div style="font-weight:900; color:{JPN_COLORS["biru_tua"]}; font-size:1.1rem;">🏫 KEPERLUAN PENGAWAS - {kod_sekolah}</div>
            <span class="jpn-badge jpn-badge-biru">JPN SELANGOR {tahun_aktif()}</span>
        </div>
        <div class="jpn-no-pusat-box">
            <div class="jpn-no-pusat-label">📍 NO PUSAT SEKOLAH ANDA</div>
            <div class="jpn-no-pusat-value">{no_pusat_list_str}</div>
        </div>
        <div style="display:flex; gap:12px; margin-top:14px; flex-wrap:wrap;">
            <div class="jpn-kad" style="flex:1; min-width:120px; text-align:center; margin:0;">
                <div style="font-size:0.75rem; color:{JPN_COLORS["kelabu_teks"]}; font-weight:700;">JUMLAH KELAS</div>
                <div style="font-size:1.6rem; font-weight:900; color:{JPN_COLORS["biru_tua"]};">{total_kelas}</div>
            </div>
            <div class="jpn-kad" style="flex:1; min-width:120px; text-align:center; margin:0;">
                <div style="font-size:0.75rem; color:{JPN_COLORS["kelabu_teks"]}; font-weight:700;">PETUGAS DIPERLUKAN</div>
                <div style="font-size:1.6rem; font-weight:900; color:{JPN_COLORS["jingga_need"]};">{total_petugas}</div>
            </div>
            <div style="flex:1.2; min-width:150px; text-align:center; background:{JPN_COLORS["merah_bg"]}; border:2px solid {JPN_COLORS["merah_gagal"]}; border-radius:12px; padding:12px;">
                <div style="font-size:0.75rem; color:{JPN_COLORS["merah_gagal"]}; font-weight:800;">SEKOLAH WAJIB CALONKAN</div>
                <div style="font-size:1.8rem; font-weight:900; color:{JPN_COLORS["merah_gagal"]};">{total_perlu} ORANG</div>
            </div>
        </div>
    </div>
    '''

def jpn_status_meter(total_pusat, total_calon, total_kelas, total_perlu, total_dicadang, ppd_code=""):
    kekurangan = total_perlu - total_dicadang
    if total_dicadang == 0:
        color = JPN_COLORS["merah_gagal"]; bg = JPN_COLORS["merah_bg"]; icon = "🔴"; teks = f"KURANG {kekurangan}"
    elif total_dicadang < total_perlu:
        color = JPN_COLORS["kuning_pending"]; bg = JPN_COLORS["kuning_bg"]; icon = "🟡"; teks = f"KURANG {kekurangan}"
    else:
        color = JPN_COLORS["hijau_lulus"]; bg = JPN_COLORS["hijau_bg"]; icon = "🟢"; teks = "CUKUP"
    return f'''
    <div style="background:{bg}; border:2px solid {color}; border-radius:12px; padding:14px 16px; margin-bottom:18px;">
        <div style="display:flex; gap:12px; align-items:center;">
            <div style="font-size:28px;">{icon}</div>
            <div>
                <div style="font-size:0.78rem; color:{JPN_COLORS["kelabu_teks"]}; font-weight:800;">RUMUSAN PPD {ppd_code} - {teks}</div>
                <div style="font-size:1rem; font-weight:800; color:{color};">{total_pusat} Pusat | {total_calon} Calon | {total_kelas} Kelas | Perlu {total_perlu} | Dicadang {total_dicadang}</div>
            </div>
        </div>
    </div>
    '''

def jpn_panduan_warna():
    return f'''
    <div class="jpn-kad" style="background:{JPN_COLORS["hijau_bg"]}; border-left:4px solid {JPN_COLORS["hijau_lulus"]}; padding:10px 14px;">
        <b>🟢 Panduan Warna:</b>
        <span class="jpn-badge jpn-badge-hijau" style="margin-left:8px;">HIJAU</span> = Sudah hantar ke PPD / Lulus
        <span class="jpn-badge jpn-badge-kuning" style="margin-left:8px;">KUNING</span> = Baru dicadangkan, belum hantar
    </div>
    '''
# ================= END TAMBAHAN TEMA =================




# ====== LOGO JATA NEGARA - MINIMAL TAMBAH (TAK KACAU LAIN) ======
JATA_B64 = """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"""
def get_jata_img_html(width=88):
    return f'<img src="data:image/png;base64,{JATA_B64}" width="{width}" style="display:block;margin:0 auto 12px auto;filter:drop-shadow(0 2px 6px rgba(0,0,0,0.25));" />'

def show_hero_header():
    _stat = statistik_hero(tahun_aktif())
    st.markdown(f"""
    <div style="background:linear-gradient(180deg,#ffffff 0%,#eef4ff 100%);border:1px solid #d6e2f5;border-radius:24px;padding:28px 20px 22px 20px;text-align:center;box-shadow:0 10px 30px rgba(13,71,161,0.08);margin-bottom:22px;">
        {get_jata_img_html(88)}
        <div style="font-family:Poppins,Inter,sans-serif;font-weight:800;font-size:1.45rem;color:#0d47a1;line-height:1.3;">SISTEM PELANTIKAN PETUGAS<br/>PEPERIKSAAN SPM TAHUN {tahun_aktif()}</div>
        <div style="width:88px;height:4px;background:linear-gradient(90deg,#0d47a1,#1565c0);margin:14px auto 0 auto;border-radius:999px;"></div>
        <div style="font-weight:700;color:#0d47a1;font-size:0.98rem;margin-top:8px;">Jabatan Pendidikan Negeri Selangor</div>
        <div style="color:#0d47a1;font-size:0.86rem;margin-top:10px;max-width:620px;margin-left:auto;margin-right:auto;line-height:1.5;">Selamat Datang ke Portal Pelantikan — Sila pilih kategori petugas untuk log masuk. Sistem ini untuk urusan pelantikan petugas peperiksaan SPM Selangor {tahun_aktif()}.</div>
        <div style="margin-top:16px;display:flex;justify-content:center;gap:8px;flex-wrap:wrap;">
            <span style="background:#fff;border:1px solid #dbe6f8;border-radius:999px;padding:6px 14px;font-weight:700;font-size:0.82rem;color:#0d47a1;">🏫 {_stat["sekolah"]:,} Sekolah</span>
            <span style="background:#fff;border:1px solid #dbe6f8;border-radius:999px;padding:6px 14px;font-weight:700;font-size:0.82rem;color:#0d47a1;">📍 {_stat["pusat"]:,} Pusat</span>
            <span style="background:#fff;border:1px solid #dbe6f8;border-radius:999px;padding:6px 14px;font-weight:700;font-size:0.82rem;color:#0d47a1;">🎓 {_stat["calon"]:,} Calon</span>
        </div>
    </div>
    """, unsafe_allow_html=True)



SUPABASE_URL = "https://gnmaijhugkkvxejvsotk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdubWFpamh1Z2trdnhlanZzb3RrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTI0ODc4OTcsImV4cCI6MjEwODA2Mzg5N30.1YWg71nCwnQzP-KUzTdHR4rZAVCAesbKVqvVC1-X6lw"

@st.cache_resource
def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

@st.cache_data(ttl=600, show_spinner=False)
def get_jpn_templates_one():
    try:
        _supa = get_supabase()
        res = _supa.table("surat_templates_jpn").select("jawatan, template_html").execute()
        return {r["jawatan"].upper(): r["template_html"] for r in res.data} if res.data else {}
    except:
        return {}

# ===== NEW: JPN TEMPLATE FETCHER UNTUK PDF - WAJIB GUNA INI =====
@st.cache_data(ttl=300, show_spinner=False)
def get_jpn_template_for_jawatan(jawatan_str):
    """Ambil template JPN ikut jawatan (tepat dahulu; kalau tiada, padanan nama paling panjang)."""
    try:
        jw = re.sub(r"\s+", " ", str(jawatan_str or "")).upper().strip()
        if not jw:
            return None
        all_t = get_jpn_templates_one()
        norm = {re.sub(r"\s+", " ", k).upper().strip(): v for k, v in all_t.items() if v and len(v) > 30}
        if jw in norm:
            return norm[jw]
        # padanan separa: pilih nama jawatan paling panjang yang sepadan (elak "PENGAWAS" tersalah ambil "KETUA PENGAWAS")
        cands = [k for k in norm if k in jw or jw in k]
        if cands:
            return norm[max(cands, key=len)]
        return None
    except Exception:
        return None

def render_jpn_template_html(jawatan, nama, ic, sek_asal, nama_sek_asal, pusat, nama_pusat, no_surat, kod_ppd, ppd_name, tarikh, bilik_kebal=""):
    """Render template JPN dengan placeholder. Boleh guna {{NAMA}}, {{ nama }}, [NAMA] (huruf besar/kecil sama sahaja)."""
    try:
        tmpl = get_jpn_template_for_jawatan(jawatan)
        if not tmpl:
            return None
        nama = clean_nan(nama) or "Nama Guru"
        ic = clean_nan(ic)
        jawatan = clean_nan(jawatan) or "Petugas"
        sek_asal = clean_nan(sek_asal)
        nama_sek_asal = clean_nan(nama_sek_asal) or get_nama_sekolah_full(sek_asal, "")
        pusat = clean_nan(pusat)
        nama_pusat = clean_nan(nama_pusat) or pusat
        no_surat = clean_nan(no_surat)
        kod_ppd = clean_nan(kod_ppd)
        ppd_name = clean_nan(ppd_name) or kod_ppd
        tarikh = clean_nan(tarikh) or str(datetime.date.today().strftime("%d %B %Y"))
        bilik_kebal = clean_nan(bilik_kebal)

        sek_penuh = f"{sek_asal} - {nama_sek_asal}" if nama_sek_asal and nama_sek_asal.upper() != str(sek_asal).upper() else (nama_sek_asal or sek_asal)
        pusat_penuh = f"{pusat} - {nama_pusat}" if nama_pusat and nama_pusat.upper() != str(pusat).upper() else pusat

        replacements = {
            "NAMA": nama, "NAMA_GURU": nama,
            "IC": ic, "IC_GURU": ic,
            "JAWATAN": jawatan, "JAWATAN_CADANGAN": jawatan,
            "SEKOLAH_ASAL": sek_asal, "KOD_SEKOLAH_ASAL": sek_asal,
            "NAMA_SEKOLAH_ASAL": nama_sek_asal,
            "SEKOLAH_ASAL_PENUH": sek_penuh,
            "PUSAT": pusat, "KOD_PUSAT": pusat, "NO_PUSAT": pusat,
            "NAMA_PUSAT": nama_pusat,
            "PUSAT_PENUH": pusat_penuh,
            "BILIK_KEBAL": bilik_kebal, "KOD_BILIK_KEBAL": bilik_kebal,
            "NO_SURAT": no_surat,
            "PPD": kod_ppd, "KOD_PPD": kod_ppd,
            "PPD_NAME": ppd_name, "NAMA_PPD": ppd_name,
            "TARIKH": tarikh,
        }
        html = tmpl
        if tahun_aktif() != 2026:
            html = html.replace("2026", str(tahun_aktif()))   # templat lama bertulis 2026 -> ikut tahun dipilih
        replacements["TAHUN"] = str(tahun_aktif())
        for k, v in replacements.items():
            v = str(v)
            esc = re.escape(k)
            html = re.sub(r"\{\{\s*" + esc + r"\s*\}\}", lambda m, v=v: v, html, flags=re.IGNORECASE)
            html = re.sub(r"\[" + esc + r"\]", lambda m, v=v: v, html, flags=re.IGNORECASE)
        return html
    except Exception as e:
        _log.debug(f"render JPN error: {e}")
        return None


def _bungkus_html_surat(html):
    """Pastikan HTML templat lengkap (A4, UTF-8) sebelum jadi PDF / dipaparkan."""
    if "<html" in html.lower():
        return html
    return ("<html><head><meta charset='UTF-8'><style>@page { size: A4; margin: 15mm; } "
            "body { font-family: Helvetica, Arial, sans-serif; font-size: 10.5pt; }</style></head><body>"
            + html + "</body></html>")


def enjin_pdf_templat_ada():
    try:
        import xhtml2pdf  # noqa: F401
        return True
    except Exception:
        return False


def html_to_pdf_bytes(html):
    """Tukar HTML templat JPN kepada PDF (xhtml2pdf). Pulang None jika enjin tiada / gagal."""
    try:
        from xhtml2pdf import pisa
        import io
        buf = io.BytesIO()
        res = pisa.CreatePDF(src=_bungkus_html_surat(html), dest=buf, encoding="utf-8")
        if res.err:
            return None
        return buf.getvalue()
    except Exception as e:
        _log.debug(f"html_to_pdf error: {e}")
        return None

# ================= V38 - PROKSI SUPABASE IKUT TAHUN =================
@st.cache_data(ttl=60, show_spinner=False)
def lajur_tahun_sedia(nama_jadual):
    """True jika jadual sudah ada lajur `tahun` (migrasi SQL sudah dijalankan)."""
    try:
        get_supabase().table(nama_jadual).select("tahun").limit(1).execute()
        return True
    except Exception:
        return False

def status_migrasi_tahun():
    return {t: lajur_tahun_sedia(t) for t in sorted(TAHUN_TABLES)}

def _tambah_tahun_payload(data, tahun):
    if isinstance(data, list):
        return [dict(d, tahun=d.get("tahun", tahun)) if isinstance(d, dict) else d for d in data]
    if isinstance(data, dict):
        return dict(data, tahun=data.get("tahun", tahun))
    return data

class _JadualTahun:
    """Bungkus jadual: setiap select/update/delete ditapis ikut tahun, setiap insert ditambah tahun."""
    def __init__(self, jadual, tahun):
        self._t = jadual
        self._y = tahun
    def select(self, *a, **k):
        return self._t.select(*a, **k).eq("tahun", self._y)
    def update(self, *a, **k):
        return self._t.update(*a, **k).eq("tahun", self._y)
    def delete(self, *a, **k):
        return self._t.delete(*a, **k).eq("tahun", self._y)
    def insert(self, data, *a, **k):
        return self._t.insert(_tambah_tahun_payload(data, self._y), *a, **k)
    def upsert(self, data, *a, **k):
        return self._t.upsert(_tambah_tahun_payload(data, self._y), *a, **k)
    def __getattr__(self, n):
        return getattr(self._t, n)

class TahunClient:
    def __init__(self, raw):
        self._raw = raw
    def table(self, nama):
        t = self._raw.table(nama)
        if nama in TAHUN_TABLES and lajur_tahun_sedia(nama):
            return _JadualTahun(t, tahun_aktif())
        return t
    def __getattr__(self, n):
        return getattr(self._raw, n)
# ================= END PROKSI =================


# ================= V38 - PEMILIH TAHUN, RINGKASAN, SALIN DATA, SQL MIGRASI =================
SQL_MIGRASI_TAHUN = """-- JALANKAN SEKALI di Supabase > SQL Editor (data sedia ada automatik jadi tahun 2026)
""" + "\n".join(
    f"DO $$ BEGIN IF to_regclass('public.{t}') IS NOT NULL THEN\n"
    f"  EXECUTE 'ALTER TABLE public.{t} ADD COLUMN IF NOT EXISTS tahun integer NOT NULL DEFAULT 2026';\n"
    f"  EXECUTE 'CREATE INDEX IF NOT EXISTS idx_{t}_tahun ON public.{t}(tahun)';\n"
    f"END IF; END $$;"
    for t in sorted(TAHUN_TABLES)
) + """

-- Buang syarat UNIQUE lama (cth. unik pada IC / kod sahaja) supaya data yang sama boleh wujud pada tahun berbeza
DO $$
DECLARE r record;
BEGIN
  FOR r IN
    SELECT con.conname, rel.relname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    JOIN pg_namespace n ON n.oid = rel.relnamespace
    WHERE n.nspname = 'public' AND con.contype = 'u'
      AND rel.relname IN (""" + ", ".join(f"'{t}'" for t in sorted(TAHUN_TABLES)) + """)
  LOOP
    EXECUTE format('ALTER TABLE public.%I DROP CONSTRAINT %I', r.relname, r.conname);
  END LOOP;
  FOR r IN
    SELECT ic.relname AS idxname
    FROM pg_index ix
    JOIN pg_class ic ON ic.oid = ix.indexrelid
    JOIN pg_class t ON t.oid = ix.indrelid
    JOIN pg_namespace n ON n.oid = t.relnamespace
    WHERE n.nspname = 'public' AND ix.indisunique AND NOT ix.indisprimary
      AND t.relname IN (""" + ", ".join(f"'{t}'" for t in sorted(TAHUN_TABLES)) + """)
      AND NOT EXISTS (SELECT 1 FROM pg_constraint c WHERE c.conindid = ix.indexrelid)
  LOOP
    EXECUTE format('DROP INDEX public.%I', r.idxname);
  END LOOP;
END $$;
"""

@st.cache_data(ttl=60, show_spinner=False)
def ringkasan_tahun(tahun):
    """Bilangan rekod guru / pusat / cadangan bagi tahun tertentu (None = jadual belum dimigrasi)."""
    out = {}
    for t in ("guru_master", "pusat_master", "cadangan_sup"):
        try:
            if not lajur_tahun_sedia(t):
                out[t] = None
                continue
            r = get_supabase().table(t).select("id", count="exact").eq("tahun", tahun).limit(1).execute()
            out[t] = r.count or 0
        except Exception:
            out[t] = None
    return out

@st.cache_data(ttl=600, show_spinner=False)
def statistik_hero(tahun):
    """Statistik kepala portal ikut tahun (sekolah, pusat, calon)."""
    sek = pus = cal = 0
    try:
        sek = get_supabase().table("sekolah_master").select("kod_sekolah", count="exact").limit(1).execute().count or 0
    except Exception:
        pass
    try:
        q = get_supabase().table("pusat_master").select("*", count="exact")
        if lajur_tahun_sedia("pusat_master"):
            q = q.eq("tahun", tahun)
        r = q.limit(2000).execute()
        pus = r.count or 0
        for x in (r.data or []):
            try:
                cal += int(float(x.get("jumlah_calon") or x.get("calon") or 0))
            except Exception:
                pass
    except Exception:
        pass
    if tahun == 2026:
        sek = sek or 369; pus = pus or 506; cal = cal or 71064
    return {"sekolah": sek, "pusat": pus, "calon": cal}

def _on_tahun_change(key):
    try:
        st.session_state["_tahun"] = int(st.session_state[key])
    except Exception:
        pass

def render_bar_tahun(ctx="main"):
    """Butang pilih tahun (2026-2030) - dipaparkan di atas setiap page. Semua data, cadangan dan surat ikut tahun ini."""
    key = f"tahun_sel_{ctx}"
    t = tahun_aktif()
    c1, c2 = st.columns([2.4, 3.6])
    with c1:
        st.radio("📅 Tahun Peperiksaan", TAHUN_PILIHAN, index=TAHUN_PILIHAN.index(t), horizontal=True,
                 key=key, on_change=_on_tahun_change, args=(key,))
    with c2:
        stat = ringkasan_tahun(t)
        if any(v is None for v in stat.values()):
            st.warning("⚠️ Pangkalan data belum disediakan untuk pilihan tahun - semua data masih dibaca sebagai tahun 2026. "
                       "JPN: buka Admin → Urus Tahun dan jalankan SQL migrasi sekali sahaja.")
        else:
            st.caption(f"📊 Data tahun {t}: Guru **{stat['guru_master']}** · Pusat **{stat['pusat_master']}** · Cadangan SUP **{stat['cadangan_sup']}**")
            if stat["guru_master"] == 0 and stat["pusat_master"] == 0:
                st.info(f"Belum ada data tahun {t}. JPN boleh salin data guru/pusat dari tahun lain (JPN → Admin → Urus Tahun); SUP juga boleh Tambah/Import guru.")
            elif stat["cadangan_sup"] == 0:
                st.info(f"Belum ada cadangan SUP bagi tahun {t} (senarai cadangan kosong).")

def salin_data_tahun(jadual, tahun_asal, tahun_tuju, timpa=False):
    """Salin rekod satu jadual dari tahun asal ke tahun tuju (cadangan_sup TIDAK disalin - mesti kosong setiap tahun)."""
    if jadual not in ("guru_master", "pusat_master", "bilik_kebal_master"):
        return False, "Jadual tidak dibenarkan disalin."
    if tahun_asal == tahun_tuju:
        return False, "Tahun asal dan tahun tuju sama."
    raw = get_supabase()
    if not lajur_tahun_sedia(jadual):
        return False, f"{jadual}: lajur tahun belum wujud (jalankan SQL migrasi)."
    ada = raw.table(jadual).select("id", count="exact").eq("tahun", tahun_tuju).limit(1).execute().count or 0
    if ada > 0 and not timpa:
        return False, f"{jadual}: tahun {tahun_tuju} sudah ada {ada} rekod. Tandakan 'Ganti data tahun tuju' jika mahu ganti."
    if ada > 0 and timpa:
        raw.table(jadual).delete().eq("tahun", tahun_tuju).execute()
    rows, start = [], 0
    while True:
        try:
            r = raw.table(jadual).select("*").eq("tahun", tahun_asal).order("id").range(start, start + 999).execute()
        except Exception:
            r = raw.table(jadual).select("*").eq("tahun", tahun_asal).range(start, start + 999).execute()
        d = r.data or []
        rows += d
        if len(d) < 1000:
            break
        start += 1000
    out = []
    for x in rows:
        x = dict(x)
        x.pop("id", None); x.pop("created_at", None)
        if jadual == "pusat_master" and "LOG-SURAT" in str(x.get("no_pusat", "")).upper():
            continue   # nombor surat bermula semula setiap tahun
        x["tahun"] = tahun_tuju
        out.append(x)
    for i in range(0, len(out), 500):
        raw.table(jadual).insert(out[i:i + 500]).execute()
    st.cache_data.clear()
    return True, f"{jadual}: {len(out)} rekod disalin dari {tahun_asal} ke {tahun_tuju}."
# ================= END V38 UI =================


supa = TahunClient(get_supabase())

# Clear cache helper - untuk refresh button cepat
def clear_all_cache():
    st.cache_data.clear()
    st.cache_resource.clear()

# ✅ FIX: Buang trailing space dari KOD_DAERAH & PPD_MAP
KOD_DAERAH = ["BA", "BB", "BC", "BD", "BE", "BF", "BG", "BH", "BJ", "BK"]
PPD_MAP = {
    "BA": "Klang", "BB": "Kuala Langat", "BC": "Kuala Selangor",
    "BD": "Hulu Langat", "BE": "Hulu Selangor", "BF": "Sabak Bernam",
    "BG": "Gombak", "BH": "Petaling Perdana", "BJ": "Sepang", "BK": "Petaling Utama"
}

# ===== PANDUAN PASSWORD UNTUK TESTING 300 USER =====
ENABLE_TESTING_GUIDE = False
MAX_PDF_KOLEKTIF = 150
MAX_ZIP_FILES = 200

def show_testing_password_guide(df_sekolah_all):
    return


# ===== HELPER: WARNA HIJAU UNTUK GURU SUDAH HANTAR KE PPD =====
def style_nama_hijau_hantar(df_input):
    """Jika STATUS HANTAR/LULUS -> NAMA_GURU jadi hijau, belum hantar kekal biasa"""
    try:
        import pandas as pd
        # Cari column status
        status_col = None
        for cand in ["STATUS","status","Status"]:
            if cand in df_input.columns:
                status_col = cand
                break
        if status_col is None:
            return df_input

        # Buat styler
        def highlight_row(row):
            status_val = str(row.get(status_col, "") or "").upper()
            is_hantar = any(x in status_val for x in ["HANTAR","LULUS","DIHANTAR","DILULUSKAN"])
            is_baru = "DICADANGKAN" in status_val or status_val.strip()=="" or "BARU" in status_val
            styles = []
            for col in row.index:
                col_str = str(col).upper()
                if "NAMA_GURU" in col_str:
                    if is_hantar:
                        styles.append('background-color: #ffffff; color: #0d47a1; font-weight: 800; border-left: 4px solid #0d47a1;')
                    elif is_baru:
                        styles.append('background-color: #e3f2fd; color: #0d47a1; font-weight: 600;')
                    else:
                        styles.append('')
                else:
                    if is_hantar:
                        styles.append('background-color: #ffffff;')
                    elif is_baru:
                        styles.append('background-color: #e3f2fd;')
                    else:
                        styles.append('')
            return styles

        return df_input.style.apply(highlight_row, axis=1)
    except Exception as e:
        return df_input

def get_status_label(status_str):
    s = str(status_str).upper()
    if "LULUS" in s:
        return "✅ SUDAH HANTAR & LULUS PPD"
    elif "HANTAR" in s or "DIHANTAR" in s:
        return "🟢 SUDAH HANTAR KE PPD"
    else:
        return "🟡 BARU DICADANGKAN (Belum Hantar)"
# ===== END HELPER =====



# ================= CSS BIRU CAIR - BACKGROUND BIRU CAIR =================
st.markdown("""
<style>
[data-testid="stSidebar"] {display: none !important;}
.stSidebar {display: none !important;}
section[data-testid="stSidebar"] {display: none !important;}

/* ===== BACKGROUND BIRU CAIR ===== */
.stApp {
    background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 50%, #e1f5fe 100%) !important;
    background-color: #e3f2fd !important;
    background-attachment: fixed !important;
}

/* Main container */
.main .block-container {
    background: transparent !important;
}

/* Metric cards - putih atas biru cair */
[data-testid="stMetric"] {
    background: #ffffff !important;
    border: 1px solid #90caf9 !important;
    border-radius: 12px !important;
    padding: 14px !important;
    box-shadow: 0 2px 8px rgba(13, 71, 161, 0.1) !important;
}
[data-testid="stMetric"] label, [data-testid="stMetric"] div {
    color: #0d47a1 !important;
}
[data-testid="stMetricValue"] {
    color: #0d47a1 !important;
    font-weight: 800 !important;
}

[data-testid="stAlert"] {
    background: #ffffff !important;
    color: #0d47a1 !important;
    border: 1px solid #90caf9 !important;
    border-radius: 10px !important;
}
[data-testid="stAlert"] p, [data-testid="stAlert"] div {
    color: #0d47a1 !important;
}

[data-testid="stDataFrame"] {
    background: white !important;
    border-radius: 10px !important;
}

/* Custom sidebar - putih atas background biru cair */
.custom-sidebar {
    background: #ffffff !important;
    border-radius: 14px;
    padding: 16px;
    border: 2px solid #1976d2 !important;
    box-shadow: 0 4px 16px rgba(13, 71, 161, 0.15);
    height: fit-content;
    position: sticky;
    top: 10px;
}
.custom-sidebar h3 {
    font-size: 20px;
    color: #0d47a1 !important;
    font-weight: 800;
    margin-bottom: 4px;
}
.custom-sidebar p, .custom-sidebar span, .custom-sidebar div {
    color: #0d47a1 !important;
}
.custom-sidebar [data-testid="stCaptionContainer"] {
    color: #0d47a1 !important;
    opacity: 1 !important;
}
.custom-sidebar [data-testid="stCaptionContainer"] p {
    color: #0d47a1 !important;
    font-weight: 700 !important;
    font-size: 13px !important;
}

.no-pusat-box {
    background: #e3f2fd !important;
    border: 2px solid #0d47a1 !important;
    border-radius: 8px;
    padding: 10px 12px;
    margin: 10px 0;
}
.no-pusat-label {
    font-size: 11px;
    color: #0d47a1 !important;
    font-weight: 700;
}
.no-pusat-value {
    font-size: 18px;
    color: #0d47a1 !important;
    font-weight: 900;
}

.ppd-table {
    background: white !important;
    color: #0d47a1 !important;
}
.ppd-table th {
    background: #0d47a1 !important;
    color: white !important;
}
.ppd-table td {
    background: white !important;
    color: #0d47a1 !important;
    border-bottom: 1px solid #e0e0e0 !important;
}

.badge-merah, .badge-kuning, .badge-hijau {
    font-weight: 800 !important;
}
.badge-merah {background: #0d47a1 !important; border: 2px solid #0d47a1 !important; color: #ffffff !important;}
.badge-kuning {background: #bbdefb !important; border: 2px solid #0d47a1 !important; color: #0d47a1 !important;}
.badge-hijau {background: #ffffff !important; border: 2px solid #0d47a1 !important; color: #0d47a1 !important;}

[data-testid="stRadio"] label {
    color: #0d47a1 !important;
    font-weight: 600 !important;
}

.stButton button {
    font-weight: 700 !important;
}

[data-testid="stTabs"] button {
    color: #0d47a1 !important;
    font-weight: 600 !important;
}

h1, h2, h3, h4, h5, h6 {
    color: #0d47a1 !important;
}

[data-testid="stCaptionContainer"] p {
    color: #0d47a1 !important;
    font-weight: 600 !important;
    opacity: 1 !important;
}

label {
    color: #0d47a1 !important;
    font-weight: 600 !important;
}

/* Card putih atas biru cair */
div[data-testid="stHorizontalBlock"] {
    background: transparent !important;
}

/* Expander */
[data-testid="stExpander"] {
    background: #ffffff !important;
    border: 1px solid #90caf9 !important;
    border-radius: 10px !important;
}
</style>
""", unsafe_allow_html=True)


# ================= V37 - SERAGAM BIRU PEKAT & PUTIH (SUP / PPD / JPN) =================
st.markdown("""
<style>
:root { --biru-pekat:#0d47a1; --biru-gelap:#002171; --biru-sederhana:#1565c0; --biru-cair:#e3f2fd; --putih:#ffffff; accent-color:#0d47a1; }

/* ---- TAJUK BESAR (header / h1 / h2): palang biru pekat, tulisan putih ---- */
.stApp h1, .stApp h2 {
    background: #0d47a1 !important; color: #ffffff !important;
    padding: 12px 18px !important; border-radius: 8px !important;
    font-size: 1.35rem !important; font-weight: 800 !important;
    margin: 6px 0 14px 0 !important; letter-spacing: 0 !important;
}
/* ---- TAJUK KECIL (subheader / h3 / h4 / h5 / h6): palang biru pekat lebih kecil ---- */
.stApp h3, .stApp h4, .stApp h5, .stApp h6 {
    background: #0d47a1 !important; color: #ffffff !important;
    padding: 8px 14px !important; border-radius: 6px !important;
    font-size: 1.02rem !important; font-weight: 700 !important;
    margin: 6px 0 10px 0 !important; letter-spacing: 0 !important;
}
.stApp h1 *, .stApp h2 *, .stApp h3 *, .stApp h4 *, .stApp h5 *, .stApp h6 * { color: #ffffff !important; }
/* tajuk di dalam kad/palang biru sedia ada: jangan bertindan */
.stApp [style*="linear-gradient"] h1, .stApp [style*="linear-gradient"] h2,
.stApp [style*="linear-gradient"] h3, .stApp [style*="linear-gradient"] h4,
.stApp [style*="background:#0d47a1"] h1, .stApp [style*="background:#0d47a1"] h2,
.stApp [style*="background:#0d47a1"] h3, .stApp [style*="background:#0d47a1"] h4,
.main-btn h3, .hero-login h1 {
    background: transparent !important; padding: 0 !important; margin: 0 0 4px 0 !important;
    color: #ffffff !important;
}
.main-btn h3 { color: #0d47a1 !important; }
.custom-sidebar h3 { margin-top: 0 !important; }

/* ---- LABEL & KAPSYEN: biru pekat (teks biasa ikut config.toml textColor) ---- */
[data-testid="stCaptionContainer"] p { color: #0d47a1 !important; }
.custom-sidebar p, .custom-sidebar span, .custom-sidebar div { color: #0d47a1 !important; }
[data-testid="stRadio"] label, [data-testid="stTabs"] button, label { color: #0d47a1 !important; }
.hero-login, .hero-login *, .hero-stats span { color: #ffffff !important; }

/* ---- TAB: biru pekat & putih ---- */
.stTabs [data-baseweb="tab-list"] { background: #0d47a1 !important; }
.stTabs [data-baseweb="tab"], .stTabs [data-baseweb="tab"] p, [data-testid="stTabs"] button { color: #ffffff !important; }
.stTabs [aria-selected="true"], .stTabs [aria-selected="true"] p { background: #ffffff !important; color: #0d47a1 !important; }

/* ---- BUTANG BIASA & MUAT TURUN: biru pekat, tulisan putih ---- */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
    background: #0d47a1 !important; color: #ffffff !important; border: 1px solid #002171 !important;
}
.stButton > button *, .stDownloadButton > button *, .stFormSubmitButton > button * { color: #ffffff !important; }
.stButton > button:hover, .stDownloadButton > button:hover { background: #1565c0 !important; }
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] { background: #002171 !important; }

/* ---- AMARAN / MAKLUMAT / BERJAYA / RALAT: putih + jalur biru ---- */
[data-testid="stAlert"] { background: #ffffff !important; border: 1px solid #0d47a1 !important; border-left: 6px solid #0d47a1 !important; }
[data-testid="stAlert"] *, [data-testid="stAlert"] svg { color: #0d47a1 !important; fill: #0d47a1 !important; }

/* ---- Metrik, delta, pill, tag, slider, progress ---- */
[data-testid="stMetricDelta"], [data-testid="stMetricDelta"] * { color: #0d47a1 !important; fill: #0d47a1 !important; }
[data-baseweb="tag"] { background: #0d47a1 !important; color: #ffffff !important; }
[data-baseweb="tag"] * { color: #ffffff !important; }
[data-testid="stProgress"] > div > div > div > div { background-color: #0d47a1 !important; }
[data-testid="stSlider"] [role="slider"] { background-color: #0d47a1 !important; }
input[type="checkbox"], input[type="radio"] { accent-color: #0d47a1 !important; }
[data-baseweb="checkbox"] > span:first-child, [data-baseweb="radio"] > div:first-child { border-color: #0d47a1 !important; }
[data-baseweb="checkbox"] input:checked + span, [data-baseweb="toggle"] input:checked + div { background-color: #0d47a1 !important; }
[data-baseweb="radio"] input:checked + div { background-color: #0d47a1 !important; border-color: #0d47a1 !important; }

/* ---- Kotak No Pusat: biru cair + sempadan biru pekat ---- */
.no-pusat-box, .jpn-no-pusat-box { background: #e3f2fd !important; border: 2px solid #0d47a1 !important; border-left-width: 6px !important; }
.no-pusat-label, .jpn-no-pusat-label, .no-pusat-value, .jpn-no-pusat-value { color: #0d47a1 !important; }
.jpn-badge-hijau { background: #ffffff !important; color: #0d47a1 !important; border: 1px solid #0d47a1 !important; }
.jpn-badge-kuning { background: #bbdefb !important; color: #0d47a1 !important; border: 1px solid #0d47a1 !important; }
</style>
""", unsafe_allow_html=True)
# ================= END V37 =================

# ================= HELPER FUNCTIONS (FORMULA & LOGIC) =================

def kira_kelas_dari_calon(jumlah_calon):
    """1 kelas = 20 calon, CEIL"""
    try:
        c = int(float(str(jumlah_calon).replace(",", "").strip() or 0))
        if c <= 0: return 0
        return math.ceil(c / 20)
    except: return 0

def kira_petugas_dari_kelas(jumlah_kelas):
    """User formula: kelas + 9 = petugas diperlukan"""
    try: return int(jumlah_kelas) + 9
    except: return 0

def kira_sekolah_perlu_calonkan(jumlah_kelas):
    """Sekolah perlu calonkan = petugas (kelas+9) + 1 KP +1 TKP +1 Penyelia = kelas+12"""
    try: return kira_petugas_dari_kelas(jumlah_kelas) + 3
    except: return 0


def clean_nan(val):
    """Bersihkan nan, None, 'nan', 'None' jadi string kosong"""
    if val is None:
        return ""
    s = str(val).strip()
    if s.lower() in ("nan", "none", "null", "nat", ""):
        return ""
    return s

def get_nama_sekolah_full(kod_sek, fallback=""):
    """Dapatkan nama penuh sekolah dari kod"""
    try:
        ks = str(kod_sek).upper().strip()
        if not ks:
            return fallback
        # Cari dalam supa sekolah_master
        try:
            res = supa.table("sekolah_master").select("nama_sekolah, kod_sekolah").eq("kod_sekolah", ks).limit(1).execute()
            if res.data:
                nm = res.data[0].get("nama_sekolah") or ""
                if nm and str(nm).lower() not in ("nan","none",""):
                    return str(nm).strip()
        except:
            pass
        # Jika fallback ada nama, guna
        if fallback and str(fallback).upper().strip() != ks:
            if str(fallback).lower() not in ("nan","none",""):
                return str(fallback).strip()
        return ks
    except:
        return fallback or str(kod_sek)

def generate_surat_html(nama, ic, jawatan, sek_asal, nama_sek_asal, pusat, nama_pusat, no_surat, kod_ppd, ppd_name, tarikh):
    """Generate surat - PPD punya akan diganti dengan template JPN jika ada (JPN selaraskan)"""
    # Bersihkan semua input dari nan
    nama = clean_nan(nama) or "Nama Guru"
    ic = clean_nan(ic)
    jawatan = clean_nan(jawatan) or "Petugas Peperiksaan"
    sek_asal = clean_nan(sek_asal)
    nama_sek_asal = clean_nan(nama_sek_asal)
    pusat = clean_nan(pusat)
    nama_pusat = clean_nan(nama_pusat)
    # FIX: jika nama_pusat kosong, cari dari pusat_master ikut NO PUSAT
    if not nama_pusat or nama_pusat.upper() == pusat.upper():
        try:
            _pmap = build_pusat_map_from_master()
            if pusat and str(pusat).upper().strip() in _pmap and _pmap[str(pusat).upper().strip()]:
                nama_pusat = _pmap[str(pusat).upper().strip()]
        except:
            pass
    no_surat = clean_nan(no_surat) or clean_nan(tarikh) or "JPN.SPP.HHJH/0001"
    kod_ppd = clean_nan(kod_ppd) or "BA"
    ppd_name = clean_nan(ppd_name) or kod_ppd

    # === V37: TEMPLAT JPN DIUTAMAKAN (baca dari jadual surat_templates_jpn) ===
    _h37 = render_jpn_template_html(jawatan, nama, ic, sek_asal, nama_sek_asal, pusat, nama_pusat, no_surat, kod_ppd, ppd_name, tarikh)
    if _h37:
        return _bungkus_html_surat(_h37)

    # === CEK TEMPLATE JPN DULU - Jika JPN dah selaraskan, guna template JPN (PPD punya diganti) ===
    try:
        # Try load from surat_templates_jpn table
        tmpl_res = supa.table("surat_templates_jpn").select("template_html").eq("jawatan", jawatan.upper().strip()).limit(1).execute()
        if tmpl_res.data and len(tmpl_res.data) > 0:
            tmpl_html = tmpl_res.data[0].get("template_html")
            if tmpl_html and len(tmpl_html) > 50:
                # Guna template JPN - ganti placeholder
                html = tmpl_html
                replacements = {
                    "NAMA": nama,
                    "IC": ic,
                    "JAWATAN": jawatan,
                    "SEKOLAH_ASAL": sek_asal,
                    "NAMA_SEKOLAH_ASAL": nama_sek_asal or get_nama_sekolah_full(sek_asal, "") if "get_nama_sekolah_full" in globals() else sek_asal,
                    "PUSAT": pusat,
                    "NAMA_PUSAT": nama_pusat or pusat,
                    "NO_SURAT": no_surat,
                    "PPD": kod_ppd,
                    "PPD_NAME": ppd_name,
                    "TARIKH": tarikh,
                    "KOD_PUSAT": pusat,
                    "KOD_PPD": kod_ppd
                }
                for k,v in replacements.items():
                    html = html.replace("{{"+k+"}}", str(v)).replace("{{ "+k+" }}", str(v)).replace("{{"+k.lower()+"}}", str(v))
                # Wrap if not html
                if "<html>" not in html.lower():
                    html = f"<html><head><meta charset='UTF-8'></head><body>{html}</body></html>"
                return html
    except Exception as e:
        # If table not exists or error, fallback to old PPD template
        pass

    try:
        # Try session state JPN templates
        if "jpn_templates" in st.session_state:
            tmpl = st.session_state.jpn_templates.get(jawatan.upper().strip()) or st.session_state.jpn_templates.get(jawatan)
            if tmpl and len(tmpl) > 50:
                html = tmpl
                for k,v in {"NAMA": nama, "IC": ic, "JAWATAN": jawatan, "SEKOLAH_ASAL": sek_asal, "PUSAT": pusat, "NO_SURAT": no_surat, "PPD": kod_ppd, "TARIKH": tarikh}.items():
                    html = html.replace("{{"+k+"}}", str(v))
                return html
    except:
        pass

    # === FALLBACK: Template lama PPD (jika JPN belum sediakan) ===
    # Dapatkan nama penuh sekolah asal - bukan sekadar kod
    if nama_sek_asal and nama_sek_asal.upper() != sek_asal.upper():
        display_sek_asal = f"{sek_asal} - {nama_sek_asal}"
    else:
        try:
            full_nama = get_nama_sekolah_full(sek_asal, nama_sek_asal)
            if full_nama.upper() != sek_asal.upper():
                display_sek_asal = f"{sek_asal} - {full_nama}"
            else:
                display_sek_asal = sek_asal
        except:
            display_sek_asal = sek_asal or "Sekolah Asal"

    if nama_pusat and nama_pusat.upper() != pusat.upper():
        display_pusat = f"{pusat} - {nama_pusat}"
    else:
        display_pusat = pusat

    html = '<html><head><meta charset="UTF-8"><title>Surat Lantikan SPM 2026</title>'.replace("2026", str(tahun_aktif()))
    html += '<style>body{font-family:Times New Roman,serif;margin:40px;color:#000;}'
    html += '.surat{border:2px solid #000;padding:30px;margin-bottom:30px;page-break-after:always;background:white;}'
    html += '.header{text-align:center;border-bottom:3px double #000;padding-bottom:15px;margin-bottom:20px;}'
    html += '.kandungan{line-height:1.6;}'
    html += 'table.info{width:100%;border-collapse:collapse;margin:15px 0;}'
    html += 'table.info td{padding:5px 10px;}'
    html += 'table.info td:first-child{width:180px;font-weight:bold;}'
    html += '.tandatangan{margin-top:60px;display:flex;justify-content:space-between;}'
    html += '</style></head><body>'
    html += '<div class="surat"><div class="header">'
    html += '<h2>JABATAN PENDIDIKAN NEGERI SELANGOR</h2>'
    html += f'<h3>PEJABAT PENDIDIKAN DAERAH {kod_ppd} - {ppd_name}</h3>'
    html += f'<p>No Surat: {no_surat} | [Template JPN Selaras - Jika ada template JPN, surat ini akan diganti]</p></div>'
    html += '<div class="kandungan">'
    html += f'<p>Tarikh: {tarikh}</p>'
    html += '<p><strong>Tuan/Puan,</strong></p>'
    html += f'<p><strong>PELANTIKAN SEBAGAI {jawatan.upper()} PEPERIKSAAN SPM TAHUN {tahun_aktif()}</strong></p>'
    html += '<p>Dengan hormatnya saya merujuk kepada perkara di atas.</p>'
    html += '<p>2. Sukacita dimaklumkan bahawa tuan/puan telah dilantik sebagai petugas peperiksaan SPM 2026 seperti butiran berikut:</p>'.replace("2026", str(tahun_aktif()))
    html += '<table class="info">'
    html += f'<tr><td>Nama</td><td>: {nama}</td></tr>'
    html += f'<tr><td>No. IC</td><td>: {ic}</td></tr>'
    html += f'<tr><td>Jawatan</td><td>: {jawatan}</td></tr>'
    html += f'<tr><td>Sekolah Asal</td><td>: {display_sek_asal}</td></tr>'
    html += f'<tr><td>Pusat Ditugaskan</td><td>: {display_pusat}</td></tr>'
    html += f'<tr><td>No Surat Lantikan</td><td>: {no_surat}</td></tr>'
    html += '</table>'
    html += '<p>3. Tuan/puan dikehendaki hadir bertugas di pusat peperiksaan yang telah ditetapkan mengikut jadual yang akan dimaklumkan kemudian.</p>'
    html += '<p>4. Kerjasama dan komitmen tuan/puan dalam menjayakan peperiksaan SPM 2026 amatlah dihargai dan didahului dengan ucapan terima kasih.</p>'.replace("2026", str(tahun_aktif()))
    html += '<p>Sekian.</p>'
    html += '<div class="footer"><p><strong>MALAYSIA MADANI</strong><br><strong>BERKHIDMAT UNTUK NEGARA</strong></p>'
    html += '<div class="tandatangan"><div><p>Yang benar,</p><br><br><br>'
    html += f'<p>_________________________<br><strong>Pegawai Pendidikan Daerah<br>PPD {kod_ppd} - {ppd_name}</strong></p></div>'
    html += '<div style="text-align:right;"><p>b.p Pengarah Pendidikan<br>Jabatan Pendidikan Negeri Selangor</p></div></div></div></div></body></html>'
    return html




def generate_surat_pdf_bytes(nama, ic, jawatan, sek_asal, nama_sek_asal, pusat, nama_pusat, no_surat, kod_ppd, ppd_name, tarikh, no_rujukan=""):
    """Generate surat lantikan as PDF bytes - untuk download PDF - FIX nan & sekolah asal"""
    # Bersihkan
    try:
        nama = clean_nan(nama) or "Nama Guru"
        ic = clean_nan(ic)
        jawatan = clean_nan(jawatan) or "Petugas Peperiksaan"
        sek_asal = clean_nan(sek_asal)
        nama_sek_asal = clean_nan(nama_sek_asal)
        pusat = clean_nan(pusat)
        nama_pusat = clean_nan(nama_pusat)
        no_surat = clean_nan(no_surat) or "JPN.SPP.HHJH/0001"
        kod_ppd = clean_nan(kod_ppd) or "BA"
        ppd_name = clean_nan(ppd_name) or kod_ppd
        tarikh = clean_nan(tarikh) or str(datetime.date.today())

        # Nama penuh sekolah
        if nama_sek_asal and nama_sek_asal.upper() != sek_asal.upper():
            display_sek_asal = f"{sek_asal} - {nama_sek_asal}"
        else:
            try:
                full_nama = get_nama_sekolah_full(sek_asal, nama_sek_asal)
                display_sek_asal = full_nama if full_nama.upper() != sek_asal.upper() else f"{sek_asal} - {full_nama}" if full_nama else sek_asal
            except:
                display_sek_asal = sek_asal

        display_pusat = f"{pusat} - {nama_pusat}" if nama_pusat and nama_pusat.upper() != pusat.upper() else pusat
    except:
        display_sek_asal = sek_asal
        display_pusat = pusat

    # ===== V37: templat JPN diutamakan =====
    try:
        _h37 = render_jpn_template_html(jawatan, nama, ic, sek_asal, nama_sek_asal, pusat, nama_pusat, no_surat, kod_ppd, ppd_name, tarikh)
        if _h37:
            _pdf37 = html_to_pdf_bytes(_h37)
            if _pdf37:
                return _pdf37
    except Exception:
        pass

    # Cuba dengan reportlab
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        import io

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm, topMargin=15*mm, bottomMargin=15*mm)

        styles = getSampleStyleSheet()
        style_title = ParagraphStyle('TitleCustom', parent=styles['Heading1'], fontSize=14, alignment=1, spaceAfter=6)
        style_heading = ParagraphStyle('HeadingCustom', parent=styles['Heading2'], fontSize=12, alignment=1, spaceAfter=4)
        style_normal = ParagraphStyle('NormalCustom', parent=styles['Normal'], fontSize=10, leading=14, spaceAfter=4)

        story = []
        story.append(Paragraph("JABATAN PENDIDIKAN NEGERI SELANGOR", style_title))
        story.append(Paragraph(f"PEJABAT PENDIDIKAN DAERAH {ppd_name.upper() or kod_ppd}", style_heading))
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"<b>SURAT LANTIKAN PETUGAS PEPERIKSAAN SPM {tahun_aktif()}</b>", style_heading))
        story.append(Spacer(1, 8))
        story.append(Paragraph(f"<b>No Rujukan: {no_surat}</b>", style_normal))
        story.append(Paragraph(f"Tarikh: {tarikh}", style_normal))
        story.append(Spacer(1, 8))

        isi = f"""
        <b>Tuan/Puan {nama} ({ic})</b><br/>
        {jawatan}<br/>
        {display_sek_asal}<br/><br/>
        Tuan/Puan,<br/><br/>
        <b>PELANTIKAN SEBAGAI {jawatan.upper()} PEPERIKSAAN SPM {tahun_aktif()}</b><br/><br/>
        Dengan hormatnya dimaklumkan bahawa tuan/puan telah dilantik sebagai <b>{jawatan}</b> bagi Peperiksaan SPM Tahun {tahun_aktif()}.<br/><br/>
        <b>Butiran Penempatan:</b><br/>
        - Sekolah Asal: {display_sek_asal}<br/>
        - Pusat Peperiksaan Ditugaskan: {display_pusat}<br/>
        - No Surat Lantikan: {no_surat}<br/>
        - Kod PPD: {kod_ppd} - {ppd_name}<br/><br/>
        Tuan/puan dikehendaki melapor diri di pusat peperiksaan yang ditetapkan pada tarikh dan masa yang akan dimaklumkan kelak.<br/><br/>
        Kerjasama tuan/puan amatlah dihargai dan didahului dengan ucapan terima kasih.<br/><br/>
        Sekian.<br/><br/>
        <b>"BERKHIDMAT UNTUK NEGARA"</b><br/><br/>
        Saya yang menjalankan amanah,<br/><br/><br/>
        <b>PEGAWAI PENDIDIKAN DAERAH</b><br/>
        {ppd_name}<br/>
        PPD {kod_ppd}<br/>
        """
        story.append(Paragraph(isi, style_normal))
        story.append(Spacer(1, 12))

        data_footer = [
            [f"No Surat: {no_surat}", f"Pusat: {display_pusat}"],
            [f"Sekolah Asal: {display_sek_asal}", f"Jawatan: {jawatan}"]
        ]
        t = Table(data_footer, colWidths=[85*mm, 85*mm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f5f5f5')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ]))
        story.append(t)

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
    except Exception as e:
        # Fallback simple canvas
        try:
            import io
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=A4)
            c.setFont("Helvetica-Bold", 14)
            c.drawString(50, 800, f"SURAT LANTIKAN SPM {tahun_aktif()} - {kod_ppd}")
            c.setFont("Helvetica", 10)
            y = 780
            lines = [
                f"No Surat: {no_surat}",
                f"Nama: {nama}",
                f"IC: {ic}",
                f"Jawatan: {jawatan}",
                f"Sekolah Asal: {display_sek_asal}",
                f"Pusat Tugas: {display_pusat}",
                f"Tarikh: {tarikh}",
                f"PPD: {kod_ppd} - {ppd_name}",
                "",
                "Tuan/Puan telah dilantik sebagai petugas peperiksaan SPM 2026.".replace("2026", str(tahun_aktif())),
                f"Sila lapor diri di pusat {pusat}.",
            ]
            for line in lines:
                c.drawString(50, y, line[:100])
                y -= 20
                if y < 50:
                    c.showPage()
                    y = 800
            c.save()
            return buffer.getvalue()
        except Exception as e2:
            # Ultimate fallback: return HTML as bytes with pdf mime (still downloadable)
            try:
                html_fallback = generate_surat_html(nama, ic, jawatan, sek_asal, nama_sek_asal, pusat, nama_pusat, no_surat, kod_ppd, ppd_name, tarikh)
                return html_fallback.encode('utf-8')
            except:
                return None


def generate_surat_kolektif_pdf_bytes(surat_list, kod_ppd, ppd_name, title="SURAT LANTIKAN KESELURUHAN"):
    """Generate kolektif PDF - V37: gabung surat individu ikut templat JPN; jika gagal guna ringkasan lama"""
    try:
        _kol = generate_surat_kolektif_pdf_bytes_JPN(surat_list, kod_ppd, ppd_name, title_prefix=title)
        if _kol:
            return _kol
    except Exception:
        pass
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.lib import colors
        import io
        from datetime import date

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=15*mm, leftMargin=15*mm, topMargin=10*mm, bottomMargin=10*mm)
        styles = getSampleStyleSheet()
        style_title = ParagraphStyle('TitleCustom', parent=styles['Heading1'], fontSize=13, alignment=1, spaceAfter=6, leading=14)
        style_heading = ParagraphStyle('HeadingCustom', parent=styles['Heading2'], fontSize=11, alignment=1, spaceAfter=6)
        style_normal = ParagraphStyle('NormalCustom', parent=styles['Normal'], fontSize=9, leading=12, spaceAfter=4)
        style_ruj = ParagraphStyle('RujCustom', parent=styles['Normal'], fontSize=9, alignment=2, leading=11)
        style_header = ParagraphStyle('HeaderCustom', parent=styles['Normal'], fontSize=10, leading=12)

        story = []

        # HEADER RASMI - Logo tepi kiri effect
        header_text = """<b>KEMENTERIAN PENDIDIKAN MALAYSIA</b><br/>JABATAN PENDIDIKAN NEGERI SELANGOR<br/><font size=8>Persiaran Tengku Ampuan Rahimah, Seksyen 20, 40300 Shah Alam</font>"""
        story.append(Paragraph(header_text, style_header))
        story.append(Paragraph("<hr/>", style_normal))

        # Ruj Kanan = No Surat
        no_surat_kolektif = surat_list[0].get('no_surat') if surat_list and len(surat_list)>0 else f"JPN.SPP.HHJH/PPD.{kod_ppd}/0001"
        tarikh_str = date.today().strftime('%d %B %Y')
        ruj_html = f"""<font size=9>Ruj. Kami: {no_surat_kolektif}<br/>Tarikh: {tarikh_str}</font>"""
        story.append(Paragraph(ruj_html, style_ruj))
        story.append(Spacer(1, 8))

        story.append(Paragraph(f"<b>{title}</b>", style_title))
        story.append(Paragraph(f"PPD {kod_ppd} - {ppd_name} - {len(surat_list)} Guru", style_heading))
        story.append(Spacer(1, 8))

        for idx, s in enumerate(surat_list, start=1):
            nama = s.get('nama','') or s.get('NAMA','') or s.get('NAMA GURU','')
            ic = s.get('ic','') or s.get('IC','')
            jawatan = s.get('jawatan') or s.get('JAWATAN') or ''
            sek_asal = s.get('sekolah_asal') or s.get('SEKOLAH ASAL') or ''
            nama_sek_asal = s.get('nama_sekolah_asal') or s.get('NAMA SEKOLAH ASAL') or ''
            pusat = s.get('pusat') or s.get('PUSAT') or ''
            no_surat = s.get('no_surat') or s.get('NO SURAT') or s.get('NO SURAT BARU') or ''
            nama_pusat = s.get('nama_pusat') or s.get('NAMA PUSAT') or ''
            bilik_kebal = s.get('bilik_kebal') or s.get('BILIK KEBAL') or ''
            sekolah_asal_full = f"{sek_asal} - {nama_sek_asal}" if nama_sek_asal else sek_asal

            isi = f"""
            <b>{idx}. {nama} ({ic}) - {jawatan}</b><br/>
            <font size=8>
            No Surat: <b>{no_surat}</b> | Sekolah Asal: {sekolah_asal_full}<br/>
            Pusat: {pusat} - {nama_pusat} | Bilik Kebal: {bilik_kebal}<br/>
            Tuan/Puan telah dilantik sebagai <b>{jawatan}</b> SPM {tahun_aktif()} di pusat {pusat}. Sila lapor diri mengikut arahan.<br/>
            </font>
            """
            story.append(Paragraph(isi, style_normal))
            story.append(Spacer(1, 6))
            if idx % 5 == 0 and idx < len(surat_list):
                story.append(PageBreak())
                story.append(Paragraph(header_text, style_header))
                story.append(Paragraph("<hr/>", style_normal))
                story.append(Paragraph(ruj_html, style_ruj))
                story.append(Spacer(1, 8))

        story.append(Spacer(1, 12))
        story.append(Paragraph("<b>MALAYSIA MADANI - BERKHIDMAT UNTUK NEGARA</b><br/><br/>(DATIN WAN NOR ASHIKIN BINTI ABU KASSIM)<br/>Pengarah Pendidikan, JPN Selangor", style_normal))

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
    except Exception as e:
        _log.debug(f"Error kolektif: {e}")
        return None




def generate_surat_penyelia_kawasan_html(nama, ic, sek_asal, nama_sek_asal, telefon, kod_bilik_kebal, nama_bilik_kebal, alamat_bilik_kebal, pusat_jagaan_list, no_surat, kod_ppd, ppd_name, tarikh):
    """Surat khas untuk Penyelia Kawasan yang ditempatkan ke Bilik Kebal"""
    # V34: Ensure pusat_jagaan_list is not empty, fallback to kod_pusat if needed
    if not pusat_jagaan_list:
        try:
            # Try from data JSON
            if isinstance(data_dict, dict):
                pusat_jagaan_list = data_dict.get("pusat_jagaan") or data_dict.get("pusat_jagaan_str","").split(",") if isinstance(data_dict.get("pusat_jagaan_str"), str) else []
        except:
            pass
    pusat_jagaan_str = ", ".join(pusat_jagaan_list) if isinstance(pusat_jagaan_list, list) else str(pusat_jagaan_list)
    pusat_jagaan_table = ""
    if isinstance(pusat_jagaan_list, list) and pusat_jagaan_list:
        for idx, p in enumerate(pusat_jagaan_list, 1):
            pusat_jagaan_table += f"<tr><td>{idx}</td><td>{p}</td></tr>"
    else:
        pusat_jagaan_table = f"<tr><td>1</td><td>{pusat_jagaan_str}</td></tr>"

    html = '<html><head><meta charset="UTF-8"><title>Surat Lantikan Penyelia Kawasan SPM 2026</title>'.replace("2026", str(tahun_aktif()))
    html += '<style>body{font-family:Times New Roman,serif;margin:40px;color:#000;}'
    html += '.surat{border:3px double #0d47a1;padding:30px;margin-bottom:30px;background:white;page-break-after:always;}'
    html += '.header{text-align:center;border-bottom:3px double #0d47a1;padding-bottom:15px;margin-bottom:20px;}'
    html += '.header h2{color:#0d47a1;margin:5px 0;}'
    html += '.kandungan{line-height:1.7;font-size:14px;}'
    html += 'table.info{width:100%;border-collapse:collapse;margin:15px 0;}'
    html += 'table.info td{padding:8px 12px;border:1px solid #ddd;}'
    html += 'table.info td:first-child{width:200px;font-weight:bold;background:#e3f2fd;}'
    html += 'table.pusat{width:100%;border-collapse:collapse;margin:10px 0;}'
    html += 'table.pusat th, table.pusat td{border:1px solid #0d47a1;padding:8px;text-align:left;}'
    html += 'table.pusat th{background:#0d47a1;color:white;}'
    html += '.tandatangan{margin-top:60px;display:flex;justify-content:space-between;}'
    html += '.penting{background:#e3f2fd;border-left:5px solid #0d47a1;padding:12px;margin:15px 0;}'
    html += '</style></head><body>'
    html += '<div class="surat"><div class="header">'
    html += '<h2>JABATAN PENDIDIKAN NEGERI SELANGOR</h2>'
    html += f'<h3>PEJABAT PENDIDIKAN DAERAH {kod_ppd} - {ppd_name}</h3>'
    html += '<h3 style="color:#0d47a1;">SURAT LANTIKAN PENYELIA KAWASAN SPM 2026</h3>'.replace("2026", str(tahun_aktif()))
    html += f'<p><strong>No Rujukan: {no_surat}</strong> | Tarikh: {tarikh}</p></div>'
    html += '<div class="kandungan">'
    html += '<p><strong>Tuan/Puan,</strong></p>'
    html += '<p><strong>PELANTIKAN SEBAGAI PENYELIA KAWASAN PEPERIKSAAN SPM TAHUN 2026 - PENEMPATAN DI BILIK KEBAL</strong></p>'.replace("2026", str(tahun_aktif()))
    html += '<p>Dengan hormatnya saya merujuk kepada perkara di atas dan sukacita dimaklumkan bahawa tuan/puan telah dilantik sebagai <strong>Penyelia Kawasan SPM 2026</strong> dengan butiran seperti berikut:</p>'.replace("2026", str(tahun_aktif()))
    html += '<table class="info">'
    html += f'<tr><td>Nama Penyelia Kawasan</td><td>{nama}</td></tr>'
    html += f'<tr><td>No. Kad Pengenalan</td><td>{ic}</td></tr>'
    html += f'<tr><td>Sekolah Asal</td><td>{sek_asal} - {nama_sek_asal}</td></tr>'
    html += f'<tr><td>No. Telefon</td><td>{telefon}</td></tr>'
    html += f'<tr><td>Jawatan Lantikan</td><td><strong>PENYELIA KAWASAN</strong></td></tr>'
    html += f'<tr><td>Dilantik di Bilik Kebal</td><td><strong>{kod_bilik_kebal} - {nama_bilik_kebal}</strong><br><small>{alamat_bilik_kebal}</small></td></tr>'
    html += f'<tr><td>No Surat Lantikan</td><td>{no_surat}</td></tr>'
    html += f'<tr><td>PPD</td><td>{kod_ppd} - {ppd_name}</td></tr>'
    html += '</table>'

    html += '<div class="penting">'
    html += '<strong>BERTANGGUNGJAWAB ATAS PUSAT-PUSAT PEPERIKSAAN:</strong>'
    html += '<p>Penyelia Kawasan ini bertanggungjawab memantau dan menyelia pusat-pusat peperiksaan berikut di bawah Bilik Kebal yang berkenaan:</p>'
    html += '</div>'

    html += '<table class="pusat">'
    html += '<tr><th>Bil</th><th>Kod Pusat / Pusat Peperiksaan Di Bawah Jagaan</th></tr>'
    html += pusat_jagaan_table
    html += '</table>'

    html += f'<p><strong>Jumlah Pusat Jagaan: {len(pusat_jagaan_list) if isinstance(pusat_jagaan_list, list) else 1} pusat</strong></p>'

    html += '<p>3. <strong>Tugas dan Tanggungjawab Penyelia Kawasan:</strong></p>'
    html += '<ul>'
    html += '<li>Bertanggungjawab sepenuhnya ke atas keselamatan dan kelancaran pengurusan kertas soalan di Bilik Kebal yang ditetapkan;</li>'
    html += f'<li>Menyelia dan memantau {len(pusat_jagaan_list) if isinstance(pusat_jagaan_list, list) else 1} pusat peperiksaan di bawah jagaan Bilik Kebal {kod_bilik_kebal};</li>'
    html += '<li>Memastikan semua prosedur keselamatan dan tatacara peperiksaan SPM dipatuhi;</li>'
    html += '<li>Melaporkan sebarang isu atau masalah kepada Pegawai Pendidikan Daerah dengan segera;</li>'
    html += '<li>Hadir bertugas mengikut jadual yang ditetapkan oleh PPD.</li>'
    html += '</ul>'

    html += '<p>4. Tuan/puan dikehendaki hadir taklimat Penyelia Kawasan yang akan dimaklumkan kemudian oleh PPD.</p>'
    html += '<p>5. Kerjasama, komitmen dan integriti tuan/puan dalam menjayakan peperiksaan SPM 2026 amatlah dihargai.</p>'.replace("2026", str(tahun_aktif()))
    html += '<p>Sekian, terima kasih.</p>'

    html += '<div class="footer"><p><strong>MALAYSIA MADANI</strong><br><strong>BERKHIDMAT UNTUK NEGARA</strong></p>'
    html += '<div class="tandatangan"><div><p>Yang benar,</p><br><br><br>'
    html += f'<p>_________________________<br><strong>Pegawai Pendidikan Daerah<br>PPD {kod_ppd} - {ppd_name}</strong><br><small>Tarikh: {tarikh}</small></p></div>'
    html += '<div style="text-align:right;"><p>b.p Pengarah Pendidikan<br>Jabatan Pendidikan Negeri Selangor<br><br><small>Salinan: Pengetua {nama_sek_asal}<br>Sekolah Asal Penyelia Kawasan</small></p></div></div></div></div></div>'
    html += '</body></html>'
    return html

def generate_surat_kolektif_html(guru_list, kod_ppd, ppd_name, tarikh, prefix):

    # guru_list is list of dicts with NAMA, IC, etc
    html = '<html><head><meta charset="UTF-8"><title>Surat Lantikan Kolektif</title>'
    html += '<style>body{font-family:Arial,sans-serif;margin:20px;} .surat{border:1px solid #ccc;padding:20px;margin:10px 0;} h2{text-align:center;}</style></head><body>'
    html += f'<h2>SURAT LANTIKAN PETUGAS SPM {tahun_aktif()} - PPD {kod_ppd}</h2>'
    html += f'<p>Tarikh: {tarikh} | Jumlah: {len(guru_list)} guru</p><hr>'
    for g in guru_list:
        html += generate_surat_html(g["NAMA GURU"], g["IC"], g["JAWATAN"], g["SEKOLAH ASAL"], g["NAMA SEKOLAH ASAL"], g["PUSAT DITEMPATKAN"], g["NAMA PUSAT DITEMPATKAN"], g["NO SURAT"], kod_ppd, ppd_name, tarikh)
    html += '</body></html>'
    return html


def safe_count(table_name):
    """Count dengan fallback kalau RLS block count exact"""
    try:
        res = supa.table(table_name).select("*", count="exact").limit(1).execute()
        if res.count is not None and res.count > 0: return res.count
        if res.data and len(res.data) > 0: return len(res.data)
        return 0
    except: return 0

def get_sekolah(kod):
    for col in ["kod_sekolah", "kod_sekolah_tuan_rumah", "KOD_SEKOLAH"]:
        try:
            res = supa.table("sekolah_master").select("*").eq(col, kod.upper()).limit(1).execute()
            if res.data:
                row = res.data[0]
                return {
                    "kod_sekolah": row.get("kod_sekolah") or row.get("KOD_SEKOLAH") or kod,
                    "nama_sekolah": row.get("nama_sekolah") or row.get("NAMA_SEKOLAH") or f"SEKOLAH {kod}",
                    "kod_ppd": row.get("kod_ppd") or row.get("KOD_PPD") or "BH",
                    "ppd": row.get("ppd") or row.get("PPD") or "Petaling Perdana",
                    "_raw": row
                }
        except: continue
    return {"kod_sekolah": kod, "nama_sekolah": f"SEKOLAH {kod}", "kod_ppd": "BH", "ppd": "Petaling Perdana"}

def get_guru_df(kod_sekolah):
    return _get_guru_df_cached(kod_sekolah, tahun_aktif())
get_guru_df.clear = _get_guru_df_cached.clear

def get_pusat_df():
    return _get_pusat_df_cached(tahun_aktif())
get_pusat_df.clear = _get_pusat_df_cached.clear

def get_cadangan_df(kod_ppd=None, kod_sekolah=None):
    return _get_cadangan_df_cached(kod_ppd, kod_sekolah, tahun_aktif())
get_cadangan_df.clear = _get_cadangan_df_cached.clear

@st.cache_data(ttl=300, show_spinner=False)
def _get_guru_df_cached(kod_sekolah, tahun=2026):
    try:
        res = None
        for col in ["kod_sekolah", "KOD_SEKOLAH", "kod_sekolah_tuan_rumah"]:
            try:
                r = supa.table("guru_master").select("*").eq(col, kod_sekolah.upper()).limit(2000).execute()
                if r.data: res=r; break
            except: continue

        if not res:
            res = supa.table("guru_master").select("*").eq("kod_sekolah", kod_sekolah.upper()).limit(2000).execute()

        rows = []
        sekolah_map_guru = {}
        try:
            res_sek = supa.table("sekolah_master").select("kod_sekolah,nama_sekolah").limit(2000).execute()
            for s in res_sek.data or []:
                k = (s.get("kod_sekolah") or s.get("KOD_SEKOLAH") or "").upper()
                n = s.get("nama_sekolah") or s.get("NAMA_SEKOLAH") or ""
                if k: sekolah_map_guru[k] = n
        except: pass

        for r in res.data or []:
            d = r.get("data") or {}
            if isinstance(d, str):
                try: d = json.loads(d)
                except: d = {}

            def _nk(x): return re.sub(r"[^A-Z0-9]", "", str(x).upper())
            _kosong_val = ("", "none", "null", "nan", "n/a", "-")
            _dn, _rn = {}, {}

            for _k, _v in d.items():
                if _v is not None and not isinstance(_v, (dict, list)) and str(_v).strip().lower() not in _kosong_val:
                    _dn.setdefault(_nk(_k), str(_v).strip())
            for _k, _v in r.items():
                if _v is not None and not isinstance(_v, (dict, list)) and str(_v).strip().lower() not in _kosong_val:
                    _rn.setdefault(_nk(_k), str(_v).strip())

            def get_val(*keys, default=""):
                for k in keys:
                    nk = _nk(k)
                    if nk in _dn: return _dn[nk]
                    if nk in _rn: return _rn[nk]
                return default

            ic_val = get_val("IC", "ic_guru", "IC_GURU", "ic", "no_ic", "NO_KP", "NO KP")
            nama_val = get_val("NAMA GURU", "nama_guru", "NAMA_GURU", "nama", "NAMA")
            jantina_val = get_val("JANTINA", "jantina", "JANTINA_GURU", "Jantina", "SEX")
            poskod_val = get_val("POSKOD_RUMAH", "poskod_rumah", "POSKOD", "poskod", "POSKOD RUMAH")
            alamat_val = get_val("ALAMAT_RUMAH", "alamat_rumah", "ALAMAT RUMAH", "alamat", "ALAMAT")
            telefon_val = get_val("TELEFON_GURU", "telefon_guru", "NO TELEFON GURU", "TELEFON", "no_telefon")
            email_val = get_val("EMAIL_GURU", "email_guru", "EMAIL GURU", "EMAIL", "email", "EMEL", "EMEL GURU", "E-MEL", "E-MAIL")
            pengalaman_val = get_val("PENGALAMAN_SPM", "pengalaman_spm", "PENGALAMAN", "pengalaman")
            jawatan_val = get_val("JAWATAN_CADANGAN", "jawatan_cadangan", "JAWATAN CADANGAN", "jawatan")
            kod_ppd_val = get_val("KOD_PPD", "kod_ppd", "kod_ppd_asal", "KOD_PPD_ASAL", "ppd", "PPD")
            kod_sek_val = get_val("KOD_SEKOLAH", "kod_sekolah", "KOD SEKOLAH", "kod_sekolah_asal", "KOD_SEKOLAH_ASAL", default=kod_sekolah)
            nama_sek_val = get_val("NAMA_SEKOLAH", "nama_sekolah", "NAMA SEKOLAH", "sekolah_asal", "NAMA_SEKOLAH_ASAL")
            no_pusat_asal_val = get_val("NO_PUSAT_ASAL", "no_pusat_asal", "NO PUSAT ASAL", "PUSAT ASAL", "pusat_asal", "KOD PUSAT ASAL", "NO_PUSAT", "KOD PUSAT")

            if not nama_sek_val or nama_sek_val == "" or nama_sek_val == kod_sek_val:
                nama_sek_val = sekolah_map_guru.get(kod_sek_val.upper(), "") or sekolah_map_guru.get(kod_sekolah.upper(), "") or kod_sek_val

            if not kod_ppd_val or kod_ppd_val == "":
                kod_ppd_val = kod_sekolah[:2] if len(kod_sekolah) >= 2 else "BA"

            if not jawatan_val or jawatan_val.strip() == "":
                jawatan_val = "Pengawas Peperiksaan"

            rows.append({
                "id": r.get("id"),
                "NAMA GURU": nama_val, "IC": ic_val, "JANTINA": jantina_val,
                "POSKOD_RUMAH": poskod_val, "ALAMAT_RUMAH": alamat_val,
                "TELEFON": telefon_val, "TELEFON_GURU": telefon_val,
                "EMAIL_GURU": email_val, "EMAIL": email_val,
                "JAWATAN CADANGAN": jawatan_val, "JAWATAN_CADANGAN": jawatan_val,
                "PENGALAMAN_SPM": pengalaman_val, "PENGALAMAN": pengalaman_val,
                "KOD_PPD": kod_ppd_val, "KOD_PPD_ASAL": kod_ppd_val,
                "KOD SEKOLAH": kod_sek_val, "KOD_SEKOLAH": kod_sek_val,
                "KOD_SEKOLAH_ASAL": kod_sek_val,
                "NAMA_SEKOLAH_ASAL": nama_sek_val, "NAMA_SEKOLAH": nama_sek_val,
                "NO_PUSAT_ASAL": no_pusat_asal_val, "ALAMAT": alamat_val,
                "data_full": d if isinstance(d, dict) else {}, "raw": r
            })
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=300, show_spinner=False)
def _get_pusat_df_cached(tahun=2026):
    try:
        res = supa.table("pusat_master").select("*").limit(2000).execute()
        df = pd.DataFrame(res.data or [])
        if not df.empty:
            df_norm = df.copy()
            if "no_pusat" in df_norm.columns: df_norm["kod_pusat_std"] = df_norm["no_pusat"]
            elif "kod_pusat" in df_norm.columns: df_norm["kod_pusat_std"] = df_norm["kod_pusat"]
            elif "NO_PUSAT" in df_norm.columns: df_norm["kod_pusat_std"] = df_norm["NO_PUSAT"]
            else: df_norm["kod_pusat_std"] = df_norm.iloc[:, 1] if len(df_norm.columns) > 1 else " "

            if "nama_pusat" in df_norm.columns: df_norm["nama_pusat_std"] = df_norm["nama_pusat"]
            elif "NAMA_PUSAT" in df_norm.columns: df_norm["nama_pusat_std"] = df_norm["NAMA_PUSAT"]
            else: df_norm["nama_pusat_std"] = df_norm.get("nama_sekolah", " ")
            return df
    except Exception as e:
        st.error(f"pusat_master error: {e}")
    return pd.DataFrame()

@st.cache_data(ttl=120, show_spinner=False)
def _get_cadangan_df_cached(kod_ppd=None, kod_sekolah=None, tahun=2026):
    try:
        # Fetch with larger limit and without strict eq first to avoid missing data due to case issues
        try:
            # Always fetch all then filter locally for robustness
            res = supa.table("cadangan_sup").select("*").limit(10000).execute()
        except:
            res = supa.table("cadangan_sup").select("*").limit(5000).execute()

        df = pd.DataFrame(res.data or [])
        if df.empty:
            return df

        # Normalize - merge data json and top-level columns
        norm_rows = []
        for _, r in df.iterrows():
            row_dict = {}
            for k, v in r.items():
                if k != 'data':
                    row_dict[k] = v
                else:
                    if isinstance(v, dict):
                        row_dict.update(v)
                    elif isinstance(v, str):
                        try:
                            parsed = json.loads(v)
                            if isinstance(parsed, dict):
                                row_dict.update(parsed)
                        except:
                            pass
            # Normalize keys to upper for consistency but keep original too
            # Ensure critical fields
            # JAWATAN - normalize various possible keys
            jaw = row_dict.get('JAWATAN_CADANGAN') or row_dict.get('jawatan_cadangan') or row_dict.get('JAWATAN') or row_dict.get('jawatan') or row_dict.get('JAWATAN CADANGAN') or ''
            jaw = str(jaw).strip()
            # Clean jawatan: remove extra spaces, normalize case for comparison but keep original display
            jaw_clean = ' '.join(jaw.split())
            row_dict['JAWATAN_CADANGAN'] = jaw_clean
            row_dict['jawatan_cadangan'] = jaw_clean
            row_dict['JAWATAN_CADANGAN_NORM'] = jaw_clean.lower()

            # KOD PPD
            kppd = row_dict.get('KOD_PPD') or row_dict.get('kod_ppd') or row_dict.get('KOD_PPD_ASAL') or row_dict.get('kod_ppd_asal') or ''
            row_dict['KOD_PPD'] = str(kppd).strip().upper()

            # KOD SEKOLAH ASAL
            ksa = row_dict.get('KOD_SEKOLAH_ASAL') or row_dict.get('kod_sekolah_asal') or row_dict.get('KOD_SEKOLAH') or row_dict.get('kod_sekolah') or row_dict.get('kod_sekolah_tuan_rumah') or ''
            row_dict['KOD_SEKOLAH_ASAL'] = str(ksa).strip().upper()

            # NAMA
            ng = row_dict.get('NAMA_GURU') or row_dict.get('nama_guru') or row_dict.get('NAMA GURU') or ''
            row_dict['NAMA_GURU'] = str(ng).strip().upper()

            # NAMA SEKOLAH ASAL - V28 FIX
            nsa = row_dict.get('NAMA_SEKOLAH_ASAL') or row_dict.get('nama_sekolah_asal') or row_dict.get('NAMA_SEKOLAH') or row_dict.get('nama_sekolah') or row_dict.get('NAMA SEKOLAH ASAL') or ''
            row_dict['NAMA_SEKOLAH_ASAL'] = str(nsa).strip().upper()
            row_dict['nama_sekolah_asal'] = str(nsa).strip()

            # IC
            ic = row_dict.get('IC_GURU') or row_dict.get('ic_guru') or row_dict.get('IC') or row_dict.get('ic') or ''
            ic = str(ic).strip()
            # Normalize IC - remove spaces
            ic = ic.replace(' ', '')
            row_dict['IC_GURU'] = ic

            # ALAMAT, TELEFON, EMAIL, POSKOD - ensure exists
            for key_lower, key_upper in [('alamat_rumah','ALAMAT_RUMAH'), ('telefon_guru','TELEFON_GURU'), ('email_guru','EMAIL_GURU'), ('poskod_rumah','POSKOD_RUMAH'), ('no_pusat_asal','NO_PUSAT_ASAL'), ('pengalaman_spm','PENGALAMAN_SPM')]:
                val = row_dict.get(key_upper) or row_dict.get(key_lower) or ''
                row_dict[key_upper] = str(val).strip()
                row_dict[key_lower] = str(val).strip()

            # Lajur `status` (top-level) ialah SUMBER SEBENAR - ia dikemas kini oleh Hantar / Jana / Lulus.
            # STATUS dalam JSON `data` hanya nilai semasa insert ("DICADANGKAN") dan tak pernah dikemas kini,
            # jadi ia tak boleh menimpa lajur `status` (punca paparan kekal "belum dihantar").
            _top = r.get('status')
            if _top is not None and not (isinstance(_top, float) and pd.isna(_top)) and str(_top).strip():
                row_dict['STATUS'] = str(_top).strip()
                row_dict['status'] = str(_top).strip()
            elif 'STATUS' not in row_dict or not row_dict['STATUS']:
                row_dict['STATUS'] = row_dict.get('status') or 'DICADANGKAN'

            # No Surat: lajur `no_surat` (top-level) ialah sumber sebenar. Nilai kosong dalam JSON `data`
            # tak boleh menimpanya (punca guru kekal "belum lulus" walaupun surat dah dijana).
            def _ns_ok(v):
                if v is None or (isinstance(v, float) and pd.isna(v)):
                    return ""
                t = str(v).strip()
                return "" if t.lower() in ("nan", "none", "null") else t
            _ns_final = _ns_ok(r.get('no_surat')) or _ns_ok(r.get('NO_SURAT')) \
                or _ns_ok(row_dict.get('no_surat')) or _ns_ok(row_dict.get('NO_SURAT')) \
                or _ns_ok(row_dict.get('surat_no')) or _ns_ok(row_dict.get('SURAT_NO')) \
                or _ns_ok(row_dict.get('no_surat_lantikan'))
            row_dict['no_surat'] = _ns_final
            row_dict['NO_SURAT'] = _ns_final

            norm_rows.append(row_dict)

        df_norm = pd.DataFrame(norm_rows)
        if df_norm.empty:
            return df_norm

        # V25 FIX: Deduplicate and keep HANTAR status prioritized over DICADANGKAN
        if 'IC_GURU' in df_norm.columns:
            # Create priority for status: LULUS=3, HANTAR=2, DICADANGKAN=1
            def status_priority(s):
                s = str(s).upper()
                if 'LULUS' in s:
                    return 5
                if any(x in s for x in ('DILANTIK', 'DIJANA', 'DITEMPATKAN', 'SURAT')):
                    return 4
                if 'HANTAR' in s:
                    return 3
                return 1
            try:
                df_norm['status_prio'] = df_norm['STATUS'].apply(status_priority)
            except:
                try:
                    df_norm['status_prio'] = df_norm['status'].apply(status_priority)
                except:
                    df_norm['status_prio'] = 1

            # Add sort key: id descending, status_prio descending
            sort_cols = ['status_prio']
            if 'id' in df_norm.columns:
                try:
                    df_norm['id_num'] = pd.to_numeric(df_norm['id'], errors='coerce')
                    sort_cols.append('id_num')
                except:
                    pass
            if 'created_at' in df_norm.columns:
                sort_cols.append('created_at')

            df_norm = df_norm.sort_values(by=sort_cols, ascending=False)
            df_norm = df_norm.drop_duplicates(subset=['IC_GURU', 'KOD_SEKOLAH_ASAL'], keep='first')
            # Clean helper columns
            for col in ['id_num', 'status_prio']:
                if col in df_norm.columns:
                    df_norm = df_norm.drop(columns=[col])

        # Filter by PPD if requested - STRICT FILTER (FIX untuk isu Sepang nampak Klang)
        if kod_ppd:
            kod_ppd_u = kod_ppd.strip().upper()
            try:
                # Step 1: Get list of sekolah kod for this PPD from sekolah_master
                kod_list = []
                try:
                    res_sek = supa.table("sekolah_master").select("kod_sekolah").eq("kod_ppd", kod_ppd_u).limit(2000).execute()
                    kod_list = [str(s.get('kod_sekolah','')).upper().strip() for s in (res_sek.data or []) if str(s.get('kod_sekolah','')).strip()]
                except:
                    kod_list = []

                # Step 2: Strict filter - only allow if KOD_PPD exact match OR KOD_SEKOLAH_ASAL in kod_list
                # NOT include empty KOD_PPD unless sekolah is in list
                if kod_list:
                    # Exact match for KOD_PPD (not contains) + sekolah in list
                    mask_ppd_exact = df_norm['KOD_PPD'].astype(str).str.upper().str.strip() == kod_ppd_u
                    mask_sek_in_list = df_norm['KOD_SEKOLAH_ASAL'].astype(str).str.upper().str.strip().isin(kod_list)
                    # Strict: only keep if either PPD matches exactly OR sekolah is in this PPD's list
                    df_norm = df_norm[mask_ppd_exact | mask_sek_in_list].copy()
                else:
                    # Fallback if sekolah_master empty - filter exact PPD only, no empty allowed
                    mask_ppd_exact = df_norm['KOD_PPD'].astype(str).str.upper().str.strip() == kod_ppd_u
                    df_norm = df_norm[mask_ppd_exact].copy()
            except Exception as e:
                # On error, try exact match only
                try:
                    kod_ppd_u = kod_ppd.strip().upper()
                    df_norm = df_norm[df_norm['KOD_PPD'].astype(str).str.upper().str.strip() == kod_ppd_u].copy()
                except:
                    pass

        if kod_sekolah:
            kod_s_u = kod_sekolah.strip().upper()
            try:
                df_norm = df_norm[df_norm['KOD_SEKOLAH_ASAL'].astype(str).str.upper() == kod_s_u]
            except:
                pass

        return df_norm
    except Exception as e:
        return pd.DataFrame()

def flash(level, msg):
    st.session_state.setdefault("_flash", []).append((level, msg))

def show_flash():
    for level, msg in st.session_state.pop("_flash", []):
        getattr(st, level)(msg)

def _id_py(x):
    if hasattr(x, "item"): x = x.item()
    if isinstance(x, float) and x.is_integer(): return int(x)
    return x

def hantar_ke_ppd(ids, kod_ppd, df_sasaran=None):
    """FIX: Hanya update STATUS, jangan sentuh nama_guru"""
    berjaya, gagal = 0, []
    ic_list = []
    if df_sasaran is not None and not df_sasaran.empty:
        try:
            if 'IC_GURU' in df_sasaran.columns:
                ic_list = df_sasaran['IC_GURU'].astype(str).str.strip().tolist()
        except:
            pass
    for i in range(0, len(ids), 100):
        kelompok = ids[i:i+100]
        payloads_to_try = [
            {"status": "HANTAR KE PPD", "status": "HANTAR KE PPD"},
            {"status": "HANTAR KE PPD"},
            {"status": "HANTAR KE PPD"},
        ]
        success = False
        last_err = ""
        for payload in payloads_to_try:
            try:
                supa.table("cadangan_sup").update(payload).in_("id", kelompok).execute()
                success = True
                break
            except Exception as e:
                last_err = str(e)
                continue
        if success:
            berjaya += len(kelompok)
        else:
            gagal.append(last_err)
    if ic_list:
        for ic_val in ic_list:
            if not ic_val or ic_val.lower() in ["nan","none",""]:
                continue
            try:
                supa.table("cadangan_sup").update({"status": "HANTAR KE PPD"}).eq("ic_guru", ic_val).execute()
            except:
                pass
    return berjaya, gagal

def simpan_penempatan_ppd(items):
    """Simpan hasil janaan ke cadangan_sup (lajur kod_pusat + status DIJANA PPD), berkelompok ikut pusat.
    items: [{"id":..., "ic":..., "pusat":...}]. Pulang (bil_berjaya, senarai_gagal)."""
    berjaya, gagal = 0, []
    ikut_pusat = {}
    for it in items:
        ikut_pusat.setdefault(str(it["pusat"]), []).append(it)
    for pusat, senarai in ikut_pusat.items():
        ids = [_id_py(i["id"]) for i in senarai if str(i.get("id") or "").strip() not in ("", "nan", "None")]
        for k in range(0, len(ids), 100):
            kelompok = ids[k:k + 100]
            try:
                supa.table("cadangan_sup").update({"kod_pusat": pusat, "status": "DIJANA PPD"}).in_("id", kelompok).execute()
                berjaya += len(kelompok)
            except Exception as e:
                gagal.append(f"{pusat}: {e}")
        for i in senarai:
            if str(i.get("id") or "").strip() in ("", "nan", "None") and i.get("ic"):
                try:
                    supa.table("cadangan_sup").update({"kod_pusat": pusat, "status": "DIJANA PPD"}).eq("ic_guru", i["ic"]).execute()
                    berjaya += 1
                except Exception as e:
                    gagal.append(f"{i.get('ic')}: {e}")
    return berjaya, gagal


def to_excel(df):
    output = BytesIO()
    try:
        import openpyxl
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        return output.getvalue()
    except ImportError: pass
    except Exception: pass

    try:
        output.write(df.to_csv(index=False).encode('utf-8-sig'))
        return output.getvalue()
    except:
        return b""


def clean_nan(val):
    if val is None:
        return ""
    s = str(val).strip()
    if s.lower() in ("nan","none","null","nat",""):
        return ""
    return s

def get_nama_sekolah_full(kod_sek, fallback=""):
    try:
        ks = str(kod_sek).upper().strip()
        if not ks:
            return fallback
        try:
            res = supa.table("sekolah_master").select("nama_sekolah, kod_sekolah").eq("kod_sekolah", ks).limit(1).execute()
            if res.data:
                nm = res.data[0].get("nama_sekolah") or ""
                if nm and str(nm).lower() not in ("nan","none",""):
                    return str(nm).strip()
        except:
            pass
        if fallback and str(fallback).upper().strip() != ks:
            if str(fallback).lower() not in ("nan","none",""):
                return str(fallback).strip()
        return ks
    except:
        return fallback or str(kod_sek)

def create_simple_pdf_bytes(pages_text_list, title="Surat Lantikan"):
    try:
        import io
        def esc_pdf(s):
            s = str(s)
            s = s.replace('\\','\\\\').replace('(','\\(').replace(')', '\\)')
            return s
        content_streams = []
        for page_lines in pages_text_list:
            stream = "BT\n/F1 10 Tf\n40 800 Td\n"
            for line in page_lines:
                line = str(line)[:120]
                if not line.strip():
                    stream += "0 -14 Td\n"
                    continue
                safe = esc_pdf(line)
                stream += f"({safe}) Tj\n0 -14 Td\n"
            stream += "ET\n"
            content_streams.append(stream)
        pdf_parts = []
        pdf_parts.append(b"%PDF-1.4\n")
        obj_offsets = []
        obj_id = 1
        obj_offsets.append(len(b"".join(pdf_parts)))
        pdf_parts.append(f"{obj_id} 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n".encode())
        obj_id+=1
        obj_offsets.append(len(b"".join(pdf_parts)))
        kids = " ".join([f"{3 + i*2} 0 R" for i in range(len(content_streams))])
        pdf_parts.append(f"{obj_id} 0 obj\n<< /Type /Pages /Kids [{kids}] /Count {len(content_streams)} >>\nendobj\n".encode())
        obj_id+=1
        for i in range(len(content_streams)):
            obj_offsets.append(len(b"".join(pdf_parts)))
            content_obj_id = obj_id+1
            font_obj_id = 2 + len(content_streams)*2 + 1
            pdf_parts.append(f"{obj_id} 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents {content_obj_id} 0 R /Resources << /Font << /F1 {font_obj_id} 0 R >> >> >>\nendobj\n".encode())
            obj_id+=1
            obj_offsets.append(len(b"".join(pdf_parts)))
            stream_bytes = content_streams[i].encode('utf-8', errors='ignore')
            pdf_parts.append(f"{obj_id} 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n".encode())
            pdf_parts.append(stream_bytes)
            pdf_parts.append(b"\nendstream\nendobj\n")
            obj_id+=1
        obj_offsets.append(len(b"".join(pdf_parts)))
        font_obj_id = obj_id
        pdf_parts.append(f"{font_obj_id} 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n".encode())
        xref_offset = len(b"".join(pdf_parts))
        pdf_parts.append(f"xref\n0 {font_obj_id+1}\n".encode())
        pdf_parts.append(b"0000000000 65535 f \n")
        for off in obj_offsets:
            pdf_parts.append(f"{off:010d} 00000 n \n".encode())
        pdf_parts.append(f"trailer\n<< /Size {font_obj_id+1} /Root 1 0 R >>\n".encode())
        pdf_parts.append(f"startxref\n{xref_offset}\n%%EOF".encode())
        return b"".join(pdf_parts)
    except Exception as e:
        return None

def create_zip_of_individual_pdfs(surat_list, kod_ppd, ppd_name):
    import io, zipfile
    try:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for idx, s in enumerate(surat_list, start=1):
                nama = str(s.get('nama','') or s.get('NAMA GURU','')).strip()
                ic = str(s.get('ic','') or s.get('IC','')).strip()
                jawatan = str(s.get('jawatan') or s.get('JAWATAN') or '').strip()
                sek_asal = str(s.get('sekolah_asal') or s.get('SEKOLAH ASAL') or '').strip()
                pusat = str(s.get('pusat') or s.get('PUSAT') or '').strip()
                no_surat = str(s.get('no_surat') or s.get('NO SURAT') or s.get('NO SURAT BARU') or '').strip()
                nama_pusat = str(s.get('nama_pusat') or s.get('NAMA PUSAT') or '').strip()
                nama_sek_asal = str(s.get('nama_sekolah_asal') or s.get('NAMA SEKOLAH ASAL') or '').strip()
                def clean_z(v):
                    v = str(v).strip()
                    return "" if v.lower() in ("nan","none","null","") else v
                nama = clean_z(nama) or f"GURU_{idx}"
                no_surat = clean_z(no_surat) or f"JPN_{idx:04d}"
                try:
                    pdf_bytes = generate_surat_pdf_bytes(nama, ic, jawatan, sek_asal, nama_sek_asal, pusat, nama_pusat, no_surat, kod_ppd, ppd_name, __import__("datetime").date.today().strftime('%d %B %Y'), no_surat)
                except:
                    pdf_bytes = None
                if pdf_bytes:
                    safe_nama = "".join(c if c.isalnum() or c in ("_","-") else "_" for c in nama)[:30]
                    safe_no = no_surat.replace("/","_").replace("\\","_")
                    file_name = f"{idx:02d}_{safe_nama}_{safe_no}.pdf"
                    zip_file.writestr(file_name, pdf_bytes)
        zip_buffer.seek(0)
        return zip_buffer.getvalue()
    except Exception as e:
        return None

def generate_surat_html_FIXED(nama, ic, jawatan, sek_asal, nama_sek_asal, pusat, nama_pusat, no_surat, kod_ppd, ppd_name, tarikh):
    nama = clean_nan(nama) or "Nama Guru"
    ic = clean_nan(ic)
    jawatan = clean_nan(jawatan) or "Petugas Peperiksaan"
    sek_asal = clean_nan(sek_asal)
    nama_sek_asal = clean_nan(nama_sek_asal)
    pusat = clean_nan(pusat)
    nama_pusat = clean_nan(nama_pusat)
    if not nama_pusat or nama_pusat.upper() == pusat.upper():
        try:
            _pmap = build_pusat_map_from_master()
            if pusat and str(pusat).upper().strip() in _pmap and _pmap[str(pusat).upper().strip()]:
                nama_pusat = _pmap[str(pusat).upper().strip()]
        except:
            pass
    no_surat = clean_nan(no_surat) or "JPN.SPP.HHJH/0001"
    kod_ppd = clean_nan(kod_ppd) or "BA"
    ppd_name = clean_nan(ppd_name) or kod_ppd
    if nama_sek_asal and nama_sek_asal.upper() != sek_asal.upper():
        display_sek_asal = f"{sek_asal} - {nama_sek_asal}"
    else:
        try:
            full_nama = get_nama_sekolah_full(sek_asal, nama_sek_asal)
            display_sek_asal = f"{sek_asal} - {full_nama}" if full_nama and full_nama.upper() != sek_asal.upper() else sek_asal
        except:
            display_sek_asal = sek_asal
    display_pusat = f"{pusat} - {nama_pusat}" if nama_pusat and nama_pusat.upper() != pusat.upper() else pusat
    html = '<html><head><meta charset="UTF-8"><title>Surat Lantikan SPM 2026</title>'.replace("2026", str(tahun_aktif()))
    html += '<style>body{font-family:Times New Roman,serif;margin:40px;color:#000;}.surat{border:2px solid #000;padding:30px;margin-bottom:30px;page-break-after:always;background:white;}.header{text-align:center;border-bottom:3px double #000;padding-bottom:15px;margin-bottom:20px;}.kandungan{line-height:1.6;}table.info{width:100%;border-collapse:collapse;margin:15px 0;}table.info td{padding:5px 10px;}table.info td:first-child{width:180px;font-weight:bold;}.tandatangan{margin-top:60px;display:flex;justify-content:space-between;}</style></head><body>'
    html += '<div class="surat"><div class="header">'
    html += '<h2>JABATAN PENDIDIKAN NEGERI SELANGOR</h2>'
    html += f'<h3>PEJABAT PENDIDIKAN DAERAH {kod_ppd} - {ppd_name}</h3>'
    html += f'<p>No Surat: {no_surat}</p></div>'
    html += '<div class="kandungan">'
    html += f'<p>Tarikh: {tarikh}</p><p><strong>Tuan/Puan,</strong></p><p><strong>PELANTIKAN SEBAGAI {jawatan.upper()} PEPERIKSAAN SPM TAHUN {tahun_aktif()}</strong></p>'
    html += '<p>Dengan hormatnya saya merujuk kepada perkara di atas.</p><p>2. Sukacita dimaklumkan bahawa tuan/puan telah dilantik sebagai petugas peperiksaan SPM 2026 seperti butiran berikut:</p><table class="info">'.replace("2026", str(tahun_aktif()))
    html += f'<tr><td>Nama</td><td>: {nama}</td></tr><tr><td>No. IC</td><td>: {ic}</td></tr><tr><td>Jawatan</td><td>: {jawatan}</td></tr><tr><td>Sekolah Asal</td><td>: {display_sek_asal}</td></tr><tr><td>Pusat Ditugaskan</td><td>: {display_pusat}</td></tr><tr><td>No Surat Lantikan</td><td>: {no_surat}</td></tr></table>'
    html += '<p>3. Tuan/puan dikehendaki hadir bertugas di pusat peperiksaan yang telah ditetapkan mengikut jadual yang akan dimaklumkan kemudian.</p><p>4. Kerjasama dan komitmen tuan/puan dalam menjayakan peperiksaan SPM 2026 amatlah dihargai dan didahului dengan ucapan terima kasih.</p><p>Sekian.</p>'.replace("2026", str(tahun_aktif()))
    html += '<div class="footer"><p><strong>MALAYSIA MADANI</strong><br><strong>BERKHIDMAT UNTUK NEGARA</strong></p><div class="tandatangan"><div><p>Yang benar,</p><br><br><br>'
    html += f'<p>_________________________<br><strong>Pegawai Pendidikan Daerah<br>PPD {kod_ppd} - {ppd_name}</strong></p></div><div style="text-align:right;"><p>b.p Pengarah Pendidikan<br>Jabatan Pendidikan Negeri Selangor</p></div></div></div></div></div></body></html>'
    return html





def generate_surat_pdf_bytes_FIXED(nama, ic, jawatan, sek_asal, nama_sek_asal, pusat, nama_pusat, no_surat, kod_ppd, ppd_name, tarikh, no_rujukan="", bilik_kebal="", kod_bilik_kebal=""):
    try:
        nama = clean_nan(nama) or "Nama Guru"
        ic = clean_nan(ic)
        jawatan = clean_nan(jawatan) or "Pengawas Peperiksaan"
        sek_asal = clean_nan(sek_asal)
        nama_sek_asal = clean_nan(nama_sek_asal) or get_nama_sekolah_full(sek_asal, "")
        pusat = clean_nan(pusat)
        nama_pusat = clean_nan(nama_pusat) or get_nama_sekolah_full(pusat, "")
        no_surat = clean_nan(no_surat) or f"JPNS.SPP 600-7/17/5 Jld.2 (01)"
        kod_ppd = clean_nan(kod_ppd) or "BA"
        ppd_name = clean_nan(ppd_name) or kod_ppd
        tarikh = clean_nan(tarikh) or datetime.date.today().strftime("%d %B %Y")
        bilik_kebal = clean_nan(bilik_kebal) or clean_nan(kod_bilik_kebal) or ""

        if nama_sek_asal and nama_sek_asal.upper() != sek_asal.upper() and sek_asal not in nama_sek_asal:
            display_sek_asal = f"{sek_asal} - {nama_sek_asal}"
        else:
            display_sek_asal = nama_sek_asal if nama_sek_asal else sek_asal
        if nama_pusat and nama_pusat.upper() != pusat.upper() and pusat not in nama_pusat:
            display_pusat = f"{pusat} - {nama_pusat}"
        else:
            display_pusat = nama_pusat if nama_pusat else pusat

        # No pusat untuk display - ambil dari pusat
        no_pusat_display = pusat.split("-")[0].strip() if "-" in pusat else pusat
        if len(no_pusat_display) < 3:
            no_pusat_display = pusat

        # ===== V37: TEMPLAT JPN DIUTAMAKAN - kalau JPN dah cipta templat jawatan ini, PDF dijana dari templat itu =====
        _h37 = render_jpn_template_html(jawatan, nama, ic, sek_asal, nama_sek_asal, pusat, nama_pusat, no_surat, kod_ppd, ppd_name, tarikh, bilik_kebal)
        if _h37:
            _pdf37 = html_to_pdf_bytes(_h37)
            if _pdf37:
                return _pdf37
        # (jika templat tiada / enjin PDF tiada -> guna susun atur lama di bawah)
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, Image as RLImage
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        import io, os
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=15*mm, leftMargin=18*mm, topMargin=10*mm, bottomMargin=12*mm)
        styles = getSampleStyleSheet()

        style_header_mid = ParagraphStyle('HeaderMid', parent=styles['Normal'], fontSize=10.5, leading=13, alignment=0, fontName='Helvetica')
        style_header_right = ParagraphStyle('HeaderRight', parent=styles['Normal'], fontSize=8.5, leading=11, alignment=0, fontName='Helvetica')
        style_normal = ParagraphStyle('NormalJPN', parent=styles['Normal'], fontSize=10, leading=13.5, spaceAfter=3, alignment=4, fontName='Helvetica')
        style_normal_left = ParagraphStyle('NormalLeft', parent=styles['Normal'], fontSize=10, leading=13.5, spaceAfter=3, alignment=0, fontName='Helvetica')
        style_bold = ParagraphStyle('BoldJPN', parent=styles['Normal'], fontSize=10, leading=13, spaceAfter=4, alignment=0, fontName='Helvetica-Bold')
        style_tajuk = ParagraphStyle('TajukJPN', parent=styles['Normal'], fontSize=10.5, leading=13.5, spaceAfter=6, alignment=0, fontName='Helvetica-Bold')
        style_small = ParagraphStyle('Small', parent=styles['Normal'], fontSize=9.5, leading=13, alignment=0, fontName='Helvetica')

        story = []

        # ===== HEADER - IKUT GAMBAR =====
        logo_path = None
        for cand in ["/mnt/data/jata_cropped.png", "/mnt/data/65b0dade-7a33-4312-b19b-9d5b24dd57ce.jpg", "jata_negara_hd.png","./jata_negara_hd.png","jata_negara.png","./jata_negara.png","/mnt/data/jata_negara_hd.png"]:
            if os.path.exists(cand):
                logo_path = cand
                break

        middle_html = """<b>KEMENTERIAN PENDIDIKAN</b><br/>Jabatan Pendidikan Negeri Selangor<br/>Jalan Jambu Bol 4/3E, Seksyen 4<br/>40604 Shah Alam, Selangor"""
        right_html = """Tel : 03 - 5518 6500<br/>Faks : 03 - 5510 2133<br/>Laman Web : jpnselangor.moe.gov.my"""

        if logo_path:
            try:
                logo_img = RLImage(logo_path, width=24*mm, height=20*mm, kind='proportional')
                header_data = [[logo_img, Paragraph(middle_html, style_header_mid), Paragraph(right_html, style_header_right)]]
                t = Table(header_data, colWidths=[26*mm, 82*mm, 60*mm])
                t.setStyle(TableStyle([('LINEBELOW', (0,0), (-1,-1), 0.8, colors.black), ('BOTTOMPADDING', (0,0), (-1,-1), 6), ('TOPPADDING', (0,0), (-1,-1), 2), ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
                story.append(t)
            except:
                header_data = [[Paragraph("", style_header_mid), Paragraph(middle_html, style_header_mid), Paragraph(right_html, style_header_right)]]
                t = Table(header_data, colWidths=[26*mm, 82*mm, 60*mm])
                t.setStyle(TableStyle([('LINEBELOW', (0,0), (-1,-1), 0.8, colors.black), ('BOTTOMPADDING', (0,0), (-1,-1), 6)]))
                story.append(t)
        else:
            header_data = [[Paragraph("", style_header_mid), Paragraph(middle_html, style_header_mid), Paragraph(right_html, style_header_right)]]
            t = Table(header_data, colWidths=[26*mm, 82*mm, 60*mm])
            t.setStyle(TableStyle([('LINEBELOW', (0,0), (-1,-1), 0.8, colors.black), ('BOTTOMPADDING', (0,0), (-1,-1), 6)]))
            story.append(t)

        story.append(Spacer(1,6))

        # ===== RUJ KAMI & TARIKH - KANAN, TABLE KEMAS =====
        style_ruj_label = ParagraphStyle('RujLabel', parent=styles['Normal'], fontSize=10, leading=13, alignment=0, fontName='Helvetica')
        style_ruj_value = ParagraphStyle('RujValue', parent=styles['Normal'], fontSize=10, leading=13, alignment=0, fontName='Helvetica')
        style_ruj_colon = ParagraphStyle('RujColon', parent=styles['Normal'], fontSize=10, leading=13, alignment=0, fontName='Helvetica')

        ruj_inner_data = [
            [Paragraph("Ruj. Kami", style_ruj_label), Paragraph(":", style_ruj_colon), Paragraph(no_surat, style_ruj_value)],
            [Paragraph("Tarikh", style_ruj_label), Paragraph(":", style_ruj_colon), Paragraph(tarikh, style_ruj_value)]
        ]
        t_ruj_inner = Table(ruj_inner_data, colWidths=[22*mm, 4*mm, 62*mm])
        t_ruj_inner.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'LEFT'), ('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 1), ('RIGHTPADDING', (0,0), (-1,-1), 1), ('TOPPADDING', (0,0), (-1,-1), 1), ('BOTTOMPADDING', (0,0), (-1,-1), 2)]))
        wrapper_data = [[Paragraph("", style_ruj_label), t_ruj_inner]]
        t_wrapper = Table(wrapper_data, colWidths=[80*mm, 88*mm])
        t_wrapper.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'LEFT'), ('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0)]))
        story.append(t_wrapper)
        story.append(Spacer(1,6))

        # ===== NAMA & MELALUI =====
        story.append(Paragraph(f"<b>{nama.upper()}</b>", style_bold))
        story.append(Spacer(1,6))
        story.append(Paragraph("Melalui:", style_normal_left))
        story.append(Spacer(1,2))
        story.append(Paragraph("Pengetua/Guru Besar,", style_normal_left))
        # Sekolah asal dari data
        story.append(Paragraph(f"{display_sek_asal.upper()},", style_normal_left))
        # PPD untuk GOMBAK etc - ambil dari ppd_name
        story.append(Paragraph(f"<b>{ppd_name.upper()}.</b>", style_normal_left))
        story.append(Spacer(1,6))
        story.append(Paragraph("Tuan,", style_normal_left))
        story.append(Spacer(1,6))

        # ===== TAJUK - IKUT GAMBAR =====
        tajuk_jawatan = jawatan.upper()
        if "PENYELIA KAWASAN" in tajuk_jawatan:
            tajuk_full = f"SIJIL PELAJARAN MALAYSIA ULANGAN ( SPMU ) TAHUN {tahun_aktif()} :<br/>PELANTIKAN SEBAGAI PENYELIA KAWASAN BERTULIS ( TATAKIRA/PEMEGANG KUNCI )"
        elif "KETUA PENGAWAS" in tajuk_jawatan:
            tajuk_full = f"SIJIL PELAJARAN MALAYSIA ( SPM ) TAHUN {tahun_aktif()} :<br/>PELANTIKAN SEBAGAI {tajuk_jawatan}"
        else:
            tajuk_full = f"SIJIL PELAJARAN MALAYSIA ( SPM ) TAHUN {tahun_aktif()} :<br/>PELANTIKAN SEBAGAI {tajuk_jawatan} - {display_pusat}"

        story.append(Paragraph(f"<b>{tajuk_full}</b>", style_tajuk))
        story.append(Spacer(1,6))
        story.append(Paragraph("Dengan segala hormatnya perkara di atas dirujuk.", style_normal))
        story.append(Spacer(1,6))

        # ===== PARA 2 - IKUT GAMBAR 100% - FIX NO PUSAT & BILIK KEBAL =====
        # LOGIK BARU: No Pusat = No Pusat sebenar (BB017), Bilik Kebal kosong dulu kalau belum set di selenggara
        # Kalau Penyelia Kawasan, bilik_kebal datang dari selenggara bilik kebal -> kod_bilik_kebal
        # No Pusat datang dari kod_pusat (pusat jagaan)

        # Tentukan jenis jawatan
        is_penyelia_kawasan = "PENYELIA KAWASAN" in jawatan.upper()

        if is_penyelia_kawasan:
            para2_text = f"2. &nbsp;&nbsp;&nbsp;&nbsp;Sukacita dimaklumkan bahawa, tuan dilantik sebagai <b>{jawatan}</b> bagi peperiksaan di atas dari tempoh <b>14 Julai hingga 16 Julai {tahun_aktif()}</b>. Pelantikan ini merupakan sebahagian daripada tugas rasmi. Maklumat pusat peperiksaan di bawah pengawasan tuan adalah seperti berikut:"
        else:
            para2_text = f"2. &nbsp;&nbsp;&nbsp;&nbsp;Sukacita dimaklumkan tuan dilantik sebagai <b>{jawatan} bagi peperiksaan di atas. Berikut adalah pusat peperiksaan di bawah pengawasan tuan:</b>"

        story.append(Paragraph(para2_text, style_normal))
        story.append(Spacer(1,6))

        # 2.1, 2.2, 2.3 - TABLE KEMAS - FIX: No Pusat betul, Bilik Kebal ikut selenggara
        style_sub_label = ParagraphStyle('SubLabel', parent=styles['Normal'], fontSize=10, leading=13, alignment=0, leftIndent=15*mm, fontName='Helvetica')
        style_sub_value = ParagraphStyle('SubValue', parent=styles['Normal'], fontSize=10, leading=13, alignment=0, fontName='Helvetica-Bold')
        style_sub_value_empty = ParagraphStyle('SubValueEmpty', parent=styles['Normal'], fontSize=10, leading=13, alignment=0, fontName='Helvetica', textColor=colors.HexColor('#1565c0'))

        # LOGIK: No Pusat = kod pusat sebenar, BUKAN bilik kebal
        # Kalau bilik_kebal kosong, paparkan - atau kosong untuk isi kemudian
        if not bilik_kebal or bilik_kebal.strip() == "" or bilik_kebal.lower() in ("nan","none","null","-"):
            bilik_kebal_display = ""  # Kosongkan dulu seperti request
            bilik_kebal_para = Paragraph(f": <i>(Akan dikemaskini melalui Selenggara Bilik Kebal)</i>", style_sub_value_empty)
        else:
            bilik_kebal_display = bilik_kebal.upper()
            bilik_kebal_para = Paragraph(f": {bilik_kebal_display}", style_sub_value)

        # No Pusat - pastikan bukan bilik kebal code (CB, BK)
        # Jika no_pusat_display mengandungi CB/BK dan kita ada pusat sebenar, guna pusat sebenar
        if no_pusat_display.upper().startswith(("CB","BK")) and pusat:
            # no_pusat_display ni sebenarnya bilik kebal, tukar guna pusat sebenar
            no_pusat_final = pusat.split(",")[0].strip() if "," in pusat else pusat
        else:
            no_pusat_final = no_pusat_display

        sub_data = [
            [Paragraph("2.1", style_small), Paragraph("No. Pusat", style_small), Paragraph(f": {no_pusat_final}", style_sub_value)],
            [Paragraph("2.2", style_small), Paragraph("Nama Pusat", style_small), Paragraph(f": {display_pusat.upper()}", style_sub_value)],
            [Paragraph("2.3", style_small), Paragraph("Bilik Kebal", style_small), bilik_kebal_para],
        ]
        t_sub = Table(sub_data, colWidths=[10*mm, 30*mm, 110*mm])
        t_sub.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 2), ('RIGHTPADDING', (0,0), (-1,-1), 2), ('TOPPADDING', (0,0), (-1,-1), 2), ('BOTTOMPADDING', (0,0), (-1,-1), 2)]))
        story.append(t_sub)
        story.append(Spacer(1,6))

        # ===== PARA 3 - ELAUN =====
        story.append(Paragraph("3. &nbsp;&nbsp;&nbsp;&nbsp;Tuan akan dibayar dengan kadar elaun berikut:", style_normal))
        story.append(Spacer(1,4))

        elaun_data = [
            [Paragraph("3.1", style_small), Paragraph("Elaun Ikhtisas", style_small), Paragraph(f": <b>RM 281.25 + S (S = Bil. Sesi)</b>", style_small)],
            [Paragraph("3.2", style_small), Paragraph("Elaun Perjalanan", style_small), Paragraph(": Tuan layak membuat tuntutan perjalanan<br/>&nbsp;&nbsp;&nbsp;&nbsp;menggunakan kenderaan sendiri/ awam berdasarkan<br/>&nbsp;&nbsp;&nbsp;&nbsp;kepada Arahan Perbendaharaan yang sedang<br/>&nbsp;&nbsp;&nbsp;&nbsp;berkuatkuasa.", style_small)],
        ]
        t_elaun = Table(elaun_data, colWidths=[10*mm, 35*mm, 105*mm])
        t_elaun.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 2), ('RIGHTPADDING', (0,0), (-1,-1), 2), ('TOPPADDING', (0,0), (-1,-1), 2), ('BOTTOMPADDING', (0,0), (-1,-1), 2)]))
        story.append(t_elaun)
        story.append(Spacer(1,6))

        # ===== PARA 4 =====
        para4 = """4. &nbsp;&nbsp;&nbsp;&nbsp;Pelantikan ini adalah sebahagian daripada tugas rasmi. Sehubungan dengan itu, tuan dikehendaki melaksanakan tugasan seperti yang tersenarai di <b>Lampiran A</b>. Tuan boleh dilantik oleh Ketua Pengawas sebagai <b>Pengawas Pengiring</b> mengikut keperluan ke bilik kebal. Pelantikan tuan adalah <b>Sulit</b> dan tertakluk kepada <b>Akta Rahsia Rasmi 1972</b> dan lain-lain peraturan keselamatan yang sedang berkuatkuasa."""
        story.append(Paragraph(para4, style_normal))
        story.append(Spacer(1,6))

        # ===== PARA 5 =====
        para5 = "5. &nbsp;&nbsp;&nbsp;&nbsp;Semoga tuan dapat melaksanakan tugas ini dengan penuh dedikasi dan berintegriti dalam menyempurnakan amanah yang dipertanggungjawabkan."
        story.append(Paragraph(para5, style_normal))
        story.append(Spacer(1,6))
        # ===== PENUTUP + TANDATANGAN (satu blok, tak terpisah antara muka surat) =====
        sig_path = None
        _base = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "."
        for _name in ["tandatangan_pengarah_hd.png", "tandatangan_pengarah.png", "tandatangan_pengarah.jpg", "tandatangan.png"]:
            for _dir in [_base, ".", "/mnt/data", os.path.join(_base, "assets")]:
                _p = os.path.join(_dir, _name)
                if os.path.exists(_p):
                    sig_path = _p
                    break
            if sig_path:
                break

        penutup = [
            Paragraph("Sekian, terima kasih.", style_normal_left),
            Spacer(1, 5),
            Paragraph("\"MALAYSIA MADANI\"", style_bold),
            Paragraph("\"BERKHIDMAT UNTUK NEGARA\"", style_bold),
            Spacer(1, 5),
            Paragraph("Saya yang menjalankan amanah,", style_normal_left),
        ]
        sig_flow = None
        if sig_path:
            try:
                sig_flow = RLImage(sig_path, width=36*mm, height=13*mm, kind='proportional')
                sig_flow.hAlign = 'LEFT'
            except Exception:
                sig_flow = None
        penutup.append(sig_flow if sig_flow is not None else Spacer(1, 26))
        penutup.append(Paragraph("<b>(DATIN WAN NOR ASHIKIN BINTI ABU KASSIM)</b><br/>Pengarah Pendidikan,<br/>Jabatan Pendidikan Negeri Selangor.", style_normal_left))
        story.append(KeepTogether(penutup))

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
    except Exception as e:
        _log.debug(f"PDF surat error: {e}")
        return None




def generate_surat_kolektif_pdf_bytes_JPN(surat_list, kod_ppd, ppd_name, title_prefix="SURAT LANTIKAN"):
    if len(surat_list) > MAX_PDF_KOLEKTIF:
        st.warning(f"PDF dihadkan {MAX_PDF_KOLEKTIF} surat (ada {len(surat_list)}).")
        surat_list = surat_list[:MAX_PDF_KOLEKTIF]
    # RINGAN-START
    """Jana PDF kolektif guna template JPN - untuk PPD download pukal"""
    # ===== V37: gabung PDF individu (templat JPN) menjadi satu PDF kolektif =====
    try:
        from pypdf import PdfWriter, PdfReader
        import io as _io
        _w = PdfWriter()
        _n = 0
        for _s in surat_list:
            _pdf = generate_surat_pdf_bytes_FIXED(
                _s.get("nama",""), _s.get("ic",""), _s.get("jawatan",""),
                _s.get("sekolah_asal",""), _s.get("nama_sekolah_asal","") or _s.get("sekolah_asal",""),
                _s.get("pusat",""), _s.get("nama_pusat","") or _s.get("pusat",""),
                _s.get("no_surat",""), kod_ppd, ppd_name,
                datetime.date.today().strftime("%d %B %Y"),
                bilik_kebal=_s.get("bilik_kebal","") or _s.get("kod_bilik_kebal","")
            )
            if _pdf:
                for _pg in PdfReader(_io.BytesIO(_pdf)).pages:
                    _w.add_page(_pg)
                _n += 1
        if _n > 0:
            _out = _io.BytesIO()
            _w.write(_out)
            return _out.getvalue()
    except Exception as _e:
        _log.debug(f"Gabung PDF kolektif gagal, guna kaedah lama: {_e}")
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        import io
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=15*mm, leftMargin=15*mm, topMargin=10*mm, bottomMargin=10*mm)
        styles = getSampleStyleSheet()
        style_title = ParagraphStyle('TitleKolektif', parent=styles['Heading1'], fontSize=12, alignment=1, spaceAfter=6)
        style_normal = ParagraphStyle('NormalKolektif', parent=styles['Normal'], fontSize=9, leading=12, spaceAfter=3)
        story = []
        story.append(Paragraph(f"{title_prefix} - PPD {kod_ppd} {ppd_name} - {len(surat_list)} Surat - JPN SELARAS", style_title))
        story.append(Spacer(1,8))
        for idx, s in enumerate(surat_list, 1):
            try:
                # Guna function JPN baru
                pdf_one = generate_surat_pdf_bytes_FIXED(
                    s.get("nama",""), s.get("ic",""), s.get("jawatan",""),
                    s.get("sekolah_asal",""), s.get("nama_sekolah_asal","") or s.get("sekolah_asal",""),
                    s.get("pusat",""), s.get("nama_pusat","") or s.get("pusat",""),
                    s.get("no_surat",""), kod_ppd, ppd_name,
                    datetime.date.today().strftime("%d %B %Y")
                )
                # Kita tak embed pdf_one, kita buat text representation kolektif - buat isi ringkas
                # Tapi untuk kolektif kita buat paragraph per surat guna template JPN HTML rendering
                jpn_html = render_jpn_template_html(
                    s.get("jawatan",""), s.get("nama",""), s.get("ic",""),
                    s.get("sekolah_asal",""), s.get("nama_sekolah_asal",""),
                    s.get("pusat",""), s.get("nama_pusat",""),
                    s.get("no_surat",""), kod_ppd, ppd_name,
                    datetime.date.today().strftime("%d %B %Y")
                )
                if jpn_html:
                    # bersihkan sikit
                    import re
                    clean = re.sub(r'<style.*?</style>', '', jpn_html, flags=re.DOTALL|re.IGNORECASE)
                    clean = re.sub(r'<head.*?</head>', '', clean, flags=re.DOTALL|re.IGNORECASE)
                    story.append(Paragraph(f"<b>{idx}. {s.get('nama','')} - {s.get('no_surat','')} - {s.get('sekolah_asal','')}</b>", style_normal))
                    story.append(Paragraph(clean[:8000], style_normal))
                else:
                    story.append(Paragraph(f"<b>{idx}. {s.get('nama','')} - {s.get('jawatan','')} - {s.get('pusat','')} - {s.get('no_surat','')}</b><br/>Sekolah Asal: {s.get('sekolah_asal','')} - Pusat: {s.get('pusat','')}", style_normal))
                story.append(Spacer(1,6))
                if idx % 3 == 0:
                    story.append(PageBreak())
            except Exception as e:
                story.append(Paragraph(f"Error surat {idx}: {e}", style_normal))
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
    except Exception as e:
        _log.debug(f"Kolektif JPN error: {e}")
        return None

def create_zip_pukal_dari_JPN(surat_list, kod_ppd, ppd_name):
    """VERSI RINGAN: Limit 200 file per ZIP untuk 300 user"""
    try:
        import zipfile, io
        if len(surat_list) > MAX_ZIP_FILES:
            st.warning(f"ZIP dihadkan {MAX_ZIP_FILES} file (ada {len(surat_list)}).")
            surat_list = surat_list[:MAX_ZIP_FILES]
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for idx, s in enumerate(surat_list, 1):
                try:
                    pdf_bytes = generate_surat_pdf_bytes_FIXED(
                        s.get("nama",""), s.get("ic",""), s.get("jawatan",""),
                        s.get("sekolah_asal",""), s.get("nama_sekolah_asal","") or s.get("sekolah_asal",""),
                        s.get("pusat",""), s.get("nama_pusat","") or s.get("pusat",""),
                        s.get("no_surat",""), kod_ppd, ppd_name,
                        datetime.date.today().strftime("%d %B %Y")
                    )
                    if pdf_bytes:
                        safe_nama = "".join(c if c.isalnum() or c in ("_","-") else "_" for c in str(s.get("nama",""))[:25])
                        safe_no = str(s.get("no_surat","")).replace("/","_").replace("\\","_").replace(" ","_")[:30]
                        safe_sek = str(s.get("sekolah_asal","")).replace("/","_")[:10]
                        # Format: 01_NAMA_SEKOLAH_NOSURAT.pdf - senang SUP cari
                        file_name = f"{idx:03d}_{safe_nama}_{safe_sek}_{safe_no}.pdf"
                        zip_file.writestr(file_name, pdf_bytes)
                except Exception as e:
                    continue
        zip_buffer.seek(0)
        return zip_buffer.getvalue()
    except Exception as e:
        _log.debug(f"ZIP JPN error: {e}")
        return None

def hantar_surat_ke_sekolah_asal_bulk(surat_list, kod_ppd):
    """NEW: Bila PPD jana surat, auto update status supaya surat sampai ke sekolah asal petugas"""
    try:
        # Kita update cadangan_sup dengan status SURAT_SAMPAI_SEKOLAH_ASAL + tambah log
        berjaya = 0
        for s in surat_list:
            try:
                no_surat = s.get("no_surat","")
                ic = s.get("ic","")
                sek_asal = s.get("sekolah_asal","")
                pusat = s.get("pusat","")
                if not ic:
                    continue
                # Update cadangan_sup
                payload = {
                    "status": "SURAT_SAMPAI_SEKOLAH_ASAL",
                    "no_surat": no_surat,
                    "kod_pusat": pusat,
                    "tarikh_jana_surat": str(datetime.date.today()),
                    "sekolah_asal_hantar": sek_asal
                }
                try:
                    supa.table("cadangan_sup").update(payload).eq("ic_guru", ic).eq("kod_ppd", kod_ppd.lower() if kod_ppd else "bh").execute()
                    berjaya += 1
                except:
                    try:
                        supa.table("cadangan_sup").update(payload).eq("ic_guru", ic).execute()
                        berjaya += 1
                    except:
                        pass
            except:
                continue
        # Cuba simpan ke table log khas jika ada (surat_hantar_sekolah_asal) - optional
        try:
            log_data = []
            for s in surat_list:
                log_data.append({
                    "kod_ppd": kod_ppd,
                    "ic_guru": s.get("ic",""),
                    "nama_guru": s.get("nama",""),
                    "kod_sekolah_asal": s.get("sekolah_asal",""),
                    "kod_pusat": s.get("pusat",""),
                    "no_surat": s.get("no_surat",""),
                    "jawatan": s.get("jawatan",""),
                    "tarikh_hantar": str(datetime.date.today()),
                    "status": "SAMPAI_KE_SEKOLAH_ASAL"
                })
            # batch insert kalau table wujud
            try:
                supa.table("surat_hantar_sekolah_asal").insert(log_data).execute()
            except:
                pass
        except:
            pass
        return berjaya
    except Exception as e:
        _log.debug(f"hantar sekolah asal error: {e}")
        return 0

# Monkey-patch
try:
    generate_surat_html = generate_surat_html_FIXED
    generate_surat_pdf_bytes = generate_surat_pdf_bytes_FIXED
    generate_surat_pdf_bytes_FIXED_OLD = generate_surat_pdf_bytes_FIXED
    # keep original names also
    globals()['generate_surat_html'] = generate_surat_html_FIXED
    globals()['generate_surat_pdf_bytes'] = generate_surat_pdf_bytes_FIXED
    # new bulk funcs
    globals()['generate_surat_kolektif_pdf_bytes_JPN'] = generate_surat_kolektif_pdf_bytes_JPN
    globals()['create_zip_pukal_dari_JPN'] = create_zip_pukal_dari_JPN
    globals()['hantar_surat_ke_sekolah_asal_bulk'] = hantar_surat_ke_sekolah_asal_bulk
except:
    pass



def get_template_guru(kod_sekolah_contoh="BFT0003", nama_sekolah_contoh="SAM NURUL IMAN", kod_ppd_contoh="BH"):
    """Template FINAL ringkas - hanya wajib, pengalaman & jawatan boleh kosong"""
    template = {
        "kod_ppd": [kod_ppd_contoh.lower()],
        "kod_sekolah": [kod_sekolah_contoh.upper()],
        "nama_guru": ["CONTOH: ALI BIN ABU"],
        "ic_guru": ["900101-01-1234"],
        "jantina": ["LELAKI"],
        "poskod_rumah": ["40000"],
        "alamat_rumah": ["NO 1, JALAN CONTOH, KLANG"],
        "telefon_guru": ["012-3456789"],
        "no_pusat_asal": ["BA142"],
        "kod_sekolah_asal": [kod_sekolah_contoh.upper()],
        "nama_sekolah_asal": [nama_sekolah_contoh],
        "kod_ppd_asal": [kod_ppd_contoh],
        "jawatan_cadangan": [""],
        "pengalaman_spm": [""],
        "email_guru": [""],
    }
    return pd.DataFrame(template)

def get_template_guru_friendly():
    template_mudah = {
        "NAMA GURU": ["CONTOH: ALI BIN ABU"],
        "IC GURU": ["900101-01-1234"],
        "JANTINA": ["L/LELAKI/PEREMPUAN"],
        "KOD PPD": ["BH"],
        "KOD SEKOLAH": ["BFT0003"],
        "POSKOD RUMAH": ["40000"],
        "ALAMAT RUMAH": ["NO 1, JALAN CONTOH, KLANG"],
        "TELEFON GURU": ["012-3456789"],
        "NO PUSAT ASAL": ["BA142"],
        "KOD SEKOLAH ASAL": ["BFT0003"],
        "NAMA SEKOLAH ASAL": ["SAM NURUL IMAN"],
        "KOD PPD ASAL": ["BH"],
        "JAWATAN CADANGAN": ["(Kosongkan)"],
        "PENGALAMAN SPM": ["(Kosongkan)"],
    }
    return pd.DataFrame(template_mudah)

def normalize_guru_import(df_upload):
    HEADER_MAP = {
        "NAMA GURU": "nama_guru", "NAMA_GURU": "nama_guru", "nama_guru": "nama_guru", "NAMA": "nama_guru",
        "IC GURU": "ic_guru", "IC_GURU": "ic_guru", "ic_guru": "ic_guru", "IC": "ic_guru",
        "KOD PPD": "kod_ppd", "KOD_PPD": "kod_ppd", "kod_ppd": "kod_ppd",
        "KOD SEKOLAH": "kod_sekolah", "KOD_SEKOLAH": "kod_sekolah", "kod_sekolah": "kod_sekolah",
        "KOD SEKOLAH ASAL": "kod_sekolah_asal", "KOD_SEKOLAH_ASAL": "kod_sekolah_asal", "kod_sekolah_asal": "kod_sekolah_asal",
        "JANTINA": "jantina", "jantina": "jantina",
        "POSKOD RUMAH": "poskod_rumah", "POSKOD_RUMAH": "poskod_rumah", "poskod_rumah": "poskod_rumah",
        "ALAMAT RUMAH": "alamat_rumah", "ALAMAT_RUMAH": "alamat_rumah", "alamat_rumah": "alamat_rumah",
        "TELEFON GURU": "telefon_guru", "TELEFON_GURU": "telefon_guru", "telefon_guru": "telefon_guru",
        "EMAIL GURU": "email_guru", "EMAIL_GURU": "email_guru", "email_guru": "email_guru",
        "JAWATAN CADANGAN": "jawatan_cadangan", "JAWATAN_CADANGAN": "jawatan_cadangan", "jawatan_cadangan": "jawatan_cadangan",
        "PENGALAMAN SPM": "pengalaman_spm", "PENGALAMAN_SPM": "pengalaman_spm", "pengalaman_spm": "pengalaman_spm",
        "NO PUSAT ASAL": "no_pusat_asal", "NO_PUSAT_ASAL": "no_pusat_asal", "no_pusat_asal": "no_pusat_asal",
        "NAMA SEKOLAH ASAL": "nama_sekolah_asal", "NAMA_SEKOLAH_ASAL": "nama_sekolah_asal", "nama_sekolah_asal": "nama_sekolah_asal",
        "KOD PPD ASAL": "kod_ppd_asal", "KOD_PPD_ASAL": "kod_ppd_asal", "kod_ppd_asal": "kod_ppd_asal",
    }
    normalized_cols = {}
    for col in df_upload.columns:
        col_str = str(col).strip()
        if col_str in HEADER_MAP:
            normalized_cols[col] = HEADER_MAP[col_str]
        elif col_str.upper() in HEADER_MAP:
            normalized_cols[col] = HEADER_MAP[col_str.upper()]
        elif col_str.lower() in HEADER_MAP:
            normalized_cols[col] = HEADER_MAP[col_str.lower()]
        else:
            for k,v in HEADER_MAP.items():
                if k.lower() == col_str.lower():
                    normalized_cols[col] = v
                    break
            else:
                normalized_cols[col] = None
    return normalized_cols

# ================= REFRESH COMPONENT =================
def add_refresh_button():
    st.markdown("---")
    st.markdown("### 🔄 Refresh Data")
    st.caption(f"Last: {datetime.datetime.now().strftime('%d/%m %H:%M:%S')}")
    if st.button("🔄 REFRESH - Baca Data Baru", use_container_width=True, type="primary", key=f"refresh_main_{st.session_state.role}_{st.session_state.kod if hasattr(st.session_state, 'kod') else 'x'}"):
        st.cache_data.clear()
        # Jangan clear resource (supabase client) - itu yang buat buffering lama
        st.toast("✅ Data refreshed! Baca perubahan terbaru")
        st.rerun()
    st.caption("Tekan selepas SUP buat pertukaran / cadangan")

# ================= SESSION INIT =================
if "role" not in st.session_state:
    st.session_state.role = None

# ================= LOGIN PAGE =================


# ===== FIX: BUILD PUSAT MAP ROBUST - IKUT NO PUSAT COLUMN REFER PUSAT_MASTER =====
def build_pusat_map_from_master():
    """Map NO_PUSAT/KOD_PUSAT -> NAMA_PUSAT dari pusat_master"""
    pmap = {}
    try:
        df_p = get_pusat_df()
        for _, pr in df_p.iterrows():
            d = pr.get("data") if isinstance(pr.get("data"), dict) else {}
            if isinstance(d, str):
                try:
                    import json as _js
                    d = _js.loads(d)
                except:
                    d = {}
            # Ambil semua kemungkinan key untuk NO PUSAT
            no_p = str(pr.get("no_pusat") or pr.get("kod_pusat") or pr.get("NO_PUSAT") or pr.get("KOD_PUSAT") or d.get("NO_PUSAT") or d.get("NO PUSAT") or d.get("KOD_PUSAT") or d.get("KOD PUSAT") or "").upper().strip()
            nama_p = str(pr.get("nama_pusat") or pr.get("NAMA_PUSAT") or d.get("NAMA_PUSAT") or d.get("NAMA PUSAT") or "").strip()
            if no_p:
                pmap[no_p] = nama_p
                # juga map tanpa prefix? simpan kedua-dua
                # contoh BA140 tetap BA140
        # Fallback: cuba direct dari supabase pusat_master jika get_pusat_df kosong
        if not pmap:
            try:
                _supa = supa
                res = _supa.table("pusat_master").select("*").limit(1000).execute()
                for r in (res.data or []):
                    no_p = str(r.get("no_pusat") or r.get("kod_pusat") or r.get("NO_PUSAT") or "").upper().strip()
                    nama_p = str(r.get("nama_pusat") or r.get("NAMA_PUSAT") or "").strip()
                    if no_p:
                        pmap[no_p] = nama_p
            except:
                pass
    except Exception as _e:
        pass
    return pmap


# ================= LOGIN POPUP BARU - IKUT HTML (SUP/PPD/JPN POPUP) =================
if st.session_state.role is None:
    show_hero_header()

    # --- State untuk popup flow ---
    if "popup_stage" not in st.session_state:
        st.session_state.popup_stage = None
    if "sel_ppd_sup" not in st.session_state:
        st.session_state.sel_ppd_sup = None
    if "sel_sekolah_kod" not in st.session_state:
        st.session_state.sel_sekolah_kod = None
        st.session_state.sel_sekolah_nama = ""
        st.session_state.sel_sekolah_id = 1

    @st.cache_data(ttl=3600, show_spinner=False)
    def load_sekolah_list_popup():
        try:
            res = supa.table("sekolah_master").select("*").limit(1000).execute()
            data = res.data or []
            rows = []
            for r in data:
                kod = r.get("kod_sekolah") or r.get("KOD_SEKOLAH") or ""
                nama = r.get("nama_sekolah") or r.get("NAMA_SEKOLAH") or ""
                kod_ppd = r.get("kod_ppd") or r.get("KOD_PPD") or "BH"
                if kod and nama:
                    rows.append({"KOD_SEKOLAH": kod.upper().strip(), "NAMA_SEKOLAH": nama.upper().strip(),
                                 "KOD_PPD": kod_ppd.upper().strip(), "PPD": PPD_MAP.get(kod_ppd.upper().strip(), "")})
            df = pd.DataFrame(rows)
            order_map = {k: i for i, k in enumerate(KOD_DAERAH)}
            if not df.empty:
                df["order"] = df["KOD_PPD"].map(order_map)
                df = df.sort_values(["order", "NAMA_SEKOLAH"]).reset_index(drop=True)
                df["ID"] = df.index + 1
                df["PASSWORD"] = df["ID"].astype(str)
            return df
        except Exception:
            return pd.DataFrame()

    df_sekolah_all = load_sekolah_list_popup()

    # --- Dialogs ---
    @st.dialog("🏫 Pilih Daerah - SUP")
    def dlg_daerah_sup():
        st.write("Sila pilih daerah PPD untuk senarai sekolah:")
        cols = st.columns(2)
        for i, kod in enumerate(KOD_DAERAH):
            label = f"{kod} - {PPD_MAP[kod]}"
            with cols[i % 2]:
                if st.button(label, key=f"dlg_sup_daerah_{kod}", use_container_width=True):
                    st.session_state.sel_ppd_sup = kod
                    st.session_state.popup_stage = "SEKOLAH"
                    st.rerun()

    @st.dialog("🏫 Pilih Sekolah")
    def dlg_sekolah_sup():
        ppd = st.session_state.sel_ppd_sup
        st.write(f"Daerah: **{ppd} - {PPD_MAP.get(ppd,'')}**")
        if df_sekolah_all.empty:
            st.warning("Tiada data sekolah.")
            return
        df_f = df_sekolah_all[df_sekolah_all["KOD_PPD"] == ppd]
        if df_f.empty:
            st.warning(f"Tiada sekolah untuk {ppd}")
            return
        q = st.text_input("Cari sekolah (kod/nama):", key="cari_sek_sup")
        if q:
            df_f = df_f[df_f["KOD_SEKOLAH"].str.contains(q.upper()) | df_f["NAMA_SEKOLAH"].str.contains(q.upper())]
        st.caption(f"{len(df_f)} sekolah dijumpai")
        for _, row in df_f.head(100).iterrows():
            lab = f"{row['KOD_SEKOLAH']} - {row['NAMA_SEKOLAH'][:40]}"
            if st.button(lab, key=f"dlg_sup_sek_{row['KOD_SEKOLAH']}", use_container_width=True):
                st.session_state.sel_sekolah_kod = row['KOD_SEKOLAH']
                st.session_state.sel_sekolah_nama = row['NAMA_SEKOLAH']
                st.session_state.sel_sekolah_id = int(row['ID'])
                st.session_state.popup_stage = "PASSWORD_SUP"
                st.rerun()

    @st.dialog("🔑 Password SUP")
    def dlg_pwd_sup():
        kod = st.session_state.sel_sekolah_kod
        nama = st.session_state.sel_sekolah_nama
        sid = st.session_state.sel_sekolah_id
        st.write(f"**{kod}** - {nama}")
        st.caption(f"ID: {sid}")
        pwd = st.text_input("Masukkan Password", type="password", key="pwd_sup_popup")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Masuk", type="primary", use_container_width=True):
                valid = [str(sid), f"12345{sid}", "12345", "a"]
                if pwd.strip() in valid or pwd.strip().lower() == "a":
                    info = get_sekolah(kod)
                    info["kod_sekolah"] = kod
                    info["nama_sekolah"] = nama
                    info["kod_ppd"] = st.session_state.sel_ppd_sup
                    st.session_state.role = "SUP"
                    st.session_state.kod = kod
                    st.session_state.info = info
                    st.session_state.sup_id = sid
                    st.session_state.popup_stage = None
                    st.rerun()
                else:
                    st.session_state.popup_stage = "ERROR"
                    st.session_state.error_msg = "Password SUP salah!"
                    st.rerun()
        with c2:
            if st.button("Batal", use_container_width=True):
                st.session_state.popup_stage = None
                st.rerun()

    @st.dialog("🏢 Pilih Daerah - PPD")
    def dlg_daerah_ppd():
        st.write("Sila pilih daerah PPD:")
        cols = st.columns(2)
        for i, kod in enumerate(KOD_DAERAH):
            label = f"{kod} - {PPD_MAP[kod]}"
            with cols[i % 2]:
                if st.button(label, key=f"dlg_ppd_daerah_{kod}", use_container_width=True):
                    st.session_state.sel_ppd_sup = kod
                    st.session_state.popup_stage = "PASSWORD_PPD"
                    st.rerun()

    @st.dialog("🔑 Password PPD")
    def dlg_pwd_ppd():
        kod = st.session_state.sel_ppd_sup
        ppd_id = KOD_DAERAH.index(kod) + 1 if kod in KOD_DAERAH else 1
        st.write(f"**PPD {kod} - {PPD_MAP.get(kod,'')}**")
        pwd = st.text_input("Masukkan Password PPD", type="password", key="pwd_ppd_popup")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Masuk PPD", type="primary", use_container_width=True):
                valid = [chr(96+ppd_id), str(ppd_id), f"12345{ppd_id}", kod.lower(), "a","b","c","d","e","f","g","h","i","j"]
                if pwd.strip().lower() in [v.lower() for v in valid]:
                    st.session_state.role = "PPD"
                    st.session_state.kod = kod
                    st.session_state.ppd_id = ppd_id
                    st.session_state.popup_stage = None
                    st.rerun()
                else:
                    st.session_state.popup_stage = "ERROR"
                    st.session_state.error_msg = f"Password PPD {kod} salah!"
                    st.rerun()
        with c2:
            if st.button("Batal", use_container_width=True):
                st.session_state.popup_stage = None
                st.rerun()

    @st.dialog("🏛️ Log Masuk JPN")
    def dlg_pwd_jpn():
        st.write("**JPN Selangor - Pentadbir Sistem**")
        jpn_id = st.text_input("ID JPN", value="1", key="jpn_id_popup")
        pwd = st.text_input("Password JPN", type="password", key="pwd_jpn_popup")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Masuk JPN", type="primary", use_container_width=True):
                if jpn_id == "1" and pwd.strip().lower() in ["a","1","123451","12345"]:
                    st.session_state.role = "JPN"
                    st.session_state.popup_stage = None
                    st.rerun()
                else:
                    st.session_state.popup_stage = "ERROR"
                    st.session_state.error_msg = "ID atau Password JPN salah!"
                    st.rerun()
        with c2:
            if st.button("Batal", use_container_width=True):
                st.session_state.popup_stage = None
                st.rerun()

    @st.dialog("❌ Salah Password")
    def dlg_error():
        st.error(st.session_state.get("error_msg","Password salah!"))
        st.write("Sila cuba semula.")
        if st.button("OK, Cuba Lagi", use_container_width=True, type="primary"):
            # kembali ke stage sebelum error
            if "PASSWORD" in str(st.session_state.popup_stage):
                pass
            st.session_state.popup_stage = None
            st.rerun()

    # --- Trigger dialogs based on stage ---
    if st.session_state.popup_stage == "DAERAH_SUP":
        dlg_daerah_sup()
    elif st.session_state.popup_stage == "SEKOLAH":
        dlg_sekolah_sup()
    elif st.session_state.popup_stage == "PASSWORD_SUP":
        dlg_pwd_sup()
    elif st.session_state.popup_stage == "DAERAH_PPD":
        dlg_daerah_ppd()
    elif st.session_state.popup_stage == "PASSWORD_PPD":
        dlg_pwd_ppd()
    elif st.session_state.popup_stage == "PASSWORD_JPN":
        dlg_pwd_jpn()
    elif st.session_state.popup_stage == "ERROR":
        dlg_error()

    # --- Butang utama macam HTML ---
    st.markdown("""
    <style>
    .main-btn {
        background: #ffffff;
        border: 1px solid #d6e2f5;
        border-radius: 20px;
        padding: 22px 18px;
        text-align: center;
        box-shadow: 0 8px 24px rgba(13,71,161,0.08);
        transition: all .2s ease;
        cursor: pointer;
    }
    .main-btn:hover { transform: translateY(-3px); box-shadow: 0 12px 32px rgba(13,71,161,0.16); border-color: #1565c0; }
    .main-btn h3 { margin: 8px 0 4px 0; color: #0d47a1; font-weight: 800; }
    .main-btn p { margin: 0; color: #0d47a1; font-size: 0.85rem; }
    </style>
    """, unsafe_allow_html=True)

    render_bar_tahun("login")
    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        st.markdown('<div class="main-btn"><div style="font-size:32px">🏫</div><h3>SUP</h3><p>Penyelia Sekolah</p></div>', unsafe_allow_html=True)
        if st.button("Masuk SUP", key="btn_main_sup", use_container_width=True, type="primary"):
            st.session_state.popup_stage = "DAERAH_SUP"
            st.rerun()
    with c2:
        st.markdown('<div class="main-btn"><div style="font-size:32px">🏢</div><h3>PPD</h3><p>Pejabat Daerah</p></div>', unsafe_allow_html=True)
        if st.button("Masuk PPD", key="btn_main_ppd", use_container_width=True, type="primary"):
            st.session_state.popup_stage = "DAERAH_PPD"
            st.rerun()
    with c3:
        st.markdown('<div class="main-btn"><div style="font-size:32px">🏛️</div><h3>JPN</h3><p>Pentadbir Negeri</p></div>', unsafe_allow_html=True)
        if st.button("Masuk JPN", key="btn_main_jpn", use_container_width=True, type="primary"):
            st.session_state.popup_stage = "PASSWORD_JPN"
            st.rerun()

    st.markdown("<div style='text-align:center;margin-top:28px;color:#0d47a1;font-size:12px;'>Sistem Pelantikan Petugas SPM Selangor 2026 · JPN Selangor</div>".replace("2026", str(tahun_aktif())), unsafe_allow_html=True)
    st.stop()

# ================= FLYOUT SUB MENU V36 - BUTANG PETAK BIRU / TULISAN PUTIH =================
st.markdown("""
<style>
/* Semua butang menu & sub menu: petak biru, tulisan putih */
[class*="st-key-flymenu_"] button,
[class*="st-key-flysub_"] button {
    background: #0d47a1 !important;
    border: 1px solid #002171 !important;
    border-radius: 3px !important;
    color: #ffffff !important;
    min-height: 38px !important;
    padding: 6px 10px !important;
    justify-content: flex-start !important;
    box-shadow: none !important;
}
[class*="st-key-flymenu_"] button *,
[class*="st-key-flysub_"] button * {
    color: #ffffff !important;
    font-size: 0.78rem !important;
    font-weight: 700 !important;
    text-align: left !important;
    white-space: normal !important;
}
[class*="st-key-flymenu_"] button:hover,
[class*="st-key-flysub_"] button:hover {
    background: #1565c0 !important;
    border-color: #002171 !important;
}
/* Butang aktif: biru tua + jalur kuning di kiri */
[class*="st-key-flymenu_"] button[kind="primary"],
[class*="st-key-flysub_"] button[kind="primary"],
[class*="st-key-flymenu_"] [data-testid="stBaseButton-primary"],
[class*="st-key-flysub_"] [data-testid="stBaseButton-primary"] {
    background: #002171 !important;
    border-color: #002171 !important;
    box-shadow: inset 5px 0 0 #ffffff !important;
}
/* Flyout terapung sebaris dengan menu terpilih (tidak tolak menu lain ke bawah) */
[data-testid="stColumn"]:has(.fly-anchor),
[data-testid="column"]:has(.fly-anchor) { position: relative; }
.st-key-flywrap {
    position: absolute !important; top: 0; left: 0; right: 0;
    width: 100% !important; z-index: 999;
}
.fly-anchor { display: block; height: 0; }
/* Panel flyout */
.fly-panel {
    background: #ffffff;
    border: 2px solid #0d47a1;
    border-radius: 6px;
    padding: 6px 8px;
    margin: 0 0 8px 0;
    position: relative;
    box-shadow: 4px 4px 12px rgba(13,71,161,0.18);
}
.fly-panel:before {
    content: "";
    position: absolute; left: -10px; top: 12px;
    border-top: 8px solid transparent; border-bottom: 8px solid transparent;
    border-right: 10px solid #0d47a1;
}
.fly-title {
    font-weight: 900; color: #0d47a1 !important; font-size: 0.72rem;
    text-align: center; letter-spacing: .5px;
}
</style>
""", unsafe_allow_html=True)


def render_menu_buttons(skey, items):
    """Menu utama sebagai butang petak biru. Pulangkan kunci menu aktif."""
    keys = [k for k, _ in items]
    if st.session_state.get(skey) not in keys:
        st.session_state[skey] = keys[0]
    cur = st.session_state[skey]
    for k, label in items:
        if st.button(label, key=f"flymenu_{skey}_{k}", use_container_width=True,
                     type="primary" if k == cur else "secondary"):
            if k != cur:
                st.session_state[skey] = k
                st.rerun()
    return st.session_state[skey]


def render_flyout(menu, fly_map, dash_key, prefix):
    """Flyout sub menu (terapung, sebaris dengan menu terpilih). Pulangkan kunci sub aktif (atau None)."""
    subs = fly_map.get(menu)
    if not subs:
        return None
    skey = dash_key if (dash_key and menu == "dashboard") else f"{prefix}_{menu}"
    keys = [k for k, _ in subs]
    if st.session_state.get(skey) not in keys:
        st.session_state[skey] = keys[0]
    cur = st.session_state[skey]
    st.markdown('<span class="fly-anchor"></span>', unsafe_allow_html=True)
    with st.container(key="flywrap"):
        st.markdown('<div class="fly-panel"><div class="fly-title">SUB MENU</div></div>', unsafe_allow_html=True)
        for k, label in subs:
            if st.button(label, key=f"flysub_{skey}_{k}", use_container_width=True,
                         type="primary" if k == cur else "secondary"):
                if k != cur:
                    st.session_state[skey] = k
                    st.rerun()
    return st.session_state[skey]


def render_menu_flyout(skey, items, fly_map, dash_key, prefix):
    """Menu utama (butang biru). Flyout keluar di baris menu yang dipilih. Pulangkan (menu, sub_aktif)."""
    keys = [k for k, _ in items]
    if st.session_state.get(skey) not in keys:
        st.session_state[skey] = keys[0]
    cur = st.session_state[skey]
    fly_cur = None
    for k, label in items:
        c_menu, c_fly = st.columns([1, 1], gap="small")
        with c_menu:
            if st.button(label, key=f"flymenu_{skey}_{k}", use_container_width=True,
                         type="primary" if k == cur else "secondary"):
                if k != cur:
                    st.session_state[skey] = k
                    st.rerun()
        if k == cur:
            with c_fly:
                fly_cur = render_flyout(k, fly_map, dash_key, prefix)
    return cur, fly_cur


FLY_SUP = {
    'dashboard': [('utama', '🏠 Utama'), ('pusat', '📍 Senarai Pusat'), ('guru', '👥 Guru Terkini')],
    'senarai':   [('filter', '🔍 Senarai & Filter'), ('edit', '✏️ Edit Data Guru')],
    'cadangan':  [('pilih', '👥 Pilih & Cadang'), ('senarai', '📋 Senarai Cadangan')],
    'surat':     [('jadual', '📑 Jadual Jawatan'), ('individu', '📄 Surat Individu')],
}
FLY_PPD = {
    'dashboard':  [('ringkasan', '📊 Ringkasan'), ('status', '📍 Status Pusat'), ('berwarna', '🎨 Paparan Warna'), ('sekolah', '🏫 Sekolah & Export')],
    'pusat':      [('senarai', '📋 Senarai Pusat'), ('poskod', '📮 Poskod Pusat')],
    'jana':       [('auto', '🌍 Jana Auto Poskod'), ('jawatan', '👑 Ikut Jawatan')],
    'hasil':      [('ringkasan', '📋 Ringkasan Pusat'), ('sekolah', '🏫 Ikut Sekolah Asal'), ('guru', '👥 Semua Guru')],
    'semakan':    [('semak', '🔍 Semakan Lantikan'), ('kosong', '➕ Isi Kekosongan')],
    'kelulusan':  [('keseluruhan', '✅ Lulus Keseluruhan'), ('pusat', '🏫 Lulus Ikut Pusat')],
    'selenggara': [('form', '➕ Tambah Bilik Kebal'), ('senarai', '📋 Senarai Bilik Kebal'), ('import', '📤 Import Excel'), ('penyelia', '🔐 Tempatkan Penyelia'), ('surat', '📄 Jana Surat Penyelia')],
    'jana_surat': [('keseluruhan', '📄 Semua Surat'), ('pusat', '🏫 Ikut Pusat'), ('sekolah', '🏫 Ikut Sekolah Asal')],
}
FLY_JPN = {
    'dashboard': [('ringkasan', '📊 Ringkasan'), ('ppd', '🏢 Breakdown PPD')],
    'sekolah':   [('senarai', '🏫 Senarai Sekolah'), ('import', '📤 Import Sekolah'), ('auto', '⚡ Auto Generate')],
    'pusat':     [('senarai', '📋 Senarai Pusat'), ('fix', '🔧 Fix Jumlah Calon'), ('tambah', '➕ Tambah Pusat'), ('import', '📤 Import Pusat'), ('kosong', '🗑️ Kosongkan Pusat')],
    'guru':      [('import', '📤 Import Master 60K'), ('data', '📊 Data Sedia Ada')],
    'admin':     [('status', '🩺 Status Sistem'), ('table', '🛠️ Buat Table'), ('tahun', '📅 Urus Tahun')],
}
# ================= END FLYOUT V36 =================


# ================= ROLE: SUP (ASAL - TAK KACAU) =================


# ================= ROLE: SUP =================
if st.session_state.role == "SUP":
    kod = st.session_state.kod
    info = st.session_state.info

    # Custom Layout
    col_menu, col_main = st.columns([1.45, 3.2], gap="large")

    with col_menu:
        st.markdown('<div class="custom-sidebar">', unsafe_allow_html=True)
        st.markdown(f"### 🏫 SUP {kod}")
        st.markdown(f"<div style='color:#0d47a1; font-weight:700; font-size:13px; margin-bottom:4px;'>{info.get('nama_sekolah', '')}</div><div style='color:#0d47a1; font-size:12px; margin-bottom:8px;'>{info.get('kod_ppd', 'BH')} - {PPD_MAP.get(info.get('kod_ppd', 'BH'), '')}</div>", unsafe_allow_html=True)
        try:
            df_pusat_sidebar = get_pusat_df()
            no_pusat_list_sidebar = []
            for _, r in df_pusat_sidebar.iterrows():
                d = r.get("data") if isinstance(r.get("data"), dict) else {}
                if isinstance(d, str):
                    try: d = json.loads(d)
                    except: d = {}
                ks_tuan = str(r.get("kod_sekolah_tuan_rumah") or r.get("kod_sekolah") or r.get("KOD_SEKOLAH") or d.get("KOD_SEKOLAH") or d.get("KOD SEKOLAH") or "").upper().strip()
                ks_biasa = str(r.get("kod_sekolah") or d.get("KOD_SEKOLAH") or "").upper().strip()
                if ks_tuan == kod.upper().strip() or ks_biasa == kod.upper().strip():
                    no_p = str(r.get("no_pusat") or r.get("kod_pusat") or r.get("NO_PUSAT") or d.get("NO_PUSAT") or d.get("NO PUSAT") or "").upper().strip()
                    if no_p and no_p not in no_pusat_list_sidebar:
                        no_pusat_list_sidebar.append(no_p)
            if no_pusat_list_sidebar:
                no_pusat_str = ", ".join(no_pusat_list_sidebar)
                st.markdown('<div class="no-pusat-box"><div class="no-pusat-label">📍 NO PUSAT SEKOLAH:</div><div class="no-pusat-value">' + no_pusat_str + '</div></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="no-pusat-box" style="background:#bbdefb; border-color:#0d47a1;"><div class="no-pusat-label" style="color:#0d47a1;">⚠️ TIADA NO PUSAT:</div><div class="no-pusat-value" style="font-size:12px;">Tiada pusat dijumpai untuk ' + kod + '<br>Hubungi PPD</div></div>', unsafe_allow_html=True)
        except Exception as e:
            st.markdown("<div style='background:#e3f2fd; padding:8px; border-radius:6px; font-size:11px;'>Error load pusat: " + str(e) + "</div>", unsafe_allow_html=True)
        add_refresh_button()

        if "sup_dash_sub" not in st.session_state:
            st.session_state.sup_dash_sub = "utama"

        MENU_SUP = [('dashboard', '📊 Dashboard'), ('senarai', '📋 Senarai Guru'), ('tambah', '➕ Tambah Guru'),
                    ('import', '📤 Import Excel'), ('buang', '🗑️ Buang Guru'), ('cadangan', '📝 Cadangan Lantikan'),
                    ('hantar', '📤 Hantar ke PPD'), ('petugas', '👥 Petugas Hadir di Sekolah Saya'), ('surat', '📄 Surat Lantikan Saya'), ('keluar', '🚪 Log Keluar')]

        menu, fly_cur = render_menu_flyout("sup_menu_sel", MENU_SUP, FLY_SUP, "sup_dash_sub", "fly_sup")

        st.markdown('</div>', unsafe_allow_html=True)
    with col_main:
        render_bar_tahun("sup")
        show_flash()
        df_guru = get_guru_df(kod)

        if menu == "keluar":
            reset_sesi_kekal_tahun()
            st.rerun()

        elif menu == "dashboard":
            st.header(f"Dashboard SUP - {kod} {info.get('nama_sekolah', '')}")
            st.markdown(f"**Kod Sekolah:** `{kod}` | **PPD:** `{info.get('kod_ppd','')} - {PPD_MAP.get(info.get('kod_ppd',''),'')}` | **Nama:** {info.get('nama_sekolah','')}")
            try:
                df_pusat_all = get_pusat_df()
                pusat_sekolah = []
                for _, r in df_pusat_all.iterrows():
                    d = r.get("data") if isinstance(r.get("data"), dict) else {}
                    if isinstance(d, str):
                        try: d = json.loads(d)
                        except: d = {}
                    ks_tuan = str(r.get("kod_sekolah_tuan_rumah") or r.get("kod_sekolah") or r.get("KOD_SEKOLAH") or d.get("KOD_SEKOLAH") or d.get("KOD SEKOLAH") or d.get("KOD_SEKOLAH_TUAN_RUMAH") or "").upper().strip()
                    ks_biasa = str(r.get("kod_sekolah") or d.get("KOD_SEKOLAH") or "").upper().strip()
                    if ks_tuan == kod.upper().strip() or ks_biasa == kod.upper().strip():
                        calon = r.get("jumlah_calon") or r.get("calon") or r.get("JUMLAH_CALON") or d.get("JUMLAH_CALON") or d.get("CALON") or 0
                        try: calon_i = int(float(str(calon) or 0))
                        except: calon_i = 0
                        kelas = kira_kelas_dari_calon(calon_i)
                        petugas_k9 = kira_petugas_dari_kelas(kelas)
                        sekolah_perlu = kira_sekolah_perlu_calonkan(kelas)
                        no_pusat_val = str(r.get("no_pusat") or r.get("kod_pusat") or r.get("NO_PUSAT") or d.get("NO_PUSAT") or d.get("NO PUSAT") or d.get("KOD_PUSAT") or "").upper().strip()
                        nama_pusat_val = str(r.get("nama_pusat") or r.get("NAMA_PUSAT") or d.get("NAMA_PUSAT") or d.get("NAMA PUSAT") or "").upper().strip()
                        pusat_sekolah.append({"NO_PUSAT": no_pusat_val, "NAMA_PUSAT": nama_pusat_val, "CALON": calon_i, "KELAS": kelas, "PETUGAS_K9": petugas_k9, "SEKOLAH_PERLU": sekolah_perlu})
            except Exception as e:
                st.error(f"Error load pusat: {e}")
                pusat_sekolah = []

            if pusat_sekolah:
                total_calon = sum([p["CALON"] for p in pusat_sekolah])
                total_kelas = sum([p["KELAS"] for p in pusat_sekolah])
                total_petugas = sum([p["PETUGAS_K9"] for p in pusat_sekolah])
                total_perlu = sum([p["SEKOLAH_PERLU"] for p in pusat_sekolah])
                no_pusat_list = ", ".join([f"{p['NO_PUSAT']}" for p in pusat_sekolah if p['NO_PUSAT']])
            else:
                total_calon = 0; total_kelas = 0; total_petugas = 0; total_perlu = 0; no_pusat_list = "-"

            sub = st.session_state.get("sup_dash_sub", "utama")

            if sub == "utama":
                if pusat_sekolah:
                    try:
                        st.markdown(jpn_kad_pusat(no_pusat_list, total_kelas, total_petugas, total_perlu, kod), unsafe_allow_html=True)
                    except:
                        st.markdown(f"<div style='background:white; padding:20px; border-radius:12px; border:3px solid #1565c0; margin-bottom:20px;'><h3>🏫 KEPERLUAN PENGAWAS - {kod}</h3><div>NO PUSAT: <b>{no_pusat_list}</b> | Kelas: {total_kelas} | Petugas: {total_petugas} | Perlu: {total_perlu}</div></div>", unsafe_allow_html=True)
                else:
                    st.warning(f"⚠️ Tiada pusat dijumpai untuk sekolah {kod}")
                st.markdown("<div style='background:#E3F2FD; border:1px dashed #CFDBF0; border-radius:8px; padding:8px 12px; font-size:0.8rem; color:#0D47A1; text-align:center; margin-bottom:12px;'>📌 Sub-menu ada di sebelah kiri (popup) - pilih di kotak sebelah kanan Dashboard</div>", unsafe_allow_html=True)
                c1, c2, c3, c4 = st.columns(4)
                with c1: st.metric("Jumlah Guru", len(df_guru))
                with c2:
                    try:
                        cnt = supa.table("guru_master").select("id", count="exact").execute()
                        st.metric("Total Guru Selangor", cnt.count)
                    except: st.metric("Total Guru Selangor", "-")
                with c3: st.metric("Pusat Sekolah Ini", len(pusat_sekolah))
                with c4:
                    try:
                        cad = get_cadangan_df(kod_sekolah=kod)
                        st.metric("Cadangan Dihantar", len(cad))
                    except: st.metric("Cadangan", "0")
                st.markdown("---")
                st.subheader("Guru Terkini (Ringkasan 5 Terbaru)")
                if not df_guru.empty:
                    st.dataframe(df_guru[["NAMA GURU", "IC", "TELEFON", "JAWATAN CADANGAN"]].head(5), use_container_width=True, hide_index=True)
                else:
                    st.warning("Belum ada guru. Sila Tambah Guru atau Import Excel.")

            elif sub == "pusat":
                st.markdown(f"<div style='background:white; border:2px solid #0D47A1; border-radius:12px; padding:14px 16px; margin-bottom:14px;'><div style='font-weight:900; color:#0D47A1; font-size:1.1rem;'>📍 Senarai Pusat Sekolah Anda - {kod}</div><div style='font-size:0.85rem; color:#0D47A1; margin-top:4px;'>Paparan dashboard utama disembunyikan. Klik Utama di popup sebelah untuk kembali.</div></div>", unsafe_allow_html=True)
                if pusat_sekolah:
                    df_pusat_display = pd.DataFrame(pusat_sekolah)
                    cols_order = ["NO_PUSAT", "NAMA_PUSAT", "CALON", "KELAS", "PETUGAS_K9", "SEKOLAH_PERLU"]
                    df_pusat_display = df_pusat_display[cols_order] if all(c in df_pusat_display.columns for c in cols_order) else df_pusat_display
                    st.dataframe(df_pusat_display, use_container_width=True, hide_index=True)
                    st.success(f"Ada {len(pusat_sekolah)} pusat | {total_calon} calon | {total_kelas} kelas")
                else:
                    st.warning("Tiada pusat dijumpai")

            elif sub == "guru":
                st.markdown(f"<div style='background:white; border:2px solid #0D47A1; border-radius:12px; padding:14px 16px; margin-bottom:14px;'><div style='font-weight:900; color:#0D47A1; font-size:1.1rem;'>👥 Guru Terkini - {kod}</div><div style='font-size:0.85rem; color:#0D47A1; margin-top:4px;'>Paparan dashboard utama disembunyikan. Klik Utama di popup sebelah untuk kembali.</div></div>", unsafe_allow_html=True)
                if not df_guru.empty:
                    cols_show = [c for c in ["NAMA GURU", "IC", "TELEFON", "JAWATAN CADANGAN", "POSKOD_RUMAH"] if c in df_guru.columns]
                    st.dataframe(df_guru[cols_show] if cols_show else df_guru, use_container_width=True, hide_index=True)
                    st.info(f"Jumlah: {len(df_guru)} guru")
                else:
                    st.warning("Belum ada guru. Sila Tambah Guru atau Import Excel.")

        elif menu == "senarai":
            st.header(f"Senarai Guru - {kod} - Lengkap")
            if df_guru.empty:
                st.info("guru_master kosong untuk sekolah ini. Sila Tambah Guru atau Import Excel.")
            else:
                st.success(f"Ada {len(df_guru)} guru di {kod}")

                # ===== FILTER IKUT JAWATAN - SUP SENARAI GURU (BARU) =====
                if fly_cur == "filter":
                    st.markdown("### 🔍 Filter Ikut Jawatan - Senarai Guru")
                    jawatan_sup_list = []
                    col_jawatan_sup = "JAWATAN CADANGAN" if "JAWATAN CADANGAN" in df_guru.columns else "JAWATAN_CADANGAN" if "JAWATAN_CADANGAN" in df_guru.columns else None
                    if col_jawatan_sup:
                        for _, r in df_guru.iterrows():
                            j = str(r.get(col_jawatan_sup, "")).strip()
                            if j and j not in jawatan_sup_list:
                                jawatan_sup_list.append(j)
                    order_j = ["Ketua Pengawas", "Timbalan Ketua Pengawas", "Penyelia Kawasan", "Pengawas Peperiksaan", "Juru Tulis", "Juru Baca", "Ketua Pengawas Hospital", "Pengawas Hospital", "Pengawas Pengiring", "Pengemas Bilik"]
                    jawatan_sup_sorted = sorted(jawatan_sup_list, key=lambda x: (order_j.index(x) if x in order_j else 99, x))

                    if "filter_jawatan_sup_senarai" not in st.session_state:
                        st.session_state["filter_jawatan_sup_senarai"] = []

                    col_f1_sup, col_f2_sup, col_f3_sup, col_f4_sup = st.columns([2,1,1,1])
                    with col_f1_sup:
                        safe_default_sup = [x for x in st.session_state["filter_jawatan_sup_senarai"] if x in jawatan_sup_sorted]
                        if not jawatan_sup_sorted:
                            jawatan_sup_sorted = ["Ketua Pengawas", "Timbalan Ketua Pengawas", "Penyelia Kawasan", "Pengawas Peperiksaan", "Juru Tulis", "Juru Baca", "Ketua Pengawas Hospital", "Pengawas Hospital", "Pengawas Pengiring", "Pengemas Bilik"]
                            safe_default_sup = st.session_state["filter_jawatan_sup_senarai"]
                        if st.session_state["filter_jawatan_sup_senarai"] and not safe_default_sup:
                            for v in st.session_state["filter_jawatan_sup_senarai"]:
                                if v not in jawatan_sup_sorted:
                                    jawatan_sup_sorted.append(v)
                            safe_default_sup = st.session_state["filter_jawatan_sup_senarai"]
                        filter_jawatan_sup = st.multiselect("Filter Jawatan", jawatan_sup_sorted, default=safe_default_sup, placeholder="Kosong = semua jawatan")
                        if filter_jawatan_sup != st.session_state["filter_jawatan_sup_senarai"]:
                            st.session_state["filter_jawatan_sup_senarai"] = filter_jawatan_sup
                    with col_f2_sup:
                        current_sup_filter = filter_jawatan_sup if filter_jawatan_sup else st.session_state.get("filter_jawatan_sup_senarai", [])
                        if current_sup_filter:
                            filtered_count = len(df_guru[df_guru[col_jawatan_sup].astype(str).str.strip().isin(current_sup_filter)]) if col_jawatan_sup else 0
                            st.metric(f"Filter: {len(current_sup_filter)}", f"{filtered_count} guru")
                        else:
                            st.metric("Semua", f"{len(df_guru)} guru")
                    with col_f3_sup:
                        if st.button("🔐 Hanya Penyelia", use_container_width=True, key="btn_filter_pk_sup"):
                            st.session_state["filter_jawatan_sup_senarai"] = ["Penyelia Kawasan"]
                            st.rerun()
                    with col_f4_sup:
                        if st.button("🔄 Clear", use_container_width=True, key="btn_clear_sup"):
                            st.session_state["filter_jawatan_sup_senarai"] = []
                            st.rerun()

                    current_sup_filter2 = st.session_state.get("filter_jawatan_sup_senarai", [])
                    df_guru_filtered = df_guru
                    if current_sup_filter2 and col_jawatan_sup:
                        df_guru_filtered = df_guru[df_guru[col_jawatan_sup].astype(str).str.strip().isin(current_sup_filter2)].copy()
                        st.success(f"✅ Filter: {', '.join(current_sup_filter2)} - {len(df_guru_filtered)} guru")

                    # Pecahan ikut jawatan
                    if not df_guru_filtered.empty and col_jawatan_sup:
                        j_counts = df_guru_filtered[col_jawatan_sup].value_counts().to_dict()
                        if j_counts:
                            st.markdown("#### 📊 Pecahan Ikut Jawatan")
                            cols_j_sup = st.columns(len(j_counts))
                            for idx, (j, cnt) in enumerate(sorted(j_counts.items(), key=lambda x: (order_j.index(x[0]) if x[0] in order_j else 99, x[0]))):
                                with cols_j_sup[idx % len(cols_j_sup)]:
                                    icon = "👑" if "Ketua Pengawas" in j and "Timbalan" not in j else "🎖️" if "Timbalan" in j else "🔐" if "Penyelia" in j else "👨‍🏫"
                                    st.metric(f"{icon} {j}", cnt)

                    cols_to_show = [c for c in ["NAMA GURU", "IC", "JANTINA", "POSKOD_RUMAH", "ALAMAT_RUMAH", "TELEFON_GURU", "EMAIL_GURU", "JAWATAN CADANGAN", "JAWATAN_CADANGAN", "PENGALAMAN_SPM", "KOD_SEKOLAH_ASAL", "NAMA_SEKOLAH_ASAL", "NO_PUSAT_ASAL"] if c in df_guru_filtered.columns]
                    if cols_to_show:
                        st.dataframe(df_guru_filtered[cols_to_show], use_container_width=True, hide_index=True)
                        kosong = df_guru_filtered[df_guru_filtered["JANTINA"].isin(["", "KOSONG"]) | df_guru_filtered["POSKOD_RUMAH"].isin(["", "KOSONG"]) | df_guru_filtered["TELEFON_GURU"].isin(["", "KOSONG"])] if "JANTINA" in df_guru_filtered.columns and "POSKOD_RUMAH" in df_guru_filtered.columns and "TELEFON_GURU" in df_guru_filtered.columns else pd.DataFrame()
                        if not kosong.empty:
                            st.warning(f"⚠️ Ada {len(kosong)} guru dengan data KOSONG (JANTINA/POSKOD/ALAMAT/TELEFON/EMAIL). Sila edit di bawah.")

                    st.download_button(" Export Excel Lengkap (Ikut Filter)", to_excel(df_guru_filtered), file_name=f"guru_{kod}_lengkap_{'_'.join(filter_jawatan_sup) if filter_jawatan_sup else 'semua'}.xlsx", use_container_width=True)
                if fly_cur == "edit":
                    st.markdown("---")
                    st.subheader("✏️ Edit Data Guru (Lengkapkan yang kosong)")
                    # Use filtered list for edit too
                    df_for_edit = df_guru_filtered if 'df_guru_filtered' in locals() else df_guru
                    edit_ic = st.selectbox("Pilih IC guru untuk edit", df_for_edit["IC"].tolist() if "IC" in df_for_edit.columns else [], format_func=lambda x: f"{x} - {df_for_edit[df_for_edit['IC']==x]['NAMA GURU'].values[0] if not df_for_edit[df_for_edit['IC']==x].empty else x}")
                    if edit_ic:
                        guru_edit = df_guru[df_guru["IC"] == edit_ic].iloc[0] if not df_guru[df_guru["IC"] == edit_ic].empty else None
                        if guru_edit is not None:
                            with st.form(f"edit_{edit_ic}"):
                                c1, c2 = st.columns(2)
                                with c1:
                                    e_nama = st.text_input("NAMA GURU", value=guru_edit.get("NAMA GURU", ""))
                                    e_ic = st.text_input("IC", value=edit_ic, disabled=True)
                                    e_jantina = st.selectbox("JANTINA", ["LELAKI", "PEREMPUAN"], index=0 if guru_edit.get("JANTINA", "") == "LELAKI" else 1)
                                    e_poskod = st.text_input("POSKOD RUMAH", value=guru_edit.get("POSKOD_RUMAH", ""))
                                    e_alamat = st.text_area("ALAMAT RUMAH", value=guru_edit.get("ALAMAT_RUMAH", ""))
                                with c2:
                                    e_tel = st.text_input("TELEFON GURU", value=guru_edit.get("TELEFON_GURU", "") or guru_edit.get("TELEFON", ""))
                                    e_email = st.text_input("EMAIL GURU", value=guru_edit.get("EMAIL_GURU", ""))
                                    e_jawatan = st.selectbox("JAWATAN CADANGAN", ["Ketua Pengawas", "Timbalan Ketua Pengawas", "Penyelia Kawasan", "Pengawas Peperiksaan", "Juru Tulis", "Juru Baca", "Ketua Pengawas Hospital", "Pengawas Hospital", "Pengawas Pengiring", "Pengemas Bilik"], index=0)
                                    e_pengalaman = st.text_input("PENGALAMAN SPM", value=guru_edit.get("PENGALAMAN_SPM", ""))
                                    e_no_pusat = st.text_input("NO PUSAT ASAL", value=guru_edit.get("NO_PUSAT_ASAL", ""))

                                if st.form_submit_button("💾 Update Guru", type="primary"):
                                    try:
                                        res = supa.table("guru_master").select("id,data").eq("ic_guru", edit_ic).eq("kod_sekolah", kod).execute()
                                        if not res.data:
                                            res = supa.table("guru_master").select("id,data").eq("ic_guru", edit_ic).execute()
                                        for row in res.data or []:
                                            old_data = row.get("data") or {}
                                            if isinstance(old_data, str):
                                                try: old_data = json.loads(old_data)
                                                except: old_data = {}
                                            new_data = {**old_data, **{"NAMA GURU": e_nama.upper(), "IC": edit_ic, "JANTINA": e_jantina, "POSKOD_RUMAH": e_poskod, "ALAMAT_RUMAH": e_alamat, "TELEFON_GURU": e_tel, "EMAIL_GURU": e_email, "JAWATAN_CADANGAN": e_jawatan, "PENGALAMAN_SPM": e_pengalaman, "NO_PUSAT_ASAL": e_no_pusat, "KOD_SEKOLAH": kod, "KOD_PPD": info.get("kod_ppd", "BH"), "NAMA_SEKOLAH_ASAL": info.get("nama_sekolah", ""), "KOD_SEKOLAH_ASAL": kod}}
                                            supa.table("guru_master").update({"nama_guru": e_nama.upper(), "ic_guru": edit_ic, "data": new_data}).eq("id", row["id"]).execute()
                                        st.success(f"✅ {e_nama} berjaya update!")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Gagal update: {e}")

        elif menu == "tambah":
            st.header(f"Tambah Guru - {kod} - Lengkap Semua Maklumat")
            with st.form("tambah_guru", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    nama = st.text_input("NAMA GURU * (Wajib)")
                    ic = st.text_input("NO IC * (12 digit, Wajib)")
                    jantina = st.selectbox("JANTINA *", ["LELAKI", "PEREMPUAN"])
                    poskod = st.text_input("POSKOD RUMAH *")
                    alamat = st.text_area("ALAMAT RUMAH * (Wajib)")
                with col2:
                    tel = st.text_input("NO TELEFON GURU * (Wajib)")
                    email = st.text_input("EMAIL GURU")
                    jaw = st.selectbox("JAWATAN CADANGAN (Betul)", ["Ketua Pengawas", "Timbalan Ketua Pengawas", "Penyelia Kawasan", "Pengawas Peperiksaan", "Juru Tulis", "Juru Baca", "Ketua Pengawas Hospital", "Pengawas Hospital", "Pengawas Pengiring", "Pengemas Bilik"])
                    pengalaman = st.text_input("PENGALAMAN SPM (Tahun) - SUP isi", placeholder="Contoh: 3 tahun")
                    no_pusat_asal = st.text_input("NO PUSAT ASAL", placeholder="Contoh: BA142")

                submit = st.form_submit_button("💾 Simpan Guru Lengkap", use_container_width=True, type="primary")
                if submit:
                    if not nama or not ic or not tel or not alamat:
                        st.error("Nama, IC, Telefon, Alamat wajib isi!")
                    else:
                        data = {"NAMA GURU": nama.upper(), "IC": ic, "JANTINA": jantina, "POSKOD_RUMAH": poskod, "ALAMAT_RUMAH": alamat, "NO TELEFON GURU": tel, "TELEFON_GURU": tel, "EMAIL_GURU": email, "JAWATAN_CADANGAN": jaw, "JAWATAN CADANGAN": jaw, "PENGALAMAN_SPM": pengalaman, "PENGALAMAN": pengalaman, "NO_PUSAT_ASAL": no_pusat_asal, "KOD_SEKOLAH": kod, "KOD_SEKOLAH_ASAL": kod, "NAMA_SEKOLAH_ASAL": info.get("nama_sekolah", ""), "KOD_PPD": info.get("kod_ppd", "BH"), "KOD_PPD_ASAL": info.get("kod_ppd", "BH"), "TARIKH DAFTAR": str(datetime.date.today())}
                        try:
                            supa.table("guru_master").insert({"kod_ppd": info.get("kod_ppd", "BH").lower(), "kod_sekolah": kod, "nama_guru": nama.upper(), "ic_guru": ic, "jantina": jantina, "poskod_rumah": poskod, "alamat_rumah": alamat, "telefon_guru": tel, "email_guru": email, "jawatan_cadangan": jaw, "pengalaman_spm": pengalaman, "no_pusat_asal": no_pusat_asal, "kod_ppd_asal": info.get("kod_ppd", "BH"), "kod_sekolah_asal": kod, "nama_sekolah_asal": info.get("nama_sekolah", ""), "data": data}).execute()
                            st.success(f"✅ {nama.upper()} berjaya tambah ke {kod} dengan data lengkap!")
                            st.balloons()
                        except Exception as e:
                            try:
                                supa.table("guru_master").insert({"kod_ppd": info.get("kod_ppd", "BH").lower(), "kod_sekolah": kod, "nama_guru": nama.upper(), "ic_guru": ic, "data": data}).execute()
                                st.success(f"✅ {nama.upper()} berjaya tambah (fallback)!")
                                st.balloons()
                            except Exception as e2:
                                st.error(f"Gagal: {e2}")

        elif menu == "import":
            st.header(f"Import Excel Guru - {kod}")
            st.info("Format Excel: NAMA GURU, IC, JANTINA, NO TELEFON GURU, EMAIL GURU, ALAMAT RUMAH, KOD SEKOLAH, KOD PPD")
            st.download_button("📥 Download Template Guru (Excel Sah)", to_excel(get_template_guru()), file_name="template_guru.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            uploaded = st.file_uploader("Upload Excel Guru", type=["xlsx", "xls"])
            if uploaded:
                try:
                    df_up = pd.read_excel(uploaded)
                    st.write(f"Preview {len(df_up)} baris:")
                    st.dataframe(df_up.head(20), use_container_width=True)
                    batch_size = 500 if len(df_up) > 1000 else 1
                    if st.button(f"Import {len(df_up)} guru (Batch {batch_size})", type="primary"):
                        bar = st.progress(0)
                        status = st.empty()
                        ok = 0
                        if batch_size > 1:
                            for start in range(0, len(df_up), batch_size):
                                end = min(start + batch_size, len(df_up))
                                batch_df = df_up.iloc[start:end]
                                batch = []
                                for _, row in batch_df.iterrows():
                                    try:
                                        d = {}
                                        for k, v in row.to_dict().items():
                                            d[k] = "" if pd.isna(v) else str(v)
                                        nama = d.get("NAMA GURU", "").upper().strip()
                                        if not nama or nama == "NAN": continue
                                        kod_sek = d.get("KOD SEKOLAH", kod).upper().strip() or kod
                                        kod_ppd_val = d.get("KOD PPD", info.get("kod_ppd", "BH")).lower().strip() or info.get("kod_ppd", "BH").lower()
                                        batch.append({"kod_ppd": kod_ppd_val, "kod_sekolah": kod_sek, "nama_guru": nama, "ic_guru": d.get("IC", ""), "data": d})
                                    except: continue
                                if batch:
                                    try:
                                        supa.table("guru_master").insert(batch).execute()
                                        ok += len(batch)
                                    except Exception as e:
                                        st.warning(f"Batch {start}-{end} error: {e}")
                                bar.progress(end / len(df_up))
                                status.write(f"Progress: {end}/{len(df_up)} | OK: {ok}")
                        else:
                            for i, row in df_up.iterrows():
                                try:
                                    nama = str(row.get("NAMA GURU", "")).upper()
                                    ic = str(row.get("IC", ""))
                                    if not nama or nama == "NAN": continue
                                    d = {k: ("" if pd.isna(v) else str(v)) for k, v in row.to_dict().items()}
                                    d["KOD SEKOLAH"] = kod
                                    supa.table("guru_master").insert({"kod_ppd": info.get("kod_ppd", "BH").lower(), "kod_sekolah": kod, "nama_guru": nama, "ic_guru": ic, "data": d}).execute()
                                    ok += 1
                                except Exception as e:
                                    st.warning(f"Baris {i}: {e}")
                                bar.progress((i + 1) / len(df_up))
                        st.success(f"✅ Berjaya import {ok}/{len(df_up)} guru!")
                        st.balloons()
                except Exception as e:
                    st.error(f"Excel error: {e}")

        elif menu == "buang":
            st.header(f"Buang Guru - {kod}")
            if df_guru.empty:
                st.info("Tiada guru untuk dibuang.")
            else:
                st.dataframe(df_guru[["NAMA GURU", "IC", "TELEFON"]], use_container_width=True)
                pilih = st.multiselect("Pilih IC untuk buang (boleh pilih banyak)", df_guru["IC"].tolist(), format_func=lambda x: f"{x} - {df_guru[df_guru['IC']==x]['NAMA GURU'].values[0] if not df_guru[df_guru['IC']==x].empty else x}")
                if pilih:
                    st.warning(f"Kau nak buang {len(pilih)} guru: {', '.join(pilih)}")
                    if st.button(f"🗑️ Confirm Buang {len(pilih)} Guru", type="primary"):
                        for ic in pilih:
                            try:
                                res = supa.table("guru_master").select("id").eq("ic_guru", ic).eq("kod_sekolah", kod).execute()
                                for r in res.data or []:
                                    supa.table("guru_master").delete().eq("id", r["id"]).execute()
                            except Exception as e:
                                st.error(f"{ic}: {e}")
                        st.success(f"✅ Berjaya buang {len(pilih)} guru")
                        st.rerun()

        elif menu == "cadangan":
            st.header(f"Cadangan Lantikan - {kod} - {info.get('nama_sekolah', '')}")
            try:
                df_pusat_all2 = get_pusat_df()
                pusat_sek = []
                for _, r in df_pusat_all2.iterrows():
                    d = r.get("data") if isinstance(r.get("data"), dict) else {}
                    if isinstance(d, str):
                        try: d = json.loads(d)
                        except: d = {}
                    ks = r.get("kod_sekolah_tuan_rumah") or r.get("kod_sekolah") or d.get("KOD_SEKOLAH") or d.get("KOD SEKOLAH") or ""
                    if ks.upper().strip() == kod.upper().strip():
                        calon = r.get("jumlah_calon") or r.get("calon") or d.get("JUMLAH_CALON") or 0
                        try: calon_i = int(float(str(calon) or 0))
                        except: calon_i = 0
                        kelas = kira_kelas_dari_calon(calon_i)
                        pusat_sek.append({"calon": calon_i, "kelas": kelas})

                total_kelas_alert = sum([p["kelas"] for p in pusat_sek]) if pusat_sek else 0
                total_calon_alert = sum([p["calon"] for p in pusat_sek]) if pusat_sek else 0
                total_need_simple = kira_sekolah_perlu_calonkan(total_kelas_alert) if total_kelas_alert > 0 else 18

                if pusat_sek:
                    st.markdown(f"""
                    <div style="background:#e3f2fd; padding:15px; border-radius:10px; border-left:5px solid #0d47a1; margin-bottom:20px;">
                        <h4 style="margin:0; color:#0d47a1;">📢 KEPERLUAN WAJIB SEKOLAH ANDA - {kod}</h4>
                        <p style="margin:5px 0;">Pusat: {len(pusat_sek)} | Calon: {total_calon_alert} | Kelas: {total_kelas_alert} (1 kelas=20 calon)</p>
                        <p style="margin:5px 0; font-size:15px;">
                            <b style="color:#0d47a1;">WAJIB:</b> Ketua Pengawas 1 orang + Timbalan Ketua 1 orang<br>
                            <b style="color:#0d47a1;">OPTIONAL:</b> Penyelia Kawasan 1 orang<br>
                            <b style="color:#1565c0;">Pengawas Peperiksaan: {total_kelas_alert} orang</b> (ikut jumlah kelas)<br>
                            <b>Total Sekolah Perlu Calonkan: {total_need_simple} orang</b> (Formula: {total_calon_alert} calon /20 = {total_kelas_alert} kelas, {total_kelas_alert}+9={total_kelas_alert+9} petugas, +3 KP/TKP/Penyelia = {total_need_simple})
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info(f"Tiada pusat untuk {kod}. Contoh: 105 calon = 6 kelas = Ketua 1 + Timbalan 1 + Penyelia 1 (optional) + Pengawas 6 = 9 wajib, total 18 dengan extra.")
            except:
                total_kelas_alert = 6
                total_need_simple = 18

            if df_guru.empty:
                st.warning("Tiada guru untuk dicadang. Tambah guru dulu.")
            else:
                df_cad_existing = get_cadangan_df(kod_sekolah=kod)
                JAWATAN_BETUL = [
            "Ketua Pengawas (WAJIB 1)",
            "Timbalan Ketua Pengawas (WAJIB 1)",
            "Penyelia Kawasan (Optional)",
            "Pengawas Peperiksaan (Ikut Kelas)",
            "Juru Tulis",
            "Juru Baca",
            "Ketua Pengawas Hospital",
            "Pengawas Hospital",
            "Pengawas Pengiring",
            "Pengemas Bilik"
        ]
                if fly_cur == "pilih":
                    st.markdown("### Pilih Guru (EMAIL kosong dibenarkan)")
                    guru_pilih = st.multiselect("Pilih Guru untuk dicadangkan (boleh pilih ramai)", df_guru["IC"].tolist(), format_func=lambda x: f"{df_guru[df_guru['IC']==x]['NAMA GURU'].values[0]} - {x}", key="guru_pilih_simple")
                    col_jawatan, col_exp = st.columns(2)
                    with col_jawatan:
                        jawatan_cadang = st.selectbox("Jawatan Lantikan (Betul)", JAWATAN_BETUL, key="jawatan_simple")
                        jawatan_clean = jawatan_cadang.split(" (")[0]
                    with col_exp:
                        pengalaman_input = st.text_input("Pengalaman SPM (Tahun) - SUP isi", placeholder="Contoh: 3 tahun", key="pengalaman_simple")

                    pusat_pilih = "BA142"
                    no_pusat_asal_input = "BA142"

                    if guru_pilih:
                        st.markdown("**Preview Data Guru Dipilih (EMAIL kosong dibenarkan - akan lepas simpan):**")
                        preview_rows = []
                        for ic_prev in guru_pilih[:10]:
                            gr_prev = df_guru[df_guru["IC"] == ic_prev]
                            if not gr_prev.empty:
                                r = gr_prev.iloc[0]
                                preview_rows.append({"IC": ic_prev, "NAMA": r.get("NAMA GURU", "")[:20], "JANTINA": r.get("JANTINA", "") or "-", "POSKOD": r.get("POSKOD_RUMAH", "") or "-", "ALAMAT": (r.get("ALAMAT_RUMAH", "")[:20] or "-"), "TELEFON": r.get("TELEFON_GURU", "") or r.get("TELEFON", "") or "-", "EMAIL": r.get("EMAIL_GURU", "") or "-"})
                        if preview_rows:
                            st.dataframe(pd.DataFrame(preview_rows), use_container_width=True, hide_index=True)

                        catatan = ""
                        if st.button(f" Simpan Cadangan - {len(guru_pilih) if 'guru_pilih' in locals() and guru_pilih else 0} guru", type="primary", key="btn_simpan_simple"):
                            if not guru_pilih:
                                st.error("Pilih sekurang-kurangnya 1 guru")
                            else:
                                st.info(f"Menyimpan {len(guru_pilih)} guru...")
                                ok_count = 0
                                fail_msg = ""
                                for ic in guru_pilih:
                                    guru_row = df_guru[df_guru["IC"] == ic]
                                    if guru_row.empty: continue
                                    gr = guru_row.iloc[0]
                                    nama = gr.get("NAMA GURU", "") or ic
                                    jantina = gr.get("JANTINA", "")
                                    poskod = gr.get("POSKOD_RUMAH", "")
                                    alamat = gr.get("ALAMAT_RUMAH", "") or gr.get("ALAMAT", "")
                                    telefon = gr.get("TELEFON_GURU", "") or gr.get("TELEFON", "")
                                    email = str(gr.get("EMAIL_GURU", "") or gr.get("EMAIL", "") or "").strip()
                                    pengalaman = pengalaman_input or gr.get("PENGALAMAN_SPM", "") or gr.get("PENGALAMAN", "")
                                    kod_ppd_guru = (gr.get("KOD_PPD", "") or info.get("kod_ppd", "BA")).upper()
                                    kod_sek_guru = gr.get("KOD_SEKOLAH", "") or kod
                                    nama_sek_guru = gr.get("NAMA_SEKOLAH_ASAL", "") or gr.get("NAMA_SEKOLAH", "") or info.get("nama_sekolah", "")
                                    no_pusat_asal = no_pusat_asal_input or gr.get("NO_PUSAT_ASAL", "")
                                    pusat_pilih = "BA142"
                                    if no_pusat_asal and no_pusat_asal.strip() != "":
                                        pusat_pilih = no_pusat_asal.strip()
                                    if kod.upper() == "BFT0003":
                                        pusat_pilih = "BA142"

                                    kod_ppd_guru = kod_ppd_guru.upper()
                                    kod_sek_guru = kod_sek_guru.upper()
                                    if not no_pusat_asal or no_pusat_asal.strip() == "":
                                        no_pusat_asal = "BA142"
                                    if not kod_sek_guru or kod_sek_guru.strip() == "":
                                        kod_sek_guru = kod.upper()
                                    if not nama_sek_guru or nama_sek_guru.strip() == "":
                                        nama_sek_guru = info.get("nama_sekolah", "SAM NURUL IMAN")

                                    email = email or ""
                                    clean_insert = {"kod_ppd": kod_ppd_guru.upper(), "kod_sekolah": kod_sek_guru, "kod_sekolah_asal": kod_sek_guru, "nama_sekolah_asal": nama_sek_guru, "ic_guru": ic, "nama_guru": nama, "jantina": jantina or "L", "poskod_rumah": poskod or "0", "alamat_rumah": alamat or "-", "telefon_guru": telefon, "email_guru": email, "jawatan_cadangan": jawatan_clean, "pengalaman_spm": pengalaman, "no_pusat_asal": no_pusat_asal or "BA142", "kod_pusat": None, "kod_ppd_asal": kod_ppd_guru.upper(), "status": "DICADANGKAN", "tarikh_cadang": str(datetime.date.today()), "data": {"KOD_PPD": kod_ppd_guru.upper(), "KOD_SEKOLAH_ASAL": kod_sek_guru.upper(), "NAMA_SEKOLAH_ASAL": nama_sek_guru, "IC_GURU": ic, "NAMA_GURU": nama, "JANTINA": jantina, "POSKOD_RUMAH": poskod, "ALAMAT_RUMAH": alamat, "TELEFON_GURU": telefon, "EMAIL_GURU": email, "JAWATAN_CADANGAN": jawatan_clean, "PENGALAMAN_SPM": pengalaman, "NO_PUSAT_ASAL": no_pusat_asal or pusat_pilih, "status": "DICADANGKAN"}}

                                    minimal_insert = {"kod_ppd": kod_ppd_guru.upper(), "kod_sekolah": kod_sek_guru.upper(), "ic_guru": ic, "nama_guru": nama, "status": "DICADANGKAN"}

                                    inserted = False
                                    for attempt in [clean_insert, clean_insert, {"kod_ppd": kod_ppd_guru.upper(), "kod_sekolah": kod_sek_guru.upper(), "ic_guru": ic, "nama_guru": nama, "kod_pusat": no_pusat_asal, "jawatan_cadangan": jawatan_clean, "status": "DICADANGKAN", "tarikh_cadang": str(datetime.date.today()), "jantina": jantina or "L", "poskod_rumah": poskod or "0", "alamat_rumah": alamat or "-", "telefon_guru": telefon or "-", "email_guru": email or "", "pengalaman_spm": pengalaman or "0", "no_pusat_asal": no_pusat_asal, "kod_ppd_asal": kod_ppd_guru.upper(), "kod_sekolah_asal": kod_sek_guru.upper(), "nama_sekolah_asal": nama_sek_guru}, minimal_insert]:
                                        try:
                                            supa.table("cadangan_sup").insert(attempt).execute()
                                            inserted = True
                                            ok_count += 1
                                            break
                                        except Exception as e:
                                            fail_msg = str(e)
                                            if "duplicate" in fail_msg.lower() or "already exists" in fail_msg.lower():
                                                try:
                                                    supa.table("cadangan_sup").update(attempt).eq("ic_guru", ic).eq("kod_sekolah", kod_sek_guru.upper()).execute()
                                                    inserted = True
                                                    ok_count += 1
                                                    break
                                                except: pass
                                            continue

                                    if not inserted:
                                        st.error(f"❌ Gagal {ic} - {nama}: {fail_msg[:500]}")

                                if ok_count > 0:
                                    st.success(f"✅ Berjaya cadang {ok_count}/{len(guru_pilih)} guru sebagai {jawatan_clean} ke pusat {pusat_pilih} - SEMUA maklumat lengkap!")
                                    st.balloons()
                                    st.rerun()

                if fly_cur == "senarai":
                    st.markdown("---")
                    st.subheader(f"Senarai Cadangan Sekolah Ini - Perlu {total_need_simple if 'total_need_simple' in locals() else 18} orang")
                    st.markdown("""
                <div style="background:#ffffff; border-left:4px solid #0d47a1; padding:8px 12px; border-radius:6px; margin-bottom:10px;">
                <b>🟢 Panduan Warna:</b> Nama guru <span style="background:#ffffff; color:#0d47a1; font-weight:800; padding:2px 8px; border-radius:4px;">HIJAU</span> = Sudah hantar ke PPD |
                <span style="background:#e3f2fd; color:#0d47a1; font-weight:600; padding:2px 8px; border-radius:4px;">KUNING</span> = Baru dicadangkan, belum hantar
                </div>
                """, unsafe_allow_html=True)
                    df_cad = get_cadangan_df(kod_sekolah=kod)
                    if df_cad.empty:
                        st.info("Belum ada cadangan")
                    else:
                        try:
                            counts = df_cad["JAWATAN_CADANGAN"].value_counts() if "JAWATAN_CADANGAN" in df_cad.columns else (df_cad["jawatan_cadangan"].value_counts() if "jawatan_cadangan" in df_cad.columns else pd.Series())
                            c1, c2, c3, c4 = st.columns(4)
                            c1.metric("Ketua Pengawas", counts.get("Ketua Pengawas", 0), delta="WAJIB 1" if counts.get("Ketua Pengawas", 0) >= 1 else "BELUM CUKUP", delta_color="normal" if counts.get("Ketua Pengawas", 0) >= 1 else "inverse")
                            c2.metric("Timbalan Ketua", counts.get("Timbalan Ketua Pengawas", 0), delta="WAJIB 1" if counts.get("Timbalan Ketua Pengawas", 0) >= 1 else "BELUM CUKUP", delta_color="normal" if counts.get("Timbalan Ketua Pengawas", 0) >= 1 else "inverse")
                            c3.metric("Penyelia Kawasan", counts.get("Penyelia Kawasan", 0))
                            c4.metric("Pengawas Peperiksaan", counts.get("Pengawas Peperiksaan", 0), delta=f"Perlu {total_kelas_alert if 'total_kelas_alert' in locals() else 6}")
                        except: pass
                        # V24 FIX: Show clean without duplicate id columns
                        clean_cols = ["NAMA_GURU", "IC_GURU", "JANTINA", "POSKOD_RUMAH", "ALAMAT_RUMAH", "TELEFON_GURU", "EMAIL_GURU", "JAWATAN_CADANGAN", "STATUS", "NAMA_SEKOLAH_ASAL"]
                        # V29: find columns case-insensitive
                        cols_map = {str(c).lower(): c for c in df_cad.columns}
                        clean_show = []
                        for wanted in clean_cols:
                            if wanted in df_cad.columns:
                                clean_show.append(wanted)
                            elif wanted.lower() in cols_map:
                                clean_show.append(cols_map[wanted.lower()])
                        df_clean_show = df_cad[clean_show] if clean_show else df_cad
                        # Remove any duplicate columns by lowercase name
                        try:
                            df_clean_show = df_clean_show.loc[:, ~df_clean_show.columns.str.lower().duplicated()]
                        except:
                            pass
                        # === WARNA HIJAU UNTUK SUDAH HANTAR ===
                        try:
                            styled = style_nama_hijau_hantar(df_clean_show)
                            st.dataframe(styled, use_container_width=True)
                            st.caption("🟢 Hijau = Sudah hantar ke PPD / Lulus  |  🟡 Kuning = Baru dicadangkan (belum hantar)")
                            # Juga tunjuk legend count
                            if "STATUS" in df_clean_show.columns or "status" in df_clean_show.columns:
                                col_status = "STATUS" if "STATUS" in df_clean_show.columns else "status"
                                s_up = df_clean_show[col_status].astype(str).str.upper()
                                hantar_cnt = s_up.str.contains("HANTAR|LULUS|DIHANTAR").sum()
                                baru_cnt = len(df_clean_show) - hantar_cnt
                                c1, c2 = st.columns(2)
                                c1.success(f"🟢 Sudah Hantar: {hantar_cnt} guru")
                                c2.warning(f"🟡 Belum Hantar: {baru_cnt} guru")
                        except Exception as e:
                            st.dataframe(df_clean_show, use_container_width=True)
                            st.caption(f"Style error: {e}")
                        # === END WARNA ===
                        st.download_button("📥 Export Cadangan", to_excel(df_clean_show), file_name=f"cadangan_{kod}.xlsx")

        elif menu == "hantar":
            st.header(f"Hantar Cadangan ke PPD {info.get('kod_ppd', 'BA')}")
            df_cad = get_cadangan_df(kod_sekolah=kod)
            if df_cad.empty:
                st.warning("Belum ada cadangan. Pergi menu Cadangan Lantikan dulu.")
            else:
                kod_ppd_sup = str(info.get('kod_ppd', 'BA')).upper()
                # V23 FIX: check both STATUS and status columns
                if "STATUS" in df_cad.columns:
                    status_s = df_cad["STATUS"].astype(str)
                elif "status" in df_cad.columns:
                    status_s = df_cad["status"].astype(str)
                else:
                    status_s = pd.Series([""] * len(df_cad), index=df_cad.index)
                status_s = status_s.fillna("").astype(str).str.upper()
                # Also check alternative column if empty
                if "status" in df_cad.columns and (status_s == "").all():
                    status_s = df_cad["status"].fillna("").astype(str).str.upper()
                m_lulus = status_s.str.contains("LULUS", na=False)
                m_hantar = status_s.str.contains("HANTAR", na=False) & ~m_lulus
                m_baru = ~(m_lulus | m_hantar)   # DICADANGKAN / TOLAK PPD - boleh dihantar (semula)
                bil_baru = int(m_baru.sum())

                # V24 FIX: Clean duplicate columns - only show unique, readable columns
                # Remove duplicate lowercase columns if uppercase exists
                cols_to_show = ["NAMA_GURU", "IC_GURU", "JANTINA", "POSKOD_RUMAH", "ALAMAT_RUMAH", "TELEFON_GURU", "EMAIL_GURU", "JAWATAN_CADANGAN", "PENGALAMAN_SPM", "NO_PUSAT_ASAL", "KOD_SEKOLAH_ASAL", "NAMA_SEKOLAH_ASAL", "STATUS"]
                display_cols = [c for c in cols_to_show if c in df_cad.columns]
                # Deduplicate columns list itself
                seen = set()
                uniq_display = []
                for c in display_cols:
                    if c.lower() not in seen:
                        uniq_display.append(c)
                        seen.add(c.lower())
                # Also ensure df_cad doesn't have duplicate columns (lower + upper)
                # Keep only upper case versions for display
                df_display = df_cad[uniq_display].copy() if uniq_display else df_cad
                # === WARNA HIJAU UNTUK SUDAH HANTAR DI MENU HANTAR ===
                try:
                    styled_hantar = style_nama_hijau_hantar(df_display)
                    st.dataframe(styled_hantar, use_container_width=True)
                    st.caption("🟢 Hijau = Sudah hantar ke PPD  |  🟡 Kuning = Belum hantar (boleh dihantar)")
                except:
                    st.dataframe(df_display, use_container_width=True)
                # === END WARNA ===

                k1, k2, k3 = st.columns(3)
                with k1: st.metric("Belum dihantar", bil_baru)
                with k2: st.metric("Sudah dihantar", int(m_hantar.sum()))
                with k3: st.metric("Lulus PPD", int(m_lulus.sum()))

                sasaran = df_cad[m_baru]
                def _kosong(col):
                    if col not in sasaran.columns: return pd.Series(False, index=sasaran.index)
                    return sasaran[col].astype(str).str.strip().isin(["", "KOSONG", "nan", "None"])

                tak_lengkap = sasaran[_kosong("POSKOD_RUMAH") | _kosong("ALAMAT_RUMAH") | _kosong("TELEFON_GURU")]
                if bil_baru and not tak_lengkap.empty:
                    st.warning(f"⚠️ {len(tak_lengkap)} cadangan belum lengkap (POSKOD / ALAMAT / TELEFON kosong) - PPD tak boleh jana ikut terdekat. Sila lengkapkan di Senarai Guru > Edit. Contoh: " + ", ".join(tak_lengkap["NAMA_GURU"].astype(str).head(3)))
                elif bil_baru:
                    st.success(f"✅ {bil_baru} cadangan ada POSKOD, ALAMAT & TELEFON lengkap.")

                col_hantar, col_batal, col_reset = st.columns(3)
                with col_hantar:
                    if bil_baru == 0: st.info("Semua cadangan sudah dihantar / lulus.")
                    if st.button(f"📤 Hantar {bil_baru} Cadangan ke PPD", type="primary", use_container_width=True, disabled=bil_baru == 0, key="btn_hantar_ppd"):
                        ids = [_id_py(x) for x in sasaran["id"].tolist()] if "id" in sasaran.columns else []
                        if not ids:
                            st.error("Tiada ID cadangan - data tak lengkap, hubungi admin.")
                        else:
                            berjaya, gagal = hantar_ke_ppd(ids, kod_ppd_sup, df_sasaran=sasaran)
                            if berjaya:
                                flash("success", f"✅ Berjaya hantar {berjaya} cadangan ke PPD {kod_ppd_sup} - {PPD_MAP.get(kod_ppd_sup, '')}!")
                                # V25: Clear cache to force fresh data
                                try:
                                    st.cache_data.clear()
                                    st.cache_resource.clear()
                                except:
                                    pass
                                # Force small delay to let Supabase replicate
                                import time
                                time.sleep(1)
                            if gagal: flash("error", "Sebahagian gagal dihantar: " + "; ".join(gagal[:3]))
                            st.rerun()

                with col_batal:
                    st.markdown("**Batal Cadangan (Selagi PPD Belum Lantik)**")
                    label_batal = {}
                    if "id" in df_cad.columns:
                        for _, r_ in df_cad.iterrows():
                            label_batal[_id_py(r_["id"])] = f"{r_.get('NAMA_GURU', '')} | {r_.get('IC_GURU', '')} | {r_.get('STATUS', '')}"
                    batal_ids = st.multiselect("Pilih untuk batal", list(label_batal.keys()), format_func=lambda x: label_batal.get(x, str(x)))
                    if st.button("❌ Batal Terpilih", use_container_width=True, key="btn_batal_cad"):
                        if not batal_ids: st.warning("Pilih sekurang-kurangnya 1")
                        else:
                            berjaya_b = 0
                            for bid in batal_ids:
                                try:
                                    if "LULUS" in str(df_cad[df_cad["id"] == bid].iloc[0].get("STATUS", "")).upper():
                                        flash("error", f"Tak boleh batal {label_batal.get(bid, bid)} - sudah LULUS PPD!")
                                        continue
                                    supa.table("cadangan_sup").delete().eq("id", bid).execute()
                                    berjaya_b += 1
                                except Exception as e:
                                    flash("error", f"Gagal batal {label_batal.get(bid, bid)}: {e}")
                            if berjaya_b: flash("success", f"✅ Berjaya batal {berjaya_b} cadangan!")
                            st.rerun()

                with col_reset:
                    st.markdown("**Reset Semua (Clear & Isi Semula)**")
                    sah_reset = st.checkbox("Ya, padam semua cadangan (kecuali yang sudah LULUS)", key="sah_reset_cad")
                    if st.button("🔄 Reset Semua Cadangan", use_container_width=True, type="secondary", disabled=not sah_reset, key="btn_reset_cad"):
                        count_del = 0
                        for _, row in df_cad.iterrows():
                            if "LULUS" in str(row.get("STATUS", "")).upper(): continue
                            try:
                                supa.table("cadangan_sup").delete().eq("id", _id_py(row["id"])).execute()
                                count_del += 1
                            except Exception as e:
                                flash("error", f"Gagal padam {row.get('NAMA_GURU', '')}: {e}")
                        flash("success", f"✅ Reset {count_del} cadangan!")
                        st.rerun()

                st.markdown("---")
                st.caption("ℹ️ Cadangan yang sudah LULUS PPD tidak akan diubah atau dipadam oleh butang di atas.")

        elif menu == "petugas":
            st.markdown(f'<div style="background: linear-gradient(135deg, #0d47a1 0%, #0d47a1 100%); padding:20px; border-radius:12px; color:white; margin-bottom:20px;"><h2 style="margin:0; color:white;">👥 Petugas Yang Akan Hadir Bertugas Di Sekolah Saya - {kod}</h2><p style="margin:5px 0 0 0; color:#e3f2fd;">Pilih pusat yang ada di sekolah anda, lihat senarai petugas yang akan hadir bertugas</p></div>', unsafe_allow_html=True)

            # Get pusat di sekolah ini
            try:
                df_pusat_all = get_pusat_df()
                pusat_di_sekolah = []
                for _, r in df_pusat_all.iterrows():
                    d = r.get("data") if isinstance(r.get("data"), dict) else {}
                    if isinstance(d, str):
                        try: d = json.loads(d)
                        except: d = {}
                    ks_tuan = str(r.get("kod_sekolah_tuan_rumah") or r.get("kod_sekolah") or r.get("KOD_SEKOLAH") or d.get("KOD_SEKOLAH") or "").upper().strip()
                    if ks_tuan == kod.upper().strip():
                        no_p = str(r.get("no_pusat") or r.get("kod_pusat") or r.get("NO_PUSAT") or d.get("NO_PUSAT") or "").upper().strip()
                        nama_p = r.get("nama_pusat") or d.get("NAMA_PUSAT") or ""
                        calon = r.get("jumlah_calon") or d.get("JUMLAH_CALON") or 0
                        try: calon_i = int(float(str(calon) or 0))
                        except: calon_i = 0
                        pusat_di_sekolah.append({"NO_PUSAT": no_p, "NAMA_PUSAT": nama_p, "CALON": calon_i})
            except Exception as e:
                st.error(f"Error load pusat: {e}")
                pusat_di_sekolah = []

            if not pusat_di_sekolah:
                st.warning(f"Tiada pusat dijumpai untuk sekolah {kod}. Hubungi PPD.")
            else:
                st.success(f"Sekolah anda {kod} - {info.get('nama_sekolah','')} ada {len(pusat_di_sekolah)} pusat:")
                for p in pusat_di_sekolah:
                    st.markdown(f"- **{p['NO_PUSAT']}** - {p['NAMA_PUSAT']} ({p['CALON']} calon)")

                st.markdown("---")
                st.markdown("### Pilih Pusat Untuk Lihat Petugas Hadir")
                pilih_pusat_sup = st.selectbox(
                    "Pilih Pusat Di Sekolah Anda",
                    [p["NO_PUSAT"] for p in pusat_di_sekolah],
                    format_func=lambda x: f"{x} - {next((p['NAMA_PUSAT'] for p in pusat_di_sekolah if p['NO_PUSAT']==x), '')[:40]}",
                    key="pilih_pusat_sup_petugas"
                )

                if pilih_pusat_sup:
                    # ===== FIX PETUGAS HADIR - HANYA LULUS PPD & BUKAN SEKOLAH SENDIRI =====
                    try:
                        res_cad = supa.table("cadangan_sup").select("*").eq("kod_pusat", pilih_pusat_sup).limit(5000).execute()
                        df_petugas_all = pd.DataFrame(res_cad.data or [])
                        if df_petugas_all.empty:
                            res_cad2 = supa.table("cadangan_sup").select("*").ilike("kod_pusat", f"%{pilih_pusat_sup}%").limit(5000).execute()
                            df_petugas_all = pd.DataFrame(res_cad2.data or [])
                    except Exception as e:
                        st.error(f"Error load petugas: {e}")
                        df_petugas_all = pd.DataFrame()

                    if df_petugas_all.empty:
                        st.warning(f"⏳ Belum ada petugas dilantik untuk pusat {pilih_pusat_sup} - PPD belum buat lantikan.")
                        st.info("Button ini hanya akan paparkan nama selepas PPD lantik dan jana surat. Cikgu dari sekolah sendiri tidak akan dipaparkan kerana tidak boleh bertugas di sekolah asal.")
                    else:
                        def get_status_val(row):
                            return str(row.get("status") or row.get("STATUS") or "").upper()
                        df_petugas_all["STATUS_NORM"] = df_petugas_all.apply(get_status_val, axis=1)
                        lulus_keywords = ["LULUS", "SURAT", "DILANTIK", "DITEMPATKAN", "DIJANA", "SAH", "LANTIK"]
                        mask_lulus = df_petugas_all["STATUS_NORM"].apply(lambda x: any(k in x for k in lulus_keywords))
                        def has_surat(row):
                            ns = str(row.get("no_surat") or row.get("NO_SURAT") or "").strip()
                            return ns != "" and ns.lower() not in ("none","null","nan","")
                        mask_surat = df_petugas_all.apply(has_surat, axis=1)
                        df_lulus_sahaja = df_petugas_all[mask_lulus | mask_surat].copy()

                        if df_lulus_sahaja.empty:
                            st.warning(f"⏳ Ada {len(df_petugas_all)} cadangan untuk pusat {pilih_pusat_sup} tapi belum diluluskan PPD.")
                            st.info(f"Status: {df_petugas_all['STATUS_NORM'].unique().tolist()[:5]} - Tunggu PPD buat lantikan.")
                        else:
                            def get_sekolah_asal(row):
                                return str(row.get("kod_sekolah_asal") or row.get("KOD_SEKOLAH_ASAL") or row.get("kod_sekolah") or "").upper().strip()
                            df_lulus_sahaja["SEKOLAH_ASAL_NORM"] = df_lulus_sahaja.apply(get_sekolah_asal, axis=1)
                            kod_semasa = kod.upper().strip()
                            df_final = df_lulus_sahaja[df_lulus_sahaja["SEKOLAH_ASAL_NORM"] != kod_semasa].copy()
                            excluded_count = len(df_lulus_sahaja) - len(df_final)
                            if excluded_count > 0:
                                st.info(f"ℹ️ {excluded_count} petugas dari sekolah sendiri ({kod_semasa}) disembunyikan kerana tidak boleh bertugas di sekolah asal.")

                            if df_final.empty:
                                st.warning(f"Tiada petugas luar untuk pusat {pilih_pusat_sup} - Semua yang lulus adalah dari sekolah sendiri.")
                            else:
                                st.success(f"✅ {len(df_final)} Petugas Luar Akan Hadir di {pilih_pusat_sup} (Sudah dilantik PPD)")
                                def get_jawatan(row):
                                    return str(row.get("jawatan_cadangan") or row.get("JAWATAN_CADANGAN") or "").strip()
                                df_final["JAWATAN_NORM"] = df_final.apply(get_jawatan, axis=1)
                                kp_list = df_final[df_final["JAWATAN_NORM"].str.contains("Ketua Pengawas", case=False, na=False) & ~df_final["JAWATAN_NORM"].str.contains("Timbalan", case=False, na=False)]
                                tkp_list = df_final[df_final["JAWATAN_NORM"].str.contains("Timbalan", case=False, na=False)]
                                peng_list = df_final[~df_final["JAWATAN_NORM"].str.contains("Ketua Pengawas|Timbalan", case=False, na=False, regex=True)]
                                col_kp, col_tkp, col_peng, col_jt, col_jb, col_pb = st.columns(6)
                                with col_kp: st.metric("Ketua Pengawas (Luar)", len(kp_list))
                                with col_tkp: st.metric("Timbalan KP (Luar)", len(tkp_list))
                                with col_peng: st.metric("Pengawas (Luar)", len(peng_list))
                                rows_petugas = []
                                for _, r in df_final.iterrows():
                                    rows_petugas.append({
                                        "NAMA GURU": r.get("nama_guru", "") or r.get("NAMA_GURU", ""),
                                        "IC": r.get("ic_guru", "") or r.get("IC_GURU", ""),
                                        "JAWATAN": r.get("jawatan_cadangan", "") or r.get("JAWATAN_CADANGAN", ""),
                                        "SEKOLAH ASAL": r.get("kod_sekolah_asal", "") or r.get("KOD_SEKOLAH_ASAL", ""),
                                        "NAMA SEKOLAH ASAL": str(r.get("nama_sekolah_asal", "") or r.get("NAMA_SEKOLAH_ASAL", ""))[:40],
                                        "NO SURAT": r.get("no_surat", "") or "",
                                        "STATUS": r.get("status", "") or ""
                                    })
                                df_display_petugas = pd.DataFrame(rows_petugas)
                                st.dataframe(df_display_petugas, use_container_width=True, hide_index=True)
                                st.download_button(f"📥 Export Petugas Luar {pilih_pusat_sup}", to_excel(df_display_petugas), file_name=f"petugas_LUAR_{pilih_pusat_sup}_{kod}.xlsx", use_container_width=True)
                    # ===== END FIX PETUGAS =====

        elif menu == "surat":
            st.markdown(f'<div style="background: linear-gradient(135deg, #0d47a1 0%, #0d47a1 100%); padding:20px; border-radius:12px; color:white; margin-bottom:20px;"><h2 style="margin:0; color:white;">📄 Surat Lantikan Saya - {kod} - {info.get("nama_sekolah","")}</h2><p style="margin:5px 0 0 0; color:#e3f2fd;">Surat lantikan petugas dari sekolah anda - Asing ikut jawatan untuk rujukan SUP</p></div>', unsafe_allow_html=True)

            df_cad_sup = get_cadangan_df(kod_sekolah=kod)
            if df_cad_sup.empty:
                st.warning("Belum ada cadangan. Sila buat cadangan di menu Cadangan Lantikan dahulu.")
            else:
                def get_status(row):
                    return str(row.get("STATUS") or row.get("status") or "").upper().strip()
                def get_jawatan(row):
                    return str(row.get("JAWATAN_CADANGAN") or row.get("jawatan_cadangan") or "").strip()
                def has_surat(row):
                    ns = str(row.get("no_surat") or row.get("NO_SURAT") or row.get("no_surat_lantikan") or "").strip()
                    return ns != "" and ns.lower() not in ("none", "null", "nan", "")

                df_cad_sup["STATUS_NORM"] = df_cad_sup.apply(lambda r: get_status(r), axis=1)
                df_cad_sup["JAWATAN_NORM"] = df_cad_sup.apply(lambda r: get_jawatan(r), axis=1)
                df_cad_sup["ADA_SURAT"] = df_cad_sup.apply(lambda r: has_surat(r), axis=1)

                total_cad = len(df_cad_sup)
                ada_surat_cnt = int(df_cad_sup["ADA_SURAT"].sum())
                tunggu_cnt = total_cad - ada_surat_cnt

                if fly_cur == "jadual":
                    c1,c2,c3,c4 = st.columns(4)
                    c1.metric("Total Cadangan Sekolah", total_cad)
                    c2.metric("✅ Sudah Ada Surat", ada_surat_cnt)
                    c3.metric("⏳ Tunggu Surat", tunggu_cnt)
                    with c4:
                        if ada_surat_cnt > 0:
                            if st.button(f"📦 Jana ZIP {ada_surat_cnt} Surat PDF Individu", type="primary", use_container_width=True, key=f"btn_zip_sup_{kod}"):
                                try:
                                    df_lulus_zip = df_cad_sup[df_cad_sup["ADA_SURAT"] == True].copy()
                                    surat_list_sup = []
                                    for _, r in df_lulus_zip.iterrows():
                                        surat_list_sup.append({
                                            "nama": r.get("NAMA_GURU","") or r.get("nama_guru",""),
                                            "ic": r.get("IC_GURU","") or r.get("ic_guru",""),
                                            "jawatan": r.get("JAWATAN_CADANGAN","") or r.get("jawatan_cadangan",""),
                                            "sekolah_asal": r.get("KOD_SEKOLAH_ASAL","") or r.get("kod_sekolah_asal","") or kod,
                                            "nama_sekolah_asal": r.get("NAMA_SEKOLAH_ASAL","") or r.get("nama_sekolah_asal","") or info.get('nama_sekolah',''),
                                            "pusat": r.get("kod_pusat","") or r.get("KOD_PUSAT",""),
                                            "nama_pusat": "",
                                            "no_surat": r.get("no_surat","") or r.get("NO_SURAT","")
                                        })
                                    # FIX: guna build_pusat_map_from_master() ikut NO PUSAT column refer pusat_master
                                    try:
                                        pusat_map_tmp = build_pusat_map_from_master()
                                        for s in surat_list_sup:
                                            s["nama_pusat"] = pusat_map_tmp.get(str(s["pusat"]).upper().strip(), "")
                                            # Jika masih kosong, cuba cari tanpa strip
                                            if not s["nama_pusat"]:
                                                s["nama_pusat"] = pusat_map_tmp.get(str(s["pusat"]).strip(), "")
                                    except:
                                        pass
                                    zip_bytes = create_zip_of_individual_pdfs(surat_list_sup, info.get('kod_ppd',''), PPD_MAP.get(info.get('kod_ppd',''), ''))
                                    if zip_bytes:
                                        st.session_state[f"zip_sup_{kod}"] = zip_bytes
                                        st.success(f"✅ ZIP {len(surat_list_sup)} surat individu berjaya dijana!")
                                    else:
                                        st.error("Gagal jana ZIP")
                                except Exception as e:
                                    st.error(f"Error jana ZIP: {e}")
                            if f"zip_sup_{kod}" in st.session_state:
                                st.download_button(f"📥 Download ZIP {ada_surat_cnt} Surat Individu (SUP {kod})", data=st.session_state[f"zip_sup_{kod}"], file_name=f"Surat_Individu_SUP_{kod}_{__import__('datetime').date.today()}.zip", mime="application/zip", use_container_width=True, key=f"dl_zip_sup_{kod}")

                    def papar_table_jawatan(df_input, tajuk, icon, keyword_list, warna_header):
                        if keyword_list:
                            mask = df_input["JAWATAN_NORM"].str.upper().apply(lambda x: any(k.upper() in x.upper() for k in keyword_list))
                            df_j = df_input[mask].copy()
                        else:
                            df_j = df_input.copy()
                        if df_j.empty:
                            return
                        st.markdown(f"""
                    <div style="background:{warna_header}; padding:12px 16px; border-radius:8px; margin:20px 0 10px 0; border-left:6px solid #0d47a1;">
                        <h3 style="margin:0; color:white;">{icon} {tajuk} - {len(df_j)} orang</h3>
                    </div>
                    """, unsafe_allow_html=True)
                        df_ada = df_j[df_j["ADA_SURAT"] == True].copy()
                        df_tunggu = df_j[df_j["ADA_SURAT"] == False].copy()
                        col_ada, col_tunggu = st.columns([1.2, 1])
                        with col_ada:
                            st.markdown(f"#### ✅ Ada Surat ({len(df_ada)})")
                            if df_ada.empty:
                                st.info(f"Belum ada surat untuk {tajuk}")
                            else:
                                # FIX: papar NAMA PUSAT ikut pusat_master
                                try:
                                    _pmap_disp = build_pusat_map_from_master()
                                except:
                                    _pmap_disp = {}
                                display_rows = []
                                for _, r in df_ada.iterrows():
                                    kod_pusat_raw = r.get("KOD_PUSAT") or r.get("kod_pusat") or r.get("PUSAT") or ""
                                    nama_pusat_disp = _pmap_disp.get(str(kod_pusat_raw).upper().strip(), "")
                                    display_rows.append({
                                        "NAMA GURU": r.get("NAMA_GURU","") or r.get("nama_guru",""),
                                        "IC": r.get("IC_GURU","") or r.get("ic_guru",""),
                                        "JAWATAN": r.get("JAWATAN_NORM",""),
                                        "PUSAT": kod_pusat_raw,
                                        "NAMA PUSAT": nama_pusat_disp,
                                        "NO SURAT": r.get("no_surat") or r.get("NO_SURAT") or "",
                                        "STATUS": r.get("STATUS_NORM",""),
                                    })
                                df_show = pd.DataFrame(display_rows)
                                st.dataframe(df_show, use_container_width=True, hide_index=True)
                                st.download_button(f"📥 Export {tajuk} - Ada Surat", to_excel(df_show), file_name=f"surat_{tajuk.replace(' ','_')}_ada_surat_{kod}.xlsx", key=f"exp_ada_{tajuk}_{kod}", use_container_width=True)
                        with col_tunggu:
                            st.markdown(f"#### ⏳ Tunggu Surat ({len(df_tunggu)})")
                            if df_tunggu.empty:
                                st.success(f"Semua {tajuk} sudah ada surat!")
                            else:
                                display_tunggu = []
                                for _, r in df_tunggu.iterrows():
                                    display_tunggu.append({
                                        "NAMA GURU": r.get("NAMA_GURU","") or r.get("nama_guru",""),
                                        "JAWATAN": r.get("JAWATAN_NORM",""),
                                        "STATUS": r.get("STATUS_NORM",""),
                                        "CATATAN": "Menunggu PPD jana surat" if "LULUS" in r.get("STATUS_NORM","") else "Belum hantar ke PPD" if "DICADANGKAN" in r.get("STATUS_NORM","") else r.get("STATUS_NORM","")
                                    })
                                df_tunggu_show = pd.DataFrame(display_tunggu)
                                st.dataframe(df_tunggu_show, use_container_width=True, hide_index=True)
                                st.download_button(f"📥 Export {tajuk} - Tunggu", to_excel(df_tunggu_show), file_name=f"surat_{tajuk.replace(' ','_')}_tunggu_{kod}.xlsx", key=f"exp_tunggu_{tajuk}_{kod}", use_container_width=True)
                        st.markdown("---")

                    papar_table_jawatan(df_cad_sup, "TABLE 1: Penyelia Kawasan", "🔐", ["Penyelia Kawasan", "Penyelia"], "linear-gradient(135deg, #0d47a1 0%, #0d47a1 100%)")
                    papar_table_jawatan(df_cad_sup, "TABLE 2: Ketua Pengawas & Timbalan", "👑", ["Ketua Pengawas", "Timbalan Ketua"], "linear-gradient(135deg, #0d47a1 0%, #1976d2 100%)")
                    papar_table_jawatan(df_cad_sup, "TABLE 3: Pengawas Peperiksaan", "👨‍🏫", ["Pengawas Peperiksaan", "Pengawas"], "linear-gradient(135deg, #0d47a1 0%, #0d47a1 100%)")

                if fly_cur == "individu":
                    st.markdown("## 📄 Paparan Surat Lantikan (Yang Ada Surat Sahaja) - Individu")
                    df_lulus = df_cad_sup[df_cad_sup["ADA_SURAT"] == True].copy()
                    if df_lulus.empty:
                        st.info("Belum ada surat lantikan.")
                    else:
                        st.success(f"Ada {len(df_lulus)} surat lantikan untuk sekolah {kod} - SUP boleh download ZIP individu atau PDF seorang-seorang di bawah")

                        # Search & Pagination untuk SUP juga (elak panjang kalau 1000)
                        col_s1, col_s2 = st.columns([2,1])
                        with col_s1:
                            search_sup = st.text_input("🔍 Cari Nama Guru / IC / Pusat di Surat Saya", placeholder="Taip nama atau pusat...", key=f"search_sup_surat_{kod}")
                        with col_s2:
                            per_page_sup = st.selectbox("Per Page", [10,20,50], index=1, key=f"per_page_sup_{kod}")

                        df_lulus_filtered = df_lulus.copy()
                        if search_sup:
                            s = search_sup.lower()
                            df_lulus_filtered = df_lulus_filtered[df_lulus_filtered.apply(lambda r: s in str(r.get("NAMA_GURU","") or r.get("nama_guru","")).lower() or s in str(r.get("IC_GURU","") or r.get("ic_guru","")).lower() or s in str(r.get("kod_pusat","") or r.get("KOD_PUSAT","")).lower(), axis=1)]

                        total_pages_sup = max(1, (len(df_lulus_filtered) + per_page_sup -1)//per_page_sup)
                        page_sup = st.number_input(f"Halaman SUP 1-{total_pages_sup}", min_value=1, max_value=total_pages_sup, value=1, step=1, key=f"page_sup_{kod}")
                        start_sup = (page_sup-1)*per_page_sup
                        end_sup = start_sup + per_page_sup
                        df_lulus_page = df_lulus_filtered.iloc[start_sup:end_sup]

                        # Quick select dropdown
                        if not df_lulus_filtered.empty:
                            options_sup = [f"{i+1}. {r.get('NAMA_GURU','') or r.get('nama_guru','')} | {r.get('IC_GURU','') or r.get('ic_guru','')} | {r.get('kod_pusat','') or r.get('KOD_PUSAT','')} | {r.get('no_surat','')}" for i, (_, r) in enumerate(df_lulus_filtered.iterrows())]
                            pilih_sup_idx = st.selectbox("⚡ Pilih Guru untuk Download Cepat", range(len(options_sup)), format_func=lambda x: options_sup[x], key=f"select_sup_surat_{kod}")
                            if st.button("📥 Jana PDF Guru Terpilih (SUP)", type="primary", key=f"btn_sup_selected_{kod}"):
                                try:
                                    r_sel = df_lulus_filtered.iloc[pilih_sup_idx]
                                    nama = r_sel.get("NAMA_GURU", "") or r_sel.get("nama_guru", "")
                                    ic = r_sel.get("IC_GURU", "") or r_sel.get("ic_guru", "")
                                    jawatan = r_sel.get("JAWATAN_CADANGAN", "") or r_sel.get("jawatan_cadangan", "") or ""
                                    pusat = r_sel.get("kod_pusat", "") or r_sel.get("KOD_PUSAT", "") or ""
                                    no_surat = r_sel.get("no_surat", "") or ""
                                    telefon = r_sel.get("TELEFON_GURU", "") or r_sel.get("telefon_guru", "") or ""
                                    try:
                                        pdf_sel = generate_surat_pdf_bytes(nama, ic, jawatan, r_sel.get("KOD_SEKOLAH_ASAL", "") or kod, r_sel.get("NAMA_SEKOLAH_ASAL", "") or info.get('nama_sekolah',''), pusat, "", no_surat, r_sel.get("KOD_PPD", "") or info.get('kod_ppd',''), PPD_MAP.get(r_sel.get("KOD_PPD", "") or info.get('kod_ppd',''), ""), __import__("datetime").date.today().strftime('%d %B %Y'), no_surat)
                                        if pdf_sel:
                                            st.download_button(f"📥 Download PDF {nama}", data=pdf_sel, file_name=f"Surat_{nama.replace(' ','_')}_{no_surat.replace('/','_')}.pdf", mime="application/pdf", key=f"dl_sup_selected_{kod}_{pilih_sup_idx}", use_container_width=True)
                                    except Exception as e:
                                        st.error("Maaf, berlaku masalah semasa memproses. Sila cuba lagi.")
                                except Exception as e:
                                    st.error("Maaf, berlaku masalah semasa memproses. Sila cuba lagi.")

                        st.markdown(f"**Papar {len(df_lulus_page)} surat (Halaman {page_sup}/{total_pages_sup}) - Total {len(df_lulus_filtered)} surat:**")

                        for _, r in df_lulus_page.iterrows():
                            nama = r.get("NAMA_GURU", "") or r.get("nama_guru", "")
                            ic = r.get("IC_GURU", "") or r.get("ic_guru", "")
                            jawatan = r.get("JAWATAN_CADANGAN", "") or r.get("jawatan_cadangan", "") or ""
                            pusat = r.get("kod_pusat", "") or r.get("KOD_PUSAT", "") or ""
                            no_surat = r.get("no_surat", "") or ""
                            telefon = r.get("TELEFON_GURU", "") or r.get("telefon_guru", "") or r.get("NO_TELEFON", "") or ""

                            # Detect if this is Penyelia Kawasan placed in Bilik Kebal
                            is_penyelia_bk = "PENYELIA" in jawatan.upper() and ("BK-" in pusat.upper() or "CB" in pusat.upper() or "BILIK" in pusat.upper() or str(r.get("status","")).upper() in ["DITEMPATKAN BILIK KEBAL", "SURAT PK DIHANTAR", "SURAT PK DIHANTAR KE SEKOLAH"])
                            # Also check data json for bilik kebal
                            data_json = r.get("data") if isinstance(r.get("data"), dict) else {}
                            if isinstance(data_json, str):
                                try:
                                    data_json = json.loads(data_json)
                                except:
                                    data_json = {}
                            if data_json and ("kod_bilik_kebal" in str(data_json).lower() or "pusat_jagaan" in str(data_json).lower()):
                                is_penyelia_bk = True

                            label_bk = "🔐 Penyelia Kawasan - Bilik Kebal" if is_penyelia_bk else f"{jawatan}"

                            with st.expander(f"{nama} - {label_bk} - {pusat} - {no_surat}"):
                                try:
                                    pusat_nama = ""
                                    alamat_bk = ""
                                    nama_bk = pusat
                                    # Try get bilik kebal details
                                    if is_penyelia_bk:
                                        try:
                                            res_bk = supa.table("bilik_kebal_master").select("*").eq("kod_bilik_kebal", pusat.upper()).limit(1).execute()
                                            if res_bk.data:
                                                nama_bk = res_bk.data[0].get("nama_bilik_kebal", pusat)
                                                alamat_bk = res_bk.data[0].get("alamat", "")
                                                pusat_nama = nama_bk
                                        except:
                                            pass
                                    else:
                                        try:
                                            df_pusat = get_pusat_df()
                                            for _, pr in df_pusat.iterrows():
                                                d = pr.get("data") if isinstance(pr.get("data"), dict) else {}
                                                if isinstance(d, str):
                                                    try: d = json.loads(d)
                                                    except: d = {}
                                                no_p = str(pr.get("no_pusat") or d.get("NO_PUSAT") or "").upper().strip()
                                                if no_p == pusat.upper():
                                                    pusat_nama = pr.get("nama_pusat") or d.get("NAMA_PUSAT") or ""
                                                    break
                                        except:
                                            pusat_nama = ""

                                    # Get pusat jagaan for penyelia
                                    pusat_jagaan_list = []
                                    if is_penyelia_bk:
                                        if isinstance(data_json, dict):
                                            pj = data_json.get("pusat_jagaan") or data_json.get("pusat_jagaan_str") or []
                                            if isinstance(pj, str):
                                                pusat_jagaan_list = [p.strip() for p in pj.split(",") if p.strip()]
                                            elif isinstance(pj, list):
                                                pusat_jagaan_list = pj
                                        if not pusat_jagaan_list:
                                            pusat_jagaan_list = [pusat]

                                        html_surat = generate_surat_penyelia_kawasan_html(
                                            nama=nama,
                                            ic=ic,
                                            sek_asal=r.get("KOD_SEKOLAH_ASAL", "") or r.get("kod_sekolah_asal", "") or kod,
                                            nama_sek_asal=r.get("NAMA_SEKOLAH_ASAL", "") or r.get("nama_sekolah_asal", "") or info.get('nama_sekolah',''),
                                            telefon=telefon,
                                            kod_bilik_kebal=pusat,
                                            nama_bilik_kebal=nama_bk,
                                            alamat_bilik_kebal=alamat_bk,
                                            pusat_jagaan_list=pusat_jagaan_list,
                                            no_surat=no_surat,
                                            kod_ppd=r.get("KOD_PPD", "") or r.get("kod_ppd", "") or info.get('kod_ppd',''),
                                            ppd_name=PPD_MAP.get(r.get("KOD_PPD", "") or r.get("kod_ppd", "") or info.get('kod_ppd',''), ""),
                                            tarikh=datetime.date.today().strftime('%d %B %Y')
                                        )
                                    else:
                                        html_surat = generate_surat_html(
                                            nama, ic, jawatan,
                                            r.get("KOD_SEKOLAH_ASAL", "") or kod,
                                            r.get("NAMA_SEKOLAH_ASAL", "") or info.get('nama_sekolah',''),
                                            pusat, pusat_nama, no_surat,
                                            r.get("KOD_PPD", "") or info.get('kod_ppd',''),
                                            PPD_MAP.get(r.get("KOD_PPD", "") or info.get('kod_ppd',''), ""),
                                            datetime.date.today().strftime('%d %B %Y')
                                        )

                                    st.components.v1.html(html_surat, height=600, scrolling=True)
                                    try:
                                        pdf_single = generate_surat_pdf_bytes(nama, ic, jawatan, r.get("KOD_SEKOLAH_ASAL", "") or kod, r.get("NAMA_SEKOLAH_ASAL", "") or info.get('nama_sekolah',''), pusat, pusat_nama or nama_bk, no_surat, r.get("KOD_PPD", "") or info.get('kod_ppd',''), PPD_MAP.get(r.get("KOD_PPD", "") or info.get('kod_ppd',''), ""), datetime.date.today().strftime('%d %B %Y'), no_surat)
                                        if pdf_single:
                                            st.download_button(f"📥 Download Surat {nama} - {label_bk} (PDF)", data=pdf_single, file_name=f"Surat_{label_bk.replace(' ', '_')}_{nama.replace(' ', '_')}_{no_surat.replace('/', '_')}.pdf", mime="application/pdf", use_container_width=True, key=f"dl_pdf_{r.get('id','')}")
                                    except:
                                        pass
                                    st.download_button(f"📥 Download Surat {nama} - {label_bk}", data=html_surat.encode('utf-8'), file_name=f"Surat_{label_bk.replace(' ', '_')}_{nama.replace(' ', '_')}_{no_surat.replace('/', '_')}.html", mime="text/html", use_container_width=True, key=f"dl_{r.get('id','')}")

                                    # Show extra info for penyelia kawasan
                                    if is_penyelia_bk and pusat_jagaan_list:
                                        st.info(f"🔐 Penyelia Kawasan ini ditempatkan di Bilik Kebal {pusat} ({nama_bk}) dan bertanggungjawab atas {len(pusat_jagaan_list)} pusat: {', '.join(pusat_jagaan_list)}")

                                except Exception as e:
                                    st.error(f"Error generate surat: {e}")



# ================= ROLE: PPD =================
elif st.session_state.role == "PPD":
    kod_ppd = st.session_state.kod

    col_menu, col_main = st.columns([1.45, 3.2], gap="large")
    with col_menu:
        st.markdown('<div class="custom-sidebar">', unsafe_allow_html=True)
        st.markdown(f"### 🏢 PPD {kod_ppd}")
        st.caption(f"{PPD_MAP.get(kod_ppd, '')}")
        add_refresh_button()

        MENU_PPD = [('dashboard', '📊 Dashboard PPD'), ('sekolah', '🏫 Sekolah dalam PPD'), ('pusat', '🏫 Pusat di PPD'),
                    ('cadangan', '📋 Cadangan SUP'), ('jana', '🚀 Jana Keseluruhan'), ('hasil', '📋 Hasil Janaan'), ('manual', '📌 Penempatan Manual'), ('selenggara', '🔐 Selenggara Bilik Kebal'), ('semakan', '🔍 Semakan Lantikan'), ('kelulusan', '✅ Kelulusan'), ('jana_surat', '📄 Janaan Surat Lantikan'),
                    ('export', '📥 Export'), ('keluar', '🚪 Log Keluar')]
        menu, fly_cur = render_menu_flyout("ppd_menu_sel", MENU_PPD, FLY_PPD, None, "fly_ppd")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_main:
        render_bar_tahun("ppd")
        if menu == "keluar":
            reset_sesi_kekal_tahun()
            st.rerun()

        elif menu == "dashboard":
            st.markdown(f"""
            <div style="background: #0d47a1; padding:20px; border-radius:12px; color:white; border: 2px solid #002171; margin-bottom:20px;">
                <div style="display:flex; align-items:center; gap:15px;">
                    <div style="font-size:48px;">🏢</div>
                    <div>
                        <h2 style="margin:0; color:white; font-size:28px;">PPD {kod_ppd} - {PPD_MAP.get(kod_ppd, '')}</h2>
                        <p style="margin:5px 0 0 0; color:#bbdefb; font-size:14px;">Dashboard Pelantikan SPM {tahun_aktif()} - Senarai Pusat & Keperluan Petugas</p>
                    </div>
                    <div style="margin-left:auto; font-size:48px;">📚</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            try:
                # Load data
                df_pusat_raw = get_pusat_df()
                df_cad_all = get_cadangan_df(kod_ppd=kod_ppd)
                df_sekolah_raw = supa.table("sekolah_master").select("*").eq("kod_ppd", kod_ppd).limit(2000).execute()
                df_sekolah_list = pd.DataFrame(df_sekolah_raw.data or [])

                # Parse pusat
                pusat_list = []
                for _, r in df_pusat_raw.iterrows():
                    d = r.get("data") if isinstance(r.get("data"), dict) else {}
                    if isinstance(d, str):
                        try: d = json.loads(d)
                        except: d = {}
                    no_pusat = str(r.get("no_pusat") or r.get("kod_pusat") or d.get("NO_PUSAT") or d.get("NO PUSAT") or "").upper().strip()
                    if not no_pusat.startswith(kod_ppd.upper()):
                        continue
                    nama_pusat = str(r.get("nama_pusat") or d.get("NAMA_PUSAT") or d.get("NAMA PUSAT") or "").upper().strip()
                    kod_tuan = str(r.get("kod_sekolah_tuan_rumah") or r.get("kod_sekolah") or d.get("KOD_SEKOLAH") or d.get("KOD_SEKOLAH_TUAN_RUMAH") or "").upper().strip()
                    j_calon = r.get("jumlah_calon") or r.get("calon") or d.get("JUMLAH_CALON") or d.get("CALON") or 0
                    j_kelas = r.get("jumlah_kelas") or d.get("JUMLAH_KELAS") or 0
                    try: jc = int(float(str(j_calon) or 0))
                    except: jc = 0
                    try: jk = int(float(str(j_kelas) or 0))
                    except: jk = 0
                    if jk == 0:
                        jk = kira_kelas_dari_calon(jc)
                    petugas_sep = kira_petugas_dari_kelas(jk)

                    # Kira berapa petugas telah dicadangkan untuk pusat ini
                    # Cari dalam cadangan_sup yang kod_pusat / no_pusat_asal / no_pusat_tugas == no_pusat ini
                    dicadangkan = 0
                    if not df_cad_all.empty:
                        # Check multiple columns
                        for _, c_row in df_cad_all.iterrows():
                            c_no_pusat = str(c_row.get("kod_pusat") or c_row.get("no_pusat_asal") or c_row.get("NO_PUSAT_ASAL") or c_row.get("KOD_PUSAT") or "").upper().strip()
                            # Also check data dict
                            c_data = c_row.get("data") or {}
                            if isinstance(c_data, str):
                                try: c_data = json.loads(c_data)
                                except: c_data = {}
                            c_no_pusat2 = str(c_data.get("NO_PUSAT_ASAL") or c_data.get("KOD_PUSAT") or "").upper().strip()
                            if c_no_pusat == no_pusat or c_no_pusat2 == no_pusat:
                                dicadangkan += 1
                        # If no specific assignment yet, distribute proportionally? For now show 0, but total will show overall

                    pusat_list.append({
                        "NO_PUSAT": no_pusat,
                        "NAMA_PUSAT": nama_pusat,
                        "KOD_TUAN_RUMAH": kod_tuan,
                        "CALON": jc,
                        "KELAS": jk,
                        "SEPATUTNYA": petugas_sep,
                        "DICADANGKAN": dicadangkan
                    })

                df_pusat_ppd = pd.DataFrame(pusat_list)

                if df_pusat_ppd.empty:
                    st.warning(f"⚠️ Tiada pusat dijumpai untuk PPD {kod_ppd} - {PPD_MAP.get(kod_ppd, '')}. Sila import pusat di JPN > Pusat Master")
                else:
                    if fly_cur == "ringkasan":
                        # Summary metrics
                        total_pusat = len(df_pusat_ppd)
                        total_calon = int(df_pusat_ppd["CALON"].sum())
                        total_kelas = int(df_pusat_ppd["KELAS"].sum())
                        total_sepatutnya = int(df_pusat_ppd["SEPATUTNYA"].sum())
                        total_dicadangkan = len(df_cad_all) if not df_cad_all.empty else 0
                        kekurangan = total_sepatutnya - total_dicadangkan

                        # Color logic for total
                        if total_dicadangkan == 0:
                            color_total = "#0d47a1"
                            bg_total = "#bbdefb"
                            icon_total = "🔴"
                        elif total_dicadangkan < total_sepatutnya:
                            color_total = "#0d47a1"
                            bg_total = "#e3f2fd"
                            icon_total = "🟡"
                        else:
                            color_total = "#0d47a1"
                            bg_total = "#ffffff"
                            icon_total = "🟢"

                        st.markdown(jpn_status_meter(total_pusat, total_calon, total_kelas, total_sepatutnya, total_dicadangkan, kod_ppd), unsafe_allow_html=True)

                        c1, c2, c3, c4, c5, c6 = st.columns(6)
                        c1.metric("🏫 Pusat", total_pusat)
                        c2.metric("👨‍🎓 Calon", total_calon)
                        c3.metric("🏫 Kelas", total_kelas)
                        c4.metric("📋 Perlu", total_sepatutnya)
                        c5.metric("✅ Dicadangkan", total_dicadangkan)
                        c6.metric("⚠️ Kurang", kekurangan if kekurangan > 0 else 0, delta=f"{'Cukup' if kekurangan <=0 else f'-{kekurangan}'}", delta_color="normal" if kekurangan <=0 else "inverse")

                    if fly_cur == "status":
                        st.markdown("---")
                        st.markdown("### 📍 Senarai Pusat Peperiksaan - Status Petugas (PPD Boleh Edit)")
                        st.caption("🔴 Merah = Belum Ada (0) | 🟡 Kuning = Belum Cukup (< sepatutnya) | 🟢 Hijau = Cukup / Lebih (>= sepatutnya) | ✏️ PPD boleh edit BIL CALON, KELAS, PERLU ikut keperluan")
                        st.info("💡 **Cara Edit:** Klik pada angka CALON / KELAS / PERLU dalam table di bawah, tukar ikut keperluan, kemudian tekan **💾 Simpan Perubahan**")

                    # Build editable table
                    # Prepare data for data_editor with BIL, editable columns
                    editable_rows = []
                    for idx, p in enumerate(df_pusat_ppd.sort_values("NO_PUSAT").iterrows()):
                        p_data = p[1]
                        no_p = p_data["NO_PUSAT"]
                        dic = p_data["DICADANGKAN"]
                        sep = p_data["SEPATUTNYA"]

                        if dic == 0:
                            status_icon = "🔴"
                            status_text = "Belum Ada"
                        elif dic < sep:
                            status_icon = "🟡"
                            status_text = f"Belum Cukup"
                        else:
                            status_icon = "🟢"
                            status_text = f"Cukup"

                        editable_rows.append({
                            "BIL": idx + 1,
                            "NO_PUSAT": no_p,
                            "NAMA_PUSAT": p_data["NAMA_PUSAT"][:35],
                            "KOD_TUAN": p_data["KOD_TUAN_RUMAH"],
                            "BIL_CALON": p_data["CALON"],
                            "KELAS": p_data["KELAS"],
                            "PERLU_K9": sep,
                            "DICADANGKAN": dic,
                            "STATUS": f"{status_icon} {status_text}",
                            "KEKURANGAN": max(0, sep - dic)
                        })

                    df_editable = pd.DataFrame(editable_rows)

                    if fly_cur == "status":
                        # Data editor - PPD boleh edit BIL_CALON, KELAS, PERLU_K9
                        st.markdown("#### ✏️ Edit Data Pusat (PPD)")
                        edited_df = st.data_editor(
                            df_editable,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "BIL": st.column_config.NumberColumn("BIL", width="small", disabled=True),
                                "NO_PUSAT": st.column_config.TextColumn("NO PUSAT", width="medium", disabled=True),
                                "NAMA_PUSAT": st.column_config.TextColumn("NAMA PUSAT", width="large", disabled=True),
                                "KOD_TUAN": st.column_config.TextColumn("KOD TUAN RUMAH", width="medium", disabled=True),
                                "BIL_CALON": st.column_config.NumberColumn("BIL CALON", help="PPD boleh edit ikut keperluan sebenar", min_value=0, max_value=500, step=1, required=True),
                                "KELAS": st.column_config.NumberColumn("KELAS", help="Auto: CEIL(Calon/20), tapi PPD boleh edit", min_value=0, max_value=30, step=1, required=True),
                                "PERLU_K9": st.column_config.NumberColumn("PERLU (K+9)", help="PPD boleh edit ikut keperluan, formula asal Kelas+9", min_value=0, max_value=50, step=1, required=True),
                                "DICADANGKAN": st.column_config.NumberColumn("DICADANGKAN", disabled=True),
                                "STATUS": st.column_config.TextColumn("STATUS", disabled=True),
                                "KEKURANGAN": st.column_config.NumberColumn("KEKURANGAN", help="Auto kira: PERLU - DICADANGKAN", disabled=True)
                            },
                            key=f"ppd_edit_{kod_ppd}",
                            num_rows="fixed"
                        )

                        # Auto-calculate logic: if BIL_CALON changed, update KELAS and PERLU suggestion
                        # Show save button
                        col_save, col_reset, col_info = st.columns([1, 1, 2])
                        with col_save:
                            if st.button("💾 Simpan Perubahan Pusat", type="primary", use_container_width=True, key=f"save_pusat_{kod_ppd}"):
                                try:
                                    # Update pusat_master table
                                    updated_count = 0
                                    for _, row in edited_df.iterrows():
                                        no_pusat = row["NO_PUSAT"]
                                        new_calon = int(row["BIL_CALON"])
                                        new_kelas = int(row["KELAS"])
                                        new_perlu = int(row["PERLU_K9"])

                                        # Find original record
                                        for _, r in df_pusat_raw.iterrows():
                                            d = r.get("data") if isinstance(r.get("data"), dict) else {}
                                            if isinstance(d, str):
                                                try: d = json.loads(d)
                                                except: d = {}
                                            r_no_pusat = str(r.get("no_pusat") or r.get("kod_pusat") or d.get("NO_PUSAT") or "").upper().strip()
                                            if r_no_pusat == no_pusat:
                                                # Update
                                                old_data = d.copy() if isinstance(d, dict) else {}
                                                old_data["JUMLAH_CALON"] = new_calon
                                                old_data["JUMLAH_KELAS"] = new_kelas
                                                old_data["CALON"] = new_calon
                                                old_data["KELAS"] = new_kelas

                                                update_payload = {
                                                    "jumlah_calon": new_calon,
                                                    "jumlah_kelas": new_kelas,
                                                    "calon": new_calon,
                                                    "data": old_data
                                                }
                                                # Try update by no_pusat
                                                try:
                                                    supa.table("pusat_master").update(update_payload).eq("no_pusat", no_pusat).execute()
                                                    updated_count += 1
                                                except:
                                                    try:
                                                        supa.table("pusat_master").update(update_payload).eq("kod_pusat", no_pusat).execute()
                                                        updated_count += 1
                                                    except Exception as e:
                                                        st.error(f"Gagal update {no_pusat}: {e}")
                                                break

                                    st.success(f"✅ Berjaya simpan {updated_count} pusat! Data calon, kelas, perlu telah dikemaskini.")
                                    st.balloons()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error simpan: {e}")

                        with col_reset:
                            if st.button("🔄 Reset Auto (Kira Semula)", use_container_width=True, key=f"reset_auto_{kod_ppd}"):
                                st.info("Auto kira semula: KELAS = CEIL(CALON/20), PERLU = KELAS+9")
                                st.rerun()

                        with col_info:
                            st.caption(f"Total: {len(edited_df)} pusat | Boleh edit CALON, KELAS, PERLU")

                    if fly_cur == "berwarna":
                        st.markdown("---")

                        # Also show colored HTML table for quick view
                        st.markdown("#### 📊 Paparan Status Berwarna")
                        # Create HTML table with colors
                        html_table = """
                    <style>
                    .ppd-table {width:100%; border-collapse:collapse; font-size:13px; background:white;}
                    .ppd-table th {background:#0d47a1; color:white; padding:0 8px; height:40px; text-align:left; font-weight:700; position:sticky; top:0; z-index:2; white-space:nowrap;}
                    .ppd-scroll {max-height:480px; overflow-y:auto; overflow-x:auto; border:2px solid #90caf9; border-radius:6px; background:white;}
                    .ppd-table td {padding:0 8px; height:44px; border-bottom:1px solid #e0e0e0; background:white; color:#0d47a1; white-space:nowrap;}
                    .ppd-table tr:hover td {background:#f5f5f5 !important;}
                    .badge-merah {background:#0d47a1 !important; color:#ffffff !important; padding:4px 8px; border-radius:12px; font-weight:700; border:2px solid #0d47a1;}
                    .badge-kuning {background:#bbdefb !important; color:#0d47a1 !important; padding:4px 8px; border-radius:12px; font-weight:700; border:2px solid #0d47a1;}
                    .badge-hijau {background:#ffffff !important; color:#0d47a1 !important; padding:4px 8px; border-radius:12px; font-weight:700; border:2px solid #0d47a1;}
                    .edit-hint {background:#e3f2fd; border-left:4px solid #1976d2; padding:6px 10px; margin:4px 0; font-size:11px;}
                    </style>
                    <div class="edit-hint">✏️ <b>PPD boleh edit:</b> BIL CALON, KELAS, PERLU (K+9) ikut keperluan sebenar - klik angka dalam table atas untuk edit &nbsp;|&nbsp; 📜 Papar 10 baris - skrol ke bawah untuk lihat selebihnya</div>
                    <div class="ppd-scroll"><table class="ppd-table">
                    <tr><th>BIL</th><th>NO PUSAT</th><th>NAMA PUSAT</th><th>KOD TUAN</th><th>BIL CALON ✏️</th><th>KELAS ✏️</th><th>PERLU (K+9) ✏️</th><th>DICADANG</th><th>STATUS</th></tr>
                    """

                        for _, r in (edited_df if 'edited_df' in locals() else df_editable).iterrows():
                            dic = r["DICADANGKAN"]
                            sep = r["PERLU_K9"]
                            if dic == 0:
                                badge_class = "badge-merah"
                                badge_text = f"🔴 {dic}"
                                status_badge = f'<span class="{badge_class}">🔴 Belum Ada</span>'
                            elif dic < sep:
                                badge_class = "badge-kuning"
                                badge_text = f"🟡 {dic}"
                                status_badge = f'<span class="{badge_class}">🟡 Belum Cukup</span>'
                            else:
                                badge_class = "badge-hijau"
                                badge_text = f"🟢 {dic}"
                                status_badge = f'<span class="{badge_class}">🟢 Cukup</span>'

                            html_table += f"<tr><td><b>{r['BIL']}</b></td><td><b>{r['NO_PUSAT']}</b></td><td>{r['NAMA_PUSAT']}</td><td>{r['KOD_TUAN']}</td><td style='text-align:center; background:#e3f2fd; font-weight:700; border:1px dashed #0d47a1;'>{r['BIL_CALON']}</td><td style='text-align:center; background:#e3f2fd; font-weight:700; border:1px dashed #1976d2;'>{r['KELAS']}</td><td style='text-align:center; background:#bbdefb; font-weight:700; border:1px dashed #0d47a1;'>{r['PERLU_K9']}</td><td style='text-align:center;'><span class='{badge_class}'>{badge_text}</span></td><td>{status_badge}</td></tr>"

                        html_table += "</table></div>"

                        st.markdown(html_table, unsafe_allow_html=True)

                    if fly_cur == "sekolah":
                        st.markdown("---")

                        # Export
                        with st.expander("📊 Export Data", expanded=False):
                            st.dataframe(df_pusat_ppd.sort_values("NO_PUSAT"), use_container_width=True, hide_index=True)
                            st.download_button(f"📥 Export Dashboard PPD {kod_ppd} (Excel)", to_excel(df_pusat_ppd), file_name=f"Dashboard_PPD_{kod_ppd}_{datetime.date.today()}.xlsx", use_container_width=True)

                        # Senarai sekolah dalam PPD
                        st.markdown("---")
                        st.markdown(f"### 🏫 Senarai Sekolah dalam PPD {kod_ppd} ({len(df_sekolah_list)} sekolah)")
                        if not df_sekolah_list.empty:
                            # Kira cadangan per sekolah
                            sekolah_cad_count = {}
                            if not df_cad_all.empty:
                                for _, c_row in df_cad_all.iterrows():
                                    k_sek = str(c_row.get("kod_sekolah") or c_row.get("kod_sekolah_asal") or "").upper().strip()
                                    if k_sek:
                                        sekolah_cad_count[k_sek] = sekolah_cad_count.get(k_sek, 0) + 1

                            sekolah_rows = []
                            for _, s in df_sekolah_list.iterrows():
                                k_sek = str(s.get("kod_sekolah") or s.get("KOD_SEKOLAH") or "").upper().strip()
                                n_sek = str(s.get("nama_sekolah") or s.get("NAMA_SEKOLAH") or "").upper().strip()
                                cad = sekolah_cad_count.get(k_sek, 0)

                                if cad == 0:
                                    s_icon = "🔴"
                                    s_status = "Belum Cadang"
                                elif cad < 5:
                                    s_icon = "🟡"
                                    s_status = f"{cad} dicadang"
                                else:
                                    s_icon = "🟢"
                                    s_status = f"{cad} dicadang"

                                sekolah_rows.append({"Logo": "🏫", "KOD_SEKOLAH": k_sek, "NAMA_SEKOLAH": n_sek[:35], "DICADANGKAN": cad, "STATUS": f"{s_icon} {s_status}"})

                            df_sekolah_display = pd.DataFrame(sekolah_rows).sort_values("KOD_SEKOLAH")
                            st.dataframe(df_sekolah_display, use_container_width=True, hide_index=True)
                        else:
                            st.info(f"Tiada sekolah dijumpai untuk PPD {kod_ppd}")

            except Exception as e:
                st.error(f"Error dashboard PPD: {e}")
                # Fallback simple
                try:
                    cnt_sekolah = supa.table("sekolah_master").select("kod_sekolah", count="exact").eq("kod_ppd", kod_ppd).execute()
                    cnt_cadang = supa.table("cadangan_sup").select("id", count="exact").eq("kod_ppd", kod_ppd).execute()
                    c1, c2 = st.columns(2)
                    c1.metric("Sekolah", cnt_sekolah.count)
                    c2.metric("Cadangan", cnt_cadang.count)
                except Exception as e2:
                    st.error(f"Fallback error: {e2}")

        elif menu == "sekolah":
            st.header(f"Senarai Sekolah PPD {kod_ppd}")
            try:
                res = supa.table("sekolah_master").select("*").eq("kod_ppd", kod_ppd).limit(2000).execute()
                df = pd.DataFrame(res.data or [])
                st.dataframe(df, use_container_width=True)
                st.download_button("Export Sekolah", to_excel(df), file_name=f"sekolah_{kod_ppd}.xlsx")
            except Exception as e:
                st.error(f"Error baca sekolah: {e}")

        elif menu == "pusat":
            st.header(f"Pusat di PPD {kod_ppd} - {PPD_MAP.get(kod_ppd, '')} - Total Calon & Poskod Pusat")
            st.caption("Filter BETUL ikut NO_PUSAT prefix BA=Klang sahaja | PPD boleh tambah/edit POSKOD PUSAT untuk jana ikut poskod terdekat")
            df_pusat_raw = get_pusat_df()
            if df_pusat_raw.empty:
                st.info("pusat_master kosong")
            else:
                rows = []
                for _, r in df_pusat_raw.iterrows():
                    d = r.get("data") if isinstance(r.get("data"), dict) else {}
                    if isinstance(d, str):
                        try: d = json.loads(d)
                        except: d = {}
                    no_pusat = str(r.get("no_pusat") or r.get("kod_pusat") or d.get("NO_PUSAT") or "").upper().strip()
                    nama = r.get("nama_pusat") or d.get("NAMA_PUSAT") or ""
                    j_calon = r.get("jumlah_calon") or r.get("calon") or d.get("JUMLAH_CALON") or 0
                    j_kelas = r.get("jumlah_kelas") or r.get("bilik") or d.get("JUMLAH_KELAS") or 0
                    try: jc = int(float(str(j_calon) or 0))
                    except: jc = 0
                    try: jk = int(float(str(j_kelas) or 0))
                    except: jk = kira_kelas_dari_calon(jc)
                    rows.append({"NO_PUSAT": no_pusat, "NAMA_PUSAT": nama, "JUMLAH_CALON": jc, "JUMLAH_KELAS": jk, "PETUGAS_K9": kira_petugas_dari_kelas(jk), "SEKOLAH_PERLU": kira_sekolah_perlu_calonkan(jk)})

                df_all = pd.DataFrame(rows)
                df_f = df_all[df_all["NO_PUSAT"].str.startswith(kod_ppd.upper())].copy() if not df_all.empty else df_all
                if df_f.empty:
                    st.warning(f"Tiada pusat dengan prefix {kod_ppd}")
                else:
                    if fly_cur == "senarai":
                        st.success(f"Jumpa {len(df_f)} pusat di PPD {kod_ppd} - {PPD_MAP.get(kod_ppd, '')}")
                        st.dataframe(df_f.sort_values("NO_PUSAT"), use_container_width=True, hide_index=True)
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Jumlah Pusat", len(df_f))
                        c2.metric("Total Calon", int(df_f["JUMLAH_CALON"].sum()))
                        c3.metric("Total Kelas", int(df_f["JUMLAH_KELAS"].sum()))
                        c4.metric("Total Perlu", int(df_f["SEKOLAH_PERLU"].sum()))
                        st.download_button(f"Export Pusat {kod_ppd}", to_excel(df_f), file_name=f"pusat_{kod_ppd}.xlsx", use_container_width=True)

                    if fly_cur == "poskod":
                        st.markdown("---")
                        st.markdown("### 📮 Tambah/Edit Poskod Pusat (Untuk Jana Poskod Terdekat)")
                        st.info("💡 Poskod Pusat diperlukan untuk sistem kira jarak poskod rumah guru vs pusat. Kalau kosong, sistem akan guna poskod sekolah tuan rumah sebagai fallback.")
                        with st.expander("✏️ Edit Poskod Pusat - Klik untuk buka", expanded=False):
                            # Build editable table for poskod
                            poskod_rows = []
                            for _, r in df_f.iterrows():
                                no_p = r["NO_PUSAT"]
                                # Try get existing poskod
                                existing_poskod = ""
                                try:
                                    df_raw = df_pusat_raw
                                    for _, pr in df_raw.iterrows():
                                        d = pr.get("data") if isinstance(pr.get("data"), dict) else {}
                                        if isinstance(d, str):
                                            try: d = json.loads(d)
                                            except: d = {}
                                        no_check = str(pr.get("no_pusat") or pr.get("kod_pusat") or d.get("NO_PUSAT") or "").upper().strip()
                                        if no_check == no_p:
                                            existing_poskod = str(pr.get("poskod") or d.get("POSKOD") or d.get("POSKOD_PUSAT") or "").strip()
                                            break
                                except:
                                    pass
                                poskod_rows.append({"NO_PUSAT": no_p, "NAMA_PUSAT": r["NAMA_PUSAT"][:30], "POSKOD_SEKARANG": existing_poskod, "POSKOD_BARU": existing_poskod})
                            df_poskod_edit = pd.DataFrame(poskod_rows)
                            edited_poskod = st.data_editor(
                                df_poskod_edit,
                                column_config={
                                    "NO_PUSAT": st.column_config.TextColumn("NO_PUSAT", disabled=True),
                                    "NAMA_PUSAT": st.column_config.TextColumn("NAMA PUSAT", disabled=True),
                                    "POSKOD_SEKARANG": st.column_config.TextColumn("Sekarang", disabled=True),
                                    "POSKOD_BARU": st.column_config.TextColumn("Poskod Baru (5 digit)", help="Contoh: 41000 untuk Klang"),
                                },
                                use_container_width=True,
                                hide_index=True,
                                key="edit_poskod_pusat"
                            )
                            if st.button("💾 Simpan Poskod Pusat", type="primary", use_container_width=True, key="simpan_poskod_pusat"):
                                try:
                                    berjaya_poskod = 0
                                    for _, row_edit in edited_poskod.iterrows():
                                        no_p = row_edit["NO_PUSAT"]
                                        pk_baru = str(row_edit["POSKOD_BARU"]).strip()
                                        if not pk_baru or pk_baru == row_edit["POSKOD_SEKARANG"]:
                                            continue
                                        # Update pusat_master
                                        try:
                                            # Get existing record
                                            res = supa.table("pusat_master").select("*").eq("no_pusat", no_p).limit(1).execute()
                                            if not res.data:
                                                res = supa.table("pusat_master").select("*").eq("kod_pusat", no_p).limit(1).execute()
                                            if res.data:
                                                rec = res.data[0]
                                                rec_id = rec.get("id")
                                                d = rec.get("data") or {}
                                                if isinstance(d, str):
                                                    try: d = json.loads(d)
                                                    except: d = {}
                                                d["POSKOD"] = pk_baru
                                                d["POSKOD_PUSAT"] = pk_baru
                                                # Try update with poskod column if exists, else only data
                                                try:
                                                    supa.table("pusat_master").update({"poskod": pk_baru, "data": d}).eq("id", rec_id).execute()
                                                except:
                                                    supa.table("pusat_master").update({"data": d}).eq("id", rec_id).execute()
                                                berjaya_poskod += 1
                                        except Exception as e:
                                            st.warning(f"{no_p}: {e}")
                                    st.success(f"✅ Berjaya kemaskini {berjaya_poskod} poskod pusat!")
                                    st.balloons()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error simpan poskod: {e}")



        elif menu == "jana":
            st.markdown(f"""
            <div style="background: #0d47a1; padding:20px; border-radius:12px; color:white; border: 2px solid #002171; margin-bottom:20px;">
                <div style="display:flex; align-items:center; gap:15px;">
                    <div style="font-size:48px;">🚀</div>
                    <div>
                        <h2 style="margin:0; color:white; font-size:24px;">Jana Keseluruhan - PPD {kod_ppd} - {PPD_MAP.get(kod_ppd, '')}</h2>
                        <p style="margin:5px 0 0 0; color:#bbdefb; font-size:13px;">Pilih: Jana Keseluruhan (Auto Poskod Terdekat) atau Jana Mengikut Jawatan - Kekal Max 3</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            df_pusat_raw = get_pusat_df()
            df_cad_all = get_cadangan_df(kod_ppd=kod_ppd)

            if df_pusat_raw.empty:
                st.warning("⚠️ Tiada pusat_master")
                st.stop()
            if df_cad_all.empty:
                st.warning(f"⚠️ Belum ada cadangan SUP untuk PPD {kod_ppd}")
                st.stop()

            # Parse pusat with poskod
            rows = []
            for _, r in df_pusat_raw.iterrows():
                d = r.get("data") if isinstance(r.get("data"), dict) else {}
                if isinstance(d, str):
                    try: d = json.loads(d)
                    except: d = {}
                no_pusat = str(r.get("no_pusat") or r.get("kod_pusat") or d.get("NO_PUSAT") or "").upper().strip()
                if not no_pusat.startswith(kod_ppd.upper()): continue
                nama = r.get("nama_pusat") or d.get("NAMA_PUSAT") or ""
                kod_sek_tuan = str(r.get("kod_sekolah_tuan_rumah") or r.get("kod_sekolah") or d.get("KOD_SEKOLAH") or "").upper().strip()
                j_calon = r.get("jumlah_calon") or d.get("JUMLAH_CALON") or 0
                j_kelas = r.get("jumlah_kelas") or d.get("JUMLAH_KELAS") or 0
                poskod_pusat = str(r.get("poskod") or d.get("POSKOD") or d.get("POSKOD_PUSAT") or "").strip()
                try: jc = int(float(str(j_calon) or 0))
                except: jc = 0
                try: jk = int(float(str(j_kelas) or 0))
                except: jk = kira_kelas_dari_calon(jc)
                if jk == 0: jk = kira_kelas_dari_calon(jc)
                rows.append({"NO_PUSAT": no_pusat, "NAMA_PUSAT": nama, "KOD_SEKOLAH_TUAN_RUMAH": kod_sek_tuan, "JUMLAH_CALON": jc, "JUMLAH_KELAS": jk, "PETUGAS": kira_petugas_dari_kelas(jk), "POSKOD_PUSAT": poskod_pusat})
            df_pusat_ppd = pd.DataFrame(rows)

            if df_pusat_ppd.empty:
                st.warning(f"Tiada pusat dengan prefix {kod_ppd}")
                st.stop()

            def get_poskod_guru(row):
                return str(row.get("POSKOD_RUMAH") or row.get("poskod_rumah") or "").strip()
            def get_poskod_pusat_val(no_pusat):
                r = df_pusat_ppd[df_pusat_ppd["NO_PUSAT"]==no_pusat]
                if not r.empty:
                    pk = str(r.iloc[0].get("POSKOD_PUSAT") or "").strip()
                    if pk and pk.lower() not in ("none","nan",""):
                        return pk
                try:
                    kod_tuan = str(r.iloc[0].get("KOD_SEKOLAH_TUAN_RUMAH") or "").strip() if not r.empty else ""
                    if kod_tuan:
                        res_sek = supa.table("sekolah_master").select("*").eq("kod_sekolah", kod_tuan).limit(1).execute()
                        if res_sek.data:
                            d = res_sek.data[0].get("data") or {}
                            if isinstance(d, str):
                                try: d = json.loads(d)
                                except: d = {}
                            pk = str(res_sek.data[0].get("poskod") or d.get("POSKOD") or "").strip()
                            if pk: return pk
                except: pass
                return ""
            def poskod_distance(pk_guru, pk_pusat):
                try:
                    g = int(re.sub(r"\D","", pk_guru)[:5] or 0)
                    p = int(re.sub(r"\D","", pk_pusat)[:5] or 0)
                    if g==0 or p==0: return 99999
                    return abs(g-p)
                except: return 99999

            # ===== SUB MENU UTAMA =====
            sub_jana = "🌍 Jana Keseluruhan (Auto Poskod Terdekat)" if fly_cur == "auto" else "👑 Jana Mengikut Jawatan"

            # ===== TAB 1: JANA KESELURUHAN AUTO POSKOD =====
            if "Jana Keseluruhan" in sub_jana:
                st.markdown("### 🌍 Jana Keseluruhan - Auto Poskod Terdekat")
                st.info("Baca POSKOD RUMAH guru vs POSKOD PUSAT, pusat paling dekat dulu. Kalau penuh, auto ke pusat kedua terdekat. Kekal Max 3 & elak sekolah sendiri. Penyelia Kawasan TIDAK termasuk di sini - lantik di Selenggara Bilik Kebal.")

                # FIX FINAL: Jana Keseluruhan Auto HANYA untuk 3 jawatan biasa sahaja - Khas langsung tak masuk
                # Hanya benarkan: Ketua Pengawas, Timbalan Ketua Pengawas, Pengawas Peperiksaan (exact)
                # Semua Khas (Juru Tulis, Juru Baca, Hospital, Pengiring, Pengemas, Penyelia) dikeluarkan terus - hanya di Penempatan Manual sahaja
                def is_auto_jawatan(r):
                    j = str(r.get("JAWATAN_CADANGAN") or r.get("jawatan_cadangan") or r.get("JAWATAN") or "").upper().strip()
                    # Hanya 3 ini sahaja yang boleh auto
                    if "KETUA PENGAWAS" in j and "TIMBALAN" not in j and "HOSPITAL" not in j:
                        return True
                    if "TIMBALAN KETUA PENGAWAS" in j or ("TIMBALAN" in j and "KETUA" in j and "HOSPITAL" not in j):
                        return True
                    if j == "PENGAWAS PEPERIKSAAN" or (j.startswith("PENGAWAS") and "HOSPITAL" not in j and "PENGIRING" not in j and "KHAS" not in j):
                        # Pengawas Peperiksaan biasa sahaja
                        if "HOSPITAL" in j or "PENGIRING" in j or "JURU" in j or "PENGEMAS" in j or "PENYELIA" in j or "SELENGGARA" in j:
                            return False
                        return True
                    # Semua lain (Juru Tulis, Juru Baca, Hospital, Pengiring, Pengemas, Penyelia, Selenggara) = False - tak masuk auto
                    return False

                df_cad_all_auto = df_cad_all[df_cad_all.apply(is_auto_jawatan, axis=1)].copy() if not df_cad_all.empty else df_cad_all.copy()
                # Info
                try:
                    khas_count = len(df_cad_all) - len(df_cad_all_auto)
                    if khas_count > 0:
                        st.info(f"ℹ️ Jana Keseluruhan Auto: {len(df_cad_all_auto)} petugas biasa (KP/TKP/Pengawas) akan dijana auto. {khas_count} Pengawas Khas (JT/JB/Hospital/Pengiring/Pengemas/Penyelia) TIDAK termasuk auto - sila guna Jana Ikut Jawatan atau Penempatan Manual")
                except:
                    pass

                cad_per_sekolah = {}
                for _, c in df_cad_all_auto.iterrows():
                    k_sek = str(c.get("KOD_SEKOLAH") or c.get("KOD_SEKOLAH_ASAL") or "").upper().strip()
                    if k_sek: cad_per_sekolah[k_sek] = cad_per_sekolah.get(k_sek, 0) + 1
                c1,c2,c3,c4 = st.columns(4)
                c1.metric("📚 Sekolah Mencadang", len(cad_per_sekolah))
                c2.metric("👨‍🏫 Guru Dicadang", len(df_cad_all))
                c3.metric("🏫 Pusat", len(df_pusat_ppd))
                c4.metric("📋 Perlu Petugas", int(df_pusat_ppd["PETUGAS"].sum()))

                with st.expander(f"📋 Lihat {len(df_cad_all)} Cadangan Dari SUP", expanded=False):
                    cols = [c for c in ["NAMA_GURU","IC_GURU","JANTINA","POSKOD_RUMAH","JAWATAN_CADANGAN","KOD_SEKOLAH_ASAL","STATUS"] if c in df_cad_all.columns]
                    st.dataframe(df_cad_all[cols] if cols else df_cad_all, use_container_width=True, hide_index=True)

                col_jana_all, col_clear = st.columns([3,1])
                with col_jana_all:
                    btn_jana_all = st.button("🌍 JANA KESELURUHAN - Auto Poskod Terdekat (1 KP + 1 TKP + Pengawas)", type="primary", use_container_width=True, key="btn_jana_all_poskod_v3")
                with col_clear:
                    if st.button("🗑️ Clear", use_container_width=True, key="clear_jana_all_v3"):
                        if "jana_all_result" in st.session_state: del st.session_state["jana_all_result"]
                        st.rerun()

                if btn_jana_all or "jana_all_result" in st.session_state:
                    if btn_jana_all:
                        import random
                        assignments = []
                        df_pool_all = df_cad_all.copy()
                        def is_belum(row):
                            kp = str(row.get("kod_pusat") or row.get("KOD_PUSAT") or "").strip()
                            return kp == "" or kp.lower() in ("none","null","nan","nat","-")
                        df_pool = df_pool_all[df_pool_all.apply(is_belum, axis=1)].copy()
                        if df_pool.empty:
                            st.warning("Semua guru telah dilantik!")
                            st.stop()
                        pusat_info_map = {}
                        for _, p in df_pusat_ppd.iterrows():
                            pusat_info_map[p["NO_PUSAT"]] = {"KOD_TUAN": str(p.get("KOD_SEKOLAH_TUAN_RUMAH","") or "").upper().strip(), "NAMA": p.get("NAMA_PUSAT",""), "PETUGAS": int(p.get("PETUGAS",0)), "POSKOD": str(p.get("POSKOD_PUSAT") or "").strip()}
                        df_pool["POSKOD_GURU_NORM"] = df_pool.apply(lambda r: get_poskod_guru(r), axis=1)
                        df_pool_shuffled = df_pool.sample(frac=1, random_state=random.randint(1,100000)).reset_index(drop=True)
                        pusat_sekolah_count = {}
                        pusat_total = {no:0 for no in pusat_info_map.keys()}
                        pusat_kp = {no:0 for no in pusat_info_map.keys()}
                        pusat_tkp = {no:0 for no in pusat_info_map.keys()}
                        used_ic = set()
                        def cari_pusat_terdekat(guru_row):
                            poskod_guru = str(guru_row.get("POSKOD_GURU_NORM") or "")
                            kod_sek_guru = str(guru_row.get("KOD_SEKOLAH_ASAL") or "").upper().strip()
                            jarak_list = []
                            for no_pusat, info in pusat_info_map.items():
                                if info["KOD_TUAN"] and kod_sek_guru and info["KOD_TUAN"] == kod_sek_guru: continue
                                if pusat_sekolah_count.get((no_pusat, kod_sek_guru),0) >=3: continue
                                if pusat_total.get(no_pusat,0) >= info["PETUGAS"]: continue
                                jaw = str(guru_row.get("JAWATAN_CADANGAN") or "").upper()
                                if "KETUA PENGAWAS" in jaw and "TIMBALAN" not in jaw:
                                    if pusat_kp.get(no_pusat,0) >=1: continue
                                elif "TIMBALAN" in jaw:
                                    if pusat_tkp.get(no_pusat,0) >=1: continue
                                poskod_pusat_val = get_poskod_pusat_val(no_pusat) or info.get("POSKOD","")
                                jarak = poskod_distance(poskod_guru, poskod_pusat_val)
                                jarak_list.append((jarak, no_pusat))
                            jarak_list.sort(key=lambda x: x[0])
                            return [no for _, no in jarak_list]
                        # KP
                        for _, guru_row in df_pool_shuffled.iterrows():
                            ic = str(guru_row.get("IC_GURU") or "")
                            if ic in used_ic: continue
                            jaw = str(guru_row.get("JAWATAN_CADANGAN") or "").upper()
                            if "KETUA PENGAWAS" not in jaw or "TIMBALAN" in jaw: continue
                            cands = cari_pusat_terdekat(guru_row)
                            if not cands: continue
                            chosen = cands[0]
                            assignments.append({"IC_GURU": ic, "NAMA_GURU": guru_row.get("NAMA_GURU",""), "KOD_SEKOLAH_ASAL": str(guru_row.get("KOD_SEKOLAH_ASAL") or "").upper(), "JAWATAN_CADANGAN": guru_row.get("JAWATAN_CADANGAN",""), "POSKOD_RUMAH": guru_row.get("POSKOD_GURU_NORM",""), "NO_PUSAT_TUGAS": chosen, "NAMA_PUSAT_TUGAS": pusat_info_map[chosen]["NAMA"], "id": guru_row.get("id","")})
                            used_ic.add(ic)
                            pusat_sekolah_count[(chosen, str(guru_row.get("KOD_SEKOLAH_ASAL") or "").upper())] = pusat_sekolah_count.get((chosen, str(guru_row.get("KOD_SEKOLAH_ASAL") or "").upper()),0)+1
                            pusat_total[chosen] +=1
                            pusat_kp[chosen] +=1
                        # TKP
                        for _, guru_row in df_pool_shuffled.iterrows():
                            ic = str(guru_row.get("IC_GURU") or "")
                            if ic in used_ic: continue
                            if "TIMBALAN" not in str(guru_row.get("JAWATAN_CADANGAN") or "").upper(): continue
                            cands = cari_pusat_terdekat(guru_row)
                            if not cands: continue
                            chosen = cands[0]
                            assignments.append({"IC_GURU": ic, "NAMA_GURU": guru_row.get("NAMA_GURU",""), "KOD_SEKOLAH_ASAL": str(guru_row.get("KOD_SEKOLAH_ASAL") or "").upper(), "JAWATAN_CADANGAN": guru_row.get("JAWATAN_CADANGAN",""), "POSKOD_RUMAH": guru_row.get("POSKOD_GURU_NORM",""), "NO_PUSAT_TUGAS": chosen, "NAMA_PUSAT_TUGAS": pusat_info_map[chosen]["NAMA"], "id": guru_row.get("id","")})
                            used_ic.add(ic)
                            pusat_sekolah_count[(chosen, str(guru_row.get("KOD_SEKOLAH_ASAL") or "").upper())] = pusat_sekolah_count.get((chosen, str(guru_row.get("KOD_SEKOLAH_ASAL") or "").upper()),0)+1
                            pusat_total[chosen] +=1
                            pusat_tkp[chosen] +=1
                        # Pengawas - HANYA Pengawas Peperiksaan biasa sahaja - Khas (JT/JB/Hospital/Pengiring/Pengemas/Penyelia) langsung tak masuk auto, hanya Penempatan Manual
                        def is_pengawas_biasa_only(row):
                            j = str(row.get("JAWATAN_CADANGAN") or row.get("jawatan_cadangan") or "").upper().strip()
                            # Hanya Pengawas Peperiksaan exact sahaja
                            if "PENGAWAS PEPERIKSAAN" not in j:
                                return False
                            if any(k in j for k in ["PENYELIA", "JURU", "HOSPITAL", "PENGIRING", "PENGEMAS", "SELENGGARA", "BILIK KEBAL"]):
                                return False
                            return True
                        df_pool_biasa = [r for _, r in df_pool_shuffled.iterrows() if is_pengawas_biasa_only(r)]
                        for guru_row in df_pool_biasa:
                            ic = str(guru_row.get("IC_GURU") or "")
                            if ic in used_ic: continue
                            jaw = str(guru_row.get("JAWATAN_CADANGAN") or "").upper()
                            if "KETUA PENGAWAS" in jaw: continue
                            if "TIMBALAN" in jaw: continue
                            if "PENYELIA" in jaw: continue
                            cands = cari_pusat_terdekat(guru_row)
                            if not cands: continue
                            chosen = cands[0]
                            poskod_guru = str(guru_row.get("POSKOD_GURU_NORM") or "")
                            poskod_pusat_val = get_poskod_pusat_val(chosen) or pusat_info_map[chosen].get("POSKOD","")
                            jarak_val = poskod_distance(poskod_guru, poskod_pusat_val)
                            assignments.append({"IC_GURU": ic, "NAMA_GURU": guru_row.get("NAMA_GURU",""), "KOD_SEKOLAH_ASAL": str(guru_row.get("KOD_SEKOLAH_ASAL") or "").upper(), "JAWATAN_CADANGAN": guru_row.get("JAWATAN_CADANGAN",""), "POSKOD_RUMAH": poskod_guru, "POSKOD_PUSAT": poskod_pusat_val, "NO_PUSAT_TUGAS": chosen, "NAMA_PUSAT_TUGAS": pusat_info_map[chosen]["NAMA"], "JARAK": jarak_val, "id": guru_row.get("id","")})
                            used_ic.add(ic)
                            pusat_sekolah_count[(chosen, str(guru_row.get("KOD_SEKOLAH_ASAL") or "").upper())] = pusat_sekolah_count.get((chosen, str(guru_row.get("KOD_SEKOLAH_ASAL") or "").upper()),0)+1
                            pusat_total[chosen] +=1
                        st.session_state["jana_all_result"] = assignments
                        st.success(f"✅ Berjaya jana {len(assignments)} guru ikut poskod terdekat!")
                    else:
                        assignments = st.session_state.get("jana_all_result", [])

                    if st.session_state.get("jana_all_result"):
                        df_assign = pd.DataFrame(st.session_state["jana_all_result"])
                        st.dataframe(df_assign, use_container_width=True, hide_index=True)
                        if st.button("💾 Simpan Jana Keseluruhan ke DB", type="primary", use_container_width=True, key="simpan_jana_all_v3"):
                            try:
                                for a in assignments:
                                    if a.get("id"):
                                        supa.table("cadangan_sup").update({"kod_pusat": a.get("NO_PUSAT_TUGAS"), "status": "DILANTIK PPD"}).eq("id", a.get("id")).execute()
                                    else:
                                        supa.table("cadangan_sup").update({"kod_pusat": a.get("NO_PUSAT_TUGAS"), "status": "DILANTIK PPD"}).eq("ic_guru", a.get("IC_GURU")).execute()
                                st.success(f"✅ {len(assignments)} disimpan!")
                                st.balloons()
                            except Exception as e:
                                st.error(f"Gagal: {e}")
                        st.download_button("📥 Export", to_excel(df_assign), file_name=f"jana_poskod_{kod_ppd}.xlsx", use_container_width=True)

            # ===== TAB 2: JANA MENGIKUT JAWATAN - FIXED VISIBLE =====
            else:
                st.markdown("### 👑 Jana Mengikut Jawatan")
                st.info("Klik jawatan di bawah, sistem akan paparkan semua guru jawatan tersebut yang BELUM ditempatkan lagi. Kemudian pilih pusat & jana.")

                # Pilihan jawatan - BUTTON style - TANPA Penyelia Kawasan (sebab lantik di Selenggara Bilik Kebal)
                st.markdown("#### Pilih Jawatan (Klik untuk papar - Penyelia Kawasan tidak perlu di sini, lantik di Selenggara Bilik Kebal):")
                col_j1, col_j2, col_j3 = st.columns(3)
                with col_j1:
                    btn_kp = st.button("👑 Ketua Pengawas", use_container_width=True, key="btn_jawatan_kp_main", type="primary" if st.session_state.get("pilih_jawatan_jana_main")=="Ketua Pengawas" else "secondary")
                with col_j2:
                    btn_tkp = st.button("👑 Timbalan KP", use_container_width=True, key="btn_jawatan_tkp_main", type="primary" if st.session_state.get("pilih_jawatan_jana_main")=="Timbalan Ketua Pengawas" else "secondary")
                with col_j3:
                    btn_peng = st.button("👨‍🏫 Pengawas Peperiksaan", use_container_width=True, key="btn_jawatan_peng_main", type="primary" if st.session_state.get("pilih_jawatan_jana_main")=="Pengawas Peperiksaan" else "secondary")

                # Set session based on button click
                if btn_kp:
                    st.session_state["pilih_jawatan_jana_main"] = "Ketua Pengawas"
                if btn_tkp:
                    st.session_state["pilih_jawatan_jana_main"] = "Timbalan Ketua Pengawas"
                if btn_peng:
                    st.session_state["pilih_jawatan_jana_main"] = "Pengawas Peperiksaan"

                # Default
                if "pilih_jawatan_jana_main" not in st.session_state:
                    st.session_state["pilih_jawatan_jana_main"] = "Ketua Pengawas"

                pilih_jawatan_jana = st.session_state["pilih_jawatan_jana_main"]
                st.markdown(f"### 📋 {pilih_jawatan_jana} - Belum Ditempatkan")

                # Filter guru by jawatan & belum lantik
                def match_jawatan(row, target):
                    jaw = str(row.get("JAWATAN_CADANGAN") or row.get("jawatan_cadangan") or "").upper()
                    tgt = target.upper()
                    if "KETUA PENGAWAS" in tgt and "TIMBALAN" not in tgt:
                        return "KETUA PENGAWAS" in jaw and "TIMBALAN" not in jaw
                    elif "TIMBALAN" in tgt:
                        return "TIMBALAN" in jaw
                    elif "PENGAWAS PEPERIKSAAN" in tgt or tgt=="PENGAWAS PEPERIKSAAN":
                        return "PENGAWAS PEPERIKSAAN" in jaw or (jaw.strip()=="PENGAWAS")
                    elif "PENYELIA" in tgt:
                        return "PENYELIA" in jaw
                    else:
                        return tgt in jaw

                df_jawatan_all = df_cad_all[df_cad_all.apply(lambda r: match_jawatan(r, pilih_jawatan_jana), axis=1)].copy()
                df_belum_jawatan = df_jawatan_all[df_jawatan_all.apply(lambda r: str(r.get("kod_pusat") or r.get("KOD_PUSAT") or "").strip() in ("", "None", "none", "null", "nan", "nat"), axis=1)].copy()

                if df_belum_jawatan.empty:
                    st.warning(f"⚠️ Tiada {pilih_jawatan_jana} yang belum ditempatkan - semua sudah dilantik atau tiada cadangan jawatan ini.")
                    if not df_jawatan_all.empty:
                        st.info(f"Ada {len(df_jawatan_all)} {pilih_jawatan_jana} total, tapi semua sudah ada kod_pusat.")
                        st.dataframe(df_jawatan_all[["NAMA_GURU","IC_GURU","KOD_SEKOLAH_ASAL","kod_pusat","STATUS"]].head(20), use_container_width=True)
                else:
                    st.success(f"✅ Jumpa {len(df_belum_jawatan)} {pilih_jawatan_jana} yang BELUM ditempatkan lagi")

                    # Add poskod & jarak sorting - need to choose pusat first? Show without pusat first, then allow pilih pusat
                    # Show list of guru belum ditempatkan
                    display_belum = []
                    for _, r in df_belum_jawatan.iterrows():
                        display_belum.append({
                            "id": r.get("id",""),
                            "NAMA GURU": r.get("NAMA_GURU","") or r.get("nama_guru",""),
                            "IC": r.get("IC_GURU","") or r.get("ic_guru",""),
                            "JAWATAN": r.get("JAWATAN_CADANGAN","") or r.get("jawatan_cadangan",""),
                            "SEKOLAH ASAL": r.get("KOD_SEKOLAH_ASAL","") or r.get("kod_sekolah_asal",""),
                            "POSKOD RUMAH": r.get("POSKOD_RUMAH","") or r.get("poskod_rumah",""),
                            "TELEFON": r.get("TELEFON_GURU","") or r.get("telefon_guru",""),
                            "STATUS": r.get("STATUS","") or r.get("status","")
                        })
                    df_display_belum = pd.DataFrame(display_belum)
                    st.dataframe(df_display_belum, use_container_width=True, hide_index=True)

                    st.markdown("---")
                    st.markdown(f"#### 🎯 Pilih Pusat Untuk {pilih_jawatan_jana} Ini")

                    # Pilih pusat dropdown
                    pilihan_pusat_jawatan = st.selectbox(
                        f"Pilih Pusat Peperiksaan untuk {pilih_jawatan_jana}",
                        df_pusat_ppd["NO_PUSAT"].tolist(),
                        format_func=lambda x: f"{x} - {df_pusat_ppd[df_pusat_ppd['NO_PUSAT']==x]['NAMA_PUSAT'].values[0][:35] if not df_pusat_ppd[df_pusat_ppd['NO_PUSAT']==x].empty else x} (Perlu {df_pusat_ppd[df_pusat_ppd['NO_PUSAT']==x]['PETUGAS'].values[0] if not df_pusat_ppd[df_pusat_ppd['NO_PUSAT']==x].empty else '?'})",
                        key=f"pilih_pusat_jawatan_v3_{pilih_jawatan_jana}"
                    )

                    info_pusat = df_pusat_ppd[df_pusat_ppd["NO_PUSAT"]==pilihan_pusat_jawatan]
                    kod_tuan = str(info_pusat["KOD_SEKOLAH_TUAN_RUMAH"].values[0] if not info_pusat.empty else "").upper().strip()
                    poskod_pusat_val = get_poskod_pusat_val(pilihan_pusat_jawatan)

                    st.caption(f"Pusat {pilihan_pusat_jawatan} | Tuan Rumah: {kod_tuan or 'Tiada'} | Poskod Pusat: {poskod_pusat_val or 'Fallback poskod sekolah'} | Max 3 per sekolah | Elak sekolah sendiri")

                    # Count current in pusat
                    try:
                        res_curr = supa.table("cadangan_sup").select("*").eq("kod_pusat", pilihan_pusat_jawatan).limit(5000).execute()
                        df_curr = pd.DataFrame(res_curr.data or [])
                        sekolah_count_curr = {}
                        if not df_curr.empty:
                            for _, r in df_curr.iterrows():
                                ks = str(r.get("kod_sekolah_asal") or "").upper().strip()
                                sekolah_count_curr[ks] = sekolah_count_curr.get(ks, 0) + 1
                        st.info(f"ℹ️ Pusat {pilihan_pusat_jawatan} sudah ada {len(df_curr)} petugas ditempatkan. Sekolah count: {sekolah_count_curr}")
                    except:
                        df_curr = pd.DataFrame()
                        sekolah_count_curr = {}

                    # Filter eligible by max3 & sekolah sendiri & poskod terdekat
                    eligible_with_jarak = []
                    for _, r in df_belum_jawatan.iterrows():
                        ks = str(r.get("KOD_SEKOLAH_ASAL") or r.get("kod_sekolah_asal") or "").upper().strip()
                        if kod_tuan and ks == kod_tuan: continue
                        if sekolah_count_curr.get(ks,0) >=3: continue
                        pk_guru = str(r.get("POSKOD_RUMAH") or r.get("poskod_rumah") or "")
                        jarak = poskod_distance(pk_guru, poskod_pusat_val)
                        eligible_with_jarak.append((jarak, r))

                    eligible_with_jarak.sort(key=lambda x: x[0])

                    if not eligible_with_jarak:
                        st.warning("Tiada calon layak untuk pusat ini (semua sekolah sama atau max 3)")
                    else:
                        st.markdown(f"**{len(eligible_with_jarak)} calon {pilih_jawatan_jana} layak untuk {pilihan_pusat_jawatan} (disusun poskod terdekat):**")
                        display_eligible = []
                        for jarak, r in eligible_with_jarak:
                            display_eligible.append({
                                "JARAK": jarak if jarak!=99999 else "Tiada poskod",
                                "NAMA GURU": r.get("NAMA_GURU","") or r.get("nama_guru",""),
                                "IC": r.get("IC_GURU","") or r.get("ic_guru",""),
                                "SEKOLAH ASAL": r.get("KOD_SEKOLAH_ASAL","") or r.get("kod_sekolah_asal",""),
                                "POSKOD RUMAH": r.get("POSKOD_RUMAH","") or r.get("poskod_rumah",""),
                                "POSKOD PUSAT": poskod_pusat_val,
                                "id": r.get("id","")
                            })
                        df_eligible_disp = pd.DataFrame(display_eligible)
                        st.dataframe(df_eligible_disp, use_container_width=True, hide_index=True)

                        pilih_guru_jawatan = st.multiselect(
                            f"Pilih {pilih_jawatan_jana} untuk lantik ke {pilihan_pusat_jawatan} (paling dekat di atas)",
                            df_eligible_disp["id"].tolist(),
                            format_func=lambda x: f"{df_eligible_disp[df_eligible_disp['id']==x]['NAMA GURU'].values[0]} - {df_eligible_disp[df_eligible_disp['id']==x]['SEKOLAH ASAL'].values[0]} - Poskod {df_eligible_disp[df_eligible_disp['id']==x]['POSKOD RUMAH'].values[0]} - Jarak {df_eligible_disp[df_eligible_disp['id']==x]['JARAK'].values[0]}" if not df_eligible_disp[df_eligible_disp['id']==x].empty else str(x),
                            key=f"multiselect_jawatan_v3_{pilih_jawatan_jana}_{pilihan_pusat_jawatan}"
                        )

                        col_lantik_j, col_export_j = st.columns([2,1])
                        with col_lantik_j:
                            if st.button(f"✅ Lantik {len(pilih_guru_jawatan)} {pilih_jawatan_jana} ke {pilihan_pusat_jawatan}", type="primary", use_container_width=True, key=f"btn_lantik_jawatan_v3_{pilih_jawatan_jana}_{pilihan_pusat_jawatan}", disabled=len(pilih_guru_jawatan)==0):
                                try:
                                    berjaya = 0
                                    for gid in pilih_guru_jawatan:
                                        supa.table("cadangan_sup").update({"kod_pusat": pilihan_pusat_jawatan, "status": "DILANTIK PPD"}).eq("id", gid).execute()
                                        berjaya+=1
                                    st.success(f"✅ {berjaya} {pilih_jawatan_jana} dilantik ke {pilihan_pusat_jawatan} (poskod terdekat)")
                                    st.balloons()
                                    st.rerun()
                                except Exception as e:
                                    st.error("Maaf, berlaku masalah semasa memproses. Sila cuba lagi.")
                        with col_export_j:
                            st.download_button(f"📥 Export {pilih_jawatan_jana}", to_excel(df_eligible_disp), file_name=f"{pilih_jawatan_jana.replace(' ','_')}_{pilihan_pusat_jawatan}.xlsx", use_container_width=True, key=f"exp_jawatan_v3_{pilih_jawatan_jana}")


        elif menu == "hasil":
            st.header(f"Hasil Janaan - PPD {kod_ppd}")

            # ===== BUTANG BATAL JANAAN - RESET SEMUA JADI 0 =====
            col_batal1, col_batal2 = st.columns([3, 1])
            with col_batal1:
                st.caption(f"PPD {kod_ppd} - Jika ada pelanggaran max 3 (contoh SAM NURUL IMAN 10 orang di BA021), batal dan jana semula")
            with col_batal2:
                if st.button("🗑️ Batal Janaan - Reset 0", type="primary", use_container_width=True, key="batal_janaan_all"):
                    st.session_state["confirm_batal"] = True

            if st.session_state.get("confirm_batal"):
                st.warning("⚠️ Anda pasti nak batal semua janaan? Semua penempatan akan jadi 0 dan perlu Jana Keseluruhan semula!")
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("✅ YA, Batal Semua Janaan", type="primary", use_container_width=True, key="confirm_yes_batal"):
                        try:
                            # Clear DB - set kod_pusat = None untuk PPD ini
                            st.info("Membatalkan semua janaan...")
                            # Update semua cadangan PPD ini
                            supa.table("cadangan_sup").update({"kod_pusat": None, "status": "DICADANGKAN"}).eq("kod_ppd", kod_ppd).execute()
                            # Clear session
                            if "jana_all_result" in st.session_state:
                                del st.session_state["jana_all_result"]
                            if "jana_pusat_result" in st.session_state:
                                del st.session_state["jana_pusat_result"]
                            if "jana_pusat_no" in st.session_state:
                                del st.session_state["jana_pusat_no"]
                            st.session_state["confirm_batal"] = False
                            st.success(f"✅ Berjaya batal semua janaan untuk PPD {kod_ppd}. Hasil janaan sekarang 0. Sila Jana Keseluruhan semula!")
                            st.balloons()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Gagal batal: {e}")
                            st.session_state["confirm_batal"] = False
                with col_no:
                    if st.button("❌ Tidak", use_container_width=True, key="confirm_no_batal"):
                        st.session_state["confirm_batal"] = False
                        st.rerun()

            st.markdown("---")
            df_pusat_raw = get_pusat_df()
            df_cad_all = get_cadangan_df(kod_ppd=kod_ppd)
            if df_pusat_raw.empty:
                st.warning("Tiada pusat_master")
                st.stop()
            pusat_list = []
            for _, r in df_pusat_raw.iterrows():
                d = r.get("data") if isinstance(r.get("data"), dict) else {}
                if isinstance(d, str):
                    try: d = json.loads(d)
                    except: d = {}
                no_pusat = str(r.get("no_pusat") or r.get("kod_pusat") or d.get("NO_PUSAT") or "").upper().strip()
                if not no_pusat.startswith(kod_ppd.upper()): continue
                nama = r.get("nama_pusat") or d.get("NAMA_PUSAT") or ""
                pusat_list.append({"NO_PUSAT": no_pusat, "NAMA_PUSAT": nama})
            df_pusat_list = pd.DataFrame(pusat_list)
            if df_pusat_list.empty:
                st.warning(f"Tiada pusat untuk PPD {kod_ppd}")
                st.stop()
            pilihan_pusat_hasil = st.selectbox("Pilih Pusat", df_pusat_list["NO_PUSAT"].tolist(), format_func=lambda x: f"{x} - {df_pusat_list[df_pusat_list['NO_PUSAT']==x]['NAMA_PUSAT'].values[0][:30] if not df_pusat_list[df_pusat_list['NO_PUSAT']==x].empty else x}", key="pilih_pusat_hasil")
            show_flash()
            def _bersih(v):
                s = "" if v is None else str(v).strip()
                return "" if s.lower() in ("", "nan", "none", "null", "nat") else s.upper()
            def _kunci(r):
                i = _bersih(r.get("id"))
                return f"ID:{i}" if i else "IC:" + re.sub(r"\D", "", str(r.get("IC_GURU") or r.get("ic_guru") or ""))
            tugas = {}
            if not df_cad_all.empty:
                for _, c in df_cad_all.iterrows():
                    k_c = _kunci(c)
                    p_db = _bersih(c.get("kod_pusat")) or _bersih(c.get("KOD_PUSAT"))
                    if p_db:
                        tugas[k_c] = {"pusat": p_db, "row": c}
            pending_rows = list(st.session_state.get("jana_all_result", []) or [])
            if st.session_state.get("jana_pusat_no"):
                pending_rows += list(st.session_state.get("jana_pusat_result", []) or [])
            for p in pending_rows:
                p_baru = _bersih(p.get("NO_PUSAT_TUGAS"))
                if not p_baru: continue
                k_p = _kunci(p)
                asal_row = pd.Series(p)
                tugas[k_p] = {"pusat": p_baru, "row": asal_row}
            hasil_pusat = []
            for v in tugas.values():
                if v["pusat"] == pilihan_pusat_hasil:
                    hasil_pusat.append(v["row"].copy())
            df_hasil = pd.DataFrame(hasil_pusat)

            # Semakan pelanggaran max 3 untuk pusat yang dipilih
            if not df_hasil.empty:
                sekolah_count_check = {}
                for _, r in df_hasil.iterrows():
                    kod = str(r.get("KOD_SEKOLAH_ASAL") or r.get("kod_sekolah_asal") or "").upper().strip()
                    if kod:
                        sekolah_count_check[kod] = sekolah_count_check.get(kod, 0) + 1
                pelanggaran = [(k, v) for k, v in sekolah_count_check.items() if v > 3]
                if pelanggaran:
                    st.error(f"❌ PELANGGARAN MAX 3 DI {pilihan_pusat_hasil}:")
                    for kod, cnt in pelanggaran:
                        st.error(f"   - {kod}: {cnt} orang (LANGGAR! Max 3 sahaja) - Contoh: SAM NURUL IMAN 10 orang di BA021")
                    st.warning("⚠️ Sila klik Batal Janaan di atas dan Jana Keseluruhan semula untuk betulkan!")
                else:
                    st.success(f"✅ Semakan Max 3 OK di {pilihan_pusat_hasil}: Tiada sekolah lebih 3 orang")

            st.markdown("---")
            if df_hasil.empty:
                st.warning(f"Belum Ada Hasil Janaan Di Pusat Yang Dipilih: {pilihan_pusat_hasil}")
                st.info("Sila pergi ke Jana Keseluruhan untuk jana petugas.")
            else:
                pusat_nama_h = df_pusat_list[df_pusat_list["NO_PUSAT"] == pilihan_pusat_hasil]["NAMA_PUSAT"].values[0] if not df_pusat_list[df_pusat_list["NO_PUSAT"] == pilihan_pusat_hasil].empty else ""
                st.success(f"{pilihan_pusat_hasil} - {pusat_nama_h} | {len(df_hasil)} petugas: 1 Ketua, 1 Timbalan, {len(df_hasil)-2} Pengawas")
                jawatan_groups = {}
                for _, r in df_hasil.iterrows():
                    jaw = str(r.get("JAWATAN_CADANGAN") or r.get("jawatan_cadangan") or r.get("JAWATAN") or "Pengawas Peperiksaan").strip()
                    if jaw not in jawatan_groups:
                        jawatan_groups[jaw] = []
                    jawatan_groups[jaw].append(r)
                order = ["Ketua Pengawas", "Timbalan Ketua Pengawas", "Pengawas Peperiksaan", "Juru Tulis", "Juru Baca", "Ketua Pengawas Hospital", "Pengawas Hospital", "Pengawas Pengiring", "Pengemas Bilik"]
                for jawatan in order:
                    if jawatan not in jawatan_groups: continue
                    guru_list = jawatan_groups[jawatan]
                    if "Ketua Pengawas" in jawatan and "Timbalan" not in jawatan:
                        label = "Ketua Pengawas - 1 orang"
                    elif "Timbalan" in jawatan:
                        label = "Timbalan Ketua Pengawas - 1 orang"
                    else:
                        label = f"Pengawas Peperiksaan - {len(guru_list)} orang"
                    st.subheader(label)
                    rows_j = []
                    for g in guru_list:
                        rows_j.append({"NAMA": g.get("NAMA_GURU", ""), "NO IC": g.get("IC_GURU", ""), "SEKOLAH ASAL": g.get("KOD_SEKOLAH_ASAL", ""), "NAMA SEKOLAH ASAL": str(g.get("NAMA_SEKOLAH_ASAL", ""))[:30], "JANTINA": g.get("JANTINA", "") or g.get("jantina", ""), "NO TELEFON": g.get("TELEFON_GURU", "") or g.get("telefon_guru", "")})
                    df_j = pd.DataFrame(rows_j)
                    st.dataframe(df_j, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("## 📊 Hasil Janaan Keseluruhan Untuk Setiap Sekolah")

            # [FLYOUT] st.tabs diganti sub menu flyout

            if fly_cur == "ringkasan":
                st.markdown("### 📋 Ringkasan Keseluruhan - Semua Pusat")
                ringkas_all = []
                for _, pr in df_pusat_list.iterrows():
                    no_p = pr["NO_PUSAT"]
                    nama_p = pr["NAMA_PUSAT"]
                    guru_di_pusat = [v for v in tugas.values() if v["pusat"] == no_p]
                    kp = sum(1 for v in guru_di_pusat if "Ketua Pengawas" in str(v["row"].get("JAWATAN_CADANGAN") or v["row"].get("JAWATAN") or "") and "Timbalan" not in str(v["row"].get("JAWATAN_CADANGAN") or ""))
                    tkp = sum(1 for v in guru_di_pusat if "Timbalan" in str(v["row"].get("JAWATAN_CADANGAN") or v["row"].get("JAWATAN") or ""))
                    peng = len(guru_di_pusat) - kp - tkp
                    status = "✅ Cukup" if len(guru_di_pusat) > 0 else "❌ Belum Ada"
                    ringkas_all.append({"NO PUSAT": no_p, "NAMA PUSAT": str(nama_p)[:30], "JUMLAH": len(guru_di_pusat), "KP": kp, "TKP": tkp, "PENGAWAS": peng, "STATUS": status})
                df_ringkas_all = pd.DataFrame(ringkas_all)
                if not df_ringkas_all.empty:
                    st.dataframe(df_ringkas_all, use_container_width=True, hide_index=True)
                    st.download_button("📥 Export Ringkasan Semua Pusat", to_excel(df_ringkas_all), file_name=f"ringkasan_semua_pusat_{kod_ppd}.xlsx", use_container_width=True)
                else:
                    st.info("Belum ada hasil janaan keseluruhan")

            if fly_cur == "sekolah":
                st.markdown("### 🏫 Hasil Janaan Mengikut Sekolah Asal")
                st.caption("Setiap sekolah - berapa guru ditempatkan dan ke pusat mana")
                sekolah_groups = {}
                for v in tugas.values():
                    r = v["row"]
                    kod_sek = str(r.get("KOD_SEKOLAH_ASAL") or r.get("kod_sekolah_asal") or "TIADA KOD").upper().strip()
                    nama_sek = str(r.get("NAMA_SEKOLAH_ASAL") or r.get("nama_sekolah_asal") or kod_sek)[:35]
                    key = f"{kod_sek} - {nama_sek}"
                    if key not in sekolah_groups:
                        sekolah_groups[key] = []
                    sekolah_groups[key].append({"row": r, "pusat": v["pusat"]})

                if not sekolah_groups:
                    st.info("Belum ada hasil janaan")
                else:
                    # Summary per sekolah
                    summary_sekolah = []
                    for key, guru_list in sorted(sekolah_groups.items()):
                        kod = key.split(" - ")[0]
                        pusat_list = list(set([g["pusat"] for g in guru_list]))
                        summary_sekolah.append({"KOD SEKOLAH": kod, "NAMA SEKOLAH": key.split(" - ", 1)[1] if " - " in key else key, "BIL GURU": len(guru_list), "PUSAT DITEMPATKAN": ", ".join(sorted(pusat_list))})
                    df_sum_sek = pd.DataFrame(summary_sekolah)
                    st.dataframe(df_sum_sek, use_container_width=True, hide_index=True)
                    st.markdown("---")
                    st.markdown("#### 🔍 Detail Setiap Sekolah")
                    pilih_sekolah = st.selectbox("Pilih Sekolah Untuk Lihat Detail", sorted(sekolah_groups.keys()), key="pilih_sekolah_hasil")
                    if pilih_sekolah:
                        detail = sekolah_groups[pilih_sekolah]
                        st.markdown(f"**{pilih_sekolah} - {len(detail)} guru ditempatkan:**")
                        rows_detail = []
                        for g in detail:
                            r = g["row"]
                            rows_detail.append({"NAMA": r.get("NAMA_GURU", ""), "NO IC": r.get("IC_GURU", ""), "JAWATAN": r.get("JAWATAN_CADANGAN") or r.get("JAWATAN") or "", "PUSAT TUGAS": g["pusat"], "JANTINA": r.get("JANTINA", "") or r.get("jantina", ""), "TELEFON": r.get("TELEFON_GURU", "") or r.get("telefon_guru", "")})
                        df_detail = pd.DataFrame(rows_detail)
                        st.dataframe(df_detail, use_container_width=True, hide_index=True)
                        st.download_button(f"📥 Export {pilih_sekolah}", to_excel(df_detail), file_name=f"hasil_{pilih_sekolah.split(' - ')[0]}_{kod_ppd}.xlsx", use_container_width=True, key=f"export_{pilih_sekolah}")

            if fly_cur == "guru":
                st.markdown("### 👥 Semua Guru Ditempatkan - Keseluruhan")
                all_guru_rows = []
                for v in tugas.values():
                    r = v["row"]
                    all_guru_rows.append({"NAMA": r.get("NAMA_GURU", ""), "NO IC": r.get("IC_GURU", ""), "JAWATAN": r.get("JAWATAN_CADANGAN") or r.get("JAWATAN") or "", "SEKOLAH ASAL": r.get("KOD_SEKOLAH_ASAL", ""), "NAMA SEKOLAH ASAL": str(r.get("NAMA_SEKOLAH_ASAL", ""))[:25], "PUSAT TUGAS": v["pusat"], "JANTINA": r.get("JANTINA", "") or r.get("jantina", ""), "TELEFON": r.get("TELEFON_GURU", "") or r.get("telefon_guru", "")})
                df_all_guru = pd.DataFrame(all_guru_rows)
                if df_all_guru.empty:
                    st.info("Belum ada guru ditempatkan")
                else:
                    st.dataframe(df_all_guru, use_container_width=True, hide_index=True)
                    st.download_button("📥 Export Semua Guru Ditempatkan", to_excel(df_all_guru), file_name=f"semua_guru_ditempatkan_{kod_ppd}.xlsx", use_container_width=True)

        elif menu == "manual":
            st.markdown(f'''
            <div style="background: linear-gradient(135deg, #0d47a1 0%, #0d47a1 100%); padding:20px; border-radius:12px; color:white; margin-bottom:20px;">
                <h2 style="margin:0; color:white;">📌 Penempatan Manual - PPD {kod_ppd}</h2>
                <p style="margin:5px 0 0 0; color:#e3f2fd;">Pilih pusat, klik kolum jawatan untuk pilih petugas secara manual - 1 Pusat = 1 KP + 1 TKP + Pengawas ikut keperluan</p>
            </div>
            ''', unsafe_allow_html=True)

            df_pusat_raw = get_pusat_df()
            df_cad_all = get_cadangan_df(kod_ppd=kod_ppd)

            if df_pusat_raw.empty:
                st.warning("Tiada pusat_master")
                st.stop()
            if df_cad_all.empty:
                st.warning(f"Belum ada cadangan SUP untuk PPD {kod_ppd}")
                st.stop()

            # ✅ INFO: Berapa guru telah dilantik vs belum
            total_cad = len(df_cad_all)
            def is_belum_info(row):
                kp = str(row.get("kod_pusat") or row.get("KOD_PUSAT") or "").strip()
                return kp == "" or kp.lower() in ("none", "null", "nan", "nat")
            belum_info = df_cad_all[df_cad_all.apply(is_belum_info, axis=1)]
            sudah_info = total_cad - len(belum_info)
            if sudah_info > 0:
                st.info(f"📊 Status PPD {kod_ppd}: {total_cad} cadangan | {sudah_info} telah dilantik (tidak akan dipapar di sini) | {len(belum_info)} belum dilantik (akan dipapar)")
            else:
                st.info(f"📊 Status PPD {kod_ppd}: {total_cad} cadangan | Semua belum dilantik")

            # Parse pusat list
            pusat_list_m = []
            for _, r in df_pusat_raw.iterrows():
                d = r.get("data") if isinstance(r.get("data"), dict) else {}
                if isinstance(d, str):
                    try: d = json.loads(d)
                    except: d = {}
                no_pusat = str(r.get("no_pusat") or r.get("kod_pusat") or d.get("NO_PUSAT") or "").upper().strip()
                if not no_pusat.startswith(kod_ppd.upper()): continue
                nama = r.get("nama_pusat") or d.get("NAMA_PUSAT") or ""
                j_calon = r.get("jumlah_calon") or d.get("JUMLAH_CALON") or 0
                try: jc = int(float(str(j_calon) or 0))
                except: jc = 0
                jk = kira_kelas_dari_calon(jc)
                petugas_perlu = kira_petugas_dari_kelas(jk)
                kod_tuan = str(r.get("kod_sekolah_tuan_rumah") or d.get("KOD_SEKOLAH_TUAN_RUMAH") or "").upper().strip()
                pusat_list_m.append({"NO_PUSAT": no_pusat, "NAMA_PUSAT": nama, "CALON": jc, "KELAS": jk, "PERLU": petugas_perlu, "KOD_TUAN": kod_tuan})

            df_pusat_m = pd.DataFrame(pusat_list_m)
            if df_pusat_m.empty:
                st.warning(f"Tiada pusat untuk PPD {kod_ppd}")
                st.stop()

            # Pilih pusat
            st.markdown("### 📍 STEP 1: Pilih Pusat Daerah")
            col_pus1, col_pus2 = st.columns([2, 1])
            with col_pus1:
                pilih_pusat_manual = st.selectbox(
                    "Pilih Pusat",
                    df_pusat_m["NO_PUSAT"].tolist(),
                    format_func=lambda x: f"{x} - {df_pusat_m[df_pusat_m['NO_PUSAT']==x]['NAMA_PUSAT'].values[0][:30] if not df_pusat_m[df_pusat_m['NO_PUSAT']==x].empty else x}",
                    key="pilih_pusat_manual"
                )
            with col_pus2:
                info_pusat = df_pusat_m[df_pusat_m["NO_PUSAT"] == pilih_pusat_manual]
                if not info_pusat.empty:
                    perlu_m = int(info_pusat["PERLU"].values[0])
                    st.markdown(f'''
                    <div style="background:#e3f2fd; border:2px solid #1565c0; border-radius:8px; padding:10px; text-align:center;">
                        <div style="font-size:11px; color:#1565c0;">KEPERLUAN PUSAT</div>
                        <div style="font-size:20px; font-weight:800; color:#0d47a1;">{perlu_m} Petugas</div>
                        <div style="font-size:11px; color:#0d47a1;">1 KP + 1 TKP + {perlu_m-2} Pengawas</div>
                        <div style="font-size:10px; color:#1565c0; margin-top:4px;">{info_pusat['CALON'].values[0]} calon | {info_pusat['KELAS'].values[0]} kelas</div>
                    </div>
                    ''', unsafe_allow_html=True)

            st.markdown("---")

            # Load current placement for this pusat
            def _bersih_m(v):
                s = "" if v is None else str(v).strip()
                return "" if s.lower() in ("", "nan", "none", "null", "nat") else s.upper()

            def _kunci_m(r):
                i = _bersih_m(r.get("id"))
                return f"ID:{i}" if i else "IC:" + re.sub(r"\D", "", str(r.get("IC_GURU") or r.get("ic_guru") or ""))

            # Current tugas untuk pusat ini
            tugas_pusat_ini = {}
            if not df_cad_all.empty:
                for _, c in df_cad_all.iterrows():
                    p_db = _bersih_m(c.get("kod_pusat")) or _bersih_m(c.get("KOD_PUSAT"))
                    if p_db == pilih_pusat_manual:
                        tugas_pusat_ini[_kunci_m(c)] = c

            # Kira sekolah count untuk max 3 check
            sekolah_count_manual = {}
            for _, c in df_cad_all.iterrows():
                p_db = _bersih_m(c.get("kod_pusat")) or _bersih_m(c.get("KOD_PUSAT"))
                if p_db == pilih_pusat_manual:
                    kod = str(c.get("KOD_SEKOLAH_ASAL") or c.get("kod_sekolah_asal") or "").upper().strip()
                    if kod:
                        sekolah_count_manual[kod] = sekolah_count_manual.get(kod, 0) + 1

            # Paparan semasa
            st.markdown(f"### 🏫 Pusat {pilih_pusat_manual} - Penempatan Semasa")
            col_curr1, col_curr2, col_curr3, col_curr4, col_curr5, col_curr6 = st.columns(6)
            # FIX: 5 jawatan - Penyelia dari SUP, Selenggara dari PPD
            kp_curr_dict = {}
            tkp_curr_dict = {}
            penyelia_curr_dict = {}
            selenggara_curr_dict = {}
            peng_curr_dict = {}
            for k, c in tugas_pusat_ini.items():
                jaw = str(c.get("JAWATAN_CADANGAN") or c.get("jawatan_cadangan") or c.get("JAWATAN") or "").upper()
                if "KETUA PENGAWAS" in jaw and "TIMBALAN" not in jaw:
                    kp_curr_dict[k] = c
                elif "TIMBALAN" in jaw:
                    tkp_curr_dict[k] = c
                elif "PENYELIA KAWASAN" in jaw or ("PENYELIA" in jaw and "KAWASAN" in jaw):
                    penyelia_curr_dict[k] = c
                elif "SELENGGARA" in jaw or "BILIK KEBAL" in jaw:
                    selenggara_curr_dict[k] = c
                else:
                    peng_curr_dict[k] = c
            kp_curr = list(kp_curr_dict.values())
            tkp_curr = list(tkp_curr_dict.values())
            peng_curr = list(peng_curr_dict.values())

            with col_curr1:
                st.metric("Ketua Pengawas", f"{len(kp_curr)}/1", delta="OK" if len(kp_curr)==1 else "Perlu 1", delta_color="normal" if len(kp_curr)==1 else "inverse")
            with col_curr2:
                st.metric("Timbalan KP", f"{len(tkp_curr)}/1", delta="OK" if len(tkp_curr)==1 else "Perlu 1", delta_color="normal" if len(tkp_curr)==1 else "inverse")
            with col_curr3:
                st.metric("Penyelia Kawasan", f"{len(penyelia_curr_dict)}/1", delta="OK" if len(penyelia_curr_dict)>=1 else "Perlu 1", delta_color="normal" if len(penyelia_curr_dict)>=1 else "inverse")
            with col_curr4:
                st.metric("Selenggara BK", f"{len(selenggara_curr_dict)}/1", delta="OK" if len(selenggara_curr_dict)>=1 else "Perlu 1", delta_color="normal" if len(selenggara_curr_dict)>=1 else "inverse")
            with col_curr5:
                perlu_p = int(info_pusat["PERLU"].values[0]) if not info_pusat.empty else 0
                st.metric("Pengawas", f"{len(peng_curr)}/{max(perlu_p-4,0)}", delta=f"Perlu {max(perlu_p-4,0)}")
            with col_curr6:
                st.metric("Jumlah", f"{len(tugas_pusat_ini)}/{perlu_p}", delta="Cukup" if len(tugas_pusat_ini)>=perlu_p else f"Kurang {perlu_p-len(tugas_pusat_ini)}")

            # Check pelanggaran max 3
            pelanggaran_m = [(k, v) for k, v in sekolah_count_manual.items() if v > 3]
            if pelanggaran_m:
                st.error(f"❌ Pelanggaran Max 3 di {pilih_pusat_manual}:")
                for kod, cnt in pelanggaran_m:
                    st.error(f"  - {kod}: {cnt} orang (Max 3 sahaja!)")
            else:
                st.success(f"✅ Max 3 OK di {pilih_pusat_manual} - Tiada sekolah lebih 3 orang")

            st.markdown("---")

            # 3 Kolum Penempatan Manual
            st.markdown("### 📌 STEP 2: Penempatan Manual - Klik Kolum Untuk Pilih")

            col_kp, col_tkp, col_peng, col_jt, col_jb, col_pb = st.columns(6)

            # ===== KOLUM KETUA PENGAWAS =====
            with col_kp:
                st.markdown('<div style="background:#bbdefb; border:2px solid #0d47a1; border-radius:8px; padding:8px; text-align:center; margin-bottom:6px;"><div style="font-size:20px;">👑</div><div style="font-weight:700; color:#0d47a1; font-size:12px;">KETUA PENGAWAS</div></div>', unsafe_allow_html=True)

                if kp_curr:
                    st.markdown("**Semasa:**")
                    for c in kp_curr:
                        st.markdown(f'''
                        <div style="background:#bbdefb; border:1px solid #0d47a1; border-radius:6px; padding:8px; margin:4px 0;">
                            <div style="font-weight:700; font-size:12px;">{c.get("NAMA_GURU", "")}</div>
                            <div style="font-size:10px;">{c.get("KOD_SEKOLAH_ASAL", "")} | {c.get("IC_GURU", "")}</div>
                        </div>
                        ''', unsafe_allow_html=True)
                    if st.button("🗑️ Buang KP", key="buang_kp", use_container_width=True):
                        for k in list(kp_curr_dict.keys()):
                            try:
                                c = tugas_pusat_ini.get(k)
                                if c is not None:
                                    supa.table("cadangan_sup").update({"kod_pusat": None, "status": "DICADANGKAN"}).eq("id", c.get("id")).execute()
                            except Exception as e:
                                st.error(str(e))
                        st.success("KP dibuang")
                        st.rerun()
                else:
                    st.info("Belum ada KP")

                st.markdown("**Pilih KP:**")
                # ✅ FIX: Hanya guru BELUM dilantik - keluarkan yang sudah ada kod_pusat atau status LULUS/SURAT
                kod_tuan_m = info_pusat["KOD_TUAN"].values[0] if not info_pusat.empty else ""
                df_kp_calon_all = df_cad_all.copy()
                def is_belum_kp(row):
                    kp = str(row.get("kod_pusat") or row.get("KOD_PUSAT") or "").strip()
                    stt = str(row.get("status") or row.get("STATUS") or "").upper()
                    ns = str(row.get("no_surat") or "").strip()
                    # Sudah dilantik jika ada kod_pusat ATAU status LULUS/DILANTIK ATAU ada no_surat sah
                    if kp != "" and kp.lower() not in ("none","null","nan","nat","-"):
                        return False
                    if "LULUS" in stt or "DILANTIK" in stt or "SURAT" in stt:
                        if ns and ns.lower() not in ("none","null","nan",""):
                            return False
                    return True
                df_kp_calon = df_kp_calon_all[df_kp_calon_all.apply(is_belum_kp, axis=1)].copy()
                # Hanya KP (bukan Timbalan)
                df_kp_calon = df_kp_calon[df_kp_calon["JAWATAN_CADANGAN"].astype(str).str.contains("Ketua Pengawas", case=False, na=False) & ~df_kp_calon["JAWATAN_CADANGAN"].astype(str).str.contains("Timbalan", case=False, na=False)]
                # Elak sekolah sendiri
                if kod_tuan_m:
                    df_kp_calon = df_kp_calon[~df_kp_calon["KOD_SEKOLAH_ASAL"].astype(str).str.upper().str.strip().eq(kod_tuan_m)]
                # Elak yang sudah ada pusat lain? Biar boleh pilih, tapi warning
                # Check max 3
                def check_kp_max3(row):
                    kod = str(row.get("KOD_SEKOLAH_ASAL", "")).upper().strip()
                    return sekolah_count_manual.get(kod, 0) < 3 if kod else True
                df_kp_calon["MAX3_OK"] = df_kp_calon.apply(check_kp_max3, axis=1)

                # Show only yang layak max 3
                df_kp_layak = df_kp_calon[df_kp_calon["MAX3_OK"] == True]

                if df_kp_layak.empty:
                    # Check if empty because all already appointed
                    if len(df_kp_calon_all) > 0 and len(df_kp_calon) == 0:
                        st.warning("⚠️ Semua KP telah dilantik")
                    else:
                        st.warning("Tiada KP layak")
                    if not df_kp_calon.empty:
                        st.dataframe(df_kp_calon[["NAMA_GURU", "KOD_SEKOLAH_ASAL", "IC_GURU"]].head(10), use_container_width=True, hide_index=True)
                else:
                    st.caption(f"{len(df_kp_layak)} calon KP belum dilantik & layak (max 3 OK) - tidak akan muncul lagi jika telah dilantik")
                    pilih_kp = st.selectbox(
                        "Klik untuk pilih Ketua Pengawas",
                        df_kp_layak["id"].tolist() if "id" in df_kp_layak.columns else [],
                        format_func=lambda x: f"{df_kp_layak[df_kp_layak['id']==x]['NAMA_GURU'].values[0]} - {df_kp_layak[df_kp_layak['id']==x]['KOD_SEKOLAH_ASAL'].values[0]} | {df_kp_layak[df_kp_layak['id']==x]['NAMA_SEKOLAH_ASAL'].values[0][:20]}" if not df_kp_layak[df_kp_layak['id']==x].empty else str(x),
                        key="pilih_kp_manual"
                    )
                    if st.button("✅ Lantik Sebagai KP", type="primary", use_container_width=True, key="lantik_kp"):
                        if pilih_kp:
                            try:
                                # Jika sudah ada KP, buang dulu
                                for k in list(kp_curr_dict.keys()):
                                    c = tugas_pusat_ini.get(k)
                                    if c is not None:
                                        supa.table("cadangan_sup").update({"kod_pusat": None}).eq("id", c.get("id")).execute()
                                supa.table("cadangan_sup").update({"kod_pusat": pilih_pusat_manual, "status": "DILANTIK PPD"}).eq("id", pilih_kp).execute()
                                st.success(f"KP dilantik ke {pilih_pusat_manual}")
                                st.balloons()
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))

            # ===== KOLUM TIMBALAN KETUA PENGAWAS =====
            with col_tkp:
                st.markdown('<div style="background:#e3f2fd; border:2px solid #0d47a1; border-radius:8px; padding:8px; text-align:center; margin-bottom:6px;"><div style="font-size:20px;">🎖️</div><div style="font-weight:700; color:#0d47a1; font-size:12px;">TIMBALAN KP</div></div>', unsafe_allow_html=True)

                if tkp_curr:
                    st.markdown("**Semasa:**")
                    for c in tkp_curr:
                        st.markdown(f'''
                        <div style="background:#e3f2fd; border:1px solid #0d47a1; border-radius:6px; padding:8px; margin:4px 0;">
                            <div style="font-weight:700; font-size:12px;">{c.get("NAMA_GURU", "")}</div>
                            <div style="font-size:10px;">{c.get("KOD_SEKOLAH_ASAL", "")} | {c.get("IC_GURU", "")}</div>
                        </div>
                        ''', unsafe_allow_html=True)
                    if st.button("🗑️ Buang TKP", key="buang_tkp", use_container_width=True):
                        for k in list(tkp_curr_dict.keys()):
                            try:
                                c = tugas_pusat_ini.get(k)
                                if c is not None:
                                    supa.table("cadangan_sup").update({"kod_pusat": None, "status": "DICADANGKAN"}).eq("id", c.get("id")).execute()
                            except Exception as e:
                                st.error(str(e))
                        st.success("TKP dibuang")
                        st.rerun()
                else:
                    st.info("Belum ada TKP")

                st.markdown("**Pilih TKP:**")
                # ✅ FIX: Hanya guru BELUM dilantik - keluarkan yang sudah dilantik
                df_tkp_calon_all = df_cad_all.copy()
                def is_belum_tkp(row):
                    kp = str(row.get("kod_pusat") or row.get("KOD_PUSAT") or "").strip()
                    stt = str(row.get("status") or row.get("STATUS") or "").upper()
                    ns = str(row.get("no_surat") or "").strip()
                    if kp != "" and kp.lower() not in ("none","null","nan","nat","-"):
                        return False
                    if "LULUS" in stt or "DILANTIK" in stt or "SURAT" in stt:
                        if ns and ns.lower() not in ("none","null","nan",""):
                            return False
                    return True
                df_tkp_calon = df_tkp_calon_all[df_tkp_calon_all.apply(is_belum_tkp, axis=1)].copy()
                df_tkp_calon = df_tkp_calon[df_tkp_calon["JAWATAN_CADANGAN"].astype(str).str.contains("Timbalan", case=False, na=False)]
                if kod_tuan_m:
                    df_tkp_calon = df_tkp_calon[~df_tkp_calon["KOD_SEKOLAH_ASAL"].astype(str).str.upper().str.strip().eq(kod_tuan_m)]
                def check_tkp_max3(row):
                    kod = str(row.get("KOD_SEKOLAH_ASAL", "")).upper().strip()
                    return sekolah_count_manual.get(kod, 0) < 3 if kod else True
                df_tkp_calon["MAX3_OK"] = df_tkp_calon.apply(check_tkp_max3, axis=1)
                df_tkp_layak = df_tkp_calon[df_tkp_calon["MAX3_OK"] == True]

                if df_tkp_layak.empty:
                    st.warning("Tiada TKP layak")
                else:
                    st.caption(f"{len(df_tkp_layak)} calon TKP layak - keseluruhan daerah {kod_ppd}")
                    pilih_tkp = st.selectbox(
                        "Klik untuk pilih Timbalan KP",
                        df_tkp_layak["id"].tolist() if "id" in df_tkp_layak.columns else [],
                        format_func=lambda x: f"{df_tkp_layak[df_tkp_layak['id']==x]['NAMA_GURU'].values[0]} - {df_tkp_layak[df_tkp_layak['id']==x]['KOD_SEKOLAH_ASAL'].values[0]}" if not df_tkp_layak[df_tkp_layak['id']==x].empty else str(x),
                        key="pilih_tkp_manual"
                    )
                    if st.button("✅ Lantik Sebagai TKP", type="primary", use_container_width=True, key="lantik_tkp"):
                        if pilih_tkp:
                            try:
                                for k in list(tkp_curr_dict.keys()):
                                    c = tugas_pusat_ini.get(k)
                                    if c is not None:
                                        supa.table("cadangan_sup").update({"kod_pusat": None}).eq("id", c.get("id")).execute()
                                supa.table("cadangan_sup").update({"kod_pusat": pilih_pusat_manual, "status": "DILANTIK PPD"}).eq("id", pilih_tkp).execute()
                                st.success(f"TKP dilantik ke {pilih_pusat_manual}")
                                st.balloons()
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))

            # ===== KOLUM PENGAWAS =====
            with col_peng:
                perlu_p = int(info_pusat["PERLU"].values[0]) if not info_pusat.empty else 10
                perlu_pengawas = max(0, perlu_p - 1 - 1)
                st.markdown(f'<div style="background:#ffffff; border:2px solid #0d47a1; border-radius:8px; padding:8px; text-align:center; margin-bottom:6px;"><div style="font-size:20px;">👨‍🏫</div><div style="font-weight:700; color:#0d47a1; font-size:12px;">PENGAWAS ({perlu_pengawas})</div></div>', unsafe_allow_html=True)

                if peng_curr:
                    st.markdown(f"**Semasa: {len(peng_curr)}/{perlu_pengawas}**")
                    for c in peng_curr[:5]:
                        st.markdown(f'''
                        <div style="background:#ffffff; border:1px solid #0d47a1; border-radius:6px; padding:6px; margin:3px 0; font-size:11px;">
                            <b>{c.get("NAMA_GURU", "")[:20]}</b> - {c.get("KOD_SEKOLAH_ASAL", "")}
                        </div>
                        ''', unsafe_allow_html=True)
                    if len(peng_curr) > 5:
                        st.caption(f"... dan {len(peng_curr)-5} lagi")
                    if st.button("🗑️ Buang Semua Pengawas", key="buang_peng", use_container_width=True):
                        for k in list(peng_curr_dict.keys()):
                            try:
                                c = tugas_pusat_ini.get(k)
                                if c is not None:
                                    supa.table("cadangan_sup").update({"kod_pusat": None, "status": "DICADANGKAN"}).eq("id", c.get("id")).execute()
                            except Exception as e:
                                st.error(str(e))
                        st.success("Pengawas dibuang")
                        st.rerun()
                else:
                    st.info(f"Belum ada Pengawas ({perlu_pengawas} perlu)")

                st.markdown("**Pilih Pengawas Baru:**")
                # FIX: Filter hanya belum dilantik untuk Pengawas juga
                def is_belum_peng_manual(r):
                    kp = str(r.get("kod_pusat") or r.get("KOD_PUSAT") or "").strip()
                    stt = str(r.get("status") or r.get("STATUS") or "").upper()
                    ns = str(r.get("no_surat") or "").strip()
                    if kp != "" and kp.lower() not in ("none","null","nan","nat","-"):
                        return False
                    if "LULUS" in stt and ns and ns.lower() not in ("none","null","nan",""):
                        return False
                    return True
                # Apply to df_cad_all for Pengawas list
                try:
                    df_cad_all_filtered_peng = df_cad_all[df_cad_all.apply(is_belum_peng_manual, axis=1)].copy()
                except:
                    df_cad_all_filtered_peng = df_cad_all.copy()
                # ✅ QUERY BARU: Hanya guru BELUM dilantik
                df_peng_calon_all = df_cad_all.copy()
                def is_belum_peng(row):
                    kp = str(row.get("kod_pusat") or row.get("KOD_PUSAT") or "").strip()
                    return kp == "" or kp.lower() in ("none", "null", "nan", "nat")
                df_peng_calon = df_peng_calon_all[df_peng_calon_all.apply(is_belum_peng, axis=1)].copy()
                # Pengawas sahaja (bukan KP/TKP)
                df_peng_calon = df_peng_calon[~df_peng_calon["JAWATAN_CADANGAN"].astype(str).str.contains("Ketua Pengawas|Timbalan|Penyelia|Selenggara|Bilik Kebal", case=False, na=False, regex=True)]
                if kod_tuan_m:
                    df_peng_calon = df_peng_calon[~df_peng_calon["KOD_SEKOLAH_ASAL"].astype(str).str.upper().str.strip().eq(kod_tuan_m)]
                def check_peng_max3(row):
                    kod = str(row.get("KOD_SEKOLAH_ASAL", "")).upper().strip()
                    return sekolah_count_manual.get(kod, 0) < 3 if kod else True
                df_peng_calon["MAX3_OK"] = df_peng_calon.apply(check_peng_max3, axis=1)
                df_peng_layak = df_peng_calon[df_peng_calon["MAX3_OK"] == True]

                # Yang belum ditempatkan - df sudah filter belum dilantik, jadi semua belum
                df_peng_belum = df_peng_layak.copy()

                st.caption(f"{len(df_peng_belum)} calon | Perlu {perlu_pengawas}")

                if df_peng_belum.empty:
                    st.warning("Tiada calon Pengawas layak yang belum ditempatkan")
                    st.dataframe(df_peng_layak[["NAMA_GURU", "KOD_SEKOLAH_ASAL", "JAWATAN_CADANGAN"]].head(10), use_container_width=True, hide_index=True)
                else:
                    # Multi select
                    pilih_peng_list = st.multiselect(
                        f"Pilih Pengawas (perlu {perlu_pengawas}, max 3 per sekolah)",
                        df_peng_belum["id"].tolist() if "id" in df_peng_belum.columns else [],
                        format_func=lambda x: f"{df_peng_belum[df_peng_belum['id']==x]['NAMA_GURU'].values[0]} - {df_peng_belum[df_peng_belum['id']==x]['KOD_SEKOLAH_ASAL'].values[0]} - {df_peng_belum[df_peng_belum['id']==x]['JAWATAN_CADANGAN'].values[0]}" if not df_peng_belum[df_peng_belum['id']==x].empty else str(x),
                        key="pilih_peng_manual"
                    )
                    # Check kalau pilih lebih dari perlu atau langgar max 3
                    if pilih_peng_list:
                        # Kira sekolah count kalau tambah yang dipilih
                        temp_count = sekolah_count_manual.copy()
                        valid = True
                        for pid in pilih_peng_list:
                            row = df_peng_belum[df_peng_belum["id"]==pid]
                            if not row.empty:
                                kod = str(row["KOD_SEKOLAH_ASAL"].values[0]).upper().strip()
                                if temp_count.get(kod, 0) >= 3:
                                    st.error(f"❌ {kod} sudah 3 orang di {pilih_pusat_manual} - tidak boleh tambah lagi!")
                                    valid = False
                                temp_count[kod] = temp_count.get(kod, 0) + 1
                        if len(pilih_peng_list) > perlu_pengawas:
                            st.warning(f"⚠️ Anda pilih {len(pilih_peng_list)} tapi pusat perlu {perlu_pengawas} sahaja")

                        if st.button(f"✅ Lantik {len(pilih_peng_list)} Sebagai Pengawas", type="primary", use_container_width=True, key="lantik_peng", disabled=not valid):
                            try:
                                berjaya = 0
                                for pid in pilih_peng_list:
                                    supa.table("cadangan_sup").update({"kod_pusat": pilih_pusat_manual, "status": "DILANTIK PPD"}).eq("id", pid).execute()
                                    berjaya += 1
                                st.success(f"✅ {berjaya} Pengawas dilantik ke {pilih_pusat_manual}")
                                st.balloons()
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))


            # ===== KOLUM JURU TULIS (Pengawas Khas - Tak Termasuk Kiraan Biasa) =====
            with col_jt:
                st.markdown('<div style="background:#e3f2fd; border:2px solid #0d47a1; border-radius:8px; padding:8px; text-align:center; margin-bottom:6px;"><div style="font-size:20px;">✍️</div><div style="font-weight:700; color:#0d47a1; font-size:12px;">JURU TULIS</div></div>', unsafe_allow_html=True)
                jt_curr = [c for k,c in tugas_pusat_ini.items() if "JURU TULIS" in str(c.get("JAWATAN_CADANGAN") or "").upper()]
                if jt_curr:
                    st.markdown(f"**Semasa: {len(jt_curr)} (Khas)**")
                    for c in jt_curr[:3]:
                        st.markdown(f'<div style="background:#e3f2fd; border-radius:6px; padding:6px; margin:3px 0; font-size:11px;"><b>{c.get("NAMA_GURU","")[:18]}</b> - {c.get("KOD_SEKOLAH_ASAL","")}</div>', unsafe_allow_html=True)
                    if st.button("🗑️ Buang Juru Tulis", key="buang_jt", use_container_width=True):
                        for c in jt_curr:
                            supa.table("cadangan_sup").update({"kod_pusat": None, "status": "DICADANGKAN"}).eq("id", c.get("id")).execute()
                        st.success("Juru Tulis dibuang"); st.rerun()
                else:
                    st.info("Belum ada Juru Tulis")
                st.markdown("**Pilih Juru Tulis:**")
                try:
                    df_jt_calon_all = df_cad_all[df_cad_all.apply(is_belum_peng_manual, axis=1)].copy()
                except:
                    try:
                        df_jt_calon_all = df_cad_all[df_cad_all.apply(is_belum_peng, axis=1)].copy()
                    except:
                        df_jt_calon_all = df_cad_all.copy()
                df_jt_calon = df_jt_calon_all[df_jt_calon_all["JAWATAN_CADANGAN"].astype(str).str.contains("Juru Tulis", case=False, na=False)]
                if kod_tuan_m:
                    df_jt_calon = df_jt_calon[~df_jt_calon["KOD_SEKOLAH_ASAL"].astype(str).str.upper().str.strip().eq(kod_tuan_m)]
                df_jt_calon["MAX3_OK"] = df_jt_calon.apply(lambda r: sekolah_count_manual.get(str(r.get("KOD_SEKOLAH_ASAL","")).upper().strip(),0) < 3, axis=1)
                df_jt_layak = df_jt_calon[df_jt_calon["MAX3_OK"]==True]
                st.caption(f"{len(df_jt_layak)} calon")
                if not df_jt_layak.empty:
                    pilih_jt = st.multiselect("Pilih Juru Tulis", df_jt_layak["id"].tolist(), format_func=lambda x: f"{df_jt_layak[df_jt_layak['id']==x]['NAMA_GURU'].values[0]} - {df_jt_layak[df_jt_layak['id']==x]['KOD_SEKOLAH_ASAL'].values[0]}" if not df_jt_layak[df_jt_layak['id']==x].empty else str(x), key="pilih_jt_manual")
                    if pilih_jt and st.button(f"✅ Lantik {len(pilih_jt)} Juru Tulis", type="primary", use_container_width=True, key="lantik_jt"):
                        for pid in pilih_jt:
                            supa.table("cadangan_sup").update({"kod_pusat": pilih_pusat_manual, "status": "DILANTIK PPD"}).eq("id", pid).execute()
                        st.success(f"✅ {len(pilih_jt)} Juru Tulis dilantik (Khas)"); st.balloons(); st.rerun()

            # ===== KOLUM JURU BACA (Pengawas Khas) =====
            with col_jb:
                st.markdown('<div style="background:#e3f2fd; border:2px solid #0d47a1; border-radius:8px; padding:8px; text-align:center; margin-bottom:6px;"><div style="font-size:20px;">📖</div><div style="font-weight:700; color:#0d47a1; font-size:12px;">JURU BACA</div></div>', unsafe_allow_html=True)
                jb_curr = [c for k,c in tugas_pusat_ini.items() if "JURU BACA" in str(c.get("JAWATAN_CADANGAN") or "").upper()]
                if jb_curr:
                    st.markdown(f"**Semasa: {len(jb_curr)} (Khas)**")
                    for c in jb_curr[:3]:
                        st.markdown(f'<div style="background:#e3f2fd; border-radius:6px; padding:6px; margin:3px 0; font-size:11px;"><b>{c.get("NAMA_GURU","")[:18]}</b> - {c.get("KOD_SEKOLAH_ASAL","")}</div>', unsafe_allow_html=True)
                    if st.button("🗑️ Buang Juru Baca", key="buang_jb", use_container_width=True):
                        for c in jb_curr:
                            supa.table("cadangan_sup").update({"kod_pusat": None, "status": "DICADANGKAN"}).eq("id", c.get("id")).execute()
                        st.success("Juru Baca dibuang"); st.rerun()
                else:
                    st.info("Belum ada Juru Baca")
                st.markdown("**Pilih Juru Baca:**")
                try:
                    df_jb_calon_all = df_cad_all[df_cad_all.apply(is_belum_peng_manual, axis=1)].copy()
                except:
                    try:
                        df_jb_calon_all = df_cad_all[df_cad_all.apply(is_belum_peng, axis=1)].copy()
                    except:
                        df_jb_calon_all = df_cad_all.copy()
                df_jb_calon = df_jb_calon_all[df_jb_calon_all["JAWATAN_CADANGAN"].astype(str).str.contains("Juru Baca", case=False, na=False)]
                if kod_tuan_m:
                    df_jb_calon = df_jb_calon[~df_jb_calon["KOD_SEKOLAH_ASAL"].astype(str).str.upper().str.strip().eq(kod_tuan_m)]
                df_jb_calon["MAX3_OK"] = df_jb_calon.apply(lambda r: sekolah_count_manual.get(str(r.get("KOD_SEKOLAH_ASAL","")).upper().strip(),0) < 3, axis=1)
                df_jb_layak = df_jb_calon[df_jb_calon["MAX3_OK"]==True]
                st.caption(f"{len(df_jb_layak)} calon")
                if not df_jb_layak.empty:
                    pilih_jb = st.multiselect("Pilih Juru Baca", df_jb_layak["id"].tolist(), format_func=lambda x: f"{df_jb_layak[df_jb_layak['id']==x]['NAMA_GURU'].values[0]} - {df_jb_layak[df_jb_layak['id']==x]['KOD_SEKOLAH_ASAL'].values[0]}" if not df_jb_layak[df_jb_layak['id']==x].empty else str(x), key="pilih_jb_manual")
                    if pilih_jb and st.button(f"✅ Lantik {len(pilih_jb)} Juru Baca", type="primary", use_container_width=True, key="lantik_jb"):
                        for pid in pilih_jb:
                            supa.table("cadangan_sup").update({"kod_pusat": pilih_pusat_manual, "status": "DILANTIK PPD"}).eq("id", pid).execute()
                        st.success(f"✅ {len(pilih_jb)} Juru Baca dilantik (Khas)"); st.balloons(); st.rerun()

            # ===== KOLUM PENGEMAS BILIK (Pengawas Khas) =====
            with col_pb:
                st.markdown('<div style="background:#e3f2fd; border:2px solid #0d47a1; border-radius:8px; padding:8px; text-align:center; margin-bottom:6px;"><div style="font-size:20px;">🧹</div><div style="font-weight:700; color:#0d47a1; font-size:12px;">PENGEMAS BILIK</div></div>', unsafe_allow_html=True)
                pb_curr = [c for k,c in tugas_pusat_ini.items() if "PENGEMAS BILIK" in str(c.get("JAWATAN_CADANGAN") or "").upper()]
                if pb_curr:
                    st.markdown(f"**Semasa: {len(pb_curr)} (Khas)**")
                    for c in pb_curr[:3]:
                        st.markdown(f'<div style="background:#e3f2fd; border-radius:6px; padding:6px; margin:3px 0; font-size:11px;"><b>{c.get("NAMA_GURU","")[:18]}</b> - {c.get("KOD_SEKOLAH_ASAL","")}</div>', unsafe_allow_html=True)
                    if st.button("🗑️ Buang Pengemas Bilik", key="buang_pb", use_container_width=True):
                        for c in pb_curr:
                            supa.table("cadangan_sup").update({"kod_pusat": None, "status": "DICADANGKAN"}).eq("id", c.get("id")).execute()
                        st.success("Pengemas Bilik dibuang"); st.rerun()
                else:
                    st.info("Belum ada Pengemas Bilik")
                st.markdown("**Pilih Pengemas Bilik:**")
                try:
                    df_pb_calon_all = df_cad_all[df_cad_all.apply(is_belum_peng_manual, axis=1)].copy()
                except:
                    try:
                        df_pb_calon_all = df_cad_all[df_cad_all.apply(is_belum_peng, axis=1)].copy()
                    except:
                        df_pb_calon_all = df_cad_all.copy()
                df_pb_calon = df_pb_calon_all[df_pb_calon_all["JAWATAN_CADANGAN"].astype(str).str.contains("Pengemas Bilik", case=False, na=False)]
                if kod_tuan_m:
                    df_pb_calon = df_pb_calon[~df_pb_calon["KOD_SEKOLAH_ASAL"].astype(str).str.upper().str.strip().eq(kod_tuan_m)]
                df_pb_calon["MAX3_OK"] = df_pb_calon.apply(lambda r: sekolah_count_manual.get(str(r.get("KOD_SEKOLAH_ASAL","")).upper().strip(),0) < 3, axis=1)
                df_pb_layak = df_pb_calon[df_pb_calon["MAX3_OK"]==True]
                st.caption(f"{len(df_pb_layak)} calon")
                if not df_pb_layak.empty:
                    pilih_pb = st.multiselect("Pilih Pengemas Bilik", df_pb_layak["id"].tolist(), format_func=lambda x: f"{df_pb_layak[df_pb_layak['id']==x]['NAMA_GURU'].values[0]} - {df_pb_layak[df_pb_layak['id']==x]['KOD_SEKOLAH_ASAL'].values[0]}" if not df_pb_layak[df_pb_layak['id']==x].empty else str(x), key="pilih_pb_manual")
                    if pilih_pb and st.button(f"✅ Lantik {len(pilih_pb)} Pengemas Bilik", type="primary", use_container_width=True, key="lantik_pb"):
                        for pid in pilih_pb:
                            supa.table("cadangan_sup").update({"kod_pusat": pilih_pusat_manual, "status": "DILANTIK PPD"}).eq("id", pid).execute()
                        st.success(f"✅ {len(pilih_pb)} Pengemas Bilik dilantik (Khas)"); st.balloons(); st.rerun()

            # ===== END 3 KOLUM TAMBAHAN =====


            st.markdown("---")
            st.markdown("### 📊 Ringkasan Penempatan Manual - Kumulatif (Tidak Hilang Bila Pilih Sekolah Kedua)")
            st.info("💡 Ringkasan ini kumulatif - bila PPD lantik Sekolah Kedua, lantikan Pertama masih kekal di bawah. Column ikut jawatan: KP, TKP, Pengawas.")

            # ===== RINGKASAN KUMULATIF - SEMUA PUSAT YANG TELAH DILANTIK MANUAL =====
            try:
                # Ambil semua yang sudah ada kod_pusat dan status DILANTIK PPD untuk PPD ini
                res_all_lantik = supa.table("cadangan_sup").select("*").eq("kod_ppd", kod_ppd).not_.is_("kod_pusat", "null").limit(5000).execute()
                df_all_lantik = __import__("pandas").DataFrame(res_all_lantik.data or [])
                # Filter hanya yang status DILANTIK / LULUS
                if not df_all_lantik.empty:
                    df_all_lantik = df_all_lantik[df_all_lantik.apply(lambda r: str(r.get("status") or "").upper() not in ("", "DICADANGKAN", "HANTAR KE PPD"), axis=1)]
            except:
                df_all_lantik = __import__("pandas").DataFrame()

            # Tambah juga yang baru di session ini (kalau belum save DB pun, tunjuk)
            # Gabungkan
            if not df_all_lantik.empty:
                # Build rows dengan column ikut jawatan
                all_rows_kum = []
                for _, c in df_all_lantik.iterrows():
                    jaw = str(c.get("jawatan_cadangan") or c.get("JAWATAN_CADANGAN") or "")
                    # Tentukan column jawatan
                    if "Ketua Pengawas" in jaw and "Timbalan" not in jaw:
                        jaw_col = "KETUA PENGAWAS"
                    elif "Timbalan" in jaw:
                        jaw_col = "TIMBALAN KP"
                    elif "Pengawas" in jaw:
                        jaw_col = "PENGAWAS PEPERIKSAAN"
                    elif "Penyelia" in jaw:
                        jaw_col = "PENYELIA KAWASAN"
                    else:
                        jaw_col = jaw.upper()

                    all_rows_kum.append({
                        "BIL": len(all_rows_kum)+1,
                        "NAMA GURU": c.get("nama_guru","") or c.get("NAMA_GURU",""),
                        "IC": c.get("ic_guru","") or c.get("IC_GURU",""),
                        "JAWATAN": jaw,
                        "KOLUM JAWATAN": jaw_col,
                        "SEKOLAH ASAL": c.get("kod_sekolah_asal","") or c.get("KOD_SEKOLAH_ASAL",""),
                        "NAMA SEKOLAH ASAL": str(c.get("nama_sekolah_asal","") or c.get("NAMA_SEKOLAH_ASAL",""))[:25],
                        "PUSAT TUGAS": c.get("kod_pusat","") or c.get("KOD_PUSAT",""),
                        "STATUS": c.get("status","")
                    })

                df_summary_kum = __import__("pandas").DataFrame(all_rows_kum)

                if df_summary_kum.empty:
                    st.info("Belum ada penempatan manual - Sila lantik di atas")
                else:
                    # Papar ikut tab jawatan
                    tab_kp, tab_tkp, tab_peng, tab_semua = st.tabs(["👑 Ketua Pengawas", "🎖️ Timbalan KP", "👨‍🏫 Pengawas", "📋 Semua (Kumulatif)"])

                    with tab_kp:
                        df_kp = df_summary_kum[df_summary_kum["KOLUM JAWATAN"]=="KETUA PENGAWAS"].copy()
                        st.markdown(f"**{len(df_kp)} Ketua Pengawas telah dilantik (kumulatif, tidak hilang bila pilih sekolah kedua):**")
                        if df_kp.empty:
                            st.info("Belum ada Ketua Pengawas dilantik")
                        else:
                            st.dataframe(df_kp[["BIL","NAMA GURU","IC","SEKOLAH ASAL","NAMA SEKOLAH ASAL","PUSAT TUGAS"]], use_container_width=True, hide_index=True)

                    with tab_tkp:
                        df_tkp = df_summary_kum[df_summary_kum["KOLUM JAWATAN"]=="TIMBALAN KP"].copy()
                        st.markdown(f"**{len(df_tkp)} Timbalan KP telah dilantik (kumulatif):**")
                        if df_tkp.empty:
                            st.info("Belum ada Timbalan KP")
                        else:
                            st.dataframe(df_tkp[["BIL","NAMA GURU","IC","SEKOLAH ASAL","NAMA SEKOLAH ASAL","PUSAT TUGAS"]], use_container_width=True, hide_index=True)

                    with tab_peng:
                        df_peng = df_summary_kum[df_summary_kum["KOLUM JAWATAN"]=="PENGAWAS PEPERIKSAAN"].copy()
                        st.markdown(f"**{len(df_peng)} Pengawas telah dilantik (kumulatif):**")
                        if df_peng.empty:
                            st.info("Belum ada Pengawas")
                        else:
                            st.dataframe(df_peng[["BIL","NAMA GURU","IC","SEKOLAH ASAL","NAMA SEKOLAH ASAL","PUSAT TUGAS"]], use_container_width=True, hide_index=True)

                    with tab_semua:
                        st.markdown(f"**📋 Ringkasan Kumulatif Keseluruhan: {len(df_summary_kum)} guru telah dilantik manual - Lantikan pertama kekal bila tambah lantikan kedua:**")
                        st.dataframe(df_summary_kum, use_container_width=True, hide_index=True)
                        # Export kumulatif
                        try:
                            import io
                            output = io.BytesIO()
                            with __import__("pandas").ExcelWriter(output, engine='openpyxl') as writer:
                                df_summary_kum.to_excel(writer, index=False, sheet_name='Kumulatif Semua')
                                if not df_kp.empty:
                                    df_kp.to_excel(writer, index=False, sheet_name='Ketua Pengawas')
                                if not df_tkp.empty:
                                    df_tkp.to_excel(writer, index=False, sheet_name='Timbalan KP')
                                if not df_peng.empty:
                                    df_peng.to_excel(writer, index=False, sheet_name='Pengawas')
                            st.download_button("📥 Export Excel Kumulatif (4 Sheet Ikut Jawatan)", data=output.getvalue(), file_name=f"ringkasan_manual_kumulatif_{kod_ppd}_{__import__('datetime').date.today()}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="export_kum_manual_excel")
                        except Exception as e:
                            st.caption(f"Export error: {e}")
                            st.download_button("📥 Export CSV Kumulatif", df_summary_kum.to_csv(index=False).encode('utf-8'), file_name=f"ringkasan_manual_kumulatif_{kod_ppd}.csv", mime="text/csv", use_container_width=True, key="export_kum_csv")

                    # Info tambahan: papar lantikan untuk pusat semasa juga (supaya nampak konteks)
                    st.markdown("---")
                    st.markdown(f"#### 📍 Lantikan Untuk Pusat Semasa: {pilih_pusat_manual}")
                    if tugas_pusat_ini:
                        all_rows_curr = []
                        for c in tugas_pusat_ini.values():
                            all_rows_curr.append({"NAMA": c.get("NAMA_GURU", ""), "IC": c.get("IC_GURU", ""), "JAWATAN": c.get("JAWATAN_CADANGAN", ""), "SEKOLAH ASAL": c.get("KOD_SEKOLAH_ASAL", ""), "PUSAT": pilih_pusat_manual})
                        df_curr_sum = __import__("pandas").DataFrame(all_rows_curr)
                        st.dataframe(df_curr_sum, use_container_width=True, hide_index=True)
                    else:
                        st.info(f"Belum ada penempatan di {pilih_pusat_manual} - ini paparan pusat semasa sahaja, ringkasan kumulatif di atas kekal")
            else:
                st.info(f"Belum ada penempatan manual di PPD {kod_ppd} - Sila lantik KP, TKP, Pengawas di atas. Ringkasan kumulatif akan muncul di sini dan tidak hilang bila pilih sekolah kedua.")

        elif menu == "cadangan":
            st.markdown(f'''
            <div style="background: linear-gradient(135deg, #1565c0 0%, #1e88e5 100%); padding:20px; border-radius:12px; color:white; margin-bottom:20px;">
                <h2 style="margin:0; color:white;">📋 Cadangan SUP - PPD {kod_ppd} - {PPD_MAP.get(kod_ppd, '')}</h2>
                <p style="margin:5px 0 0 0; color:#bbdefb;">Pilih sekolah dalam daerah untuk lihat senarai cadangan dari sekolah berkenaan</p>
            </div>
            ''', unsafe_allow_html=True)

            df_cad_all = get_cadangan_df(kod_ppd=kod_ppd)
            if df_cad_all.empty:
                st.warning(f"Belum ada cadangan SUP untuk PPD {kod_ppd}")
                st.stop()

            # ===== FILTER IKUT JAWATAN (MESTI AWAL) + CLEAN NAN =====
            # Clean NAN rows from df_cad_all - remove rows where KOD_SEKOLAH_ASAL is NAN/nan/None/empty
            def is_valid_sekolah(row):
                kod = str(row.get("KOD_SEKOLAH_ASAL") or row.get("kod_sekolah_asal") or row.get("KOD_SEKOLAH") or row.get("kod_sekolah") or "").strip()
                if kod.lower() in ("", "nan", "none", "null", "nat", "-"):
                    return False
                return True

            # Filter out NAN sekolah for display, but keep count for info
            df_cad_valid = df_cad_all[df_cad_all.apply(is_valid_sekolah, axis=1)].copy()
            df_cad_invalid = df_cad_all[~df_cad_all.apply(is_valid_sekolah, axis=1)].copy()
            if not df_cad_invalid.empty:
                st.warning(f"⚠️ Ada {len(df_cad_invalid)} cadangan dengan KOD SEKOLAH kosong/NAN - akan disembunyikan dari senarai sekolah. Sila betulkan di SUP.")

            jawatan_list_all = []
            for _, r in df_cad_valid.iterrows():
                j = str(r.get("JAWATAN_CADANGAN") or r.get("jawatan_cadangan") or r.get("JAWATAN") or "").strip()
                if j and j.lower() not in ("", "nan", "none") and j not in jawatan_list_all:
                    jawatan_list_all.append(j)
            order_jawatan = ["Ketua Pengawas", "Timbalan Ketua Pengawas", "Penyelia Kawasan", "Pengawas Peperiksaan", "Selenggara Bilik Kebal", "Juru Tulis", "Juru Baca", "Ketua Pengawas Hospital", "Pengawas Hospital", "Pengawas Pengiring", "Pengemas Bilik"]
            jawatan_sorted = sorted(jawatan_list_all, key=lambda x: (order_jawatan.index(x) if x in order_jawatan else 99, x))

            # Default filter from session
            filter_jawatan = st.session_state.get("filter_jawatan_cad", [])
            if filter_jawatan is None:
                filter_jawatan = []

            # Init df_cad_filtered as valid first
            df_cad_filtered = df_cad_valid.copy()
            if filter_jawatan:
                df_cad_filtered = df_cad_valid[df_cad_valid.apply(lambda r: str(r.get("JAWATAN_CADANGAN") or r.get("jawatan_cadangan") or r.get("JAWATAN") or "").strip() in filter_jawatan, axis=1)].copy()

            # Get sekolah list in PPD
            try:
                res_sek = supa.table("sekolah_master").select("*").eq("kod_ppd", kod_ppd).limit(2000).execute()
                df_sek_list = pd.DataFrame(res_sek.data or [])
            except:
                df_sek_list = pd.DataFrame()

            # Build sekolah groups dari cadangan (ikut filter) - SKIP NAN + STRICT PPD CHECK
            # Safety: get sekolah list for this PPD again to ensure no cross-PPD leak
            kod_list_ppd_check = []
            try:
                res_sek_check = supa.table("sekolah_master").select("kod_sekolah").eq("kod_ppd", kod_ppd.upper()).limit(2000).execute()
                kod_list_ppd_check = [str(s.get('kod_sekolah','')).upper().strip() for s in (res_sek_check.data or [])]
            except:
                kod_list_ppd_check = []

            sekolah_groups = {}
            for _, r in df_cad_filtered.iterrows():
                # Extra strict check: if sekolah code not in PPD list and KOD_PPD != requested PPD, skip
                kppd_row = str(r.get("KOD_PPD") or "").upper().strip()
                ksek_row = str(r.get("KOD_SEKOLAH_ASAL") or "").upper().strip()
                if kod_list_ppd_check:
                    if ksek_row not in kod_list_ppd_check and kppd_row != kod_ppd.upper():
                        continue
                else:
                    # If no list, check KOD_PPD exact
                    if kppd_row and kppd_row != kod_ppd.upper():
                        continue
                kod_sek_raw = r.get("KOD_SEKOLAH_ASAL") or r.get("kod_sekolah_asal") or r.get("KOD_SEKOLAH") or r.get("kod_sekolah") or ""
                kod_sek = str(kod_sek_raw).strip().upper()
                if kod_sek.lower() in ("", "nan", "none", "null", "nat", "-", "tiada kod"):
                    continue
                nama_sek_raw = r.get("NAMA_SEKOLAH_ASAL") or r.get("nama_sekolah_asal") or r.get("NAMA_SEKOLAH") or kod_sek
                nama_sek = str(nama_sek_raw).strip()
                if nama_sek.lower() in ("", "nan", "none", "null"):
                    nama_sek = kod_sek
                nama_sek = nama_sek[:50]
                key = f"{kod_sek} - {nama_sek}"
                if key not in sekolah_groups:
                    sekolah_groups[key] = []
                sekolah_groups[key].append(r)

            # Summary
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🏫 Sekolah Mencadang", len(sekolah_groups))
            with col2:
                st.metric("👥 Jumlah Cadangan", len(df_cad_all))
            with col3:
                # Belum vs sudah lantik
                def is_belum(row):
                    kp = str(row.get("kod_pusat") or row.get("KOD_PUSAT") or "").strip()
                    return kp == "" or kp.lower() in ("none", "null", "nan", "nat")
                belum = df_cad_all[df_cad_all.apply(is_belum, axis=1)]
                st.metric("✅ Belum Dilantik", len(belum), delta=f"{len(df_cad_all)-len(belum)} telah dilantik")

            st.markdown("### 🔍 Filter Ikut Jawatan")
            st.caption("Filter untuk tengok siapa Penyelia Kawasan, Ketua Pengawas, Timbalan, Pengawas Peperiksaan - senang PPD semak")

            # V20: SIMPLE - no widget key manipulation at all, use direct variable
            if "filter_jawatan_cad" not in st.session_state:
                st.session_state["filter_jawatan_cad"] = []

            col_f1, col_f2, col_f3, col_f4 = st.columns(4)
            with col_f1:
                # V21 FIX DefaultNotInOptionsError: pastikan default ada dalam options
                # Jika Penyelia Kawasan tidak ada dalam jawatan_sorted (data kosong), tambah manual
                safe_default = [x for x in st.session_state["filter_jawatan_cad"] if x in jawatan_sorted]
                # Jika user pilih Penyelia Kawasan tapi jawatan_sorted kosong, tetap tunjuk semua option yang mungkin
                if not jawatan_sorted:
                    jawatan_sorted = ["Ketua Pengawas", "Timbalan Ketua Pengawas", "Penyelia Kawasan", "Pengawas Peperiksaan", "Juru Tulis", "Juru Baca", "Ketua Pengawas Hospital", "Pengawas Hospital", "Pengawas Pengiring", "Pengemas Bilik"]
                    safe_default = st.session_state["filter_jawatan_cad"]
                # Jika safe_default kosong tapi session ada value yang bukan dalam options, guna empty supaya tak error
                # Tapi untuk kes Penyelia Kawasan, kita benarkan jika memang dalam senarai tetap
                if st.session_state["filter_jawatan_cad"] and not safe_default:
                    # Kalau filter ada tapi takde dalam options, jangan error - guna filter tu sebagai options tambahan
                    for v in st.session_state["filter_jawatan_cad"]:
                        if v not in jawatan_sorted:
                            jawatan_sorted.append(v)
                    safe_default = st.session_state["filter_jawatan_cad"]

                filter_jawatan_ui = st.multiselect("Filter Jawatan", jawatan_sorted, default=safe_default, placeholder="Pilih jawatan - kosong = semua")
            with col_f2:
                if filter_jawatan_ui:
                    st.metric(f"Filter: {len(filter_jawatan_ui)} jawatan", f"{len(df_cad_valid[df_cad_valid.apply(lambda r: str(r.get('JAWATAN_CADANGAN') or r.get('jawatan_cadangan') or r.get('JAWATAN') or '').strip() in filter_jawatan_ui, axis=1)]) if filter_jawatan_ui else len(df_cad_all)} guru")
                else:
                    st.metric("Semua Jawatan", f"{len(df_cad_all)} guru")
            with col_f3:
                if st.button("🔐 Hanya Penyelia Kawasan", use_container_width=True, key="btn_filter_pk"):
                    st.session_state["filter_jawatan_cad"] = ["Penyelia Kawasan"]
                    st.rerun()
            with col_f4:
                if st.button("🔄 Clear Filter", use_container_width=True, key="btn_clear_filter"):
                    st.session_state["filter_jawatan_cad"] = []
                    st.rerun()

            # V22 ROBUST: filter using normalized lowercase contains
            def match_jawatan(row_jawatan, filter_list):
                if not filter_list:
                    return True
                rj = str(row_jawatan).strip().lower()
                rj = ' '.join(rj.split())
                for f in filter_list:
                    f_low = str(f).strip().lower()
                    f_low = ' '.join(f_low.split())
                    # Exact or contains
                    if f_low == rj or f_low in rj or rj in f_low:
                        return True
                    # Special for Penyelia Kawasan - check both words
                    if 'penyelia' in f_low and 'penyelia' in rj:
                        return True
                return False

            # Determine active filter list
            active_filter = filter_jawatan_ui if filter_jawatan_ui else st.session_state.get("filter_jawatan_cad", [])

            if active_filter:
                df_cad_filtered = df_cad_valid[df_cad_valid['JAWATAN_CADANGAN'].apply(lambda x: match_jawatan(x, active_filter))].copy()
                # Save for next run default
                if active_filter != st.session_state["filter_jawatan_cad"]:
                    st.session_state["filter_jawatan_cad"] = active_filter
                filter_jawatan_ui = active_filter
            else:
                df_cad_filtered = df_cad_valid.copy()

            if active_filter and len(df_cad_filtered) == 0:
                st.info("Tiada guru yang sepadan dengan penapis jawatan yang dipilih.")

            if st.session_state.get("filter_jawatan_cad"):
                st.success(f"✅ Filter aktif: {', '.join(st.session_state.get('filter_jawatan_cad', []))} - Jumpa {len(df_cad_filtered)} guru")

            # Show breakdown by jawatan
            st.markdown("#### 📊 Pecahan Ikut Jawatan")
            jawatan_counts = {}
            for _, r in df_cad_filtered.iterrows():
                j = str(r.get("JAWATAN_CADANGAN") or r.get("jawatan_cadangan") or "TIADA").strip()
                jawatan_counts[j] = jawatan_counts.get(j, 0) + 1

            if jawatan_counts:
                cols_j = st.columns(len(jawatan_counts))
                for idx, (j, cnt) in enumerate(sorted(jawatan_counts.items(), key=lambda x: (order_jawatan.index(x[0]) if x[0] in order_jawatan else 99, x[0]))):
                    with cols_j[idx % len(cols_j)]:
                        icon = "👑" if "Ketua Pengawas" in j and "Timbalan" not in j else "🎖️" if "Timbalan" in j else "🔐" if "Penyelia" in j else "👨‍🏫" if "Pengawas" in j else "🔧"
                        st.metric(f"{icon} {j}", cnt)

            st.markdown("---")

            # Ringkasan ikut sekolah
            st.markdown("### 📋 Ringkasan Cadangan Mengikut Sekolah (Ikut Filter Jawatan)")
            summary_rows = []
            for key, guru_list in sorted(sekolah_groups.items()):
                kod = key.split(" - ")[0]
                nama = key.split(" - ", 1)[1] if " - " in key else key
                # Kira belum vs sudah
                def _is_sudah_lantik(g):
                    kp = str(g.get("kod_pusat") or g.get("KOD_PUSAT") or g.get("kod_pusat_tugas") or "").strip()
                    status = str(g.get("status") or g.get("STATUS") or "").upper().strip()
                    if kp == "" or kp.lower() in ("none","null","nan","nat",""):
                        return False
                    # Jika kod_pusat == no_pusat_asal dan status HANTAR KE PPD, itu BUKAN sudah lantik (bug lama)
                    no_asal = str(g.get("no_pusat_asal") or g.get("NO_PUSAT_ASAL") or "").upper().strip()
                    if kp.upper() == no_asal and "HANTAR KE PPD" in status:
                        return False
                    # Sudah lantik jika ada kod_pusat dan status LULUS/DILANTIK/SURAT
                    if any(x in status for x in ["LULUS","DILANTIK","DITEMPATKAN","SURAT","SAH"]):
                        return True
                    # Jika kod_pusat ada tapi status masih HANTAR/DICADANGKAN, masih belum lantik
                    if "HANTAR KE PPD" in status or "DICADANGKAN" in status:
                        return False
                    # Default: kalau ada kod_pusat dan bukan HANTAR/DICADANGKAN, anggap sudah
                    return kp != ""
                belum_cnt = sum(1 for g in guru_list if not _is_sudah_lantik(g))
                sudah_cnt = len(guru_list) - belum_cnt
                summary_rows.append({
                    "KOD SEKOLAH": kod,
                    "NAMA SEKOLAH": nama[:35],
                    "JUMLAH CADANGAN": len(guru_list),
                    "BELUM LANTIK": belum_cnt,
                    "SUDAH LANTIK": sudah_cnt,
                    "status": "✅ Lengkap" if belum_cnt == 0 else f"⏳ {belum_cnt} belum"
                })
            df_summary = pd.DataFrame(summary_rows)
            st.dataframe(df_summary, use_container_width=True, hide_index=True)
            st.download_button("📥 Export Ringkasan Cadangan Ikut Sekolah", to_excel(df_summary), file_name=f"ringkasan_cadangan_{kod_ppd}.xlsx", use_container_width=True)

            st.markdown("---")
            st.markdown("### 🔍 Detail Cadangan Ikut Sekolah - Pilih Sekolah (Ikut Filter Jawatan)")
            if filter_jawatan:
                st.info(f"📋 Menunjukkan guru dengan jawatan: {', '.join(filter_jawatan)} sahaja. Clear filter untuk lihat semua.")

            # Pilih sekolah dropdown
            pilih_sek_cad = st.selectbox(
                "Pilih Sekolah Dalam Daerah Untuk Lihat Senarai Cadangan",
                sorted(sekolah_groups.keys()),
                format_func=lambda x: f"{x} ({len(sekolah_groups[x])} cadangan)",
                key="pilih_sekolah_cadangan"
            )

            if pilih_sek_cad:
                guru_list = sekolah_groups[pilih_sek_cad]
                st.markdown(f"#### 🏫 {pilih_sek_cad} - {len(guru_list)} cadangan")

                # Filter tabs: Semua, Belum Lantik, Sudah Lantik
                tab_all, tab_belum, tab_sudah = st.tabs(["📋 Semua", "⏳ Belum Dilantik", "✅ Sudah Dilantik"])

                def make_df_from_list(g_list):
                    rows = []
                    for g in g_list:
                        rows.append({
                            "NAMA GURU": g.get("NAMA_GURU", "") or g.get("nama_guru", ""),
                            "NO IC": g.get("IC_GURU", "") or g.get("ic_guru", ""),
                            "JAWATAN": g.get("JAWATAN_CADANGAN", "") or g.get("jawatan_cadangan", ""),
                            "JANTINA": g.get("JANTINA", "") or g.get("jantina", ""),
                            "TELEFON": g.get("TELEFON_GURU", "") or g.get("telefon_guru", ""),
                            "KOD PUSAT": g.get("kod_pusat", "") or g.get("KOD_PUSAT", "") or "- Belum -",
                            "STATUS": g.get("status", "") or g.get("STATUS", ""),
                            "SEKOLAH": g.get("KOD_SEKOLAH_ASAL", "") or g.get("kod_sekolah_asal", "")
                        })
                    return pd.DataFrame(rows)

                with tab_all:
                    # Additional filter inside school view by jawatan
                    if filter_jawatan:
                        guru_list_filtered_j = [g for g in guru_list if str(g.get("JAWATAN_CADANGAN") or g.get("jawatan_cadangan") or "").strip() in filter_jawatan]
                    else:
                        guru_list_filtered_j = guru_list

                    df_all_guru = make_df_from_list(guru_list_filtered_j)
                    if filter_jawatan:
                        st.caption(f"Filter aktif: {', '.join(filter_jawatan)} - {len(guru_list_filtered_j)} guru dalam sekolah ini")
                    st.dataframe(df_all_guru, use_container_width=True, hide_index=True)
                    st.download_button(f"📥 Export {pilih_sek_cad.split(' - ')[0]} - Semua", to_excel(df_all_guru), file_name=f"cadangan_{pilih_sek_cad.split(' - ')[0]}_semua.xlsx", use_container_width=True, key="exp_all")

                    # Show jawatan breakdown for this school
                    if guru_list_filtered_j:
                        j_count_school = {}
                        for g in guru_list_filtered_j:
                            jj = str(g.get("JAWATAN_CADANGAN") or g.get("jawatan_cadangan") or "TIADA").strip()
                            j_count_school[jj] = j_count_school.get(jj, 0) + 1
                        cols_js = st.columns(len(j_count_school))
                        for idx, (jj, cnt) in enumerate(j_count_school.items()):
                            with cols_js[idx]:
                                st.metric(jj, cnt)

                with tab_belum:
                    def _check_sudah(g):
                        kp = str(g.get("kod_pusat") or g.get("KOD_PUSAT") or "").strip()
                        stt = str(g.get("status") or g.get("STATUS") or "").upper()
                        no_asal = str(g.get("no_pusat_asal") or g.get("NO_PUSAT_ASAL") or "").upper().strip()
                        if kp == "" or kp.lower() in ("none","null","nan","nat",""):
                            return False
                        if kp.upper() == no_asal and "HANTAR KE PPD" in stt:
                            return False
                        if "HANTAR KE PPD" in stt or "DICADANGKAN" in stt:
                            return False
                        if any(x in stt for x in ["LULUS","DILANTIK","DITEMPATKAN","SURAT"]):
                            return True
                        return kp != ""
                    belum_list = [g for g in guru_list if not _check_sudah(g)]
                    st.markdown(f"**{len(belum_list)} guru belum dilantik dari {pilih_sek_cad}**")
                    if belum_list:
                        df_belum_guru = make_df_from_list(belum_list)
                        st.dataframe(df_belum_guru, use_container_width=True, hide_index=True)
                        st.download_button(f"📥 Export Belum Lantik", to_excel(df_belum_guru), file_name=f"cadangan_{pilih_sek_cad.split(' - ')[0]}_belum.xlsx", use_container_width=True, key="exp_belum")
                    else:
                        st.success("✅ Semua guru dari sekolah ini telah dilantik!")

                with tab_sudah:
                    sudah_list = [g for g in guru_list if _check_sudah(g)]
                    st.markdown(f"**{len(sudah_list)} guru sudah dilantik dari {pilih_sek_cad}**")
                    if sudah_list:
                        df_sudah_guru = make_df_from_list(sudah_list)
                        st.dataframe(df_sudah_guru, use_container_width=True, hide_index=True)
                        st.download_button(f"📥 Export Sudah Lantik", to_excel(df_sudah_guru), file_name=f"cadangan_{pilih_sek_cad.split(' - ')[0]}_sudah.xlsx", use_container_width=True, key="exp_sudah")
                    else:
                        st.info("Belum ada guru dilantik dari sekolah ini")


        elif menu == "semakan":
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #0d47a1 0%, #0d47a1 100%); padding:20px; border-radius:12px; color:white; margin-bottom:20px;">
                <h2 style="margin:0; color:white;">🔍 Semakan Lantikan Ikut Pusat - PPD {kod_ppd}</h2>
                <p style="margin:5px 0 0 0; color:#e3f2fd;">Pilih pusat, akan keluar 4 table ikut jawatan: Penyelia Kawasan, Ketua Pengawas, Timbalan, Pengawas. PPD boleh batalkan lantikan & guru masuk semula ke cadangan untuk pilih pusat lain. Boleh isi kekosongan dengan guru lain.</p>
            </div>
            """, unsafe_allow_html=True)

            df_pusat_raw = get_pusat_df()
            df_cad_all = get_cadangan_df(kod_ppd=kod_ppd)

            if df_pusat_raw.empty:
                st.warning("Tiada pusat_master")
                st.stop()
            if df_cad_all.empty:
                st.warning("Belum ada cadangan")
                st.stop()

            # Parse pusat list
            pusat_list = []
            for _, r in df_pusat_raw.iterrows():
                d = r.get("data") if isinstance(r.get("data"), dict) else {}
                if isinstance(d, str):
                    try: d = json.loads(d)
                    except: d = {}
                no_pusat = str(r.get("no_pusat") or r.get("kod_pusat") or d.get("NO_PUSAT") or "").upper().strip()
                if not no_pusat.startswith(kod_ppd.upper()): continue
                nama = r.get("nama_pusat") or d.get("NAMA_PUSAT") or ""
                pusat_list.append({"NO_PUSAT": no_pusat, "NAMA_PUSAT": nama})
            df_pusat_list = __import__("pandas").DataFrame(pusat_list)

            if df_pusat_list.empty:
                st.warning(f"Tiada pusat untuk PPD {kod_ppd}")
                st.stop()

            # Pilih pusat
            pilihan_pusat_semak = st.selectbox(
                "📍 Pilih Pusat Untuk Semakan Lantikan",
                df_pusat_list["NO_PUSAT"].tolist(),
                format_func=lambda x: f"{x} - {df_pusat_list[df_pusat_list['NO_PUSAT']==x]['NAMA_PUSAT'].values[0][:35] if not df_pusat_list[df_pusat_list['NO_PUSAT']==x].empty else x}",
                key="pilih_pusat_semakan"
            )

            st.markdown(f"### 🔍 Semakan Lantikan - Pusat {pilihan_pusat_semak}")

            # Get lantikan for this pusat
            try:
                res_lantik = supa.table("cadangan_sup").select("*").eq("kod_pusat", pilihan_pusat_semak).limit(5000).execute()
                df_lantik_pusat = __import__("pandas").DataFrame(res_lantik.data or [])
            except Exception as e:
                st.error(f"Error baca lantikan: {e}")
                df_lantik_pusat = __import__("pandas").DataFrame()

            if fly_cur == "semak":
                if df_lantik_pusat.empty:
                    st.warning(f"Belum ada lantikan di pusat {pilihan_pusat_semak}")
                    # Still allow to add guru
                    df_lantik_pusat = __import__("pandas").DataFrame()
                else:
                    st.success(f"Ada {len(df_lantik_pusat)} lantikan di {pilihan_pusat_semak}")

                # Helper to get jawatan groups
                def get_jawatan_group(df, keyword, exclude_keywords=[]):
                    if df.empty:
                        return __import__("pandas").DataFrame()
                    def match(row):
                        jaw = str(row.get("jawatan_cadangan") or row.get("JAWATAN_CADANGAN") or "").upper()
                        if keyword.upper() not in jaw:
                            return False
                        for ex in exclude_keywords:
                            if ex.upper() in jaw:
                                # Special handling for Ketua vs Timbalan
                                if keyword.upper()=="KETUA PENGAWAS" and "TIMBALAN" in jaw:
                                    return False
                                if keyword.upper()=="PENYELIA" and ex.upper() not in jaw:
                                    continue
                        # For Ketua Pengawas, exclude Timbalan
                        if keyword.upper()=="KETUA PENGAWAS" and "TIMBALAN" in jaw:
                            return False
                        # For Pengawas Peperiksaan, exclude Ketua, Timbalan, Penyelia
                        if keyword.upper()=="PENGAWAS" and any(k in jaw for k in ["KETUA","TIMBALAN","PENYELIA","SELENGGARA"]):
                            return False
                        return True
                    return df[df.apply(match, axis=1)].copy()

                # Split into 4 groups
                # Penyelia Kawasan
                df_penyelia = df_lantik_pusat[df_lantik_pusat.apply(lambda r: "PENYELIA" in str(r.get("jawatan_cadangan") or "").upper(), axis=1)].copy() if not df_lantik_pusat.empty else __import__("pandas").DataFrame()
                # Ketua Pengawas
                df_kp = df_lantik_pusat[df_lantik_pusat.apply(lambda r: "KETUA PENGAWAS" in str(r.get("jawatan_cadangan") or "").upper() and "TIMBALAN" not in str(r.get("jawatan_cadangan") or "").upper(), axis=1)].copy() if not df_lantik_pusat.empty else __import__("pandas").DataFrame()
                # Timbalan
                df_tkp = df_lantik_pusat[df_lantik_pusat.apply(lambda r: "TIMBALAN" in str(r.get("jawatan_cadangan") or "").upper(), axis=1)].copy() if not df_lantik_pusat.empty else __import__("pandas").DataFrame()
                # Pengawas
                df_peng = df_lantik_pusat[df_lantik_pusat.apply(lambda r: "PENGAWAS" in str(r.get("jawatan_cadangan") or "").upper() and "KETUA" not in str(r.get("jawatan_cadangan") or "").upper() and "TIMBALAN" not in str(r.get("jawatan_cadangan") or "").upper() and "PENYELIA" not in str(r.get("jawatan_cadangan") or "").upper(), axis=1)].copy() if not df_lantik_pusat.empty else __import__("pandas").DataFrame()

                # Function to display table with batal action
                def display_jawatan_table(df_jawatan, tajuk, icon, color, jawatan_name):
                    st.markdown(f"""
                <div style="background: {color}; padding:12px; border-radius:8px; color:white; margin:15px 0 10px 0;">
                    <h3 style="margin:0; color:white;">{icon} {tajuk} - {len(df_jawatan)} orang di {pilihan_pusat_semak}</h3>
                </div>
                """, unsafe_allow_html=True)

                    if df_jawatan.empty:
                        st.info(f"Belum ada {tajuk} di pusat ini")
                        return

                    # Build display rows
                    rows = []
                    for _, r in df_jawatan.iterrows():
                        rows.append({
                            "id": r.get("id",""),
                            "NAMA GURU": r.get("nama_guru","") or r.get("NAMA_GURU",""),
                            "IC": r.get("ic_guru","") or r.get("IC_GURU",""),
                            "JAWATAN": r.get("jawatan_cadangan","") or r.get("JAWATAN_CADANGAN",""),
                            "SEKOLAH ASAL": r.get("kod_sekolah_asal","") or r.get("KOD_SEKOLAH_ASAL",""),
                            "NAMA SEKOLAH ASAL": str(r.get("nama_sekolah_asal","") or r.get("NAMA_SEKOLAH_ASAL",""))[:25],
                            "POSKOD RUMAH": r.get("poskod_rumah","") or r.get("POSKOD_RUMAH",""),
                            "TELEFON": r.get("telefon_guru","") or r.get("TELEFON_GURU",""),
                            "STATUS": r.get("status","") or r.get("STATUS","")
                        })
                    df_disp = __import__("pandas").DataFrame(rows)
                    st.dataframe(df_disp, use_container_width=True, hide_index=True)

                    # Batalkan lantikan section
                    with st.expander(f"❌ Batalkan Lantikan {tajuk} di {pilihan_pusat_semak}", expanded=False):
                        st.warning(f"Jika PPD rasa guru ini tidak sesuai di {pilihan_pusat_semak}, boleh batalkan. Guru akan masuk semula ke bahagian cadangan SUP untuk dipilih di pusat lain.")
                        batal_ids = st.multiselect(
                            f"Pilih {tajuk} untuk batalkan lantikan di {pilihan_pusat_semak}",
                            df_disp["id"].tolist(),
                            format_func=lambda x: f"{df_disp[df_disp['id']==x]['NAMA GURU'].values[0]} - {df_disp[df_disp['id']==x]['SEKOLAH ASAL'].values[0]} - {df_disp[df_disp['id']==x]['IC'].values[0]}" if not df_disp[df_disp['id']==x].empty else str(x),
                            key=f"batal_{jawatan_name}_{pilihan_pusat_semak}"
                        )
                        if batal_ids:
                            st.error(f"Anda akan batalkan {len(batal_ids)} {tajuk} dari {pilihan_pusat_semak}. Guru akan kembali ke cadangan SUP (kod_pusat = NULL, status = HANTAR KE PPD).")
                            if st.button(f"❌ Confirm Batalkan {len(batal_ids)} {tajuk} dari {pilihan_pusat_semak}", type="primary", use_container_width=True, key=f"btn_batal_{jawatan_name}_{pilihan_pusat_semak}"):
                                try:
                                    berjaya = 0
                                    for gid in batal_ids:
                                        # Batalkan: set kod_pusat None, status HANTAR KE PPD supaya masuk semula ke cadangan
                                        supa.table("cadangan_sup").update({"kod_pusat": None, "status": "HANTAR KE PPD", "status": "HANTAR KE PPD"}).eq("id", gid).execute()
                                        berjaya+=1
                                    st.success(f"✅ Berjaya batalkan {berjaya} {tajuk} dari {pilihan_pusat_semak}. Guru masuk semula ke cadangan SUP untuk dipilih di pusat lain.")
                                    st.balloons()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Gagal batal: {e}")

                # Display 4 tables
                display_jawatan_table(df_penyelia, "Penyelia Kawasan", "🔐", "linear-gradient(135deg, #0d47a1 0%, #0d47a1 100%)", "penyelia")
                display_jawatan_table(df_kp, "Ketua Pengawas", "👑", "linear-gradient(135deg, #0d47a1 0%, #0d47a1 100%)", "kp")
                display_jawatan_table(df_tkp, "Timbalan Ketua Pengawas", "🎖️", "linear-gradient(135deg, #0d47a1 0%, #0d47a1 100%)", "tkp")
                display_jawatan_table(df_peng, "Pengawas Peperiksaan", "👨‍🏫", "linear-gradient(135deg, #0d47a1 0%, #0d47a1 100%)", "pengawas")

            if fly_cur == "kosong":
                st.markdown("---")
                st.markdown(f"### ➕ Isi Kekosongan di {pilihan_pusat_semak} - Pilih Guru Lain")
                st.info(f"Selepas batalkan lantikan di atas, PPD boleh pilih guru lain dari cadangan SUP untuk isi kekosongan di {pilihan_pusat_semak}. Guru yang dibatalkan tadi sudah masuk semula ke pool cadangan.")

                # Get guru yang belum dilantik (pool untuk isi kekosongan)
                try:
                    df_belum_pool = df_cad_all[df_cad_all.apply(lambda r: str(r.get("kod_pusat") or r.get("KOD_PUSAT") or "").strip() in ("", "None", "none", "null", "nan", "nat"), axis=1)].copy()
                except:
                    df_belum_pool = __import__("pandas").DataFrame()

                if df_belum_pool.empty:
                    st.warning("Tiada guru dalam pool cadangan yang belum dilantik - semua sudah dilantik. Batalkan dulu lantikan di atas untuk kembalikan guru ke pool.")
                else:
                    st.markdown(f"**{len(df_belum_pool)} guru dalam pool belum dilantik - boleh pilih untuk isi kekosongan di {pilihan_pusat_semak}:**")

                    # Filter by jawatan for easier selection
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        filter_jawatan_semak = st.selectbox(
                            "Filter Ikut Jawatan Untuk Isi Kekosongan",
                            ["Semua Jawatan", "Ketua Pengawas", "Timbalan Ketua Pengawas", "Pengawas Peperiksaan", "Penyelia Kawasan", "Juru Tulis", "Juru Baca", "Ketua Pengawas Hospital", "Pengawas Hospital", "Pengawas Pengiring", "Pengemas Bilik"],
                            key=f"filter_jawatan_semak_{pilihan_pusat_semak}"
                        )
                    with col_f2:
                        # Info pusat tuan rumah for max3 check
                        info_pusat_semak = df_pusat_list[df_pusat_list["NO_PUSAT"]==pilihan_pusat_semak]
                        # Get current count per sekolah in this pusat
                        sekolah_count_semak = {}
                        if not df_lantik_pusat.empty:
                            for _, r in df_lantik_pusat.iterrows():
                                ks = str(r.get("kod_sekolah_asal") or "").upper().strip()
                                sekolah_count_semak[ks] = sekolah_count_semak.get(ks, 0) + 1
                        st.caption(f"Pusat {pilihan_pusat_semak} sudah ada {len(df_lantik_pusat)} petugas. Max 3 per sekolah. Count: {sekolah_count_semak}")

                    df_pool_filtered = df_belum_pool.copy()
                    if filter_jawatan_semak != "Semua Jawatan":
                        def match_filter(r, target):
                            jaw = str(r.get("JAWATAN_CADANGAN") or r.get("jawatan_cadangan") or "").upper()
                            tgt = target.upper()
                            if "KETUA PENGAWAS" in tgt and "TIMBALAN" not in tgt:
                                return "KETUA PENGAWAS" in jaw and "TIMBALAN" not in jaw
                            elif "TIMBALAN" in tgt:
                                return "TIMBALAN" in jaw
                            elif "PENGAWAS PEPERIKSAAN" in tgt:
                                return "PENGAWAS PEPERIKSAAN" in jaw or jaw.strip()=="PENGAWAS"
                            elif "PENYELIA" in tgt:
                                return "PENYELIA" in jaw
                            else:
                                return tgt in jaw
                        df_pool_filtered = df_pool_filtered[df_pool_filtered.apply(lambda r: match_filter(r, filter_jawatan_semak), axis=1)].copy()

                    # Filter out sekolah tuan rumah and max3
                    # Get kod tuan rumah
                    kod_tuan_semak = ""
                    try:
                        df_pusat_raw_all = get_pusat_df()
                        for _, pr in df_pusat_raw_all.iterrows():
                            d = pr.get("data") if isinstance(pr.get("data"), dict) else {}
                            if isinstance(d, str):
                                try: d = json.loads(d)
                                except: d = {}
                            no_p = str(pr.get("no_pusat") or pr.get("kod_pusat") or d.get("NO_PUSAT") or "").upper().strip()
                            if no_p == pilihan_pusat_semak:
                                kod_tuan_semak = str(pr.get("kod_sekolah_tuan_rumah") or pr.get("kod_sekolah") or d.get("KOD_SEKOLAH") or "").upper().strip()
                                break
                    except:
                        kod_tuan_semak = ""

                    df_pool_layak = df_pool_filtered.copy()
                    if kod_tuan_semak:
                        df_pool_layak = df_pool_layak[~df_pool_layak.apply(lambda r: str(r.get("KOD_SEKOLAH_ASAL") or r.get("kod_sekolah_asal") or "").upper().strip() == kod_tuan_semak, axis=1)]

                    # Check max3
                    def check_max3_semak(row):
                        kod = str(row.get("KOD_SEKOLAH_ASAL") or row.get("kod_sekolah_asal") or "").upper().strip()
                        return sekolah_count_semak.get(kod, 0) < 3 if kod else True
                    df_pool_layak = df_pool_layak[df_pool_layak.apply(check_max3_semak, axis=1)].copy()

                    st.markdown(f"**{len(df_pool_layak)} calon layak untuk isi kekosongan di {pilihan_pusat_semak} (selepas filter {filter_jawatan_semak}, elak sekolah sendiri & max3):**")

                    if df_pool_layak.empty:
                        st.warning("Tiada calon layak untuk pusat ini")
                    else:
                        display_pool = []
                        for _, r in df_pool_layak.iterrows():
                            display_pool.append({
                                "id": r.get("id",""),
                                "NAMA GURU": r.get("NAMA_GURU","") or r.get("nama_guru",""),
                                "IC": r.get("IC_GURU","") or r.get("ic_guru",""),
                                "JAWATAN": r.get("JAWATAN_CADANGAN","") or r.get("jawatan_cadangan",""),
                                "SEKOLAH ASAL": r.get("KOD_SEKOLAH_ASAL","") or r.get("kod_sekolah_asal",""),
                                "POSKOD": r.get("POSKOD_RUMAH","") or r.get("poskod_rumah",""),
                                "STATUS": r.get("STATUS","") or r.get("status","")
                            })
                        df_pool_disp = __import__("pandas").DataFrame(display_pool)
                        st.dataframe(df_pool_disp, use_container_width=True, hide_index=True)

                        pilih_guru_isi = st.multiselect(
                            f"Pilih guru untuk isi kekosongan di {pilihan_pusat_semak}",
                            df_pool_disp["id"].tolist(),
                            format_func=lambda x: f"{df_pool_disp[df_pool_disp['id']==x]['NAMA GURU'].values[0]} - {df_pool_disp[df_pool_disp['id']==x]['SEKOLAH ASAL'].values[0]} - {df_pool_disp[df_pool_disp['id']==x]['JAWATAN'].values[0]}" if not df_pool_disp[df_pool_disp['id']==x].empty else str(x),
                            key=f"pilih_guru_isi_{pilihan_pusat_semak}"
                        )

                        if pilih_guru_isi:
                            if st.button(f"✅ Lantik {len(pilih_guru_isi)} Guru Terpilih ke {pilihan_pusat_semak} Untuk Isi Kekosongan", type="primary", use_container_width=True, key=f"btn_lantik_isi_{pilihan_pusat_semak}"):
                                try:
                                    berjaya = 0
                                    for gid in pilih_guru_isi:
                                        supa.table("cadangan_sup").update({"kod_pusat": pilihan_pusat_semak, "status": "DILANTIK PPD", "status": "DILANTIK PPD"}).eq("id", gid).execute()
                                        berjaya+=1
                                    st.success(f"✅ Berjaya lantik {berjaya} guru untuk isi kekosongan di {pilihan_pusat_semak}")
                                    st.balloons()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Gagal lantik: {e}")




        elif menu == "kelulusan":
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #0d47a1 0%, #0d47a1 100%); padding:20px; border-radius:12px; color:white; margin-bottom:20px;">
                <h2 style="margin:0; color:white;">✅ Kelulusan - PPD {kod_ppd} - {PPD_MAP.get(kod_ppd,'')}</h2>
                <p style="margin:5px 0 0 0; color:#ffffff;">Pilihan: Kelulusan Keseluruhan (Lulus Semua & Jana Surat Keseluruhan) atau Lulus Mengikut Pusat (Pilih Pusat & Lulus Jana Surat) - No Surat Berturutan Ikut Daerah, Tak Berulang, Auto Sequential</p>
            </div>
            """, unsafe_allow_html=True)

            # Helper to get max no surat for this PPD to ensure sequential no repeat
            def get_max_no_surat_ppd(kod_ppd_filter):
                try:
                    res = supa.table("cadangan_sup").select("no_surat").eq("kod_ppd", kod_ppd_filter).not_.is_("no_surat", "null").limit(10000).execute()
                    max_no = 0
                    import re
                    for r in (res.data or []):
                        ns = str(r.get("no_surat") or "").strip()
                        if not ns:
                            continue
                        # Cari angka di akhir: contoh JPN.SEL/PPD.BA/SPM/2026/0001 -> 1
                        nums = re.findall(r'(\d+)', ns)
                        if nums:
                            try:
                                val = int(nums[-1])
                                if val > max_no:
                                    max_no = val
                            except:
                                pass
                    return max_no
                except Exception as e:
                    return 0

            def get_next_no_surat_format(kod_ppd_filter, seq_no):
                # Guna rujukan yang PPD type: contoh JPN.SPP.HHJH + bilangan surat
                rujukan = st.session_state.get("selenggara_rujukan_format") or st.session_state.get("input_no_rujukan_ppd") or f"JPN.SEL/PPD.{kod_ppd_filter}/SPM/{datetime.date.today().year}"
                # Jika rujukan sudah ada / di hujung, tambah bilangan sahaja
                rujukan_clean = rujukan.rstrip('/')
                return f"{rujukan_clean}/{seq_no:04d}"

            def sebab_belum_lulus(r):
                st_ = str(r.get("status") or r.get("STATUS") or "").strip()
                ns_ = str(r.get("no_surat") or r.get("NO_SURAT") or "").strip().lower()
                if "LULUS" not in st_.upper():
                    return f"Status belum LULUS ({st_ or 'kosong'})"
                if ns_ in ("", "nan", "none", "null"):
                    return "Status LULUS tetapi No Surat kosong"
                return "-"

            def paparkan_sebab_belum(df_b, tajuk):
                if df_b is None or df_b.empty:
                    return
                with st.expander(f"🔎 Kenapa {len(df_b)} guru ini masih dalam senarai belum lulus? ({tajuk})", expanded=False):
                    _rows = []
                    for _, _r in df_b.iterrows():
                        _rows.append({
                            "ID": _r.get("id", ""),
                            "NAMA": _r.get("NAMA_GURU", "") or _r.get("nama_guru", ""),
                            "IC": _r.get("IC_GURU", "") or _r.get("ic_guru", ""),
                            "PUSAT": _r.get("kod_pusat", "") or _r.get("KOD_PUSAT", ""),
                            "STATUS": _r.get("status", "") or _r.get("STATUS", ""),
                            "NO SURAT": _r.get("no_surat", "") or _r.get("NO_SURAT", ""),
                            "SEBAB": sebab_belum_lulus(_r),
                        })
                    st.dataframe(pd.DataFrame(_rows), use_container_width=True, hide_index=True)

            def semak_selepas_lulus(df_b, ns_map):
                """Baca semula dari DB: pastikan setiap guru betul-betul LULUS + ada No Surat. Cuba simpan semula yang gagal.
                Pulangkan senarai nama yang masih gagal."""
                gagal = []
                try:
                    ids = [r.get("id") for _, r in df_b.iterrows() if r.get("id")]
                    ok_ids = set()
                    if ids:
                        chk = supa.table("cadangan_sup").select("id,status,no_surat").in_("id", ids).execute()
                        for x in (chk.data or []):
                            if "LULUS" in str(x.get("status") or "").upper() and str(x.get("no_surat") or "").strip().lower() not in ("", "nan", "none", "null"):
                                ok_ids.add(x.get("id"))
                    for _, r in df_b.iterrows():
                        id_x = r.get("id")
                        if not id_x or id_x in ok_ids:
                            continue
                        ns_x = ns_map.get(id_x) or str(r.get("no_surat") or "").strip()
                        try:
                            supa.table("cadangan_sup").update({"status": "LULUS PPD - SURAT DIHANTAR KE SEKOLAH ASAL", "no_surat": ns_x}).eq("id", id_x).execute()
                            chk2 = supa.table("cadangan_sup").select("id,status,no_surat").eq("id", id_x).limit(1).execute()
                            d2 = (chk2.data or [{}])[0]
                            if not ("LULUS" in str(d2.get("status") or "").upper() and str(d2.get("no_surat") or "").strip()):
                                gagal.append(f"{r.get('NAMA_GURU','') or r.get('nama_guru','')} (ID {id_x})")
                        except Exception as e_retry:
                            gagal.append(f"{r.get('NAMA_GURU','') or r.get('nama_guru','')} (ID {id_x}): {e_retry}")
                except Exception as e_chk:
                    gagal.append(f"Semakan gagal: {e_chk}")
                return gagal

            # Get all data for PPD
            df_cad_all = get_cadangan_df(kod_ppd=kod_ppd)
            df_pusat_raw = get_pusat_df()

            # Build pusat map for display
            pusat_map = {}
            try:
                for _, r in df_pusat_raw.iterrows():
                    d = r.get("data") if isinstance(r.get("data"), dict) else {}
                    if isinstance(d, str):
                        try: d = json.loads(d)
                        except: d = {}
                    no_p = str(r.get("no_pusat") or r.get("kod_pusat") or d.get("NO_PUSAT") or "").upper().strip()
                    nama_p = r.get("nama_pusat") or d.get("NAMA_PUSAT") or ""
                    if no_p:
                        pusat_map[no_p] = nama_p
            except:
                pass

            # ===== SUB MENU KELULUSAN =====
            sub_kelulusan = "✅ Kelulusan Keseluruhan (Lulus Semua & Jana Surat Keseluruhan)" if fly_cur == "keseluruhan" else "🏫 Lulus Mengikut Pusat (Pilih Pusat & Lulus Jana Surat)"

            max_no_global = get_max_no_surat_ppd(kod_ppd)
            # BUANG PENYATAAN No Surat terakhir - tak perlu info panjang



            # ===== RUANG SELENGGARA NO SURAT DI ATAS - PPD TYPE NO RUJUKAN & BILANGAN SURAT SAHAJA - ADA COLUM UNTUK ISI =====
            st.markdown("### 🔐 Selenggara No Surat")

            # Check max existing
            try:
                max_exist = get_max_no_surat_ppd(kod_ppd)
            except:
                max_exist = 0

            # ALWAYS SHOW COLUM UNTUK PPD TYPE NO RUJUKAN DAN NO SURAT - BUANG PENYATAAN
            col_ruj1, col_ruj2 = st.columns(2)
            with col_ruj1:
                no_rujukan_input = st.text_input(
                    "No Rujukan (Contoh: JPN.SPP.HHJH)",
                    value=st.session_state.get("input_no_rujukan_ppd", f"JPN.SPP.HHJH/PPD.{kod_ppd}"),
                    placeholder="Taip contoh: JPN.SPP.HHJH",
                    key="input_no_rujukan_ppd_final"
                )
            with col_ruj2:
                bil_surat_input = st.number_input(
                    "Bilangan Surat / No Surat",
                    min_value=1,
                    value=int(st.session_state.get("input_bil_surat_ppd", max_exist+1 if max_exist>0 else 1)),
                    step=1,
                    key="input_bil_surat_ppd_final"
                )

            st.markdown(f"**Preview No Surat: {no_rujukan_input}/{bil_surat_input:04d}**")

            # Save to session
            st.session_state["selenggara_rujukan_format"] = no_rujukan_input
            st.session_state["selenggara_bil_mula"] = bil_surat_input

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button(f"🔐 Sahkan No Surat {no_rujukan_input}/{bil_surat_input:04d}", type="primary", use_container_width=True, key="btn_sahkan_no_surat_final"):
                    try:
                        df_pusat_all = get_pusat_df()
                        try:
                            marker_found = False
                            for _, r in df_pusat_all.iterrows():
                                d = r.get("data") if isinstance(r.get("data"), dict) else {}
                                if isinstance(d, str):
                                    try: d = json.loads(d)
                                    except: d = {}
                                no_p = str(r.get("no_pusat") or r.get("kod_pusat") or d.get("NO_PUSAT") or "").upper().strip()
                                if no_p.startswith(kod_ppd.upper()):
                                    rec_id = r.get("id")
                                    d["SELENGGARA_NO_SURAT_DONE"] = True
                                    d["SELENGGARA_NO_SURAT_TARIKH"] = str(datetime.date.today())
                                    d["SELENGGARA_NO_SURAT_OLEH"] = kod_ppd
                                    d["SELENGGARA_NO_SURAT_RUJUKAN"] = no_rujukan_input
                                    d["SELENGGARA_NO_SURAT_MULA"] = bil_surat_input
                                    d["SELENGGARA_NO_SURAT_FORMAT"] = f"{no_rujukan_input}/{bil_surat_input:04d}"
                                    supa.table("pusat_master").update({"data": d}).eq("id", rec_id).execute()
                                    marker_found = True
                                    break
                            if not marker_found:
                                log_data = {
                                    "SELENGGARA_NO_SURAT_DONE": True,
                                    "SELENGGARA_NO_SURAT_TARIKH": str(datetime.date.today()),
                                    "SELENGGARA_NO_SURAT_OLEH": kod_ppd,
                                    "SELENGGARA_NO_SURAT_RUJUKAN": no_rujukan_input,
                                    "SELENGGARA_NO_SURAT_MULA": bil_surat_input,
                                    "NO_PUSAT": f"{kod_ppd}-LOG-SURAT",
                                    "NAMA_PUSAT": f"LOG SELENGGARA NO SURAT PPD {kod_ppd}"
                                }
                                supa.table("pusat_master").insert({"no_pusat": f"{kod_ppd}-LOG-SURAT", "kod_ppd": kod_ppd, "nama_pusat": f"LOG SELENGGARA NO SURAT PPD {kod_ppd}", "data": log_data}).execute()
                        except Exception as e_inner:
                            pass
                        st.success(f"✅ No Surat Disahkan: {no_rujukan_input}/{bil_surat_input:04d} - Akan guna untuk jana surat")
                        st.balloons()
                    except Exception as e:
                        st.error("Maaf, berlaku masalah semasa memproses. Sila cuba lagi.")
            with col_btn2:
                if max_exist > 0:
                    st.caption(f"Sedia ada max: {max_exist} | Seterusnya: {max_exist+1}")
                else:
                    st.caption("Belum ada No Surat - mula dari 1")

            st.markdown("---")

            # ===== OPTION 1: KELULUSAN KESELURUHAN =====
            st.markdown("---")

            # ===== OPTION 1: KELULUSAN KESELURUHAN =====
            st.markdown("---")

            # ===== OPTION 1: KELULUSAN KESELURUHAN =====
            if st.session_state.get("kelulusan_amaran"):
                st.error("⚠️ Guru berikut TIDAK berjaya disimpan sebagai LULUS dalam pangkalan data (sila semak kebenaran/jadual Supabase):\n\n" + "\n".join(f"- {x}" for x in st.session_state["kelulusan_amaran"]))
                if st.button("Tutup amaran", key="btn_tutup_amaran_kelulusan"):
                    st.session_state["kelulusan_amaran"] = []
                    st.rerun()

            # ===== OPTION 1: KELULUSAN KESELURUHAN =====
            if "Keseluruhan" in sub_kelulusan:
                st.markdown("### ✅ Kelulusan Keseluruhan - Lulus Semua & Jana Surat Keseluruhan")
                st.caption("Semua guru yang telah dilantik (DILANTIK PPD) di PPD ini akan diluluskan sekaligus. No Surat auto berturutan ikut daerah, tak berulang.")

                def is_valid_no_surat_fix(ns):
                    s = str(ns or "").strip()
                    return s != "" and s.lower() not in ("nan","none","null","")
                def is_true_lulus_fix(row):
                    status = str(row.get("status") or row.get("STATUS") or "").upper()
                    ns = row.get("no_surat") or ""
                    return "LULUS" in status and is_valid_no_surat_fix(ns)
                def is_belum_lulus_fix(row):
                    return not is_true_lulus_fix(row)
                df_sudah = df_cad_all[df_cad_all.apply(lambda r: str(r.get("kod_pusat") or r.get("KOD_PUSAT") or "").strip() != "" and str(r.get("kod_pusat") or "").lower() not in ("none","null","nan"), axis=1)].copy() if not df_cad_all.empty else pd.DataFrame()
                df_belum_lulus = df_sudah[df_sudah.apply(is_belum_lulus_fix, axis=1)].copy() if not df_sudah.empty else pd.DataFrame()
                df_sudah_lulus = df_sudah[df_sudah.apply(is_true_lulus_fix, axis=1)].copy() if not df_sudah.empty else pd.DataFrame()

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Dilantik", len(df_sudah))
                col2.metric("Belum Lulus (Perlu Lulus)", len(df_belum_lulus))
                col3.metric("Sudah Lulus Ada No Surat", len(df_sudah_lulus))
                col4.metric("No Surat Seterusnya", f"{max_no_global+1:04d}")

                if df_sudah.empty:
                    st.warning("Belum ada guru dilantik di PPD ini - sila jana di Jana Keseluruhan / Manual dulu")
                    st.stop()

                with st.expander(f"📋 Lihat {len(df_sudah)} Guru Telah Dilantik di PPD {kod_ppd} (Semua Pusat)", expanded=False):
                    display_cols = [c for c in ["NAMA_GURU","IC_GURU","JAWATAN_CADANGAN","KOD_SEKOLAH_ASAL","kod_pusat","KOD_PUSAT","status","no_surat"] if c in df_sudah.columns]
                    st.dataframe(df_sudah[display_cols] if display_cols else df_sudah, use_container_width=True, hide_index=True)

                if df_belum_lulus.empty:
                    st.success(f"✅ Semua {len(df_sudah)} guru sudah LULUS dan ada No Surat - tiada yang perlu diluluskan lagi")
                else:
                    st.markdown(f"#### 📝 {len(df_belum_lulus)} Guru Perlu Diluluskan - No Surat Berturutan {max_no_global+1} hingga {max_no_global+len(df_belum_lulus)}")
                    paparkan_sebab_belum(df_belum_lulus, "Kelulusan Keseluruhan")

                    # Preview
                    preview_rows = []
                    cur_no = max_no_global + 1
                    for _, r in df_belum_lulus.iterrows():
                        existing_ns = str(r.get("no_surat") or "").strip()
                        if existing_ns:
                            no_baru = existing_ns
                        else:
                            no_baru = get_next_no_surat_format(kod_ppd, cur_no)
                            cur_no += 1
                        preview_rows.append({
                            "NAMA GURU": r.get("NAMA_GURU","") or r.get("nama_guru",""),
                            "IC": r.get("IC_GURU","") or r.get("ic_guru",""),
                            "JAWATAN": r.get("JAWATAN_CADANGAN","") or r.get("jawatan_cadangan",""),
                            "SEKOLAH ASAL": r.get("KOD_SEKOLAH_ASAL","") or r.get("kod_sekolah_asal",""),
                            "PUSAT TUGAS": r.get("kod_pusat","") or r.get("KOD_PUSAT",""),
                            "NAMA PUSAT": pusat_map.get(str(r.get("kod_pusat","") or "").upper().strip(), ""),
                            "NO SURAT BARU": no_baru,
                            "STATUS SEKARANG": r.get("status","") or r.get("STATUS","")
                        })
                    df_preview_keseluruhan = pd.DataFrame(preview_rows)
                    st.dataframe(df_preview_keseluruhan, use_container_width=True, hide_index=True)

                    col_lulus_all, col_jana_all = st.columns(2)
                    with col_lulus_all:
                        if st.button(f"✅ LULUS KESELURUHAN {len(df_belum_lulus)} GURU - Jana No Surat {max_no_global+1} hingga {max_no_global+len(preview_rows)}", type="primary", use_container_width=True, key="btn_lulus_keseluruhan"):
                            try:
                                berjaya = 0
                                cur_no = max_no_global + 1
                                surat_list_all = []
                                _map_ns_all = {}
                                for _, r in df_belum_lulus.iterrows():
                                    id_g = r.get("id","")
                                    existing_ns = str(r.get("no_surat") or "").strip()
                                    if existing_ns:
                                        no_surat_baru = existing_ns
                                    else:
                                        no_surat_baru = get_next_no_surat_format(kod_ppd, cur_no)
                                        cur_no += 1

                                    # Generate surat HTML untuk hantar ke sekolah asal
                                    nama_g = r.get("NAMA_GURU","") or r.get("nama_guru","")
                                    ic_g = r.get("IC_GURU","") or r.get("ic_guru","")
                                    jaw_g = r.get("JAWATAN_CADANGAN","") or r.get("jawatan_cadangan","")
                                    sek_asal = r.get("KOD_SEKOLAH_ASAL","") or r.get("kod_sekolah_asal","")
                                    pusat_tugas = r.get("kod_pusat","") or r.get("KOD_PUSAT","")
                                    nama_pusat_tugas = pusat_map.get(str(pusat_tugas).upper().strip(), "")

                                    # Simpan surat HTML dalam data json untuk hantar ke sekolah asal
                                    try:
                                        tarikh_surat = datetime.date.today().strftime('%d %B %Y')
                                        html_surat_single = generate_surat_html(nama_g, ic_g, jaw_g, sek_asal, sek_asal, pusat_tugas, nama_pusat_tugas, no_surat_baru, kod_ppd, PPD_MAP.get(kod_ppd,""), tarikh_surat)
                                    except:
                                        html_surat_single = ""

                                    data_update = {}
                                    if html_surat_single:
                                        data_update = {"surat_html": html_surat_single, "surat_tarikh": str(datetime.date.today()), "surat_no": no_surat_baru}

                                    if id_g:
                                        # Update dengan no_surat, status LULUS, dan data surat untuk sekolah asal
                                        try:
                                            existing_data = supa.table("cadangan_sup").select("data").eq("id", id_g).limit(1).execute()
                                            old_data = {}
                                            if existing_data.data:
                                                old_data = existing_data.data[0].get("data") or {}
                                                if isinstance(old_data, str):
                                                    try: old_data = json.loads(old_data)
                                                    except: old_data = {}
                                            old_data.update(data_update)
                                            old_data["SURAT_DIHANTAR_KE_SEKOLAH_ASAL"] = True
                                            supa.table("cadangan_sup").update({"status": "LULUS PPD - SURAT DIHANTAR KE SEKOLAH ASAL", "no_surat": no_surat_baru, "data": old_data}).eq("id", id_g).execute()
                                        except:
                                            supa.table("cadangan_sup").update({"status": "LULUS PPD - SURAT DIHANTAR KE SEKOLAH ASAL", "no_surat": no_surat_baru}).eq("id", id_g).execute()
                                    else:
                                        supa.table("cadangan_sup").update({"status": "LULUS PPD - SURAT DIHANTAR KE SEKOLAH ASAL", "no_surat": no_surat_baru}).eq("ic_guru", r.get("IC_GURU","") or r.get("ic_guru","")).execute()

                                    surat_list_all.append({"nama": nama_g, "ic": ic_g, "sekolah_asal": sek_asal, "pusat": pusat_tugas, "no_surat": no_surat_baru, "html": html_surat_single})
                                    if id_g:
                                        _map_ns_all[id_g] = no_surat_baru
                                    berjaya += 1

                                # Semak semula dari pangkalan data - pastikan semua betul-betul LULUS
                                st.session_state["kelulusan_amaran"] = semak_selepas_lulus(df_belum_lulus, _map_ns_all)

                                # Simpan surat kolektif untuk PPD download HTML
                                full_html_all = f'<html><head><meta charset="UTF-8"><title>Surat Lantikan Keseluruhan PPD {kod_ppd}</title><style>body{{font-family:Arial;margin:20px;}} .surat{{border:2px solid #000; padding:20px; margin:20px 0; page-break-after:always;}}</style></head><body>'
                                full_html_all += f'<h1 style="text-align:center;">SURAT LANTIKAN PETUGAS PEPERIKSAAN SPM {tahun_aktif()} - KESELURUHAN PPD {kod_ppd}</h1><p style="text-align:center;">No Surat: {max_no_global+1} hingga {cur_no-1}</p><hr>'
                                for s in surat_list_all:
                                    full_html_all += s["html"]
                                full_html_all += '</body></html>'
                                st.session_state[f"surat_keseluruhan_html_{kod_ppd}"] = full_html_all
                                st.session_state[f"surat_keseluruhan_list_{kod_ppd}"] = surat_list_all

                                st.success(f"✅ Berjaya LULUS KESELURUHAN {berjaya} guru! No Surat {max_no_global+1} hingga {cur_no-1} - Surat HTML dijana & DIHANTAR KE SEKOLAH ASAL GURU untuk SUP cetak & bagi pada guru berkenaan")
                                st.balloons()
                                st.info(f"📄 Surat yang sama telah dihantar ke sekolah asal guru (SUP boleh lihat di menu Surat Lantikan Saya > ada surat - untuk SUP cetak dan bagi pada guru di mana dia kena bertugas)")
                                st.components.v1.html(full_html_all[:15000], height=700, scrolling=True)
                                try:
                                    pdf_bytes_all = generate_surat_kolektif_pdf_bytes(surat_list_all, kod_ppd, PPD_MAP.get(kod_ppd,""), f"SURAT LANTIKAN KESELURUHAN PPD {kod_ppd}")
                                    if pdf_bytes_all:
                                        st.download_button("📥 Download Surat Keseluruhan (PDF)", data=pdf_bytes_all, file_name=f"Surat_Lantikan_Keseluruhan_{kod_ppd}_{datetime.date.today()}.pdf", mime="application/pdf", use_container_width=True, key="dl_surat_keseluruhan_pdf_after_lulus")
                                except:
                                    pass
                                st.download_button("📥 Download Surat Keseluruhan (HTML) - Untuk PPD", data=full_html_all.encode('utf-8'), file_name=f"Surat_Lantikan_Keseluruhan_{kod_ppd}_{datetime.date.today()}.html", mime="text/html", use_container_width=True, key="dl_surat_keseluruhan_after_lulus")
                                # Also PDF individual zip? For now collective PDF

                                st.cache_data.clear()   # segar semula data supaya bilangan "Belum Lulus" betul
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error lulus keseluruhan: {e}")

                    with col_jana_all:
                        if st.button(f"📄 Jana Surat Keseluruhan {len(df_belum_lulus)} Guru (No Berturutan)", use_container_width=True, key="btn_jana_surat_keseluruhan"):
                            tarikh = datetime.date.today().strftime('%d %B %Y')
                            full_html = f'<html><head><meta charset="UTF-8"><title>Surat Lantikan Keseluruhan PPD {kod_ppd}</title><style>body{{font-family:Arial;margin:20px;}} .surat{{border:1px solid #ccc; padding:20px; margin:20px 0; page-break-after:always;}} h2{{text-align:center;}}</style></head><body>'
                            full_html += f'<h1 style="text-align:center;">SURAT LANTIKAN PETUGAS PEPERIKSAAN SPM {tahun_aktif()}</h1><h2 style="text-align:center;">PPD {kod_ppd} - {PPD_MAP.get(kod_ppd,"")} - KESELURUHAN</h2><p style="text-align:center;">No Surat Berturutan: {max_no_global+1} hingga {max_no_global+len(df_preview_keseluruhan)} - Ikut Daerah {kod_ppd} - Siapa Jana Dahulu No Dia Dahulu</p><hr>'
                            for s in preview_rows:
                                full_html += generate_surat_html(s["NAMA GURU"], s["IC"], s["JAWATAN"], s["SEKOLAH ASAL"], s["NAMA GURU"], s["PUSAT TUGAS"], s["NAMA PUSAT"], s["NO SURAT BARU"], kod_ppd, PPD_MAP.get(kod_ppd,""), tarikh)
                            full_html += '</body></html>'
                            st.session_state["surat_keseluruhan_html"] = full_html
                            st.success(f"Surat Keseluruhan {len(preview_rows)} guru berjaya dijana! No Surat {max_no_global+1} hingga {max_no_global+len(preview_rows)} berturutan")
                            st.components.v1.html(full_html[:10000], height=600, scrolling=True)
                            try:
                                pdf_k = generate_surat_kolektif_pdf_bytes([{"nama": s["NAMA GURU"], "ic": s["IC"], "jawatan": s["JAWATAN"], "sekolah_asal": s["SEKOLAH ASAL"], "pusat": s["PUSAT"], "no_surat": s["NO SURAT BARU"], "nama_pusat": s["NAMA PUSAT"]} for s in preview_rows], kod_ppd, PPD_MAP.get(kod_ppd,""), f"SURAT LANTIKAN KESELURUHAN PPD {kod_ppd}")
                                if pdf_k:
                                    st.download_button("📥 Download Surat Keseluruhan (PDF)", data=pdf_k, file_name=f"Surat_Lantikan_Keseluruhan_{kod_ppd}_{datetime.date.today()}.pdf", mime="application/pdf", use_container_width=True, key="dl_surat_keseluruhan_pdf")
                            except:
                                pass
                            st.download_button("📥 Download Surat Keseluruhan (HTML)", data=full_html.encode('utf-8'), file_name=f"Surat_Lantikan_Keseluruhan_{kod_ppd}_{datetime.date.today()}.html", mime="text/html", use_container_width=True, key="dl_surat_keseluruhan")

            # ===== OPTION 2: LULUS MENGIKUT PUSAT =====
            else:
                st.markdown("### 🏫 Lulus Mengikut Pusat - Pilih Pusat & Lulus Jana Surat")
                st.caption("Pilih satu pusat, luluskan guru di pusat tersebut sahaja. No Surat tetap berturutan untuk semua (ikut daerah), tak berulang - siapa jana dulu no dia dahulu.")

                # Build pusat list that has dilantik guru
                df_sudah_all = df_cad_all[df_cad_all.apply(lambda r: str(r.get("kod_pusat") or r.get("KOD_PUSAT") or "").strip() != "" and str(r.get("kod_pusat") or "").lower() not in ("none","null","nan"), axis=1)].copy() if not df_cad_all.empty else pd.DataFrame()

                if df_sudah_all.empty:
                    st.warning("Belum ada guru dilantik di PPD ini")
                    st.stop()

                # Group by pusat
                pusat_groups = {}
                for _, r in df_sudah_all.iterrows():
                    kp = str(r.get("kod_pusat") or r.get("KOD_PUSAT") or "").upper().strip()
                    if kp:
                        if kp not in pusat_groups:
                            pusat_groups[kp] = []
                        pusat_groups[kp].append(r)

                pilihan_pusat_lulus = st.selectbox(
                    "📍 Pilih Pusat Untuk Lulus Mengikut Pusat",
                    sorted(pusat_groups.keys()),
                    format_func=lambda x: f"{x} - {pusat_map.get(x,'')} ({len(pusat_groups[x])} guru dilantik)",
                    key="pilih_pusat_kelulusan_mengikut_pusat"
                )

                if pilihan_pusat_lulus:
                    guru_pusat_list = pusat_groups[pilihan_pusat_lulus]
                    st.markdown(f"#### {pilihan_pusat_lulus} - {pusat_map.get(pilihan_pusat_lulus,'')} - {len(guru_pusat_list)} guru dilantik")

                    df_pusat_lulus = pd.DataFrame(guru_pusat_list)

                    # Belum lulus vs sudah lulus
                    def _is_lulus_pusat(r):
                        _st = str(r.get("status") or r.get("STATUS") or "").upper()
                        _ns = str(r.get("no_surat") or r.get("NO_SURAT") or "").strip().lower()
                        return ("LULUS" in _st) and (_ns not in ("", "nan", "none", "null"))
                    df_belum_pusat = df_pusat_lulus[~df_pusat_lulus.apply(_is_lulus_pusat, axis=1)].copy()
                    df_sudah_lulus_pusat = df_pusat_lulus[df_pusat_lulus.apply(_is_lulus_pusat, axis=1)].copy()

                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total Dilantik di Pusat", len(df_pusat_lulus))
                    col2.metric("Belum Lulus (Perlu Lulus)", len(df_belum_pusat))
                    col3.metric("Sudah Lulus Ada No Surat", len(df_sudah_lulus_pusat))

                    # Display table
                    rows_pusat = []
                    for r in guru_pusat_list:
                        rows_pusat.append({
                            "id": r.get("id",""),
                            "NAMA GURU": r.get("NAMA_GURU","") or r.get("nama_guru",""),
                            "IC": r.get("IC_GURU","") or r.get("ic_guru",""),
                            "JAWATAN": r.get("JAWATAN_CADANGAN","") or r.get("jawatan_cadangan",""),
                            "SEKOLAH ASAL": r.get("KOD_SEKOLAH_ASAL","") or r.get("kod_sekolah_asal",""),
                            "PUSAT": r.get("kod_pusat","") or r.get("KOD_PUSAT",""),
                            "STATUS": r.get("status","") or r.get("STATUS",""),
                            "NO SURAT": r.get("no_surat","") or ""
                        })
                    df_display_pusat = pd.DataFrame(rows_pusat)
                    st.dataframe(df_display_pusat, use_container_width=True, hide_index=True)

                    if df_belum_pusat.empty:
                        st.success(f"✅ Semua guru di {pilihan_pusat_lulus} sudah LULUS dan ada No Surat")
                    else:
                        st.markdown(f"#### 📝 {len(df_belum_pusat)} Guru di {pilihan_pusat_lulus} Perlu Diluluskan - No Surat Berturutan Bermula {max_no_global+1}")
                        paparkan_sebab_belum(df_belum_pusat, pilihan_pusat_lulus)

                        preview_pusat = []
                        cur_no = max_no_global + 1
                        for _, r in df_belum_pusat.iterrows():
                            existing_ns = str(r.get("no_surat") or "").strip()
                            if existing_ns:
                                no_baru = existing_ns
                            else:
                                no_baru = get_next_no_surat_format(kod_ppd, cur_no)
                                cur_no += 1
                            preview_pusat.append({
                                "NAMA GURU": r.get("NAMA_GURU","") or r.get("nama_guru",""),
                                "IC": r.get("IC_GURU","") or r.get("ic_guru",""),
                                "JAWATAN": r.get("JAWATAN_CADANGAN","") or r.get("jawatan_cadangan",""),
                                "SEKOLAH ASAL": r.get("KOD_SEKOLAH_ASAL","") or r.get("kod_sekolah_asal",""),
                                "PUSAT": r.get("kod_pusat","") or r.get("KOD_PUSAT",""),
                                "NO SURAT BARU": no_baru
                            })
                        df_preview_pusat = pd.DataFrame(preview_pusat)
                        st.dataframe(df_preview_pusat, use_container_width=True, hide_index=True)

                        col_lulus_pusat, col_jana_pusat = st.columns(2)
                        with col_lulus_pusat:
                            if st.button(f"✅ Lulus {len(df_belum_pusat)} Guru di {pilihan_pusat_lulus} - No {max_no_global+1} hingga {cur_no-1} & Hantar ke Sekolah Asal", type="primary", use_container_width=True, key=f"btn_lulus_pusat_{pilihan_pusat_lulus}"):
                                try:
                                    berjaya = 0
                                    cur_no2 = max_no_global + 1
                                    surat_list_pusat = []
                                    _map_ns_p = {}
                                    for _, r in df_belum_pusat.iterrows():
                                        id_g = r.get("id","")
                                        existing_ns = str(r.get("no_surat") or "").strip()
                                        if existing_ns:
                                            no_baru = existing_ns
                                        else:
                                            no_baru = get_next_no_surat_format(kod_ppd, cur_no2)
                                            cur_no2 += 1

                                        nama_g = r.get("NAMA_GURU","") or r.get("nama_guru","")
                                        ic_g = r.get("IC_GURU","") or r.get("ic_guru","")
                                        jaw_g = r.get("JAWATAN_CADANGAN","") or r.get("jawatan_cadangan","")
                                        sek_asal = r.get("KOD_SEKOLAH_ASAL","") or r.get("kod_sekolah_asal","")

                                        try:
                                            tarikh_surat = datetime.date.today().strftime('%d %B %Y')
                                            html_single = generate_surat_html(nama_g, ic_g, jaw_g, sek_asal, sek_asal, pilihan_pusat_lulus, pusat_map.get(pilihan_pusat_lulus,""), no_baru, kod_ppd, PPD_MAP.get(kod_ppd,""), tarikh_surat)
                                        except:
                                            html_single = ""

                                        try:
                                            existing_data = supa.table("cadangan_sup").select("data").eq("id", id_g).limit(1).execute() if id_g else None
                                            old_data = {}
                                            if existing_data and existing_data.data:
                                                old_data = existing_data.data[0].get("data") or {}
                                                if isinstance(old_data, str):
                                                    try: old_data = json.loads(old_data)
                                                    except: old_data = {}
                                            old_data.update({"surat_html": html_single, "surat_tarikh": str(datetime.date.today()), "surat_no": no_baru, "SURAT_DIHANTAR_KE_SEKOLAH_ASAL": True})
                                            if id_g:
                                                supa.table("cadangan_sup").update({"status": "LULUS PPD - SURAT DIHANTAR KE SEKOLAH ASAL", "no_surat": no_baru, "data": old_data}).eq("id", id_g).execute()
                                            else:
                                                supa.table("cadangan_sup").update({"status": "LULUS PPD - SURAT DIHANTAR KE SEKOLAH ASAL", "no_surat": no_baru}).eq("ic_guru", r.get("IC_GURU","") or r.get("ic_guru","")).execute()
                                        except:
                                            if id_g:
                                                supa.table("cadangan_sup").update({"status": "LULUS PPD - SURAT DIHANTAR KE SEKOLAH ASAL", "no_surat": no_baru}).eq("id", id_g).execute()

                                        surat_list_pusat.append({"nama": nama_g, "ic": ic_g, "sekolah_asal": sek_asal, "pusat": pilihan_pusat_lulus, "no_surat": no_baru, "html": html_single})
                                        if id_g:
                                            _map_ns_p[id_g] = no_baru
                                        berjaya += 1

                                    # Semak semula dari pangkalan data - pastikan semua betul-betul LULUS
                                    st.session_state["kelulusan_amaran"] = semak_selepas_lulus(df_belum_pusat, _map_ns_p)

                                    # Generate full HTML for this pusat
                                    full_html_pusat = f'<html><head><meta charset="UTF-8"><title>Surat {pilihan_pusat_lulus}</title><style>body{{font-family:Arial;margin:20px;}} .surat{{border:2px solid #000; padding:20px; margin:20px 0; page-break-after:always;}}</style></head><body>'
                                    full_html_pusat += f'<h1 style="text-align:center;">SURAT LANTIKAN SPM {tahun_aktif()} - {pilihan_pusat_lulus} - {pusat_map.get(pilihan_pusat_lulus,"")}</h1><p style="text-align:center;">PPD {kod_ppd} - No Surat {max_no_global+1} hingga {cur_no2-1}</p><hr>'
                                    for s in surat_list_pusat:
                                        full_html_pusat += s["html"]
                                    full_html_pusat += '</body></html>'
                                    st.session_state[f"surat_pusat_{pilihan_pusat_lulus}_html"] = full_html_pusat

                                    st.success(f"✅ Berjaya Lulus {berjaya} guru di {pilihan_pusat_lulus}! No Surat {max_no_global+1} hingga {cur_no2-1} - Surat DIHANTAR KE SEKOLAH ASAL GURU untuk SUP cetak & bagi pada guru berkenaan")
                                    st.balloons()
                                    st.info(f"📄 Surat yang sama telah sampai ke sekolah asal guru - SUP boleh lihat di Surat Lantikan Saya untuk cetak & bagi pada guru di mana dia kena bertugas ({pilihan_pusat_lulus})")
                                    st.components.v1.html(full_html_pusat[:15000], height=700, scrolling=True)
                                    try:
                                        pdf_pusat = generate_surat_kolektif_pdf_bytes(surat_list_pusat, kod_ppd, PPD_MAP.get(kod_ppd,""), f"SURAT LANTIKAN {pilihan_pusat_lulus}")
                                        if pdf_pusat:
                                            st.download_button(f"📥 Download Surat {pilihan_pusat_lulus} (PDF) & Hantar ke Sekolah Asal", data=pdf_pusat, file_name=f"Surat_{pilihan_pusat_lulus}_{kod_ppd}_{datetime.date.today()}.pdf", mime="application/pdf", use_container_width=True, key=f"dl_surat_pusat_pdf_after_{pilihan_pusat_lulus}")
                                    except:
                                        pass
                                    st.download_button(f"📥 Download Surat {pilihan_pusat_lulus} (HTML) & Hantar ke Sekolah Asal", data=full_html_pusat.encode('utf-8'), file_name=f"Surat_{pilihan_pusat_lulus}_{kod_ppd}_{datetime.date.today()}.html", mime="text/html", use_container_width=True, key=f"dl_surat_pusat_after_{pilihan_pusat_lulus}")
                                    st.cache_data.clear()   # segar semula data supaya bilangan "Belum Lulus" betul
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error lulus pusat: {e}")

                        with col_jana_pusat:
                            if st.button(f"📄 Jana Surat {pilihan_pusat_lulus} - {len(df_belum_pusat)} Guru", use_container_width=True, key=f"btn_jana_surat_pusat_{pilihan_pusat_lulus}"):
                                tarikh = datetime.date.today().strftime('%d %B %Y')
                                full_html = f'<html><head><meta charset="UTF-8"><title>Surat Lantikan {pilihan_pusat_lulus}</title><style>body{{font-family:Arial;margin:20px;}} .surat{{border:1px solid #ccc; padding:20px; margin:20px 0; page-break-after:always;}}</style></head><body>'
                                full_html += f'<h1 style="text-align:center;">SURAT LANTIKAN SPM {tahun_aktif()} - {pilihan_pusat_lulus}</h1><h2 style="text-align:center;">{pusat_map.get(pilihan_pusat_lulus,"")} - PPD {kod_ppd}</h2><p style="text-align:center;">No Surat Berturutan: {max_no_global+1} hingga {max_no_global+len(preview_pusat)} - Ikut Daerah {kod_ppd}</p><hr>'
                                for s in preview_pusat:
                                    full_html += generate_surat_html(s["NAMA GURU"], s["IC"], s["JAWATAN"], s["SEKOLAH ASAL"], s["NAMA GURU"], s["PUSAT"], pusat_map.get(s["PUSAT"],""), s["NO SURAT BARU"], kod_ppd, PPD_MAP.get(kod_ppd,""), tarikh)
                                full_html += '</body></html>'
                                st.session_state[f"surat_pusat_{pilihan_pusat_lulus}"] = full_html
                                st.success(f"Surat {pilihan_pusat_lulus} berjaya dijana! {len(preview_pusat)} guru")
                                st.components.v1.html(full_html[:10000], height=600, scrolling=True)
                                try:
                                    pdf_k2 = generate_surat_kolektif_pdf_bytes([{"nama": s["NAMA GURU"], "ic": s["IC"], "jawatan": s["JAWATAN"], "sekolah_asal": s["SEKOLAH ASAL"], "pusat": s["PUSAT"], "no_surat": s["NO SURAT BARU"]} for s in preview_pusat], kod_ppd, PPD_MAP.get(kod_ppd,""), f"SURAT LANTIKAN {pilihan_pusat_lulus}")
                                    if pdf_k2:
                                        st.download_button(f"📥 Download Surat {pilihan_pusat_lulus} (PDF)", data=pdf_k2, file_name=f"Surat_Lantikan_{pilihan_pusat_lulus}_{kod_ppd}_{datetime.date.today()}.pdf", mime="application/pdf", use_container_width=True, key=f"dl_surat_pusat_pdf_{pilihan_pusat_lulus}")
                                except:
                                    pass
                                st.download_button(f"📥 Download Surat {pilihan_pusat_lulus}", data=full_html.encode('utf-8'), file_name=f"Surat_Lantikan_{pilihan_pusat_lulus}_{kod_ppd}_{datetime.date.today()}.html", mime="text/html", use_container_width=True, key=f"dl_surat_pusat_{pilihan_pusat_lulus}")



        elif menu == "selenggara":
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #0d47a1 0%, #1565c0 100%); padding:20px; border-radius:12px; color:white; margin-bottom:20px; border:2px solid #002171;">
                <h2 style="margin:0; color:white;">🔐 Selenggara Bilik Kebal - PPD {kod_ppd} - {PPD_MAP.get(kod_ppd,'')}</h2>
                <p style="margin:5px 0 0 0; color:#bbdefb;">Tapak Bilik Kebal Master - PPD isi data bilik kebal ikut daerah. Penyelia Kawasan akan ditempatkan ke bilik kebal ini. SUP tidak nampak menu ini.</p>
            </div>
            """, unsafe_allow_html=True)

            def get_bilik_kebal_df(kod_ppd_filter=None):
                try:
                    q = supa.table("bilik_kebal_master").select("*").limit(10000)
                    if kod_ppd_filter:
                        q = q.eq("kod_ppd", kod_ppd_filter)
                    res = q.execute()
                    return pd.DataFrame(res.data or [])
                except Exception as e:
                    st.error(f"Error load bilik_kebal_master: {e}")
                    return pd.DataFrame()

            df_bk = get_bilik_kebal_df(kod_ppd)

            c1,c2,c3 = st.columns(3)
            c1.metric("Bilik Kebal di PPD", len(df_bk))
            c2.metric("Daerah", PPD_MAP.get(kod_ppd,''))
            try:
                res_cad = supa.table("cadangan_sup").select("*", count="exact").eq("kod_ppd", kod_ppd.lower()).limit(1).execute()
                total_guru_ppd = res_cad.count if hasattr(res_cad,'count') else 0
            except:
                total_guru_ppd = 0
            c3.metric("Guru PPD", total_guru_ppd)

            # [FLYOUT] st.tabs diganti sub menu flyout

            if fly_cur == "form":
                st.markdown("### Borang Daftar Bilik Kebal Baru")
                st.caption("PPD isi form ini, data terus masuk Supabase table bilik_kebal_master")
                with st.form("form_bilik_kebal"):
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        kod_bk = st.text_input("KOD_BILIK_KEBAL *", placeholder="Contoh: BK-BA001 atau BA-BK01")
                        nama_bk = st.text_input("NAMA_BILIK_KEBAL *", placeholder="Contoh: Bilik Kebal PPD Klang")
                        kod_ppd_form = st.text_input("KOD_PPD", value=kod_ppd, disabled=True)
                    with col_f2:
                        alamat_bk = st.text_area("ALAMAT *", placeholder="Alamat penuh bilik kebal", height=100)
                        catatan = st.text_area("Catatan / DATA JSON (optional)", placeholder='Contoh: {"kapasiti": 50}', height=100)
                    submit_bk = st.form_submit_button("Simpan Bilik Kebal ke Supabase", type="primary", use_container_width=True)
                    if submit_bk:
                        if not kod_bk or not nama_bk or not alamat_bk:
                            st.error("Sila isi KOD, NAMA dan ALAMAT wajib!")
                        else:
                            try:
                                data_json = {}
                                if catatan:
                                    try:
                                        data_json = json.loads(catatan)
                                    except:
                                        data_json = {"catatan": catatan}
                                existing = supa.table("bilik_kebal_master").select("*").eq("kod_bilik_kebal", kod_bk.upper().strip()).limit(1).execute()
                                if existing.data:
                                    st.error(f"KOD {kod_bk} sudah wujud!")
                                else:
                                    payload = {
                                        "kod_bilik_kebal": kod_bk.upper().strip(),
                                        "nama_bilik_kebal": nama_bk.upper().strip(),
                                        "alamat": alamat_bk.strip(),
                                        "kod_ppd": kod_ppd.upper().strip(),
                                        "data": data_json
                                    }
                                    supa.table("bilik_kebal_master").insert(payload).execute()
                                    st.success(f"Berjaya simpan {kod_bk} - {nama_bk}")
                                    st.balloons()
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Error simpan: {e}")

            if fly_cur == "senarai":
                st.markdown(f"### Senarai Bilik Kebal PPD {kod_ppd}")
                if df_bk.empty:
                    st.info("Belum ada bilik kebal didaftarkan untuk PPD ini.")
                else:
                    cari_bk = st.text_input("Cari bilik kebal (kod / nama / alamat)", key="cari_bk")
                    if cari_bk:
                        mask = df_bk.apply(lambda r: cari_bk.lower() in str(r.get("kod_bilik_kebal","")).lower() or cari_bk.lower() in str(r.get("nama_bilik_kebal","")).lower() or cari_bk.lower() in str(r.get("alamat","")).lower(), axis=1)
                        df_show = df_bk[mask]
                    else:
                        df_show = df_bk
                    st.dataframe(df_show, use_container_width=True, hide_index=True)
                    col_exp1, col_exp2 = st.columns(2)
                    with col_exp1:
                        st.download_button("Download Senarai Bilik Kebal (Excel)", to_excel(df_show), file_name=f"bilik_kebal_{kod_ppd}_{datetime.date.today()}.xlsx", use_container_width=True)
                    with col_exp2:
                        if st.button("Refresh", use_container_width=True):
                            st.rerun()
                    st.markdown("---")
                    st.markdown("### Buang Bilik Kebal")
                    if not df_show.empty:
                        pilih_buang = st.selectbox("Pilih Bilik Kebal untuk buang", df_show["kod_bilik_kebal"].tolist() if "kod_bilik_kebal" in df_show.columns else [], key="buang_bk")
                        if st.button(f"Buang {pilih_buang}", type="secondary", use_container_width=True):
                            try:
                                supa.table("bilik_kebal_master").delete().eq("kod_bilik_kebal", pilih_buang).execute()
                                st.success(f"Berjaya buang {pilih_buang}")
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))

            if fly_cur == "import":
                st.markdown("### Import Pukal Bilik Kebal dari Excel")
                st.info("Format Excel mesti ada column: KOD_BILIK_KEBAL, NAMA_BILIK_KEBAL, ALAMAT, KOD_PPD")
                df_template = pd.DataFrame([
                    {"KOD_BILIK_KEBAL": f"BK-{kod_ppd}01", "NAMA_BILIK_KEBAL": f"BILIK KEBAL PPD {PPD_MAP.get(kod_ppd,'')} 1", "ALAMAT": "SMK CONTOH 1, KLANG", "KOD_PPD": kod_ppd},
                    {"KOD_BILIK_KEBAL": f"BK-{kod_ppd}02", "NAMA_BILIK_KEBAL": f"BILIK KEBAL PPD {PPD_MAP.get(kod_ppd,'')} 2", "ALAMAT": "SMK CONTOH 2, KLANG", "KOD_PPD": kod_ppd},
                ])
                st.download_button("Download Template Excel Bilik Kebal", to_excel(df_template), file_name=f"template_bilik_kebal_{kod_ppd}.xlsx", use_container_width=True)
                st.markdown("---")
                up_bk = st.file_uploader("Upload Excel Bilik Kebal", type=["xlsx","xls"], key="up_bk_excel")
                if up_bk:
                    try:
                        df_up = pd.read_excel(up_bk, sheet_name=0)
                        st.write(f"Ada {len(df_up)} baris.")
                        st.dataframe(df_up.head(10), use_container_width=True)
                        if st.button(f"Import {len(df_up)} Bilik Kebal ke Supabase", type="primary", use_container_width=True):
                            bar = st.progress(0)
                            ok = 0
                            err = 0
                            for idx, row in df_up.iterrows():
                                try:
                                    kod = str(row.get("KOD_BILIK_KEBAL") or row.get("kod_bilik_kebal") or "").upper().strip()
                                    nama = str(row.get("NAMA_BILIK_KEBAL") or row.get("nama_bilik_kebal") or "").upper().strip()
                                    alamat = str(row.get("ALAMAT") or row.get("alamat") or "").strip()
                                    kppd = str(row.get("KOD_PPD") or row.get("kod_ppd") or kod_ppd).upper().strip()
                                    if not kod or not nama:
                                        err += 1
                                        continue
                                    dup = supa.table("bilik_kebal_master").select("*").eq("kod_bilik_kebal", kod).limit(1).execute()
                                    if dup.data:
                                        err += 1
                                        continue
                                    supa.table("bilik_kebal_master").insert({"kod_bilik_kebal": kod, "nama_bilik_kebal": nama, "alamat": alamat, "kod_ppd": kppd, "data": {}}).execute()
                                    ok += 1
                                except:
                                    err += 1
                                bar.progress((idx+1)/len(df_up))
                            st.success(f"Selesai: {ok} berjaya, {err} gagal/duplicate")
                            st.balloons()
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error baca Excel: {e}")

            if fly_cur == "penyelia":
                st.markdown(f"### Penempatan Penyelia Kawasan ke Bilik Kebal - PPD {kod_ppd}")
                st.caption("STEP 1: Pilih Bilik Kebal → STEP 2: Pilih Pusat di bawah Bilik Kebal (contoh 12 pusat) → STEP 3: Agihkan pusat tu kepada setiap Penyelia Kawasan (bukan bagi semua untuk sorang)")
                if df_bk.empty:
                    st.warning("Belum ada bilik kebal. Sila daftar bilik kebal dulu di tab Tambah / Import.")
                else:
                    df_cad_all_bk = get_cadangan_df(kod_ppd=kod_ppd)
                    if not df_cad_all_bk.empty:
                        col_jaw = "JAWATAN_CADANGAN" if "JAWATAN_CADANGAN" in df_cad_all_bk.columns else "jawatan_cadangan" if "jawatan_cadangan" in df_cad_all_bk.columns else None
                        if col_jaw:
                            df_penyelia_all = df_cad_all_bk[df_cad_all_bk[col_jaw].astype(str).str.contains("Penyelia Kawasan", case=False, na=False)].copy()
                        else:
                            df_penyelia_all = pd.DataFrame()
                        # FIX: Keluarkan yang sudah dilantik - hanya tinggalkan belum dilantik
                        def is_belum_penyelia(r):
                            kp = str(r.get("kod_pusat") or r.get("KOD_PUSAT") or r.get("kod_bilik_kebal") or "").strip()
                            return kp == "" or kp.lower() in ("none","null","nan","nat","-")
                        if not df_penyelia_all.empty:
                            df_penyelia = df_penyelia_all[df_penyelia_all.apply(is_belum_penyelia, axis=1)].copy()
                            sudah = len(df_penyelia_all) - len(df_penyelia)
                        else:
                            df_penyelia = pd.DataFrame()
                            sudah = 0
                    else:
                        df_penyelia = pd.DataFrame()
                        sudah = 0

                    if sudah > 0:
                        st.info(f"Ada {len(df_penyelia_all)} Penyelia dicadangkan, {sudah} sudah dilantik (disembunyikan), {len(df_penyelia)} belum dilantik - hanya yang belum dilantik dipaparkan untuk pilihan")
                    else:
                        st.info(f"Ada {len(df_penyelia)} Penyelia Kawasan dicadangkan SUP untuk PPD {kod_ppd} (belum dilantik)")

                    if not df_penyelia.empty:
                        df_pusat_raw_all = get_pusat_df()
                        pusat_list_ppd = []
                        for _, r in df_pusat_raw_all.iterrows():
                            d = r.get("data") if isinstance(r.get("data"), dict) else {}
                            if isinstance(d, str):
                                try:
                                    d = json.loads(d)
                                except:
                                    d = {}
                            no_p = str(r.get("no_pusat") or r.get("kod_pusat") or d.get("NO_PUSAT") or "").upper().strip()
                            if not no_p.startswith(kod_ppd.upper()):
                                continue
                            nama_p = r.get("nama_pusat") or d.get("NAMA_PUSAT") or ""
                            pusat_list_ppd.append({"NO_PUSAT": no_p, "NAMA_PUSAT": nama_p})
                        df_pusat_ppd_list = pd.DataFrame(pusat_list_ppd)

                        # STEP 1: Pilih Bilik Kebal
                        st.markdown("#### STEP 1: Pilih Bilik Kebal")
                        pilih_bk_tempat = st.selectbox("Pilih Bilik Kebal", df_bk["kod_bilik_kebal"].tolist() if "kod_bilik_kebal" in df_bk.columns else [], format_func=lambda x: f"{x} - {df_bk[df_bk['kod_bilik_kebal']==x]['nama_bilik_kebal'].values[0][:30] if not df_bk[df_bk['kod_bilik_kebal']==x].empty and 'nama_bilik_kebal' in df_bk.columns else x}", key="pilih_bk_tempat_v8")

                        # STEP 2: Pilih Pusat di bawah Bilik Kebal ini
                        st.markdown(f"#### STEP 2: Pilih Pusat-Pusat Di Bawah Bilik Kebal {pilih_bk_tempat}")
                        st.caption("Contoh: 1 bilik kebal jaga 12 pusat. Pilih semua pusat yang bernaung bawah bilik kebal ini dulu.")
                        if not df_pusat_ppd_list.empty:
                            pilih_pusat_bawah_bk = st.multiselect(f"Pilih Pusat-Pusat Di Bawah {pilih_bk_tempat} (Tick semua pusat di bawah bilik kebal ini)", df_pusat_ppd_list["NO_PUSAT"].tolist() if "NO_PUSAT" in df_pusat_ppd_list.columns else [], format_func=lambda x: f"{x} - {df_pusat_ppd_list[df_pusat_ppd_list['NO_PUSAT']==x]['NAMA_PUSAT'].values[0][:25] if not df_pusat_ppd_list[df_pusat_ppd_list['NO_PUSAT']==x].empty else x}", key="pilih_pusat_bawah_bk_v8")
                            if pilih_pusat_bawah_bk:
                                st.success(f"✅ {len(pilih_pusat_bawah_bk)} pusat dipilih di bawah {pilih_bk_tempat}: {', '.join(pilih_pusat_bawah_bk)}")
                                # Simpan ke session untuk guna di step 3
                                st.session_state[f"pusat_bawah_{pilih_bk_tempat}"] = pilih_pusat_bawah_bk
                        else:
                            pilih_pusat_bawah_bk = []
                            st.warning("Tiada pusat dalam PPD ini")

                        # Load saved pusat if exists
                        saved_pusat_bawah = st.session_state.get(f"pusat_bawah_{pilih_bk_tempat}", pilih_pusat_bawah_bk if 'pilih_pusat_bawah_bk' in locals() else [])

                        if not saved_pusat_bawah:
                            st.warning("⚠️ Sila pilih pusat di bawah bilik kebal dulu di STEP 2")
                            st.stop()

                        st.markdown("---")
                        st.markdown("#### STEP 3: Pilih Penyelia Kawasan & Agihkan Pusat Jagaan")
                        st.caption(f"Pusat yang boleh diagihkan hanya dari senarai yang dipilih untuk {pilih_bk_tempat} tadi ({len(saved_pusat_bawah)} pusat), bukan semua pusat PPD. Agihkan supaya sorang Penyelia tidak pegang semua.")

                        def get_col2(df, *cands):
                            # V29: case-insensitive search
                            cols_lower = {str(c).lower(): c for c in df.columns}
                            for cand in cands:
                                if cand in df.columns:
                                    return cand
                                if cand.lower() in cols_lower:
                                    return cols_lower[cand.lower()]
                            return None

                        c_nama = get_col2(df_penyelia, "NAMA_GURU","nama_guru")
                        c_ic = get_col2(df_penyelia, "IC_GURU","ic_guru")
                        c_sek = get_col2(df_penyelia, "KOD_SEKOLAH_ASAL","kod_sekolah_asal")
                        c_sek_nama = get_col2(df_penyelia, "NAMA_SEKOLAH_ASAL","nama_sekolah_asal")
                        c_tel = get_col2(df_penyelia, "TELEFON_GURU","telefon_guru")
                        c_pusat = get_col2(df_penyelia, "KOD_PUSAT","kod_pusat")

                        cols_disp = [c for c in [c_nama,c_ic,c_sek,c_sek_nama,c_tel,c_pusat] if c]
                        if cols_disp:
                            df_disp = df_penyelia[cols_disp].copy()
                            rename_map = {}
                            if c_nama:
                                rename_map[c_nama] = "NAMA PENYELIA"
                            if c_ic:
                                rename_map[c_ic] = "IC"
                            if c_sek:
                                rename_map[c_sek] = "KOD SEKOLAH ASAL"
                            if c_sek_nama and c_sek_nama != c_sek:
                                rename_map[c_sek_nama] = "NAMA SEKOLAH ASAL"
                            if c_tel:
                                rename_map[c_tel] = "NO TELEFON"
                            if c_pusat:
                                rename_map[c_pusat] = "BILIK KEBAL / PUSAT"
                            df_disp = df_disp.rename(columns=rename_map)
                            st.dataframe(df_disp.head(100), use_container_width=True, hide_index=True)
                        else:
                            st.dataframe(df_penyelia.head(100), use_container_width=True, hide_index=True)

                        id_col = "id" if "id" in df_penyelia.columns else None
                        if id_col:
                            id_list = df_penyelia[id_col].tolist()
                            def format_penyelia(x):
                                try:
                                    row = df_penyelia[df_penyelia[id_col].astype(str) == str(x)]
                                    if row.empty:
                                        row = df_penyelia[df_penyelia[id_col] == x]
                                    if not row.empty:
                                        nama = str(row.iloc[0].get(c_nama,"") if c_nama else "")[:30]
                                        sek = str(row.iloc[0].get(c_sek,"") if c_sek else "")[:15]
                                        tel = str(row.iloc[0].get(c_tel,"") if c_tel else "")[:15]
                                        return f"{nama} | {sek} | {tel} (ID:{x})"
                                    else:
                                        return f"ID:{x}"
                                except:
                                    return f"ID:{x}"

                            pilih_penyelia_bk = st.multiselect("Pilih Penyelia Kawasan (akan keluar nama + sekolah + telefon)", id_list, format_func=format_penyelia, key="pilih_penyelia_bk_v8")

                            if pilih_penyelia_bk:
                                st.markdown(f"##### Agihkan Pusat Jagaan Untuk {len(pilih_penyelia_bk)} Penyelia Terpilih")
                                st.caption(f"Setiap Penyelia hanya boleh pilih pusat dari {len(saved_pusat_bawah)} pusat yang dipilih untuk {pilih_bk_tempat} tadi. Contoh: Penyelia 1 jaga 6 pusat, Penyelia 2 jaga 6 pusat lain.")

                                # For each selected penyelia, show multiselect for pusat jagaan (only from saved list)
                                penyelia_pusat_map = {}
                                for pid in pilih_penyelia_bk:
                                    row = df_penyelia[df_penyelia[id_col].astype(str) == str(pid)]
                                    if row.empty:
                                        row = df_penyelia[df_penyelia[id_col] == pid]
                                    if not row.empty:
                                        nama_peny = str(row.iloc[0].get(c_nama,"") if c_nama else f"ID:{pid}")[:30]
                                        sek_peny = str(row.iloc[0].get(c_sek,"") if c_sek else "")
                                        tel_peny = str(row.iloc[0].get(c_tel,"") if c_tel else "")
                                    else:
                                        nama_peny = f"ID:{pid}"
                                        sek_peny = ""
                                        tel_peny = ""

                                    st.markdown(f"**{nama_peny} - {sek_peny} - {tel_peny}**")
                                    # Multiselect pusat untuk penyelia ini sahaja, option dari saved_pusat_bawah
                                    selected_pusat_for_this = st.multiselect(f"Pilih pusat jagaan untuk {nama_peny} (dari {len(saved_pusat_bawah)} pusat di bawah {pilih_bk_tempat})", saved_pusat_bawah, format_func=lambda x: f"{x} - {df_pusat_ppd_list[df_pusat_ppd_list['NO_PUSAT']==x]['NAMA_PUSAT'].values[0][:25] if not df_pusat_ppd_list[df_pusat_ppd_list['NO_PUSAT']==x].empty else x}", key=f"pusat_untuk_{pid}_v8")
                                    penyelia_pusat_map[pid] = selected_pusat_for_this
                                    if selected_pusat_for_this:
                                        st.caption(f"→ {nama_peny} akan jaga {len(selected_pusat_for_this)} pusat: {', '.join(selected_pusat_for_this)}")
                                    st.markdown("---")

                                # Preview before save
                                if any(penyelia_pusat_map.values()):
                                    st.markdown("**Preview Penempatan (dengan Sekolah Asal & Telefon):**")
                                    preview_rows = []
                                    for pid, pusat_list in penyelia_pusat_map.items():
                                        if not pusat_list:
                                            continue
                                        row = df_penyelia[df_penyelia[id_col].astype(str) == str(pid)]
                                        if not row.empty:
                                            r = row.iloc[0]
                                            preview_rows.append({
                                                "NAMA PENYELIA": r.get(c_nama,"") if c_nama else "",
                                                "IC": r.get(c_ic,"") if c_ic else "",
                                                "SEKOLAH ASAL": r.get(c_sek,"") if c_sek else "",
                                                "NAMA SEKOLAH ASAL": r.get(c_sek_nama,"") if c_sek_nama else "",
                                                "NO TELEFON": r.get(c_tel,"") if c_tel else "",
                                                "BILIK KEBAL": pilih_bk_tempat,
                                                "PUSAT JAGAAN": ", ".join(pusat_list),
                                                "BIL PUSAT": len(pusat_list)
                                            })
                                    if preview_rows:
                                        df_preview = pd.DataFrame(preview_rows)
                                        st.dataframe(df_preview, use_container_width=True, hide_index=True)

                                # Save button
                                if st.button(f"✅ Lantik & Simpan {len(pilih_penyelia_bk)} Penyelia ke {pilih_bk_tempat} dengan Pusat Jagaan", type="primary", use_container_width=True, key="btn_tempat_penyelia_bk_v8"):
                                    try:
                                        for pid, pusat_list in penyelia_pusat_map.items():
                                            if not pusat_list:
                                                continue
                                            pusat_str = ",".join(pusat_list)
                                            existing_row = df_penyelia[df_penyelia[id_col].astype(str) == str(pid)]
                                            existing_data = {}
                                            if not existing_row.empty:
                                                ed = existing_row.iloc[0].get("data")
                                                if isinstance(ed, dict):
                                                    existing_data = ed
                                                elif isinstance(ed, str):
                                                    try:
                                                        existing_data = json.loads(ed)
                                                    except:
                                                        existing_data = {}
                                            existing_data["kod_bilik_kebal"] = pilih_bk_tempat
                                            existing_data["pusat_jagaan"] = pusat_list
                                            existing_data["pusat_jagaan_str"] = pusat_str
                                            existing_data["pusat_bawah_bilik_kebal"] = saved_pusat_bawah

                                            # V33 FIX: kod_bilik_kebal = CB01 (bilik kebal), kod_pusat = pusat jagaan (BA021, BA053) untuk Penyelia Kawasan
                                            pusat_jagaan_str = ",".join(pusat_list) if isinstance(pusat_list, list) else str(pusat_list)
                                            existing_data["kod_bilik_kebal"] = pilih_bk_tempat
                                            existing_data["kod_bilik_kebal_explicit"] = pilih_bk_tempat
                                            existing_data["pusat_jagaan"] = pusat_list
                                            existing_data["pusat_jagaan_str"] = pusat_jagaan_str
                                            existing_data["pusat_bawah_bilik_kebal"] = saved_pusat_bawah

                                            # V33: kod_pusat = pusat jagaan sebenar, kod_bilik_kebal = bilik kebal
                                            # Contoh: kod_bilik_kebal=CB01, kod_pusat=BA021, BA053
                                            payloads_try = [
                                                {"kod_bilik_kebal": pilih_bk_tempat, "kod_pusat": pusat_jagaan_str, "status": "DITEMPATKAN BILIK KEBAL", "data": existing_data},
                                                {"kod_bilik_kebal": pilih_bk_tempat, "kod_pusat": pusat_jagaan_str, "status": "DITEMPATKAN BILIK KEBAL"},
                                                {"kod_bilik_kebal": pilih_bk_tempat, "status": "DITEMPATKAN BILIK KEBAL", "data": existing_data},
                                                {"kod_bilik_kebal": pilih_bk_tempat, "status": "DITEMPATKAN BILIK KEBAL"},
                                                {"kod_pusat": pusat_jagaan_str, "status": "DITEMPATKAN BILIK KEBAL", "data": existing_data},
                                            ]
                                            last_err = None
                                            success = False
                                            for payload in payloads_try:
                                                try:
                                                    supa.table("cadangan_sup").update(payload).eq("id", pid).execute()
                                                    success = True
                                                    break
                                                except Exception as e:
                                                    last_err = e
                                                    continue
                                            if not success and last_err:
                                                raise last_err
                                        st.success(f"✅ {len([v for v in penyelia_pusat_map.values() if v])} Penyelia berjaya ditempatkan ke {pilih_bk_tempat}")
                                        st.balloons()
                                        st.rerun()
                                    except Exception as e:
                                        st.error("Maaf, berlaku masalah semasa memproses. Sila cuba lagi.")
                            else:
                                st.info("Pilih Penyelia Kawasan di atas")
                        else:
                            st.warning("Tiada id column")

                    st.markdown("---")
                    st.markdown("### 📊 Ringkasan Penempatan Penyelia ke Bilik Kebal (Column Berasingan Ikut Bilangan Penyelia)")
                    st.caption("Setiap Penyelia ada column sendiri: NAMA, IC, SEKOLAH ASAL, TELEFON, PUSAT JAGAAN. Kalau ada 2 penyelia, akan ada 2 set column. Kalau 6, akan ada 6 set.")
                    # V27 FIX: Ringkasan penempatan - 1 baris per Penyelia, bukan semua dalam 1 baris
                    ringkas_bk = []
                    df_cad_all_bk2 = get_cadangan_df(kod_ppd=kod_ppd)
                    for _, bk_row in df_bk.iterrows():
                        kod_bk_r = bk_row.get("kod_bilik_kebal","") or bk_row.get("KOD_BILIK_KEBAL","")
                        nama_bk_r = str(bk_row.get("nama_bilik_kebal",""))[:30]
                        alamat_bk_r = str(bk_row.get("alamat",""))[:40]
                        penyelia_assigned = []
                        if not df_cad_all_bk2.empty:
                            for _, c in df_cad_all_bk2.iterrows():
                                p = str(c.get("kod_bilik_kebal") or c.get("kod_pusat") or c.get("KOD_PUSAT") or c.get("KOD_BILIK_KEBAL") or "").upper()
                                if p == kod_bk_r.upper():
                                    jaw = str(c.get("JAWATAN_CADANGAN") or c.get("jawatan_cadangan") or "").upper()
                                    if "PENYELIA" in jaw:
                                        nama_g = str(c.get("NAMA_GURU") or c.get("nama_guru") or "")
                                        ic_g = str(c.get("IC_GURU") or c.get("ic_guru") or "")
                                        sek_g = str(c.get("KOD_SEKOLAH_ASAL") or c.get("kod_sekolah_asal") or "")
                                        sek_nama_g = str(c.get("NAMA_SEKOLAH_ASAL") or c.get("nama_sekolah_asal") or "")[:30]
                                        tel_g = str(c.get("TELEFON_GURU") or c.get("telefon_guru") or "")
                                        d = c.get("data") if isinstance(c.get("data"), dict) else {}
                                        if isinstance(d, str):
                                            try:
                                                d = json.loads(d)
                                            except:
                                                d = {}
                                        # V34 FIX: Baca pusat jagaan dari data JSON, fallback ke kod_pusat jika data kosong
                                        pusat_j = d.get("pusat_jagaan_str") or d.get("pusat_jagaan") or ""
                                        if isinstance(pusat_j, list):
                                            pusat_j = ",".join(pusat_j)
                                        # Jika pusat_j masih kosong, cuba baca dari kod_pusat column (untuk data baru V33)
                                        if not pusat_j or pusat_j == "-" or pusat_j.strip() == "":
                                            raw_kod_pusat = str(c.get("kod_pusat") or c.get("KOD_PUSAT") or "").strip()
                                            # Jika kod_pusat bukan bilik kebal (CB, BK, BILIK), anggap itu pusat jagaan
                                            if raw_kod_pusat and not any(x in raw_kod_pusat.upper() for x in ["CB", "BK-", "BILIK"]) or "," in raw_kod_pusat:
                                                pusat_j = raw_kod_pusat
                                            # Jika kod_pusat adalah CB01 tapi data ada pusat_bawah, guna pusat_bawah sebagai fallback lama
                                            elif not pusat_j:
                                                pusat_j = d.get("pusat_bawah_bilik_kebal") or ""
                                                if isinstance(pusat_j, list):
                                                    pusat_j = ",".join(pusat_j)

                                        pusat_bawah = d.get("pusat_bawah_bilik_kebal") or d.get("pusat_bawah") or ""
                                        if isinstance(pusat_bawah, list):
                                            pusat_bawah = ",".join(pusat_bawah)
                                        # Jika pusat_bawah kosong, fallback ke semua pusat bawah bilik kebal dari kod_bilik_kebal
                                        if not pusat_bawah:
                                            pusat_bawah = d.get("kod_bilik_kebal") or c.get("kod_bilik_kebal") or ""
                                        penyelia_assigned.append({
                                            "nama": nama_g,
                                            "ic": ic_g,
                                            "sekolah": sek_g,
                                            "sekolah_nama": sek_nama_g,
                                            "telefon": tel_g,
                                            "pusat_jagaan": pusat_j,
                                            "pusat_bawah": pusat_bawah,
                                            "id": c.get("id")
                                        })

                        # V27: Buat 1 baris per penyelia, bukan gabung dalam 1 baris
                        if penyelia_assigned:
                            for idx, pen in enumerate(penyelia_assigned, 1):
                                row_dict = {
                                    "BIL": idx,
                                    "KOD BILIK KEBAL": kod_bk_r,
                                    "NAMA BILIK KEBAL": nama_bk_r,
                                    "ALAMAT": alamat_bk_r,
                                    "PENYELIA KE": f"{idx} dari {len(penyelia_assigned)}",
                                    "NAMA PENYELIA": pen["nama"],
                                    "IC PENYELIA": pen["ic"],
                                    "SEKOLAH ASAL": pen["sekolah"],
                                    "NAMA SEK ASAL": pen["sekolah_nama"],
                                    "TELEFON": pen["telefon"],
                                    "PUSAT JAGAAN (Di bawah Penyelia Ini)": pen["pusat_jagaan"],
                                    "SEMUA PUSAT DI BAWAH BILIK KEBAL": pen["pusat_bawah"],
                                    "BIL PUSAT JAGAAN": len(pen["pusat_jagaan"].split(",")) if pen["pusat_jagaan"] and pen["pusat_jagaan"] != "-" else 0,
                                    "ID": pen["id"]
                                }
                                ringkas_bk.append(row_dict)
                        else:
                            # Jika kosong, buat 1 baris kosong
                            ringkas_bk.append({
                                "BIL": 0,
                                "KOD BILIK KEBAL": kod_bk_r,
                                "NAMA BILIK KEBAL": nama_bk_r,
                                "ALAMAT": alamat_bk_r,
                                "PENYELIA KE": "0",
                                "NAMA PENYELIA": "-",
                                "IC PENYELIA": "-",
                                "SEKOLAH ASAL": "-",
                                "NAMA SEK ASAL": "-",
                                "TELEFON": "-",
                                "PUSAT JAGAAN (Di bawah Penyelia Ini)": "-",
                                "SEMUA PUSAT DI BAWAH BILIK KEBAL": "-",
                                "BIL PUSAT JAGAAN": 0,
                                "ID": "-"
                            })

                    if ringkas_bk:
                        df_ringkas_bk = pd.DataFrame(ringkas_bk)
                        df_ringkas_bk = df_ringkas_bk.fillna("-")
                        # Sort by bilik kebal then penyelia ke
                        try:
                            df_ringkas_bk = df_ringkas_bk.sort_values(by=["KOD BILIK KEBAL", "BIL"])
                        except:
                            pass
                        st.dataframe(df_ringkas_bk, use_container_width=True, hide_index=True)
                        # Highlight if more than 1 penyelia per bilik kebal
                        try:
                            bil_bk_counts = df_ringkas_bk[df_ringkas_bk["NAMA PENYELIA"] != "-"].groupby("KOD BILIK KEBAL").size()
                            for bk_code, cnt in bil_bk_counts.items():
                                if cnt > 1:
                                    st.info(f"📌 Bilik Kebal {bk_code} ada {cnt} Penyelia Kawasan - setiap penyelia ada baris sendiri di atas")
                        except:
                            pass
                        st.download_button("📥 Export Ringkasan Bilik Kebal (1 Baris = 1 Penyelia)", to_excel(df_ringkas_bk), file_name=f"ringkasan_bilik_kebal_{kod_ppd}_1baris_1penyelia_{datetime.date.today()}.xlsx", use_container_width=True)
                    else:
                        st.info("Belum ada ringkasan")

                    st.markdown("---")
                    st.markdown("### 🗑️ Batal Penempatan Penyelia Kawasan")
                    st.caption("Pilih bilik kebal, kemudian batalkan penempatan penyelia di bilik kebal tersebut. Data akan kembali ke status DICADANGKAN dan pusat jagaan akan dipadam.")
                    if not df_bk.empty:
                        pilih_bk_batal = st.selectbox("Pilih Bilik Kebal untuk Batal Penempatan", df_bk["kod_bilik_kebal"].tolist() if "kod_bilik_kebal" in df_bk.columns else [], key="pilih_bk_batal_v8")
                        if st.button(f"🗑️ Batal Semua Penempatan Penyelia di {pilih_bk_batal}", type="secondary", use_container_width=True, key="btn_batal_penyelia"):
                            try:
                                df_cad_batal = get_cadangan_df(kod_ppd=kod_ppd)
                                count_batal = 0
                                for _, c in df_cad_batal.iterrows():
                                    p = str(c.get("kod_bilik_kebal") or c.get("kod_pusat") or c.get("KOD_PUSAT") or c.get("KOD_BILIK_KEBAL") or "").upper()
                                    if p == pilih_bk_batal.upper():
                                        jaw = str(c.get("JAWATAN_CADANGAN") or c.get("jawatan_cadangan") or "").upper()
                                        if "PENYELIA" in jaw:
                                            # Reset balik ke pool cadangan - kosongkan bilik kebal & pusat jagaan
                                            supa.table("cadangan_sup").update({"kod_pusat": None, "status": "DICADANGKAN SEMULA - BATAL BILIK KEBAL", "no_surat": None, "data": {}}).eq("id", c.get("id")).execute()
                                            count_batal += 1
                                st.success(f"✅ {count_batal} penempatan di {pilih_bk_batal} telah dibatalkan. Cadangan kembali ke PPD > Cadangan SUP & SUP > Cadangan Lantikan dengan status DICADANGKAN")
                                # Clear session pusat bawah
                                if f"pusat_bawah_{pilih_bk_batal}" in st.session_state:
                                    del st.session_state[f"pusat_bawah_{pilih_bk_batal}"]
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error batal: {e}")

                        # Batal individu
                        st.markdown("**Batal Individu Penyelia:**")
                        df_cad_batal_ind = get_cadangan_df(kod_ppd=kod_ppd)
                        df_batal_list = []
                        for _, c in df_cad_batal_ind.iterrows():
                            p = str(c.get("kod_bilik_kebal") or c.get("kod_pusat") or c.get("KOD_PUSAT") or c.get("KOD_BILIK_KEBAL") or "").upper()
                            if p == pilih_bk_batal.upper():
                                jaw = str(c.get("JAWATAN_CADANGAN") or c.get("jawatan_cadangan") or "").upper()
                                if "PENYELIA" in jaw:
                                    df_batal_list.append(c)
                        if df_batal_list:
                            df_batal_df = pd.DataFrame(df_batal_list)
                            id_col_batal = "id" if "id" in df_batal_df.columns else None
                            if id_col_batal:
                                def fmt_batal(x):
                                    row = df_batal_df[df_batal_df[id_col_batal].astype(str)==str(x)]
                                    if not row.empty:
                                        return f"{row.iloc[0].get('NAMA_GURU','')} - {row.iloc[0].get('KOD_SEKOLAH_ASAL','')}"
                                    return str(x)
                                pilih_batal_ind = st.multiselect("Pilih Penyelia untuk Batal", df_batal_df[id_col_batal].tolist(), format_func=fmt_batal, key="batal_ind_v8")
                                if pilih_batal_ind and st.button(f"🗑️ Batal {len(pilih_batal_ind)} Penyelia Terpilih", use_container_width=True, key="btn_batal_ind"):
                                    try:
                                        for pid in pilih_batal_ind:
                                            supa.table("cadangan_sup").update({"kod_pusat": None, "status": "DICADANGKAN SEMULA - BATAL BILIK KEBAL", "no_surat": None, "data": {}}).eq("id", pid).execute()
                                        st.success(f"✅ Berjaya batal {len(pilih_batal_ind)} penyelia. Mereka kembali ke pool cadangan - boleh lihat di PPD > Cadangan SUP")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(str(e))
                            else:
                                st.info("Tiada penyelia untuk dibatalkan di bilik kebal ini")
                        else:
                            st.info(f"Tiada penyelia ditempatkan di {pilih_bk_batal}")




            if fly_cur == "surat":
                st.markdown(f"### 📄 Jana Surat Lantikan Penyelia Kawasan - PPD {kod_ppd}")
                st.caption("Surat akan dijana dengan Nama, IC, Sekolah Asal, Bilik Kebal, Pusat Jagaan. Boleh download HTML dan hantar ke sekolah asal. SUP akan nampak di Petugas di Sekolah Saya.")

                # Load bilik kebal and penyelia assigned
                df_cad_all_surat = get_cadangan_df(kod_ppd=kod_ppd)
                if df_cad_all_surat.empty:
                    st.warning("Belum ada cadangan")
                else:
                    # Filter penyelia yang sudah ditempatkan di bilik kebal
                    df_surat = []
                    seen_ids_surat = set()
                    for _, c in df_cad_all_surat.iterrows():
                        p = str(c.get("kod_bilik_kebal") or c.get("kod_pusat") or c.get("KOD_PUSAT") or c.get("KOD_BILIK_KEBAL") or "").upper()
                        jaw = str(c.get("JAWATAN_CADANGAN") or c.get("jawatan_cadangan") or "").upper()
                        c_id = str(c.get("id") or c.get("IC_GURU") or c.get("ic_guru") or "") + "_" + str(c.get("KOD_SEKOLAH_ASAL") or "")
                        # Check if already added
                        if c_id in seen_ids_surat:
                            continue
                        if "PENYELIA" in jaw and p:
                            # Check if p is bilik kebal
                            is_bk = False
                            try:
                                for _, bk in df_bk.iterrows():
                                    if str(bk.get("kod_bilik_kebal","")).upper() == p:
                                        is_bk = True
                                        break
                            except:
                                pass
                            if is_bk or "BK-" in p or "CB" in p or p.startswith(kod_ppd+"-BK") or "BILIK" in p:
                                df_surat.append(c)
                                seen_ids_surat.add(c_id)
                                continue
                        # Also include if status DITEMPATKAN BILIK KEBAL
                        if str(c.get("status") or c.get("STATUS") or "").upper() == "DITEMPATKAN BILIK KEBAL":
                            if c_id not in seen_ids_surat:
                                df_surat.append(c)
                                seen_ids_surat.add(c_id)

                    df_surat = pd.DataFrame(df_surat) if df_surat else pd.DataFrame()

                    if df_surat.empty:
                        st.info("Belum ada Penyelia Kawasan yang ditempatkan ke Bilik Kebal. Sila tempatkan dulu di tab Tempatkan Penyelia Kawasan.")
                    else:
                        st.success(f"Ada {len(df_surat)} Penyelia Kawasan telah ditempatkan ke Bilik Kebal dan sedia untuk jana surat")

                        # Select penyelia to generate surat
                        def get_col_s(df, *cands):
                            for cand in cands:
                                if cand in df.columns:
                                    return cand
                            return None

                        c_nama_s = get_col_s(df_surat, "NAMA_GURU","nama_guru")
                        c_ic_s = get_col_s(df_surat, "IC_GURU","ic_guru")
                        c_sek_s = get_col_s(df_surat, "KOD_SEKOLAH_ASAL","kod_sekolah_asal")
                        c_sek_nama_s = get_col_s(df_surat, "NAMA_SEKOLAH_ASAL","nama_sekolah_asal")
                        c_tel_s = get_col_s(df_surat, "TELEFON_GURU","telefon_guru","TELEFON","telefon")
                        c_pusat_s = get_col_s(df_surat, "KOD_PUSAT","kod_pusat")
                        c_id_s = "id" if "id" in df_surat.columns else None

                        # Display
                        cols_s = [c for c in [c_nama_s,c_ic_s,c_sek_s,c_sek_nama_s,c_tel_s,c_pusat_s] if c]
                        if cols_s:
                            st.dataframe(df_surat[cols_s].head(50), use_container_width=True, hide_index=True)

                        # Pilih penyelia
                        if c_id_s:
                            id_list_s = df_surat[c_id_s].tolist()
                            def fmt_surat(x):
                                row = df_surat[df_surat[c_id_s].astype(str)==str(x)]
                                if row.empty:
                                    row = df_surat[df_surat[c_id_s]==x]
                                if not row.empty:
                                    nama = str(row.iloc[0].get(c_nama_s,"") if c_nama_s else "")[:25]
                                    bk = str(row.iloc[0].get(c_pusat_s,"") if c_pusat_s else "")[:15]
                                    return f"{nama} - {bk} (ID:{x})"
                                return f"ID:{x}"

                            pilih_surat = st.multiselect("Pilih Penyelia Kawasan untuk Jana Surat", id_list_s, format_func=fmt_surat, key="pilih_surat_penyelia")

                            # No surat settings - FIX: Ikut no berturutan daerah (sama seperti petugas lain)
                            st.markdown("#### 🔢 No Surat Berturutan Ikut Daerah (Sama seperti petugas lain)")
                            try:
                                # Get max no surat sedia ada di daerah ini dari semua petugas (termasuk KP, TKP, Pengawas)
                                max_no_global = 0
                                try:
                                    df_all_cad_for_no = get_cadangan_df(kod_ppd=kod_ppd)
                                    if not df_all_cad_for_no.empty:
                                        for _, rc in df_all_cad_for_no.iterrows():
                                            ns = str(rc.get("no_surat") or "").strip()
                                            if ns:
                                                # Extract last number from format like JPN.SEL/PPD.BA/SPM/2026/0028 or PPD.BA/SPM/PK/2026/0001
                                                try:
                                                    parts = ns.split("/")
                                                    last_part = parts[-1].strip()
                                                    num = int(''.join(filter(str.isdigit, last_part)))
                                                    if num > max_no_global:
                                                        max_no_global = num
                                                except:
                                                    pass
                                except:
                                    max_no_global = 0
                                st.info(f"📌 No Surat terakhir di PPD {kod_ppd} (semua petugas): {max_no_global} - Surat Penyelia baru akan mula dari {max_no_global+1} berturutan")
                            except:
                                max_no_global = 0

                            col_no1, col_no2, col_no3 = st.columns(3)
                            with col_no1:
                                # Default prefix ikut format standard daerah - sama seperti petugas lain
                                default_prefix = f"JPN.SEL/PPD.{kod_ppd}/SPM/{tahun_aktif()}/"
                                prefix_surat = st.text_input("Prefix No Surat (ikut format daerah)", value=default_prefix, key="prefix_surat_pk", help="No surat Penyelia akan ikut format yang sama seperti petugas lain di daerah ini, cuma berturutan")
                            with col_no2:
                                no_mula_auto = max_no_global + 1
                                no_mula = st.number_input("No Mula (auto ikut daerah)", min_value=1, value=no_mula_auto, key="no_mula_pk", help=f"Auto dikira dari max sedia ada di daerah {kod_ppd} - jika petugas lain sudah ada no 1-100, Penyelia akan mula 101")
                            with col_no3:
                                tarikh_surat = st.date_input("Tarikh Surat", value=datetime.date.today(), key="tarikh_surat_pk")

                            if pilih_surat and st.button(f"📄 Jana {len(pilih_surat)} Surat Penyelia Kawasan (No Berturutan Daerah {kod_ppd})", type="primary", use_container_width=True, key="btn_jana_surat_pk"):
                                try:
                                    tarikh_str = tarikh_surat.strftime("%d %B %Y")
                                    surat_html_all = ""
                                    surat_list_data = []
                                    current_no = no_mula

                                    for pid in pilih_surat:
                                        row = df_surat[df_surat[c_id_s].astype(str)==str(pid)]
                                        if row.empty:
                                            row = df_surat[df_surat[c_id_s]==pid]
                                        if row.empty:
                                            continue
                                        r = row.iloc[0]
                                        nama = str(r.get(c_nama_s,"") if c_nama_s else "")
                                        ic = str(r.get(c_ic_s,"") if c_ic_s else "")
                                        sek = str(r.get(c_sek_s,"") if c_sek_s else "")
                                        nama_sek = str(r.get(c_sek_nama_s,"") if c_sek_nama_s else sek)
                                        tel = str(r.get(c_tel_s,"") if c_tel_s else "")
                                        # V35 FIX: kod_bk dari column kod_bilik_kebal, bukan kod_pusat
                                        kod_bk = str(r.get("kod_bilik_kebal") or r.get("KOD_BILIK_KEBAL") or r.get(c_pusat_s,"") if c_pusat_s else "").strip()
                                        # Jika kod_bk masih nampak macam pusat jagaan (BA021), cuba cari dalam data
                                        d = r.get("data") if isinstance(r.get("data"), dict) else {}
                                        if isinstance(d, str):
                                            try:
                                                d = json.loads(d)
                                            except:
                                                d = {}
                                        # Jika kod_bk adalah BA... bukan CB/BK, ambil dari data
                                        if kod_bk and not any(x in kod_bk.upper() for x in ["CB", "BK-", "BK", "BILIK"]) or "," in kod_bk:
                                            # kod_bk sekarang sebenarnya pusat jagaan, jadi cari bilik kebal sebenar dalam data
                                            real_bk = d.get("kod_bilik_kebal") or d.get("kod_bilik_kebal_explicit") or ""
                                            if real_bk:
                                                kod_bk = str(real_bk).strip()

                                        # V36 FIX: CB01 SMK RAJA ZARINA - ensure lookup works
                                        bk_row = pd.DataFrame()
                                        if not df_bk.empty and "kod_bilik_kebal" in df_bk.columns:
                                            try:
                                                mask = df_bk["kod_bilik_kebal"].astype(str).str.upper().str.strip() == kod_bk.upper().strip()
                                                bk_row = df_bk[mask]
                                            except:
                                                pass
                                        if not bk_row.empty:
                                            nama_bk = str(bk_row.iloc[0].get("nama_bilik_kebal","")).strip()
                                            alamat_bk = str(bk_row.iloc[0].get("alamat","")).strip()
                                            # If CB01 should be SMK RAJA ZARINA, ensure name
                                            if kod_bk.upper() == "CB01" and "RAJA ZARINA" not in nama_bk.upper():
                                                # Keep existing name but note CB01 is SMK RAJA ZARINA
                                                if not nama_bk or nama_bk == kod_bk:
                                                    nama_bk = "SMK RAJA ZARINA - BILIK KEBAL CB01"
                                        else:
                                            # Fallback: Try from data JSON or hardcode CB01
                                            nama_bk = str(d.get("nama_bilik_kebal","") or d.get("nama_bk","") or "").strip()
                                            alamat_bk = str(d.get("alamat_bilik_kebal","") or d.get("alamat","") or "").strip()
                                            if not nama_bk or nama_bk == kod_bk:
                                                if kod_bk.upper() == "CB01":
                                                    nama_bk = "SMK RAJA ZARINA"
                                                    alamat_bk = alamat_bk or "SMK RAJA ZARINA, KLANG"
                                                else:
                                                    nama_bk = kod_bk
                                            # If still CB01, ensure SMK RAJA ZARINA
                                            if kod_bk.upper() == "CB01" and "RAJA ZARINA" not in nama_bk.upper():
                                                if len(nama_bk) < 5:
                                                    nama_bk = "SMK RAJA ZARINA"

                                        # V35 FIX: Get pusat jagaan - dari kod_pusat ATAU data JSON
                                        pusat_jagaan = d.get("pusat_jagaan") or d.get("pusat_jagaan_str") or []
                                        if not pusat_jagaan:
                                            # Fallback: kod_pusat sekarang adalah pusat jagaan (BA021, BA053) untuk V33+
                                            raw_kod_pusat = str(r.get("kod_pusat") or r.get("KOD_PUSAT") or r.get(c_pusat_s,"") if c_pusat_s else "").strip()
                                            if raw_kod_pusat and raw_kod_pusat.upper() != kod_bk.upper():
                                                pusat_jagaan = raw_kod_pusat
                                        if isinstance(pusat_jagaan, str):
                                            pusat_jagaan = [p.strip() for p in pusat_jagaan.split(",") if p.strip()]
                                        if not isinstance(pusat_jagaan, list):
                                            pusat_jagaan = [str(pusat_jagaan)] if pusat_jagaan else []

                                        no_surat = f"{prefix_surat}{current_no:04d}"
                                        current_no += 1

                                        html_surat = generate_surat_penyelia_kawasan_html(
                                            nama=nama,
                                            ic=ic,
                                            sek_asal=sek,
                                            nama_sek_asal=nama_sek,
                                            telefon=tel,
                                            kod_bilik_kebal=kod_bk,
                                            nama_bilik_kebal=nama_bk,
                                            alamat_bilik_kebal=alamat_bk,
                                            pusat_jagaan_list=pusat_jagaan,
                                            no_surat=no_surat,
                                            kod_ppd=kod_ppd,
                                            ppd_name=PPD_MAP.get(kod_ppd,""),
                                            tarikh=tarikh_str
                                        )
                                        surat_html_all += html_surat + "\n"
                                        surat_list_data.append({
                                            "id": pid,
                                            "nama": nama,
                                            "ic": ic,
                                            "sekolah_asal": sek,
                                            "bilik_kebal": kod_bk,
                                            "nama_bilik_kebal": nama_bk,
                                            "pusat_jagaan": pusat_jagaan,
                                            "no_surat": no_surat,
                                            "html": html_surat
                                        })

                                    # Generate PDF bytes untuk setiap surat juga (untuk download PDF & hantar ke sekolah asal)
                                    for s_data in surat_list_data:
                                        try:
                                            # Generate PDF untuk surat ini
                                            pdf_bytes_ind = None
                                            try:
                                                pdf_bytes_ind = generate_surat_pdf_bytes(
                                                    s_data["nama"], s_data["ic"], "Penyelia Kawasan",
                                                    s_data["sekolah_asal"], "", s_data["bilik_kebal"], s_data.get("nama_bilik_kebal",""),
                                                    s_data["no_surat"], kod_ppd, PPD_MAP.get(kod_ppd,""),
                                                    tarikh_str, s_data["no_surat"]
                                                )
                                            except:
                                                # Fallback to HTML as PDF bytes
                                                pdf_bytes_ind = s_data.get("html","").encode('utf-8')
                                            s_data["pdf_bytes"] = pdf_bytes_ind
                                        except:
                                            s_data["pdf_bytes"] = None

                                    # Save to session for download and hantar
                                    st.session_state[f"surat_pk_html_{kod_ppd}"] = surat_html_all
                                    st.session_state[f"surat_pk_list_{kod_ppd}"] = surat_list_data

                                    st.success(f"✅ Berjaya jana {len(surat_list_data)} surat Penyelia Kawasan - No Surat {no_mula} hingga {current_no-1} (bertuturan daerah {kod_ppd} ikut petugas lain)")
                                    st.balloons()
                                    st.components.v1.html(surat_html_all[:10000], height=600, scrolling=True)

                                    # Auto generate ZIP PDF individu untuk Penyelia
                                    try:
                                        import io, zipfile
                                        zip_buffer = io.BytesIO()
                                        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                                            for s_data in surat_list_data:
                                                if s_data.get("pdf_bytes"):
                                                    safe_nama = "".join(c if c.isalnum() else "_" for c in s_data["nama"])[:20]
                                                    fname = f"{s_data['no_surat'].replace('/','_')}_{safe_nama}_Penyelia_{s_data['bilik_kebal']}.pdf"
                                                    zf.writestr(fname, s_data["pdf_bytes"])
                                        zip_bytes = zip_buffer.getvalue()
                                        st.session_state[f"surat_pk_zip_{kod_ppd}"] = zip_bytes
                                    except Exception as e:
                                        st.caption(f"ZIP error: {e}")

                                except Exception as e:
                                    st.error(f"Error jana surat: {e}")

                            # Show generated surat if exists
                            if f"surat_pk_html_{kod_ppd}" in st.session_state:
                                st.markdown("---")
                                st.markdown("### 📄 Surat Telah Dijana")
                                html_all = st.session_state[f"surat_pk_html_{kod_ppd}"]
                                list_data = st.session_state.get(f"surat_pk_list_{kod_ppd}", [])

                                st.components.v1.html(html_all[:12000], height=700, scrolling=True)

                                col_dl1, col_dl2, col_dl3, col_dl4 = st.columns(4)
                                with col_dl1:
                                    st.download_button("📥 Download Semua Surat (HTML)", data=html_all.encode('utf-8'), file_name=f"Surat_Penyelia_Kawasan_{kod_ppd}_{datetime.date.today()}.html", mime="text/html", use_container_width=True, key="dl_all_surat_pk")
                                with col_dl2:
                                    # Excel list
                                    df_dl = pd.DataFrame([{"NAMA": s["nama"], "IC": s["ic"], "SEKOLAH ASAL": s["sekolah_asal"], "BILIK KEBAL": s["bilik_kebal"], "NO SURAT": s["no_surat"]} for s in list_data])
                                    st.download_button("📥 Download Senarai (Excel)", to_excel(df_dl), file_name=f"Senarai_Surat_PK_{kod_ppd}.xlsx", use_container_width=True, key="dl_excel_pk")
                                with col_dl3:
                                    # PDF individu ZIP
                                    if f"surat_pk_zip_{kod_ppd}" in st.session_state:
                                        st.download_button("📥 Download ZIP PDF Individu (Penyelia)", data=st.session_state[f"surat_pk_zip_{kod_ppd}"], file_name=f"Surat_Penyelia_Kawasan_{kod_ppd}_Individu_{datetime.date.today()}.zip", mime="application/zip", use_container_width=True, key="dl_zip_pk")
                                    else:
                                        st.caption("Jana semula untuk dapat ZIP PDF")
                                with col_dl4:
                                    if st.button(f"📤 Hantar Surat ke Sekolah Asal + PDF (SUP boleh download)", type="primary", use_container_width=True, key="btn_hantar_surat_pk"):
                                        try:
                                            berjaya = 0
                                            for s in list_data:
                                                try:
                                                    # Simpan surat_html + pdf info ke data json untuk sekolah asal
                                                    existing = supa.table("cadangan_sup").select("data").eq("id", s["id"]).limit(1).execute()
                                                    old_data = {}
                                                    if existing.data:
                                                        old_data = existing.data[0].get("data") or {}
                                                        if isinstance(old_data, str):
                                                            try:
                                                                import json
                                                                old_data = json.loads(old_data)
                                                            except:
                                                                old_data = {}
                                                    old_data.update({
                                                        "surat_html": s.get("html",""),
                                                        "surat_tarikh": str(datetime.date.today()),
                                                        "surat_no": s["no_surat"],
                                                        "SURAT_DIHANTAR_KE_SEKOLAH_ASAL": True,
                                                        "jenis": "Penyelia Kawasan",
                                                        "bilik_kebal": s.get("bilik_kebal",""),
                                                        "pusat_jagaan": s.get("pusat_jagaan", [])
                                                    })
                                                    supa.table("cadangan_sup").update({"status": "LULUS PPD - SURAT PK DIHANTAR KE SEKOLAH ASAL", "no_surat": s["no_surat"], "data": old_data}).eq("id", s["id"]).execute()
                                                except:
                                                    # Fallback simple
                                                    supa.table("cadangan_sup").update({"status": "SURAT PK DIHANTAR", "no_surat": s["no_surat"]}).eq("id", s["id"]).execute()
                                                berjaya += 1
                                            st.success(f"✅ {berjaya} surat Penyelia Kawasan (No {list_data[0]['no_surat']} hingga {list_data[-1]['no_surat']}) telah DIHANTAR ke sekolah asal! SUP boleh lihat & download PDF di menu Surat Lantikan Saya")
                                            st.balloons()
                                            st.info(f"📄 Surat telah dihantar ke sekolah asal guru - No surat ikut berturutan daerah {kod_ppd} (sama seperti petugas lain). SUP boleh cetak PDF di Surat Lantikan Saya")
                                        except Exception as e:
                                            st.error(f"Error hantar: {e}")


        elif menu == "jana_surat":
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #0d47a1 0%, #1976d2 100%); padding:20px; border-radius:12px; color:white; margin-bottom:20px;">
                <h2 style="margin:0; color:white;">📄 Janaan Surat Lantikan - PPD {kod_ppd} - {PPD_MAP.get(kod_ppd,'')}</h2>
                <p style="margin:5px 0 0 0; color:#bbdefb;">Surat yang telah diluluskan PPD - PPD boleh lihat, jana semula & download PDF. Surat yang sama juga dihantar ke sekolah asal guru untuk SUP cetak.</p>
            </div>
            """, unsafe_allow_html=True)

            df_cad_all_surat = get_cadangan_df(kod_ppd=kod_ppd)
            if df_cad_all_surat.empty:
                st.warning("Belum ada cadangan di PPD ini")
                st.stop()

            # Build pusat map
            df_pusat_raw_surat = get_pusat_df()
            pusat_map_surat = {}
            try:
                for _, r in df_pusat_raw_surat.iterrows():
                    d = r.get("data") if isinstance(r.get("data"), dict) else {}
                    if isinstance(d, str):
                        try: d = json.loads(d)
                        except: d = {}
                    no_p = str(r.get("no_pusat") or r.get("kod_pusat") or d.get("NO_PUSAT") or "").upper().strip()
                    nama_p = r.get("nama_pusat") or d.get("NAMA_PUSAT") or ""
                    if no_p:
                        pusat_map_surat[no_p] = nama_p
            except:
                pass

            # Filter yang ada no_surat / sudah LULUS
            def has_surat_ppd(row):
                ns = str(row.get("no_surat") or "").strip()
                stt = str(row.get("status") or "").upper()
                return (ns != "" and ns.lower() not in ("none","null","nan")) or ("LULUS" in stt)

            df_lulus_surat = df_cad_all_surat[df_cad_all_surat.apply(has_surat_ppd, axis=1)].copy() if not df_cad_all_surat.empty else pd.DataFrame()
            df_belum_surat = df_cad_all_surat[~df_cad_all_surat.apply(has_surat_ppd, axis=1)].copy() if not df_cad_all_surat.empty else pd.DataFrame()

            def papar_belum_surat_ppd(df_belum, pusat_map):
                """Senarai nama guru yang belum ada surat. Hanya dipanggil jika ada yang belum."""
                st.markdown(f"#### ⏳ Senarai Guru Belum Ada Surat ({len(df_belum)} orang)")
                rows_b = []
                for i_b, (_, r) in enumerate(df_belum.iterrows(), start=1):
                    kp = str(r.get("kod_pusat", "") or r.get("KOD_PUSAT", "") or "").strip()
                    if kp.lower() in ("none", "null", "nan"):
                        kp = ""
                    rows_b.append({
                        "BIL": i_b,
                        "NAMA GURU": r.get("NAMA_GURU", "") or r.get("nama_guru", ""),
                        "IC": r.get("IC_GURU", "") or r.get("ic_guru", ""),
                        "JAWATAN": r.get("JAWATAN_CADANGAN", "") or r.get("jawatan_cadangan", ""),
                        "SEKOLAH ASAL": r.get("KOD_SEKOLAH_ASAL", "") or r.get("kod_sekolah_asal", ""),
                        "PUSAT TUGAS": kp or "-",
                        "NAMA PUSAT": str(pusat_map.get(kp.upper(), ""))[:30] if kp else "",
                        "STATUS": r.get("status", "") or r.get("STATUS", ""),
                        "SEBAB": "Belum ditempatkan ke pusat" if not kp else "Belum diluluskan (menu Kelulusan)",
                    })
                df_b_show = pd.DataFrame(rows_b)
                st.dataframe(df_b_show, use_container_width=True, hide_index=True, height=min(420, 38 + 35 * len(df_b_show)))
                st.download_button("📥 Export Senarai Belum Ada Surat (Excel)", to_excel(df_b_show),
                                   file_name=f"belum_ada_surat_{kod_ppd}_{datetime.date.today()}.xlsx",
                                   key="dl_belum_ada_surat_ppd")

            if df_belum_surat.empty:
                # Tiada yang belum ada surat -> kotak "Belum Ada Surat" tidak dipaparkan
                c1, c2 = st.columns(2)
                c1.metric("Total Cadangan PPD", len(df_cad_all_surat))
                c2.metric("✅ Sudah Lulus Ada Surat", len(df_lulus_surat))
            else:
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Cadangan PPD", len(df_cad_all_surat))
                c2.metric("✅ Sudah Lulus Ada Surat", len(df_lulus_surat))
                c3.metric("⏳ Belum Ada Surat", len(df_belum_surat))
                papar_belum_surat_ppd(df_belum_surat, pusat_map_surat)

            if df_lulus_surat.empty:
                st.warning("Belum ada surat yang diluluskan di PPD ini - sila luluskan di menu Kelulusan dahulu")
                st.info("Pergi ke Kelulusan > Lulus Keseluruhan atau Lulus Mengikut Pusat untuk luluskan dan jana surat")
                st.stop()

            # Tabs for view
            # [FLYOUT] st.tabs diganti sub menu flyout

            if fly_cur == "keseluruhan":
                st.markdown(f"### 📄 Semua Surat Lantikan PPD {kod_ppd} - {len(df_lulus_surat)} Surat - Template JPN Selaras")
                st.info(f"🔹 Template surat diambil dari function JPN `surat_templates_jpn` - JPN cipta, PPD guna. Jika JPN belum cipta template untuk jawatan, akan guna fallback PPD.")

                display_rows = []
                for _, r in df_lulus_surat.iterrows():
                    display_rows.append({
                        "id": r.get("id",""),
                        "NAMA GURU": r.get("NAMA_GURU","") or r.get("nama_guru",""),
                        "IC": r.get("IC_GURU","") or r.get("ic_guru",""),
                        "JAWATAN": r.get("JAWATAN_CADANGAN","") or r.get("jawatan_cadangan",""),
                        "SEKOLAH ASAL": r.get("KOD_SEKOLAH_ASAL","") or r.get("kod_sekolah_asal",""),
                        "NAMA SEKOLAH ASAL": str(r.get("NAMA_SEKOLAH_ASAL","") or r.get("nama_sekolah_asal",""))[:30],
                        "PUSAT TUGAS": r.get("kod_pusat","") or r.get("KOD_PUSAT",""),
                        "NAMA PUSAT": pusat_map_surat.get(str(r.get("kod_pusat","") or "").upper().strip(), "")[:30],
                        "NO SURAT": r.get("no_surat","") or "",
                        "STATUS": r.get("status","") or ""
                    })
                df_display_all = pd.DataFrame(display_rows)
                st.dataframe(df_display_all, use_container_width=True, hide_index=True)

                # ===== NEW V33: JANA DENGAN TEMPLATE JPN + ZIP + HANTAR KE SEKOLAH ASAL =====
                col_gen1, col_gen2, col_gen3 = st.columns(3)
                with col_gen1:
                    if st.button(f"📄 Jana Surat {len(df_display_all)} (Template JPN)", type="primary", use_container_width=True, key="btn_jana_pdf_keseluruhan_v33"):
                        with st.spinner(f"Menjana {len(df_display_all)} surat guna template JPN..."):
                            try:
                                surat_list = []
                                for _, r in df_display_all.iterrows():
                                    surat_list.append({
                                        "nama": r["NAMA GURU"],
                                        "ic": r["IC"],
                                        "jawatan": r["JAWATAN"],
                                        "sekolah_asal": r["SEKOLAH ASAL"],
                                        "nama_sekolah_asal": r["NAMA SEKOLAH ASAL"],
                                        "pusat": r["PUSAT TUGAS"],
                                        "nama_pusat": r["NAMA PUSAT"],
                                        "no_surat": r["NO SURAT"]
                                    })
                                # 1. PDF Kolektif guna JPN template
                                pdf_kolektif = generate_surat_kolektif_pdf_bytes_JPN(surat_list, kod_ppd, PPD_MAP.get(kod_ppd,""), f"SURAT LANTIKAN KESELURUHAN PPD {kod_ppd} - {len(surat_list)} GURU - JPN SELARAS")
                                if pdf_kolektif:
                                    st.session_state[f"pdf_keseluruhan_{kod_ppd}"] = pdf_kolektif
                                # 2. ZIP Pukal individu guna JPN template
                                zip_bytes = create_zip_pukal_dari_JPN(surat_list, kod_ppd, PPD_MAP.get(kod_ppd,""))
                                if zip_bytes:
                                    st.session_state[f"zip_keseluruhan_{kod_ppd}"] = zip_bytes
                                # 3. Hantar ke sekolah asal petugas (auto update status)
                                jml_hantar = hantar_surat_ke_sekolah_asal_bulk(surat_list, kod_ppd)
                                st.session_state[f"surat_list_keseluruhan_{kod_ppd}"] = surat_list
                                st.success(f"✅ Berjaya! {len(surat_list)} surat dijana guna template JPN, {jml_hantar} surat sampai ke sekolah asal!")
                                st.balloons()
                            except Exception as e:
                                st.error("Maaf, surat tidak dapat dijana. Sila cuba lagi atau hubungi pentadbir sistem.")

                with col_gen2:
                    if f"pdf_keseluruhan_{kod_ppd}" in st.session_state:
                        pdf_data = st.session_state[f"pdf_keseluruhan_{kod_ppd}"]
                        st.download_button(f"📥 Download PDF Pukal Kolektif {len(df_display_all)} Surat (Template JPN)", data=pdf_data, file_name=f"Surat_Kolektif_JPN_{kod_ppd}_{datetime.date.today()}.pdf", mime="application/pdf", use_container_width=True, key="dl_pdf_keseluruhan_main_v33")
                    else:
                        st.caption("Belum jana PDF kolektif")

                with col_gen3:
                    if f"zip_keseluruhan_{kod_ppd}" in st.session_state:
                        zip_data = st.session_state[f"zip_keseluruhan_{kod_ppd}"]
                        st.download_button(f"📦 Download ZIP Pukal Individu {len(df_display_all)} PDF (Template JPN)", data=zip_data, file_name=f"ZIP_Surat_Individu_JPN_{kod_ppd}_{datetime.date.today()}.zip", mime="application/zip", use_container_width=True, key="dl_zip_keseluruhan_main_v33", type="primary")
                        st.caption(f"✅ {len(df_display_all)} fail PDF individu dalam ZIP - senang edar")
                    else:
                        st.caption("Belum jana ZIP pukal")

                # Preview if exists
                if f"pdf_keseluruhan_{kod_ppd}" in st.session_state:
                    st.success(f"✅ PDF & ZIP telah dijana guna template JPN. Surat auto sampai ke sekolah asal guru untuk SUP cetak. ({len(df_display_all)} surat)")
                    # Tunjuk breakdown ikut sekolah asal
                    if f"surat_list_keseluruhan_{kod_ppd}" in st.session_state:
                        sl = st.session_state[f"surat_list_keseluruhan_{kod_ppd}"]
                        from collections import Counter
                        cnt = Counter([s.get("sekolah_asal","") for s in sl])
                        st.markdown("**📊 Surat sampai ke sekolah asal:**")
                        cols = st.columns(4)
                        for i, (sek, jml) in enumerate(cnt.most_common(12)):
                            cols[i % 4].metric(sek, f"{jml} surat")

            if fly_cur == "pusat":
                st.markdown("### 🏫 Janaan Surat Ikut Pusat - Template JPN + ZIP")
                st.info("Guna template JPN selaras, jana PDF kolektif + ZIP pukal individu, auto sampai ke sekolah asal")
                # Group by pusat
                pusat_groups_surat = {}
                for _, r in df_lulus_surat.iterrows():
                    kp = str(r.get("kod_pusat") or r.get("KOD_PUSAT") or "").upper().strip()
                    if kp:
                        if kp not in pusat_groups_surat:
                            pusat_groups_surat[kp] = []
                        pusat_groups_surat[kp].append(r)

                pilih_pusat_jana = st.selectbox(
                    "Pilih Pusat Untuk Jana Surat PDF",
                    sorted(pusat_groups_surat.keys()),
                    format_func=lambda x: f"{x} - {pusat_map_surat.get(x,'')} ({len(pusat_groups_surat[x])} surat)",
                    key="pilih_pusat_jana_surat"
                )

                if pilih_pusat_jana:
                    guru_pusat = pusat_groups_surat[pilih_pusat_jana]
                    df_pusat_surat = pd.DataFrame([{
                        "NAMA GURU": r.get("NAMA_GURU","") or r.get("nama_guru",""),
                        "IC": r.get("IC_GURU","") or r.get("ic_guru",""),
                        "JAWATAN": r.get("JAWATAN_CADANGAN","") or r.get("jawatan_cadangan",""),
                        "SEKOLAH ASAL": r.get("KOD_SEKOLAH_ASAL","") or r.get("kod_sekolah_asal",""),
                        "NO SURAT": r.get("no_surat",""),
                        "STATUS": r.get("status","")
                    } for r in guru_pusat])
                    st.dataframe(df_pusat_surat, use_container_width=True, hide_index=True)

                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button(f"📄 Jana {len(guru_pusat)} Surat {pilih_pusat_jana} (JPN + ZIP)", type="primary", use_container_width=True, key=f"btn_jana_pdf_pusat_{pilih_pusat_jana}_v33"):
                            with st.spinner(f"Menjana {len(guru_pusat)} surat..."):
                                try:
                                    surat_list_p = []
                                    for r in guru_pusat:
                                        surat_list_p.append({
                                            "nama": r.get("NAMA_GURU","") or r.get("nama_guru",""),
                                            "ic": r.get("IC_GURU","") or r.get("ic_guru",""),
                                            "jawatan": r.get("JAWATAN_CADANGAN","") or r.get("jawatan_cadangan",""),
                                            "sekolah_asal": r.get("KOD_SEKOLAH_ASAL","") or r.get("kod_sekolah_asal",""),
                                            "nama_sekolah_asal": r.get("NAMA_SEKOLAH_ASAL","") or r.get("nama_sekolah_asal",""),
                                            "pusat": r.get("kod_pusat","") or r.get("KOD_PUSAT",""),
                                            "nama_pusat": pusat_map_surat.get(str(r.get("kod_pusat","") or "").upper().strip(), ""),
                                            "no_surat": r.get("no_surat","")
                                        })
                                    pdf_pusat = generate_surat_kolektif_pdf_bytes_JPN(surat_list_p, kod_ppd, PPD_MAP.get(kod_ppd,""), f"SURAT LANTIKAN {pilih_pusat_jana} - {pusat_map_surat.get(pilih_pusat_jana,'')} - JPN SELARAS")
                                    zip_pusat = create_zip_pukal_dari_JPN(surat_list_p, kod_ppd, PPD_MAP.get(kod_ppd,""))
                                    jml_hantar = hantar_surat_ke_sekolah_asal_bulk(surat_list_p, kod_ppd)
                                    if pdf_pusat:
                                        st.session_state[f"pdf_pusat_{pilih_pusat_jana}"] = pdf_pusat
                                    if zip_pusat:
                                        st.session_state[f"zip_pusat_{pilih_pusat_jana}"] = zip_pusat
                                    st.success(f"✅ PDF+ZIP {pilih_pusat_jana} {len(surat_list_p)} surat berjaya dijana (Template JPN) + {jml_hantar} sampai sekolah asal!")
                                except Exception as e:
                                    st.error("Maaf, berlaku masalah semasa memproses. Sila cuba lagi.")
                    with c2:
                        if f"pdf_pusat_{pilih_pusat_jana}" in st.session_state:
                            pdf_d = st.session_state[f"pdf_pusat_{pilih_pusat_jana}"]
                            st.download_button(f"📥 PDF Kolektif {pilih_pusat_jana} ({len(guru_pusat)}) - JPN", data=pdf_d, file_name=f"Surat_{pilih_pusat_jana}_{kod_ppd}_{datetime.date.today()}_JPN.pdf", mime="application/pdf", use_container_width=True, key=f"dl_pdf_pusat_{pilih_pusat_jana}_v33")
                        if f"zip_pusat_{pilih_pusat_jana}" in st.session_state:
                            zip_d = st.session_state[f"zip_pusat_{pilih_pusat_jana}"]
                            st.download_button(f"📦 ZIP Pukal Individu {pilih_pusat_jana} ({len(guru_pusat)}) - JPN", data=zip_d, file_name=f"ZIP_{pilih_pusat_jana}_{kod_ppd}_{datetime.date.today()}_JPN.zip", mime="application/zip", use_container_width=True, key=f"dl_zip_pusat_{pilih_pusat_jana}_v33", type="primary")
                        if f"pdf_pusat_{pilih_pusat_jana}" in st.session_state:
                            st.info(f"Surat {pilih_pusat_jana} auto sampai ke sekolah asal guru untuk SUP cetak")

            if fly_cur == "sekolah":
                st.markdown("### 🏫 Surat Ikut Sekolah Asal - Untuk Hantar ke SUP Cetak - Template JPN + ZIP")
                st.caption("Surat yang telah diluluskan akan sampai ke sekolah asal guru - SUP boleh cetak dan bagi pada guru berkenaan. Guna template JPN selaras + ZIP pukal.")

                # Group by sekolah asal
                sekolah_groups_surat = {}
                for _, r in df_lulus_surat.iterrows():
                    ks = str(r.get("KOD_SEKOLAH_ASAL") or r.get("kod_sekolah_asal") or "").upper().strip()
                    if ks:
                        if ks not in sekolah_groups_surat:
                            sekolah_groups_surat[ks] = []
                        sekolah_groups_surat[ks].append(r)

                pilih_sekolah_surat = st.selectbox(
                    "Pilih Sekolah Asal Untuk Lihat Surat Yang Sampai",
                    sorted(sekolah_groups_surat.keys()),
                    format_func=lambda x: f"{x} - {len(sekolah_groups_surat[x])} surat sampai (untuk SUP cetak) - Template JPN",
                    key="pilih_sekolah_surat_jana"
                )

                if pilih_sekolah_surat:
                    guru_sekolah = sekolah_groups_surat[pilih_sekolah_surat]
                    df_sek_surat = pd.DataFrame([{
                        "NAMA GURU": r.get("NAMA_GURU","") or r.get("nama_guru",""),
                        "IC": r.get("IC_GURU","") or r.get("ic_guru",""),
                        "JAWATAN": r.get("JAWATAN_CADANGAN","") or r.get("jawatan_cadangan",""),
                        "PUSAT TUGAS": r.get("kod_pusat","") or r.get("KOD_PUSAT",""),
                        "NAMA PUSAT": pusat_map_surat.get(str(r.get("kod_pusat","") or "").upper().strip(), "")[:30],
                        "NO SURAT": r.get("no_surat",""),
                        "STATUS": r.get("status","")
                    } for r in guru_sekolah])
                    st.dataframe(df_sek_surat, use_container_width=True, hide_index=True)
                    st.success(f"✅ {len(guru_sekolah)} surat telah sampai ke sekolah asal {pilih_sekolah_surat} - SUP boleh cetak (Template JPN)")

                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button(f"📄 Jana PDF {pilih_sekolah_surat} - {len(guru_sekolah)} Guru (JPN+ZIP)", type="primary", use_container_width=True, key=f"btn_jana_pdf_sekolah_{pilih_sekolah_surat}_v33"):
                            with st.spinner(f"Menjana {len(guru_sekolah)} surat sekolah asal..."):
                                try:
                                    surat_list_s = []
                                    for r in guru_sekolah:
                                        surat_list_s.append({
                                            "nama": r.get("NAMA_GURU","") or r.get("nama_guru",""),
                                            "ic": r.get("IC_GURU","") or r.get("ic_guru",""),
                                            "jawatan": r.get("JAWATAN_CADANGAN","") or r.get("jawatan_cadangan",""),
                                            "sekolah_asal": r.get("KOD_SEKOLAH_ASAL","") or r.get("kod_sekolah_asal",""),
                                            "nama_sekolah_asal": r.get("NAMA_SEKOLAH_ASAL","") or r.get("nama_sekolah_asal","") or pilih_sekolah_surat,
                                            "pusat": r.get("kod_pusat","") or r.get("KOD_PUSAT",""),
                                            "nama_pusat": pusat_map_surat.get(str(r.get("kod_pusat","") or "").upper().strip(), ""),
                                            "no_surat": r.get("no_surat","")
                                        })
                                    pdf_sek = generate_surat_kolektif_pdf_bytes_JPN(surat_list_s, kod_ppd, PPD_MAP.get(kod_ppd,""), f"SURAT LANTIKAN SEKOLAH ASAL {pilih_sekolah_surat} - {len(surat_list_s)} GURU - UNTUK SUP CETAK - JPN SELARAS")
                                    zip_sek = create_zip_pukal_dari_JPN(surat_list_s, kod_ppd, PPD_MAP.get(kod_ppd,""))
                                    if pdf_sek:
                                        st.session_state[f"pdf_sekolah_{pilih_sekolah_surat}"] = pdf_sek
                                    if zip_sek:
                                        st.session_state[f"zip_sekolah_{pilih_sekolah_surat}"] = zip_sek
                                    st.success(f"✅ PDF+ZIP Sekolah Asal {pilih_sekolah_surat} {len(surat_list_s)} surat berjaya dijana (JPN)!")
                                except Exception as e:
                                    st.error("Maaf, berlaku masalah semasa memproses. Sila cuba lagi.")
                    with c2:
                        if f"pdf_sekolah_{pilih_sekolah_surat}" in st.session_state:
                            pdf_s = st.session_state[f"pdf_sekolah_{pilih_sekolah_surat}"]
                            st.download_button(f"📥 PDF Sekolah Asal {pilih_sekolah_surat} ({len(guru_sekolah)}) - JPN", data=pdf_s, file_name=f"Surat_SekolahAsal_{pilih_sekolah_surat}_{kod_ppd}_{datetime.date.today()}_JPN.pdf", mime="application/pdf", use_container_width=True, key=f"dl_pdf_sekolah_{pilih_sekolah_surat}_v33")
                        if f"zip_sekolah_{pilih_sekolah_surat}" in st.session_state:
                            zip_s = st.session_state[f"zip_sekolah_{pilih_sekolah_surat}"]
                            st.download_button(f"📦 ZIP Sekolah Asal {pilih_sekolah_surat} ({len(guru_sekolah)}) - JPN", data=zip_s, file_name=f"ZIP_SekolahAsal_{pilih_sekolah_surat}_{kod_ppd}_{datetime.date.today()}_JPN.zip", mime="application/zip", use_container_width=True, key=f"dl_zip_sekolah_{pilih_sekolah_surat}_v33", type="primary")
                        if f"pdf_sekolah_{pilih_sekolah_surat}" in st.session_state:
                            st.info(f"📄 Surat ini akan dicetak oleh SUP {pilih_sekolah_surat} dan diberi kepada guru berkenaan (Template JPN selaras)")



        elif menu == "export":
            st.header(f"Export Data PPD {kod_ppd}")

            st.header(f"Export Data PPD {kod_ppd}")


            df_cad = get_cadangan_df(kod_ppd=kod_ppd)
            if not df_cad.empty:
                st.download_button("📥 Export Cadangan PPD (Excel)", to_excel(df_cad), file_name=f"laporan_PPD_{kod_ppd}_{datetime.date.today()}.xlsx", use_container_width=True)
            try:
                res = supa.table("guru_master").select("*").eq("kod_ppd", kod_ppd.lower()).limit(5000).execute()
                df_guru = pd.DataFrame(res.data or [])
                if not df_guru.empty:
                    st.download_button("📥 Export Guru PPD (Excel)", to_excel(df_guru), file_name=f"guru_PPD_{kod_ppd}.xlsx", use_container_width=True)
            except Exception as e:
                st.error(str(e))

# ================= ROLE: JPN =================
elif st.session_state.role == "JPN":
    col_menu, col_main = st.columns([1.45, 3.2], gap="large")
    with col_menu:
        st.markdown('<div class="custom-sidebar">', unsafe_allow_html=True)
        st.markdown("### 🏛️ JPN Selangor")
        add_refresh_button()

        MENU_JPN = [('dashboard', '📊 Dashboard JPN'), ('jpn_template_surat', '📄 Template Surat JPN (11 Jawatan)'), ('sekolah', '🏫 Semua Sekolah'), ('pusat', '🏫 Pusat Master'),
                    ('guru', '👨\u200d🏫 Guru Master'), ('cadangan', '📋 Semua Cadangan'), ('export', '📥 Export Negeri'),
                    ('admin', '⚙️ Admin'), ('keluar', '🚪 Log Keluar')]
        menu, fly_cur = render_menu_flyout("jpn_menu_sel", MENU_JPN, FLY_JPN, None, "fly_jpn")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_main:
        render_bar_tahun("jpn")
        if menu == "keluar":
            reset_sesi_kekal_tahun()
            st.rerun()

        elif menu == "dashboard":
            st.header("Dashboard JPN Selangor - Pelantikan SPM 2026".replace("2026", str(tahun_aktif())))
            if fly_cur == "ringkasan":
                cols = st.columns(5)
                for idx, t in enumerate(["sekolah_master", "pusat_master", "guru_master", "cadangan_sup"]):
                    try:
                        res = supa.table(t).select("*", count="exact").limit(1).execute()
                        cols[idx].metric(t, res.count)
                    except Exception as e:
                        cols[idx].error(f"{t}: {e}")

            if fly_cur == "ppd":
                st.markdown("---")
                st.subheader("Breakdown Ikut PPD")
                rows = []
                for ppd in KOD_DAERAH:
                    try:
                        c1 = supa.table("sekolah_master").select("kod_sekolah", count="exact").eq("kod_ppd", ppd).execute()
                        c2 = supa.table("guru_master").select("id", count="exact").eq("kod_ppd", ppd.lower()).execute()
                        c3 = supa.table("cadangan_sup").select("id", count="exact").eq("kod_ppd", ppd).execute()
                        rows.append({"PPD": f"{ppd} - {PPD_MAP[ppd]}", "Sekolah": c1.count, "Guru": c2.count, "Cadangan": c3.count})
                    except:
                        rows.append({"PPD": ppd, "Sekolah": 0, "Guru": 0, "Cadangan": 0})
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        elif menu == "jpn_template_surat":
            st.header("📄 Template Surat JPN - 11 Jawatan (LAJU)")
            st.caption("JPN selaraskan - PPD auto guna template ini")

            try:
                JAWATAN_11 = ["KETUA PENGAWAS","TIMBALAN KETUA PENGAWAS","PENGAWAS PEPERIKSAAN","JURU TULIS","JURU BACA","KETUA PENGAWAS HOSPITAL","PENGAWAS HOSPITAL","PENGAWAS PENGIRING","PENGEMAS BILIK","PENYELIA KAWASAN","SELENGGARA BILIK KEBAL"]
                DEFAULT_11 = {
                    "KETUA PENGAWAS": "<div style='font-family:Arial; padding:25px; border:1px solid #000;'><table style='width:100%; border:none;'><tr><td style='width:80px; vertical-align:top; border:none;'><img src='https://upload.wikimedia.org/wikipedia/commons/2/2a/Coat_of_arms_of_Malaysia.svg' style='width:70px;'></td><td style='vertical-align:top; border:none; text-align:left;'><b>KEMENTERIAN PENDIDIKAN MALAYSIA</b><br>JABATAN PENDIDIKAN NEGERI SELANGOR<br><small>Persiaran Tengku Ampuan Rahimah, Seksyen 20, 40300 Shah Alam, Selangor</small></td></tr></table><hr style='border:2px solid #000; margin:10px 0;'><div style='text-align:right; font-size:10pt;'>Ruj. Kami: {{NO_SURAT}}<br>Tarikh: {{TARIKH}}</div><div style='font-size:10pt; margin-top:12px;'><b>{{NAMA}}</b><br>Melalui:<br>PENGETUA<br><b>{{NAMA_SEKOLAH_ASAL}}</b><br>{{PPD}}<br><br>Tuan,<br><b>SPM 2026 : PELANTIKAN KETUA PENGAWAS</b><br><br>2. Dilantik sebagai <b>Ketua Pengawas</b> di {{PUSAT}} - {{NAMA_PUSAT}}<br>Bilik Kebal: {{BILIK_KEBAL}}<br>Sekolah Asal: {{SEKOLAH_ASAL}} - {{NAMA_SEKOLAH_ASAL}}<br>No Surat: {{NO_SURAT}}<br><br>3. Elaun: RM 375.00 + 0.25C + 2S<br>4. Sulit - Akta Rahsia Rasmi 1972<br><br>MALAYSIA MADANI<br>BERKHIDMAT UNTUK NEGARA<br><br>(DATIN WAN NOR ASHIKIN)<br>Pengarah JPN Selangor</div></div>".replace("2026", str(tahun_aktif())),
                    "TIMBALAN KETUA PENGAWAS": "<div style='font-family:Arial; padding:25px; border:1px solid #000;'><table style='width:100%; border:none;'><tr><td style='width:80px; vertical-align:top; border:none;'><img src='https://upload.wikimedia.org/wikipedia/commons/2/2a/Coat_of_arms_of_Malaysia.svg' style='width:70px;'></td><td style='vertical-align:top; border:none; text-align:left;'><b>KEMENTERIAN PENDIDIKAN MALAYSIA</b><br>JABATAN PENDIDIKAN NEGERI SELANGOR<br><small>Persiaran Tengku Ampuan Rahimah, Seksyen 20, 40300 Shah Alam, Selangor</small></td></tr></table><hr style='border:2px solid #000; margin:10px 0;'><div style='text-align:right; font-size:10pt;'>Ruj. Kami: {{NO_SURAT}}<br>Tarikh: {{TARIKH}}</div><div style='font-size:10pt; margin-top:12px;'><b>{{NAMA}}</b><br>Melalui:<br>PENGETUA<br><b>{{NAMA_SEKOLAH_ASAL}}</b><br>{{PPD}}<br><br>Tuan,<br><b>SPM 2026 : PELANTIKAN TIMBALAN KETUA PENGAWAS</b><br><br>2. Dilantik sebagai <b>Timbalan Ketua Pengawas</b> di {{PUSAT}} - {{NAMA_PUSAT}}<br>Bilik Kebal: {{BILIK_KEBAL}}<br>Sekolah Asal: {{SEKOLAH_ASAL}} - {{NAMA_SEKOLAH_ASAL}}<br>No Surat: {{NO_SURAT}}<br><br>3. Elaun: RM 375.00<br>4. Sulit - Akta Rahsia Rasmi 1972<br><br>MALAYSIA MADANI<br>BERKHIDMAT UNTUK NEGARA<br><br>(DATIN WAN NOR ASHIKIN)<br>Pengarah JPN Selangor</div></div>".replace("2026", str(tahun_aktif())),
                    "PENGAWAS PEPERIKSAAN": "<div style='font-family:Arial; padding:25px; border:1px solid #000;'><table style='width:100%; border:none;'><tr><td style='width:80px; vertical-align:top; border:none;'><img src='https://upload.wikimedia.org/wikipedia/commons/2/2a/Coat_of_arms_of_Malaysia.svg' style='width:70px;'></td><td style='vertical-align:top; border:none; text-align:left;'><b>KEMENTERIAN PENDIDIKAN MALAYSIA</b><br>JABATAN PENDIDIKAN NEGERI SELANGOR<br><small>Persiaran Tengku Ampuan Rahimah, Seksyen 20, 40300 Shah Alam, Selangor</small></td></tr></table><hr style='border:2px solid #000; margin:10px 0;'><div style='text-align:right; font-size:10pt;'>Ruj. Kami: {{NO_SURAT}}<br>Tarikh: {{TARIKH}}</div><div style='font-size:10pt; margin-top:12px;'><b>{{NAMA}}</b><br>Melalui:<br>PENGETUA<br><b>{{NAMA_SEKOLAH_ASAL}}</b><br>{{PPD}}<br><br>Tuan,<br><b>SPM 2026 : PELANTIKAN PENGAWAS PEPERIKSAAN</b><br><br>2. Dilantik sebagai <b>Pengawas Peperiksaan</b> di {{PUSAT}} - {{NAMA_PUSAT}}<br>Bilik Kebal: {{BILIK_KEBAL}}<br>Sekolah Asal: {{SEKOLAH_ASAL}} - {{NAMA_SEKOLAH_ASAL}}<br>No Surat: {{NO_SURAT}}<br><br>3. Elaun: RM 281.25 + S<br>4. Sulit - Akta Rahsia Rasmi 1972<br><br>MALAYSIA MADANI<br>BERKHIDMAT UNTUK NEGARA<br><br>(DATIN WAN NOR ASHIKIN)<br>Pengarah JPN Selangor</div></div>".replace("2026", str(tahun_aktif())),
                    "PENYELIA KAWASAN": "<div style='font-family:Arial; padding:25px; border:1px solid #000;'><table style='width:100%; border:none;'><tr><td style='width:80px; vertical-align:top; border:none;'><img src='https://upload.wikimedia.org/wikipedia/commons/2/2a/Coat_of_arms_of_Malaysia.svg' style='width:70px;'></td><td style='vertical-align:top; border:none; text-align:left;'><b>KEMENTERIAN PENDIDIKAN MALAYSIA</b><br>JABATAN PENDIDIKAN NEGERI SELANGOR<br><small>Persiaran Tengku Ampuan Rahimah, Seksyen 20, 40300 Shah Alam, Selangor</small></td></tr></table><hr style='border:2px solid #000; margin:10px 0;'><div style='text-align:right; font-size:10pt;'>Ruj. Kami: {{NO_SURAT}}<br>Tarikh: {{TARIKH}}</div><div style='font-size:10pt; margin-top:12px;'><b>{{NAMA}}</b><br>Melalui:<br>PENGETUA<br><b>{{NAMA_SEKOLAH_ASAL}}</b><br>{{PPD}}<br><br>Tuan,<br><b>SPM 2026 : PELANTIKAN PENYELIA KAWASAN</b><br><br>2. Dilantik sebagai <b>Penyelia Kawasan</b> di {{PUSAT}} - {{NAMA_PUSAT}}<br>Bilik Kebal: {{BILIK_KEBAL}}<br>Sekolah Asal: {{SEKOLAH_ASAL}} - {{NAMA_SEKOLAH_ASAL}}<br>No Surat: {{NO_SURAT}}<br><br>3. Elaun: RM 437.50 + 10P + 2S<br>4. Sulit - Akta Rahsia Rasmi 1972<br><br>MALAYSIA MADANI<br>BERKHIDMAT UNTUK NEGARA<br><br>(DATIN WAN NOR ASHIKIN)<br>Pengarah JPN Selangor</div></div>".replace("2026", str(tahun_aktif())),
                    "KETUA PENGAWAS HOSPITAL": "<div style='font-family:Arial; padding:25px; border:1px solid #000;'><table style='width:100%; border:none;'><tr><td style='width:80px; vertical-align:top; border:none;'><img src='https://upload.wikimedia.org/wikipedia/commons/2/2a/Coat_of_arms_of_Malaysia.svg' style='width:70px;'></td><td style='vertical-align:top; border:none; text-align:left;'><b>KEMENTERIAN PENDIDIKAN MALAYSIA</b><br>JABATAN PENDIDIKAN NEGERI SELANGOR<br><small>Persiaran Tengku Ampuan Rahimah, Seksyen 20, 40300 Shah Alam, Selangor</small></td></tr></table><hr style='border:2px solid #000; margin:10px 0;'><div style='text-align:right; font-size:10pt;'>Ruj. Kami: {{NO_SURAT}}<br>Tarikh: {{TARIKH}}</div><div style='font-size:10pt; margin-top:12px;'><b>{{NAMA}}</b><br>Melalui:<br>PENGETUA<br><b>{{NAMA_SEKOLAH_ASAL}}</b><br>{{PPD}}<br><br>Tuan,<br><b>SPM 2026 : PELANTIKAN KETUA PENGAWAS HOSPITAL</b><br><br>2. Dilantik sebagai <b>Ketua Pengawas Hospital</b> di {{PUSAT}} - {{NAMA_PUSAT}}<br>Bilik Kebal: {{BILIK_KEBAL}}<br>Sekolah Asal: {{SEKOLAH_ASAL}} - {{NAMA_SEKOLAH_ASAL}}<br>No Surat: {{NO_SURAT}}<br><br>3. Elaun: RM 375.00 + 0.25C + 2S<br>4. Sulit - Akta Rahsia Rasmi 1972<br><br>MALAYSIA MADANI<br>BERKHIDMAT UNTUK NEGARA<br><br>(DATIN WAN NOR ASHIKIN)<br>Pengarah JPN Selangor</div></div>".replace("2026", str(tahun_aktif())),
                    "PENGAWAS HOSPITAL": "<div style='font-family:Arial; padding:25px; border:1px solid #000;'><table style='width:100%; border:none;'><tr><td style='width:80px; vertical-align:top; border:none;'><img src='https://upload.wikimedia.org/wikipedia/commons/2/2a/Coat_of_arms_of_Malaysia.svg' style='width:70px;'></td><td style='vertical-align:top; border:none; text-align:left;'><b>KEMENTERIAN PENDIDIKAN MALAYSIA</b><br>JABATAN PENDIDIKAN NEGERI SELANGOR<br><small>Persiaran Tengku Ampuan Rahimah, Seksyen 20, 40300 Shah Alam, Selangor</small></td></tr></table><hr style='border:2px solid #000; margin:10px 0;'><div style='text-align:right; font-size:10pt;'>Ruj. Kami: {{NO_SURAT}}<br>Tarikh: {{TARIKH}}</div><div style='font-size:10pt; margin-top:12px;'><b>{{NAMA}}</b><br>Melalui:<br>PENGETUA<br><b>{{NAMA_SEKOLAH_ASAL}}</b><br>{{PPD}}<br><br>Tuan,<br><b>SPM 2026 : PELANTIKAN PENGAWAS HOSPITAL</b><br><br>2. Dilantik sebagai <b>Pengawas Hospital</b> di {{PUSAT}} - {{NAMA_PUSAT}}<br>Bilik Kebal: {{BILIK_KEBAL}}<br>Sekolah Asal: {{SEKOLAH_ASAL}} - {{NAMA_SEKOLAH_ASAL}}<br>No Surat: {{NO_SURAT}}<br><br>3. Elaun: RM 281.25 + S<br>4. Sulit - Akta Rahsia Rasmi 1972<br><br>MALAYSIA MADANI<br>BERKHIDMAT UNTUK NEGARA<br><br>(DATIN WAN NOR ASHIKIN)<br>Pengarah JPN Selangor</div></div>".replace("2026", str(tahun_aktif())),
                    "JURU TULIS": "<div style='font-family:Arial; padding:25px; border:1px solid #000;'><table style='width:100%; border:none;'><tr><td style='width:80px; vertical-align:top; border:none;'><img src='https://upload.wikimedia.org/wikipedia/commons/2/2a/Coat_of_arms_of_Malaysia.svg' style='width:70px;'></td><td style='vertical-align:top; border:none; text-align:left;'><b>KEMENTERIAN PENDIDIKAN MALAYSIA</b><br>JABATAN PENDIDIKAN NEGERI SELANGOR<br><small>Persiaran Tengku Ampuan Rahimah, Seksyen 20, 40300 Shah Alam, Selangor</small></td></tr></table><hr style='border:2px solid #000; margin:10px 0;'><div style='text-align:right; font-size:10pt;'>Ruj. Kami: {{NO_SURAT}}<br>Tarikh: {{TARIKH}}</div><div style='font-size:10pt; margin-top:12px;'><b>{{NAMA}}</b><br>Melalui:<br>PENGETUA<br><b>{{NAMA_SEKOLAH_ASAL}}</b><br>{{PPD}}<br><br>Tuan,<br><b>SPM 2026 : PELANTIKAN JURU TULIS</b><br><br>2. Dilantik sebagai <b>Juru Tulis</b> di {{PUSAT}} - {{NAMA_PUSAT}}<br>Bilik Kebal: {{BILIK_KEBAL}}<br>Sekolah Asal: {{SEKOLAH_ASAL}} - {{NAMA_SEKOLAH_ASAL}}<br>No Surat: {{NO_SURAT}}<br><br>3. Elaun: RM 281.25 + S<br>4. Sulit - Akta Rahsia Rasmi 1972<br><br>MALAYSIA MADANI<br>BERKHIDMAT UNTUK NEGARA<br><br>(DATIN WAN NOR ASHIKIN)<br>Pengarah JPN Selangor</div></div>".replace("2026", str(tahun_aktif())),
                    "JURU BACA": "<div style='font-family:Arial; padding:25px; border:1px solid #000;'><table style='width:100%; border:none;'><tr><td style='width:80px; vertical-align:top; border:none;'><img src='https://upload.wikimedia.org/wikipedia/commons/2/2a/Coat_of_arms_of_Malaysia.svg' style='width:70px;'></td><td style='vertical-align:top; border:none; text-align:left;'><b>KEMENTERIAN PENDIDIKAN MALAYSIA</b><br>JABATAN PENDIDIKAN NEGERI SELANGOR<br><small>Persiaran Tengku Ampuan Rahimah, Seksyen 20, 40300 Shah Alam, Selangor</small></td></tr></table><hr style='border:2px solid #000; margin:10px 0;'><div style='text-align:right; font-size:10pt;'>Ruj. Kami: {{NO_SURAT}}<br>Tarikh: {{TARIKH}}</div><div style='font-size:10pt; margin-top:12px;'><b>{{NAMA}}</b><br>Melalui:<br>PENGETUA<br><b>{{NAMA_SEKOLAH_ASAL}}</b><br>{{PPD}}<br><br>Tuan,<br><b>SPM 2026 : PELANTIKAN JURU BACA</b><br><br>2. Dilantik sebagai <b>Juru Baca</b> di {{PUSAT}} - {{NAMA_PUSAT}}<br>Bilik Kebal: {{BILIK_KEBAL}}<br>Sekolah Asal: {{SEKOLAH_ASAL}} - {{NAMA_SEKOLAH_ASAL}}<br>No Surat: {{NO_SURAT}}<br><br>3. Elaun: RM 281.25 + S<br>4. Sulit - Akta Rahsia Rasmi 1972<br><br>MALAYSIA MADANI<br>BERKHIDMAT UNTUK NEGARA<br><br>(DATIN WAN NOR ASHIKIN)<br>Pengarah JPN Selangor</div></div>".replace("2026", str(tahun_aktif())),
                    "PENGAWAS PENGIRING": "<div style='font-family:Arial; padding:25px; border:1px solid #000;'><table style='width:100%; border:none;'><tr><td style='width:80px; vertical-align:top; border:none;'><img src='https://upload.wikimedia.org/wikipedia/commons/2/2a/Coat_of_arms_of_Malaysia.svg' style='width:70px;'></td><td style='vertical-align:top; border:none; text-align:left;'><b>KEMENTERIAN PENDIDIKAN MALAYSIA</b><br>JABATAN PENDIDIKAN NEGERI SELANGOR<br><small>Persiaran Tengku Ampuan Rahimah, Seksyen 20, 40300 Shah Alam, Selangor</small></td></tr></table><hr style='border:2px solid #000; margin:10px 0;'><div style='text-align:right; font-size:10pt;'>Ruj. Kami: {{NO_SURAT}}<br>Tarikh: {{TARIKH}}</div><div style='font-size:10pt; margin-top:12px;'><b>{{NAMA}}</b><br>Melalui:<br>PENGETUA<br><b>{{NAMA_SEKOLAH_ASAL}}</b><br>{{PPD}}<br><br>Tuan,<br><b>SPM 2026 : PELANTIKAN PENGAWAS PENGIRING</b><br><br>2. Dilantik sebagai <b>Pengawas Pengiring</b> di {{PUSAT}} - {{NAMA_PUSAT}}<br>Bilik Kebal: {{BILIK_KEBAL}}<br>Sekolah Asal: {{SEKOLAH_ASAL}} - {{NAMA_SEKOLAH_ASAL}}<br>No Surat: {{NO_SURAT}}<br><br>3. Elaun: RM 281.25 + S<br>4. Sulit - Akta Rahsia Rasmi 1972<br><br>MALAYSIA MADANI<br>BERKHIDMAT UNTUK NEGARA<br><br>(DATIN WAN NOR ASHIKIN)<br>Pengarah JPN Selangor</div></div>".replace("2026", str(tahun_aktif())),
                    "PENGEMAS BILIK": "<div style='font-family:Arial; padding:25px; border:1px solid #000;'><table style='width:100%; border:none;'><tr><td style='width:80px; vertical-align:top; border:none;'><img src='https://upload.wikimedia.org/wikipedia/commons/2/2a/Coat_of_arms_of_Malaysia.svg' style='width:70px;'></td><td style='vertical-align:top; border:none; text-align:left;'><b>KEMENTERIAN PENDIDIKAN MALAYSIA</b><br>JABATAN PENDIDIKAN NEGERI SELANGOR<br><small>Persiaran Tengku Ampuan Rahimah, Seksyen 20, 40300 Shah Alam, Selangor</small></td></tr></table><hr style='border:2px solid #000; margin:10px 0;'><div style='text-align:right; font-size:10pt;'>Ruj. Kami: {{NO_SURAT}}<br>Tarikh: {{TARIKH}}</div><div style='font-size:10pt; margin-top:12px;'><b>{{NAMA}}</b><br>Melalui:<br>PENGETUA<br><b>{{NAMA_SEKOLAH_ASAL}}</b><br>{{PPD}}<br><br>Tuan,<br><b>SPM 2026 : PELANTIKAN PENGEMAS BILIK</b><br><br>2. Dilantik sebagai <b>Pengemas Bilik</b> di {{PUSAT}} - {{NAMA_PUSAT}}<br>Bilik Kebal: {{BILIK_KEBAL}}<br>Sekolah Asal: {{SEKOLAH_ASAL}} - {{NAMA_SEKOLAH_ASAL}}<br>No Surat: {{NO_SURAT}}<br><br>3. Elaun: RM 281.25 + S<br>4. Sulit - Akta Rahsia Rasmi 1972<br><br>MALAYSIA MADANI<br>BERKHIDMAT UNTUK NEGARA<br><br>(DATIN WAN NOR ASHIKIN)<br>Pengarah JPN Selangor</div></div>".replace("2026", str(tahun_aktif())),
                    "SELENGGARA BILIK KEBAL": "<div style='font-family:Arial; padding:25px; border:1px solid #000;'><table style='width:100%; border:none;'><tr><td style='width:80px; vertical-align:top; border:none;'><img src='https://upload.wikimedia.org/wikipedia/commons/2/2a/Coat_of_arms_of_Malaysia.svg' style='width:70px;'></td><td style='vertical-align:top; border:none; text-align:left;'><b>KEMENTERIAN PENDIDIKAN MALAYSIA</b><br>JABATAN PENDIDIKAN NEGERI SELANGOR<br><small>Persiaran Tengku Ampuan Rahimah, Seksyen 20, 40300 Shah Alam, Selangor</small></td></tr></table><hr style='border:2px solid #000; margin:10px 0;'><div style='text-align:right; font-size:10pt;'>Ruj. Kami: {{NO_SURAT}}<br>Tarikh: {{TARIKH}}</div><div style='font-size:10pt; margin-top:12px;'><b>{{NAMA}}</b><br>Melalui:<br>PENGETUA<br><b>{{NAMA_SEKOLAH_ASAL}}</b><br>{{PPD}}<br><br>Tuan,<br><b>SPM 2026 : PELANTIKAN SELENGGARA BILIK KEBAL</b><br><br>2. Dilantik sebagai <b>Selenggara Bilik Kebal</b> di {{PUSAT}} - {{NAMA_PUSAT}}<br>Bilik Kebal: {{BILIK_KEBAL}}<br>Sekolah Asal: {{SEKOLAH_ASAL}} - {{NAMA_SEKOLAH_ASAL}}<br>No Surat: {{NO_SURAT}}<br><br>3. Elaun: RM 281.25 + S<br>4. Sulit - Akta Rahsia Rasmi 1972<br><br>MALAYSIA MADANI<br>BERKHIDMAT UNTUK NEGARA<br><br>(DATIN WAN NOR ASHIKIN)<br>Pengarah JPN Selangor</div></div>".replace("2026", str(tahun_aktif())),
                }
                templates = get_jpn_templates_one()
                pilih = st.selectbox("Pilih Jawatan", JAWATAN_11, key="pilih_11_fix")
                curr = templates.get(pilih.upper()) or DEFAULT_11.get(pilih, "<div>Template {{NAMA}} - {{PUSAT}} - {{NO_SURAT}}</div>")
                edited = st.text_area(f"Template {pilih}", value=curr, height=280, key=f"edit_{pilih}_fix")
                c1,c2 = st.columns(2)
                with c1:
                    if st.button(f"💾 Simpan {pilih}", type="primary", use_container_width=True, key=f"save_{pilih}_fix"):
                        try:
                            ex = supa.table("surat_templates_jpn").select("id").eq("jawatan", pilih).execute()
                            if ex.data:
                                supa.table("surat_templates_jpn").update({"template_html": edited}).eq("jawatan", pilih).execute()
                            else:
                                supa.table("surat_templates_jpn").insert({"jawatan": pilih, "template_html": edited}).execute()
                            st.cache_data.clear()
                            st.success(f"✅ {pilih} disimpan - PPD akan guna JPN")
                        except Exception as e:
                            st.error(str(e))
                            st.code("CREATE TABLE IF NOT EXISTS surat_templates_jpn (id SERIAL PRIMARY KEY, jawatan TEXT UNIQUE, template_html TEXT);")
                with c2:
                    if st.button("🔄 Clear Cache", use_container_width=True, key="clear_fix"):
                        st.cache_data.clear()
                        st.rerun()
                # ===== V37: Panduan placeholder, preview sebenar & ujian PDF =====
                st.caption("Placeholder boleh guna (huruf besar/kecil sama): {{NAMA}} {{IC}} {{JAWATAN}} {{SEKOLAH_ASAL}} {{NAMA_SEKOLAH_ASAL}} {{SEKOLAH_ASAL_PENUH}} {{PUSAT}} {{NAMA_PUSAT}} {{PUSAT_PENUH}} {{BILIK_KEBAL}} {{NO_SURAT}} {{PPD}} {{PPD_NAME}} {{TARIKH}} {{TAHUN}}")
                if enjin_pdf_templat_ada():
                    st.success("✅ Enjin PDF templat aktif - butang PDF / ZIP / kolektif PPD akan ikut templat ini.")
                else:
                    st.warning("⚠️ Enjin PDF templat (xhtml2pdf) belum dipasang di server. Surat PDF masih guna susun atur lama. Minta pentadbir tambah `xhtml2pdf` dalam requirements.txt (sekali sahaja).")
                _sample = {"NAMA":"ALI BIN ABU","IC":"800101-01-1234","JAWATAN":pilih,"SEKOLAH_ASAL":"BAA0001","NAMA_SEKOLAH_ASAL":"SK CONTOH","PUSAT":"BA001","NAMA_PUSAT":"SMK CONTOH","NO_SURAT":"JPNS.SPP 600-7/17/5 Jld.2 (01)","PPD":"BA","PPD_NAME":"KLANG","TARIKH":datetime.date.today().strftime("%d %B %Y"),"BILIK_KEBAL":"BK01"}
                _prev_html = edited
                for _k, _v in _sample.items():
                    _prev_html = re.sub(r"\{\{\s*" + re.escape(_k) + r"\s*\}\}", lambda m, _v=_v: _v, _prev_html, flags=re.IGNORECASE)
                    _prev_html = re.sub(r"\[" + re.escape(_k) + r"\]", lambda m, _v=_v: _v, _prev_html, flags=re.IGNORECASE)
                if st.checkbox("Preview", key=f"prev_check_{pilih}"):
                    import streamlit.components.v1 as _cv1
                    _cv1.html(_bungkus_html_surat(_prev_html), height=700, scrolling=True)
                _pdf_uji = html_to_pdf_bytes(_prev_html) if enjin_pdf_templat_ada() else None
                if _pdf_uji:
                    st.download_button("⬇️ Uji PDF (data contoh)", data=_pdf_uji, file_name=f"uji_{pilih.replace(' ','_')}.pdf", mime="application/pdf", key=f"uji_pdf_{pilih}")
            except Exception as e:
                st.error("Maaf, template tidak dapat dipaparkan. Sila cuba lagi.")

        elif menu == "sekolah":
            st.header("Semua Sekolah Master (369 Sekolah)")
            if fly_cur == "senarai":
                try:
                    res = supa.table("sekolah_master").select("*", count="exact").limit(5000).execute()
                    df_count = res.count
                    res2 = supa.table("sekolah_master").select("*").limit(1000).execute()
                    df = pd.DataFrame(res2.data or [])
                    st.write(f"Total dalam Supabase: **{df_count}** sekolah")
                    if not df.empty:
                        st.dataframe(df, use_container_width=True)
                        st.download_button("📥 Export Sekolah Master", to_excel(df), file_name="sekolah_master.xlsx")
                    else:
                        st.warning("sekolah_master kosong - belum push dari pusat_2026.csv. Sila import di bawah.")
                except Exception as e:
                    st.error(f"sekolah_master error: {e}")

            if fly_cur == "import":
                st.markdown("---")
                st.subheader("📤 Import Sekolah Master dari Pusat & Guru")
                st.info("File sekolah digenerate dari pusat_2026.csv (506 pusat = 369 sekolah unik) + guru 60K. Upload SEKOLAH_MASTER_FINAL_2026.xlsx untuk push masuk sekolah_master.")
                up_sek = st.file_uploader("Upload Sekolah Master Excel (KOD SEKOLAH, NAMA SEKOLAH, KOD PPD)", type=["xlsx", "csv"], key="sekolah_up")
                if up_sek:
                    try:
                        if up_sek.name.endswith(".csv"):
                            try: df_up = pd.read_csv(up_sek)
                            except:
                                up_sek.seek(0)
                                df_up = pd.read_csv(up_sek, encoding='latin1')
                        else:
                            df_up = pd.read_excel(up_sek)
                        st.write(f"Preview {len(df_up)} sekolah:")
                        st.dataframe(df_up.head(30), use_container_width=True)
                        if st.button(f"🚀 Import {len(df_up)} Sekolah ke Supabase", type="primary", use_container_width=True):
                            bar = st.progress(0)
                            stat = st.empty()
                            ok = 0
                            try:
                                supa.table("sekolah_master").delete().gt("id", 0).execute()
                                st.write("Old sekolah_master cleared")
                            except: pass
                            BATCH = 200
                            for start in range(0, len(df_up), BATCH):
                                end = min(start + BATCH, len(df_up))
                                bdf = df_up.iloc[start:end]
                                batch = []
                                for _, row in bdf.iterrows():
                                    try:
                                        kod = str(row.get("KOD SEKOLAH", "") or row.get("kod_sekolah", "") or row.get("KOD_SEKOLAH", "")).strip().upper()
                                        if not kod: continue
                                        nama = str(row.get("NAMA SEKOLAH", "") or row.get("nama_sekolah", "") or row.get("NAMA_PUSAT", "")).strip().upper()
                                        kod_ppd = str(row.get("KOD PPD", "") or row.get("kod_ppd", "") or row.get("PPD_CODE", "") or "BH").strip().upper()
                                        batch.append({"kod_sekolah": kod, "nama_sekolah": nama, "kod_ppd": kod_ppd, "data": {k: (" " if pd.isna(v) else str(v)) for k, v in row.to_dict().items()}})
                                    except: continue
                                if batch:
                                    try:
                                        supa.table("sekolah_master").insert(batch).execute()
                                        ok += len(batch)
                                    except Exception as e:
                                        st.warning(f"Batch {start}-{end}: {e}")
                                bar.progress(end / len(df_up))
                                stat.write(f"Progress {end}/{len(df_up)} | OK {ok}")
                            st.success(f"✅ Selesai import {ok}/{len(df_up)} sekolah!")
                            st.balloons()
                            st.rerun()
                    except Exception as e:
                        st.error("Maaf, berlaku masalah semasa memproses. Sila cuba lagi.")

            if fly_cur == "auto":
                st.markdown("---")
                st.subheader("Auto Generate Sekolah dari Pusat 506")
                if st.button("⚡ Generate Sekolah Master dari pusat_master yang sedia ada (506 pusat)", use_container_width=True):
                    try:
                        res = supa.table("pusat_master").select("*").limit(1000).execute()
                        df_p = pd.DataFrame(res.data or [])
                        if df_p.empty:
                            st.error("pusat_master kosong, import pusat dulu")
                        else:
                            sekolah_list = []
                            seen = set()
                            for _, r in df_p.iterrows():
                                d = r.get("data") or {}
                                kod_sek = d.get("KOD_SEKOLAH", "") or r.get("kod_sekolah", "") or ""
                                kod_sek = str(kod_sek).upper().strip()
                                if not kod_sek or kod_sek in seen: continue
                                seen.add(kod_sek)
                                sekolah_list.append({"kod_sekolah": kod_sek, "nama_sekolah": r.get("nama_pusat", "") or d.get("NAMA_PUSAT", ""), "kod_ppd": r.get("kod_ppd", "BH"), "data": {"KOD SEKOLAH": kod_sek, "NAMA SEKOLAH": r.get("nama_pusat", ""), "KOD PPD": r.get("kod_ppd", "BH")}})
                            if sekolah_list:
                                try: supa.table("sekolah_master").delete().gt("id", 0).execute()
                                except: pass
                                for i in range(0, len(sekolah_list), 200):
                                    supa.table("sekolah_master").insert(sekolah_list[i:i + 200]).execute()
                                st.success(f"✅ Generated {len(sekolah_list)} sekolah dari pusat_master!")
                                st.rerun()
                    except Exception as e:
                        st.error(f"Error generate: {e}")

        elif menu == "pusat":
            st.header("Pusat Master - Selangor 2026 (506 Pusat) - FIX Jumlah Calon".replace("2026", str(tahun_aktif())))
            try:
                total = safe_count("pusat_master")
                res = supa.table("pusat_master").select("*").limit(1000).execute()
                raw_data = res.data or []
                df = pd.DataFrame(raw_data)
                st.write(f"Total Pusat Sedia Ada: **{total}** / 506 pusat")
                display_rows = []
                for r in raw_data:
                    d = r.get("data") or {}
                    if isinstance(d, str):
                        try: d = json.loads(d)
                        except: d = {}
                    no_pusat = r.get("no_pusat") or r.get("kod_pusat") or d.get("NO_PUSAT") or d.get("KOD PUSAT") or ""
                    nama = r.get("nama_pusat") or d.get("NAMA_PUSAT") or ""
                    kod_sek = r.get("kod_sekolah_tuan_rumah") or r.get("kod_sekolah") or d.get("KOD_SEKOLAH") or ""
                    ppd = r.get("ppd") or d.get("PPD") or ""
                    j_calon = r.get("jumlah_calon") or r.get("calon") or r.get("JUMLAH_CALON") or d.get("JUMLAH_CALON") or d.get("CALON") or 0
                    j_kelas = r.get("jumlah_kelas") or r.get("bilik") or d.get("JUMLAH_KELAS") or d.get("BILIK") or 0
                    petugas = d.get("PETUGAS_NEEDED") or r.get("petugas_needed") or 0
                    try: j_calon_int = int(float(str(j_calon).replace(",", "").strip() or 0))
                    except: j_calon_int = 0
                    try: j_kelas_int = int(float(str(j_kelas).strip() or 0))
                    except: j_kelas_int = 0
                    display_rows.append({"NO_PUSAT": no_pusat, "NAMA_PUSAT": nama, "KOD_SEKOLAH": kod_sek, "PPD": ppd, "JUMLAH_CALON": j_calon_int, "JUMLAH_KELAS": j_kelas_int, "PETUGAS": petugas, "_id": r.get("id"), "_raw": r})

                df_display = pd.DataFrame(display_rows)
                if fly_cur == "senarai":
                    if not df_display.empty:
                        st.subheader(f"Senarai Pusat dengan Jumlah Calon (dari CSV)")
                        st.dataframe(df_display[["NO_PUSAT", "NAMA_PUSAT", "KOD_SEKOLAH", "PPD", "JUMLAH_CALON", "JUMLAH_KELAS", "PETUGAS"]].head(500), use_container_width=True)
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Total Calon", int(df_display["JUMLAH_CALON"].sum()))
                        c2.metric("Total Kelas", int(df_display["JUMLAH_KELAS"].sum()))
                        c3.metric("Ada Calon", len(df_display[df_display["JUMLAH_CALON"] > 0]))
                        if len(df_display[df_display["JUMLAH_CALON"] == 0]) > 100:
                            st.error(f"⚠️ {len(df_display[df_display['JUMLAH_CALON']==0])} pusat JUMLAH_CALON = 0 / kosong! Kena fix dari CSV.")
                        st.download_button("📥 Export Pusat dengan Calon", to_excel(pd.DataFrame(display_rows)), file_name="pusat_master_dengan_calon.xlsx")
                    else:
                        st.warning("pusat_master kosong")

                if fly_cur == "fix":
                    st.markdown("---")
                    st.subheader("🔧 FIX: Update Jumlah Calon yang Hilang")
                    st.info("Kalau JUMLAH_CALON 0/kosong, upload pusat_2026.csv untuk update balik 506 pusat dengan jumlah calon betul.")
                    up_fix = st.file_uploader("Upload pusat_2026.csv untuk FIX jumlah calon", type=["csv", "xlsx"], key="fix_calon")
                    if up_fix:
                        try:
                            if up_fix.name.endswith(".csv"):
                                try: df_fix = pd.read_csv(up_fix)
                                except:
                                    up_fix.seek(0)
                                    df_fix = pd.read_csv(up_fix, encoding='latin1')
                            else:
                                df_fix = pd.read_excel(up_fix)
                            st.write(f"File fix ada {len(df_fix)} baris")
                            st.dataframe(df_fix.head(10), use_container_width=True)
                            if st.button(f"🚀 FIX Update {len(df_fix)} Pusat dengan Jumlah Calon", type="primary", use_container_width=True):
                                bar = st.progress(0)
                                stat = st.empty()
                                ok = 0
                                fail = 0
                                for idx, row in df_fix.iterrows():
                                    try:
                                        no_pusat = str(row.get("NO_PUSAT", "") or row.get("KOD PUSAT", "")).upper().strip()
                                        if not no_pusat: continue
                                        j_calon = row.get("JUMLAH_CALON", "0")
                                        j_kelas = row.get("JUMLAH_KELAS", "0")
                                        update_data = {"jumlah_calon": int(float(str(j_calon).strip() or 0)), "jumlah_kelas": int(float(str(j_kelas).strip() or 0)), "calon": int(float(str(j_calon).strip() or 0)), "bilik": int(float(str(j_kelas).strip() or 0))}
                                        try:
                                            supa.table("pusat_master").update(update_data).eq("no_pusat", no_pusat).execute()
                                            ok += 1
                                        except:
                                            try:
                                                supa.table("pusat_master").update(update_data).eq("kod_pusat", no_pusat).execute()
                                                ok += 1
                                            except: fail += 1
                                    except: fail += 1
                                    if idx % 20 == 0:
                                        bar.progress((idx + 1) / len(df_fix))
                                        stat.write(f"Progress {idx+1}/{len(df_fix)} OK {ok} Fail {fail}")
                                bar.progress(1.0)
                                st.success(f"✅ FIX selesai! OK {ok} Fail {fail} | Refresh page untuk lihat jumlah calon masuk!")
                                st.balloons()
                        except Exception as e:
                            st.error(f"Error fix: {e}")
            except Exception as e:
                st.error(f"pusat_master error: {e}")
                st.code("""
-- SQL FIX: Tambah column jumlah_calon kalau belum ada - Run di Supabase SQL Editor:
ALTER TABLE pusat_master ADD COLUMN IF NOT EXISTS jumlah_calon INT DEFAULT 0;
ALTER TABLE pusat_master ADD COLUMN IF NOT EXISTS jumlah_kelas INT DEFAULT 0;
ALTER TABLE pusat_master ADD COLUMN IF NOT EXISTS calon INT DEFAULT 0;
ALTER TABLE pusat_master ADD COLUMN IF NOT EXISTS bilik INT DEFAULT 0;
ALTER TABLE pusat_master ADD COLUMN IF NOT EXISTS petugas_needed INT DEFAULT 0;
ALTER TABLE pusat_master ADD COLUMN IF NOT EXISTS kod_pusat TEXT;
ALTER TABLE pusat_master ADD COLUMN IF NOT EXISTS nama_pusat TEXT;
""", language="sql")

            st.markdown("---")
            col1, col2 = st.columns(2)
            if fly_cur == "tambah":
                st.subheader("➕ Tambah Pusat Manual - Auto Kira SPM")
                st.caption("Formula: 1 kelas=20 calon, CEIL(calon/20)=kelas, petugas=kelas+9, sekolah perlu calonkan=kelas+12 (petugas+KP+TKP+Penyelia)")
                with st.form("tambah_pusat"):
                    kod_pusat = st.text_input("KOD PUSAT * (cth: BA001)")
                    nama_pusat = st.text_input("NAMA PUSAT *")
                    kod_ppd_pusat = st.selectbox("KOD PPD", KOD_DAERAH, format_func=lambda x: f"{x}-{PPD_MAP[x]}")
                    alamat_pusat = st.text_area("ALAMAT PUSAT (KOD SEKOLAH)")
                    calon_input = st.number_input("JUMLAH CALON * (contoh 105)", min_value=1, value=100, step=1, help="1 kelas = 20 calon. Auto kira kelas & petugas")
                    kelas_preview = kira_kelas_dari_calon(calon_input)
                    petugas_preview = kira_petugas_dari_kelas(kelas_preview)
                    sekolah_need_preview = kira_sekolah_perlu_calonkan(kelas_preview)
                    st.info(f" Auto Kira: {calon_input} calon → {kelas_preview} kelas (20/kelas) → {petugas_preview} petugas (kelas+9) → Sekolah perlu calonkan {sekolah_need_preview} orang (petugas+KP+TKP+Penyelia)")
                    submit_pusat = st.form_submit_button("💾 Simpan Pusat (Auto Kira)", type="primary", use_container_width=True)
                    if submit_pusat:
                        if not kod_pusat or not nama_pusat:
                            st.error("Kod & Nama Pusat wajib!")
                        else:
                            try:
                                kelas_calc = kira_kelas_dari_calon(calon_input)
                                petugas_calc = kira_petugas_dari_kelas(kelas_calc)
                                sekolah_need = kira_sekolah_perlu_calonkan(kelas_calc)
                                supa.table("pusat_master").insert({"kod_pusat": kod_pusat.upper(), "nama_pusat": nama_pusat.upper(), "kod_ppd": kod_ppd_pusat, "ppd": PPD_MAP.get(kod_ppd_pusat, ""), "alamat": alamat_pusat, "bilik": kelas_calc, "calon": int(calon_input), "jumlah_calon": int(calon_input), "jumlah_kelas": kelas_calc, "petugas_needed": petugas_calc, "data": {"NO_PUSAT": kod_pusat.upper(), "NAMA_PUSAT": nama_pusat.upper(), "KOD PPD": kod_ppd_pusat, "KOD_SEKOLAH": alamat_pusat, "JUMLAH_CALON": str(calon_input), "JUMLAH_KELAS": str(kelas_calc), "PETUGAS_NEEDED": str(petugas_calc), "SEKOLAH_PERLU_CALON": str(sekolah_need), "FORMULA": f"{calon_input} calon /20 = {kelas_calc} kelas, {kelas_calc}+9={petugas_calc} petugas, +3 KP/TKP/Penyelia = {sekolah_need} sekolah perlu calon"}}).execute()
                                st.success(f"✅ Pusat {kod_pusat} berjaya tambah! {calon_input} calon = {kelas_calc} kelas, {petugas_calc} petugas, sekolah perlu {sekolah_need} orang")
                                st.balloons()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Gagal: {e}")

            if fly_cur == "import":
                st.subheader("📤 Import Excel/CSV Pusat (Batch)")
                st.info("Support: pusat_2026.csv (NO_PUSAT format) & Excel KOD PUSAT format | 506 pusat")
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    st.download_button("📥 Template Pusat", to_excel(pd.DataFrame([{"KOD PUSAT": "BA001", "NAMA PUSAT": "SMK DATO HAMZAH", "KOD PPD": "BA", "ALAMAT PUSAT": "Jalan Dato Hamzah", "BILIK": 10, "CALON": 250}])), "TEMPLATE_PUSAT.xlsx")
                with col_t2:
                    st.download_button("📥 Sample pusat_2026.csv", open("/mnt/data/pusat_2026.csv", "rb").read() if __import__("os").path.exists("/mnt/data/pusat_2026.csv") else b"", "pusat_2026_sample.csv")

                up = st.file_uploader("Upload Excel/CSV Pusat (Excel atau CSV)", type=["xlsx", "csv"], key="pusat_up")
                if up:
                    try:
                        if up.name.endswith(".csv"):
                            try: df_up = pd.read_csv(up)
                            except:
                                up.seek(0)
                                df_up = pd.read_csv(up, encoding='latin1')
                        else:
                            df_up = pd.read_excel(up)
                        st.write(f"Preview {len(df_up)} pusat:")
                        st.dataframe(df_up.head(20), use_container_width=True)
                        if st.button(f"🚀 Import {len(df_up)} Pusat (Batch 200)", type="primary", use_container_width=True):
                            bar = st.progress(0)
                            stat = st.empty()
                            ok = 0
                            BATCH = 200
                            ppd_name_map = {"klang": "BA", "kuala langat": "BB", "kuala selangor": "BC", "hulu langat": "BD", "hulu selangor": "BE", "sabak bernam": "BF", "gombak": "BG", "petaling perdana": "BH", "sepang": "BJ", "petaling utama": "BK"}
                            for start in range(0, len(df_up), BATCH):
                                end = min(start + BATCH, len(df_up))
                                bdf = df_up.iloc[start:end]
                                batch = []
                                for _, row in bdf.iterrows():
                                    try:
                                        d = {}
                                        for k, v in row.to_dict().items():
                                            d[k] = " " if pd.isna(v) else str(v)
                                        kod_p = d.get("NO_PUSAT", "") or d.get("KOD PUSAT", "") or d.get("kod_pusat", "")
                                        kod_p = kod_p.upper().strip()
                                        if not kod_p: continue
                                        kod_ppd_val = d.get("KOD PPD", "") or d.get("KOD_PPD", "") or d.get("PPD_CODE", "")
                                        if not kod_ppd_val:
                                            ppd_raw = d.get("PPD", "").lower()
                                            for name, code in ppd_name_map.items():
                                                if name in ppd_raw:
                                                    kod_ppd_val = code
                                                    break
                                        if not kod_ppd_val: kod_ppd_val = "BH"
                                        kod_ppd_val = kod_ppd_val.upper().strip()
                                        nama_p = d.get("NAMA_PUSAT", "") or d.get("NAMA PUSAT", "") or kod_p
                                        bilik_val = d.get("JUMLAH_KELAS", "") or d.get("BILIK", "") or "10"
                                        calon_val = d.get("JUMLAH_CALON", "") or d.get("CALON", "") or "200"
                                        try: bilik_int = int(float(bilik_val))
                                        except: bilik_int = 10
                                        try: calon_int = int(float(calon_val))
                                        except: calon_int = 200
                                        batch.append({"kod_pusat": kod_p, "nama_pusat": nama_p.upper(), "kod_ppd": kod_ppd_val, "ppd": d.get("PPD", "") or PPD_MAP.get(kod_ppd_val, ""), "alamat": d.get("KOD_SEKOLAH", "") or d.get("ALAMAT PUSAT", "") or d.get("ALAMAT", ""), "bilik": bilik_int, "calon": calon_int, "data": d})
                                    except: continue
                                if batch:
                                    try:
                                        supa.table("pusat_master").insert(batch).execute()
                                        ok += len(batch)
                                    except Exception as e:
                                        st.warning(f"Batch {start}-{end}: {e}")
                                bar.progress(end / len(df_up))
                                stat.write(f"Progress {end}/{len(df_up)} | OK {ok}")
                            st.success(f"✅ Selesai import {ok}/{len(df_up)} pusat! Total 506")
                            st.balloons()
                            st.rerun()
                    except Exception as e:
                        st.error("Maaf, berlaku masalah semasa memproses. Sila cuba lagi.")

            if fly_cur == "kosong":
                st.markdown("---")
                if st.button("🗑️ Kosongkan Semua Pusat (Hati-hati!)", type="secondary"):
                    try:
                        supa.table("pusat_master").delete().gt("id", 0).execute()
                        st.success("Semua pusat dipadam")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

        elif menu == "guru":
            st.header("Guru Master Seluruh Negeri")
            if fly_cur == "import":
                st.subheader(" Import MASTER 60K Guru Selangor")
                st.info("Upload file MASTER-GURU-SELANGOR-2026.xlsx (60K) di sini untuk restore balik data yang hilang. Guna batch 500 untuk laju.")
                up_master = st.file_uploader("Upload MASTER 60K Excel", type=["xlsx"], key="master60k")
                if up_master:
                    try:
                        df_m = pd.read_excel(up_master, sheet_name=0)
                        st.write(f"File ada {len(df_m)} baris.")
                        st.dataframe(df_m.head(10), use_container_width=True)
                        if st.button(f"🚀 Import {len(df_m)} Guru ke Supabase (Batch 500)", type="primary", use_container_width=True):
                            bar = st.progress(0)
                            stat = st.empty()
                            ok = 0
                            BATCH = 500
                            for start in range(0, len(df_m), BATCH):
                                end = min(start + BATCH, len(df_m))
                                bdf = df_m.iloc[start:end]
                                batch = []
                                for _, row in bdf.iterrows():
                                    try:
                                        d = {}
                                        for k, v in row.to_dict().items():
                                            d[k] = "" if pd.isna(v) else str(v)
                                        nama = d.get("NAMA GURU", "").upper().strip()
                                        if not nama or nama == "NAN": continue
                                        batch.append({
                                            "kod_ppd": d.get("KOD PPD", "").lower().strip(),
                                            "kod_sekolah": d.get("KOD SEKOLAH", "").upper().strip(),
                                            "nama_guru": nama,
                                            "ic_guru": d.get("IC", ""),
                                            "jantina": d.get("JANTINA",""),
                                            "poskod_rumah": d.get("POSKOD RUMAH","") or d.get("POSKOD_RUMAH",""),
                                            "alamat_rumah": d.get("ALAMAT RUMAH","") or d.get("ALAMAT_RUMAH",""),
                                            "telefon_guru": d.get("NO TELEFON GURU","") or d.get("TELEFON_GURU",""),
                                            "email_guru": d.get("EMAIL GURU","") or d.get("EMAIL_GURU",""),
                                            "pengalaman_spm": d.get("PENGALAMAN SPM","") or d.get("PENGALAMAN_SPM",""),
                                            "kod_sekolah_asal": d.get("KOD SEKOLAH","").upper().strip(),
                                            "nama_sekolah_asal": d.get("NAMA SEKOLAH",""),
                                            "no_pusat_asal": "BA142",
                                            "data": d
                                        })
                                    except: continue
                                if batch:
                                    try:
                                        supa.table("guru_master").insert(batch).execute()
                                        ok += len(batch)
                                    except Exception as e:
                                        st.error(f"Batch {start}-{end} error: {e}")
                                bar.progress(end / len(df_m))
                                stat.write(f"Imported {end}/{len(df_m)} | OK {ok}")
                            st.success(f"✅ Selesai import {ok}/{len(df_m)} guru!")
                            st.balloons()
                    except Exception as e:
                        st.error("Maaf, berlaku masalah semasa memproses. Sila cuba lagi.")

            if fly_cur == "data":
                st.markdown("---")
                st.subheader("Data Sedia Ada")
                try:
                    res = supa.table("guru_master").select("*", count="exact").limit(5000).execute()
                    df = pd.DataFrame(res.data or [])
                    st.write(f"Total dalam Supabase: {res.count} records")
                    if not df.empty:
                        st.dataframe(df.head(100), use_container_width=True)
                        st.download_button("Export Guru Master (5000)", to_excel(df), file_name="guru_master_full.xlsx")
                except Exception as e:
                    st.error(str(e))

        elif menu == "cadangan":
            st.header("Semua Cadangan Seluruh Negeri")
            try:
                res = supa.table("cadangan_sup").select("*").limit(10000).execute()
                df = pd.DataFrame(res.data or [])
                st.dataframe(df, use_container_width=True)
                if not df.empty:
                    st.download_button("Export Semua Cadangan", to_excel(df), file_name=f"cadangan_negeri_{datetime.date.today()}.xlsx")
            except Exception as e:
                st.error(str(e))


        elif menu == "jana_surat":
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #0d47a1 0%, #1976d2 100%); padding:20px; border-radius:12px; color:white; margin-bottom:20px;">
                <h2 style="margin:0; color:white;">📄 Janaan Surat Lantikan - PPD {kod_ppd} - {PPD_MAP.get(kod_ppd,'')}</h2>
                <p style="margin:5px 0 0 0; color:#bbdefb;">Surat yang telah diluluskan PPD - PPD boleh lihat, jana semula & download PDF. Surat yang sama juga dihantar ke sekolah asal guru untuk SUP cetak.</p>
            </div>
            """, unsafe_allow_html=True)

            df_cad_all_surat = get_cadangan_df(kod_ppd=kod_ppd)
            if df_cad_all_surat.empty:
                st.warning("Belum ada cadangan di PPD ini")
                st.stop()

            # Build pusat map
            df_pusat_raw_surat = get_pusat_df()
            pusat_map_surat = {}
            try:
                for _, r in df_pusat_raw_surat.iterrows():
                    d = r.get("data") if isinstance(r.get("data"), dict) else {}
                    if isinstance(d, str):
                        try: d = json.loads(d)
                        except: d = {}
                    no_p = str(r.get("no_pusat") or r.get("kod_pusat") or d.get("NO_PUSAT") or "").upper().strip()
                    nama_p = r.get("nama_pusat") or d.get("NAMA_PUSAT") or ""
                    if no_p:
                        pusat_map_surat[no_p] = nama_p
            except:
                pass

            # Filter yang ada no_surat / sudah LULUS
            def has_surat_ppd(row):
                ns = str(row.get("no_surat") or "").strip()
                stt = str(row.get("status") or "").upper()
                return (ns != "" and ns.lower() not in ("none","null","nan")) or ("LULUS" in stt)

            df_lulus_surat = df_cad_all_surat[df_cad_all_surat.apply(has_surat_ppd, axis=1)].copy() if not df_cad_all_surat.empty else pd.DataFrame()
            df_belum_surat = df_cad_all_surat[~df_cad_all_surat.apply(has_surat_ppd, axis=1)].copy() if not df_cad_all_surat.empty else pd.DataFrame()

            c1, c2, c3 = st.columns(3)
            c1.metric("Total Cadangan PPD", len(df_cad_all_surat))
            c2.metric("✅ Sudah Lulus Ada Surat", len(df_lulus_surat))
            c3.metric("⏳ Belum Ada Surat", len(df_belum_surat))

            if df_lulus_surat.empty:
                st.warning("Belum ada surat yang diluluskan di PPD ini - sila luluskan di menu Kelulusan dahulu")
                st.info("Pergi ke Kelulusan > Lulus Keseluruhan atau Lulus Mengikut Pusat untuk luluskan dan jana surat")
                st.stop()

            # Tabs for view
            tab_keseluruhan, tab_pusat_surat, tab_sekolah_asal = st.tabs(["📄 Semua Surat (Keseluruhan)", "🏫 Ikut Pusat", "🏫 Ikut Sekolah Asal (Untuk Hantar)"])

            with tab_keseluruhan:
                st.markdown(f"### 📄 Semua Surat Lantikan PPD {kod_ppd} - {len(df_lulus_surat)} Surat - Template JPN Selaras")
                st.info(f"🔹 Template surat diambil dari function JPN `surat_templates_jpn` - JPN cipta, PPD guna. Jika JPN belum cipta template untuk jawatan, akan guna fallback PPD.")

                display_rows = []
                for _, r in df_lulus_surat.iterrows():
                    display_rows.append({
                        "id": r.get("id",""),
                        "NAMA GURU": r.get("NAMA_GURU","") or r.get("nama_guru",""),
                        "IC": r.get("IC_GURU","") or r.get("ic_guru",""),
                        "JAWATAN": r.get("JAWATAN_CADANGAN","") or r.get("jawatan_cadangan",""),
                        "SEKOLAH ASAL": r.get("KOD_SEKOLAH_ASAL","") or r.get("kod_sekolah_asal",""),
                        "NAMA SEKOLAH ASAL": str(r.get("NAMA_SEKOLAH_ASAL","") or r.get("nama_sekolah_asal",""))[:30],
                        "PUSAT TUGAS": r.get("kod_pusat","") or r.get("KOD_PUSAT",""),
                        "NAMA PUSAT": pusat_map_surat.get(str(r.get("kod_pusat","") or "").upper().strip(), "")[:30],
                        "NO SURAT": r.get("no_surat","") or "",
                        "STATUS": r.get("status","") or ""
                    })
                df_display_all = pd.DataFrame(display_rows)
                st.dataframe(df_display_all, use_container_width=True, hide_index=True)

                # ===== NEW V33: JANA DENGAN TEMPLATE JPN + ZIP + HANTAR KE SEKOLAH ASAL =====
                col_gen1, col_gen2, col_gen3 = st.columns(3)
                with col_gen1:
                    if st.button(f"📄 Jana Surat {len(df_display_all)} (Template JPN)", type="primary", use_container_width=True, key="btn_jana_pdf_keseluruhan_v33"):
                        with st.spinner(f"Menjana {len(df_display_all)} surat guna template JPN..."):
                            try:
                                surat_list = []
                                for _, r in df_display_all.iterrows():
                                    surat_list.append({
                                        "nama": r["NAMA GURU"],
                                        "ic": r["IC"],
                                        "jawatan": r["JAWATAN"],
                                        "sekolah_asal": r["SEKOLAH ASAL"],
                                        "nama_sekolah_asal": r["NAMA SEKOLAH ASAL"],
                                        "pusat": r["PUSAT TUGAS"],
                                        "nama_pusat": r["NAMA PUSAT"],
                                        "no_surat": r["NO SURAT"]
                                    })
                                # 1. PDF Kolektif guna JPN template
                                pdf_kolektif = generate_surat_kolektif_pdf_bytes_JPN(surat_list, kod_ppd, PPD_MAP.get(kod_ppd,""), f"SURAT LANTIKAN KESELURUHAN PPD {kod_ppd} - {len(surat_list)} GURU - JPN SELARAS")
                                if pdf_kolektif:
                                    st.session_state[f"pdf_keseluruhan_{kod_ppd}"] = pdf_kolektif
                                # 2. ZIP Pukal individu guna JPN template
                                zip_bytes = create_zip_pukal_dari_JPN(surat_list, kod_ppd, PPD_MAP.get(kod_ppd,""))
                                if zip_bytes:
                                    st.session_state[f"zip_keseluruhan_{kod_ppd}"] = zip_bytes
                                # 3. Hantar ke sekolah asal petugas (auto update status)
                                jml_hantar = hantar_surat_ke_sekolah_asal_bulk(surat_list, kod_ppd)
                                st.session_state[f"surat_list_keseluruhan_{kod_ppd}"] = surat_list
                                st.success(f"✅ Berjaya! {len(surat_list)} surat dijana guna template JPN, {jml_hantar} surat sampai ke sekolah asal!")
                                st.balloons()
                            except Exception as e:
                                st.error("Maaf, surat tidak dapat dijana. Sila cuba lagi atau hubungi pentadbir sistem.")

                with col_gen2:
                    if f"pdf_keseluruhan_{kod_ppd}" in st.session_state:
                        pdf_data = st.session_state[f"pdf_keseluruhan_{kod_ppd}"]
                        st.download_button(f"📥 Download PDF Pukal Kolektif {len(df_display_all)} Surat (Template JPN)", data=pdf_data, file_name=f"Surat_Kolektif_JPN_{kod_ppd}_{datetime.date.today()}.pdf", mime="application/pdf", use_container_width=True, key="dl_pdf_keseluruhan_main_v33")
                    else:
                        st.caption("Belum jana PDF kolektif")

                with col_gen3:
                    if f"zip_keseluruhan_{kod_ppd}" in st.session_state:
                        zip_data = st.session_state[f"zip_keseluruhan_{kod_ppd}"]
                        st.download_button(f"📦 Download ZIP Pukal Individu {len(df_display_all)} PDF (Template JPN)", data=zip_data, file_name=f"ZIP_Surat_Individu_JPN_{kod_ppd}_{datetime.date.today()}.zip", mime="application/zip", use_container_width=True, key="dl_zip_keseluruhan_main_v33", type="primary")
                        st.caption(f"✅ {len(df_display_all)} fail PDF individu dalam ZIP - senang edar")
                    else:
                        st.caption("Belum jana ZIP pukal")

                # Preview if exists
                if f"pdf_keseluruhan_{kod_ppd}" in st.session_state:
                    st.success(f"✅ PDF & ZIP telah dijana guna template JPN. Surat auto sampai ke sekolah asal guru untuk SUP cetak. ({len(df_display_all)} surat)")
                    # Tunjuk breakdown ikut sekolah asal
                    if f"surat_list_keseluruhan_{kod_ppd}" in st.session_state:
                        sl = st.session_state[f"surat_list_keseluruhan_{kod_ppd}"]
                        from collections import Counter
                        cnt = Counter([s.get("sekolah_asal","") for s in sl])
                        st.markdown("**📊 Surat sampai ke sekolah asal:**")
                        cols = st.columns(4)
                        for i, (sek, jml) in enumerate(cnt.most_common(12)):
                            cols[i % 4].metric(sek, f"{jml} surat")

            with tab_pusat_surat:
                st.markdown("### 🏫 Janaan Surat Ikut Pusat - Template JPN + ZIP")
                st.info("Guna template JPN selaras, jana PDF kolektif + ZIP pukal individu, auto sampai ke sekolah asal")
                # Group by pusat
                pusat_groups_surat = {}
                for _, r in df_lulus_surat.iterrows():
                    kp = str(r.get("kod_pusat") or r.get("KOD_PUSAT") or "").upper().strip()
                    if kp:
                        if kp not in pusat_groups_surat:
                            pusat_groups_surat[kp] = []
                        pusat_groups_surat[kp].append(r)

                pilih_pusat_jana = st.selectbox(
                    "Pilih Pusat Untuk Jana Surat PDF",
                    sorted(pusat_groups_surat.keys()),
                    format_func=lambda x: f"{x} - {pusat_map_surat.get(x,'')} ({len(pusat_groups_surat[x])} surat)",
                    key="pilih_pusat_jana_surat"
                )

                if pilih_pusat_jana:
                    guru_pusat = pusat_groups_surat[pilih_pusat_jana]
                    df_pusat_surat = pd.DataFrame([{
                        "NAMA GURU": r.get("NAMA_GURU","") or r.get("nama_guru",""),
                        "IC": r.get("IC_GURU","") or r.get("ic_guru",""),
                        "JAWATAN": r.get("JAWATAN_CADANGAN","") or r.get("jawatan_cadangan",""),
                        "SEKOLAH ASAL": r.get("KOD_SEKOLAH_ASAL","") or r.get("kod_sekolah_asal",""),
                        "NO SURAT": r.get("no_surat",""),
                        "STATUS": r.get("status","")
                    } for r in guru_pusat])
                    st.dataframe(df_pusat_surat, use_container_width=True, hide_index=True)

                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button(f"📄 Jana {len(guru_pusat)} Surat {pilih_pusat_jana} (JPN + ZIP)", type="primary", use_container_width=True, key=f"btn_jana_pdf_pusat_{pilih_pusat_jana}_v33"):
                            with st.spinner(f"Menjana {len(guru_pusat)} surat..."):
                                try:
                                    surat_list_p = []
                                    for r in guru_pusat:
                                        surat_list_p.append({
                                            "nama": r.get("NAMA_GURU","") or r.get("nama_guru",""),
                                            "ic": r.get("IC_GURU","") or r.get("ic_guru",""),
                                            "jawatan": r.get("JAWATAN_CADANGAN","") or r.get("jawatan_cadangan",""),
                                            "sekolah_asal": r.get("KOD_SEKOLAH_ASAL","") or r.get("kod_sekolah_asal",""),
                                            "nama_sekolah_asal": r.get("NAMA_SEKOLAH_ASAL","") or r.get("nama_sekolah_asal",""),
                                            "pusat": r.get("kod_pusat","") or r.get("KOD_PUSAT",""),
                                            "nama_pusat": pusat_map_surat.get(str(r.get("kod_pusat","") or "").upper().strip(), ""),
                                            "no_surat": r.get("no_surat","")
                                        })
                                    pdf_pusat = generate_surat_kolektif_pdf_bytes_JPN(surat_list_p, kod_ppd, PPD_MAP.get(kod_ppd,""), f"SURAT LANTIKAN {pilih_pusat_jana} - {pusat_map_surat.get(pilih_pusat_jana,'')} - JPN SELARAS")
                                    zip_pusat = create_zip_pukal_dari_JPN(surat_list_p, kod_ppd, PPD_MAP.get(kod_ppd,""))
                                    jml_hantar = hantar_surat_ke_sekolah_asal_bulk(surat_list_p, kod_ppd)
                                    if pdf_pusat:
                                        st.session_state[f"pdf_pusat_{pilih_pusat_jana}"] = pdf_pusat
                                    if zip_pusat:
                                        st.session_state[f"zip_pusat_{pilih_pusat_jana}"] = zip_pusat
                                    st.success(f"✅ PDF+ZIP {pilih_pusat_jana} {len(surat_list_p)} surat berjaya dijana (Template JPN) + {jml_hantar} sampai sekolah asal!")
                                except Exception as e:
                                    st.error("Maaf, berlaku masalah semasa memproses. Sila cuba lagi.")
                    with c2:
                        if f"pdf_pusat_{pilih_pusat_jana}" in st.session_state:
                            pdf_d = st.session_state[f"pdf_pusat_{pilih_pusat_jana}"]
                            st.download_button(f"📥 PDF Kolektif {pilih_pusat_jana} ({len(guru_pusat)}) - JPN", data=pdf_d, file_name=f"Surat_{pilih_pusat_jana}_{kod_ppd}_{datetime.date.today()}_JPN.pdf", mime="application/pdf", use_container_width=True, key=f"dl_pdf_pusat_{pilih_pusat_jana}_v33")
                        if f"zip_pusat_{pilih_pusat_jana}" in st.session_state:
                            zip_d = st.session_state[f"zip_pusat_{pilih_pusat_jana}"]
                            st.download_button(f"📦 ZIP Pukal Individu {pilih_pusat_jana} ({len(guru_pusat)}) - JPN", data=zip_d, file_name=f"ZIP_{pilih_pusat_jana}_{kod_ppd}_{datetime.date.today()}_JPN.zip", mime="application/zip", use_container_width=True, key=f"dl_zip_pusat_{pilih_pusat_jana}_v33", type="primary")
                        if f"pdf_pusat_{pilih_pusat_jana}" in st.session_state:
                            st.info(f"Surat {pilih_pusat_jana} auto sampai ke sekolah asal guru untuk SUP cetak")

            with tab_sekolah_asal:
                st.markdown("### 🏫 Surat Ikut Sekolah Asal - Untuk Hantar ke SUP Cetak - Template JPN + ZIP")
                st.caption("Surat yang telah diluluskan akan sampai ke sekolah asal guru - SUP boleh cetak dan bagi pada guru berkenaan. Guna template JPN selaras + ZIP pukal.")

                # Group by sekolah asal
                sekolah_groups_surat = {}
                for _, r in df_lulus_surat.iterrows():
                    ks = str(r.get("KOD_SEKOLAH_ASAL") or r.get("kod_sekolah_asal") or "").upper().strip()
                    if ks:
                        if ks not in sekolah_groups_surat:
                            sekolah_groups_surat[ks] = []
                        sekolah_groups_surat[ks].append(r)

                pilih_sekolah_surat = st.selectbox(
                    "Pilih Sekolah Asal Untuk Lihat Surat Yang Sampai",
                    sorted(sekolah_groups_surat.keys()),
                    format_func=lambda x: f"{x} - {len(sekolah_groups_surat[x])} surat sampai (untuk SUP cetak) - Template JPN",
                    key="pilih_sekolah_surat_jana"
                )

                if pilih_sekolah_surat:
                    guru_sekolah = sekolah_groups_surat[pilih_sekolah_surat]
                    df_sek_surat = pd.DataFrame([{
                        "NAMA GURU": r.get("NAMA_GURU","") or r.get("nama_guru",""),
                        "IC": r.get("IC_GURU","") or r.get("ic_guru",""),
                        "JAWATAN": r.get("JAWATAN_CADANGAN","") or r.get("jawatan_cadangan",""),
                        "PUSAT TUGAS": r.get("kod_pusat","") or r.get("KOD_PUSAT",""),
                        "NAMA PUSAT": pusat_map_surat.get(str(r.get("kod_pusat","") or "").upper().strip(), "")[:30],
                        "NO SURAT": r.get("no_surat",""),
                        "STATUS": r.get("status","")
                    } for r in guru_sekolah])
                    st.dataframe(df_sek_surat, use_container_width=True, hide_index=True)
                    st.success(f"✅ {len(guru_sekolah)} surat telah sampai ke sekolah asal {pilih_sekolah_surat} - SUP boleh cetak (Template JPN)")

                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button(f"📄 Jana PDF {pilih_sekolah_surat} - {len(guru_sekolah)} Guru (JPN+ZIP)", type="primary", use_container_width=True, key=f"btn_jana_pdf_sekolah_{pilih_sekolah_surat}_v33"):
                            with st.spinner(f"Menjana {len(guru_sekolah)} surat sekolah asal..."):
                                try:
                                    surat_list_s = []
                                    for r in guru_sekolah:
                                        surat_list_s.append({
                                            "nama": r.get("NAMA_GURU","") or r.get("nama_guru",""),
                                            "ic": r.get("IC_GURU","") or r.get("ic_guru",""),
                                            "jawatan": r.get("JAWATAN_CADANGAN","") or r.get("jawatan_cadangan",""),
                                            "sekolah_asal": r.get("KOD_SEKOLAH_ASAL","") or r.get("kod_sekolah_asal",""),
                                            "nama_sekolah_asal": r.get("NAMA_SEKOLAH_ASAL","") or r.get("nama_sekolah_asal","") or pilih_sekolah_surat,
                                            "pusat": r.get("kod_pusat","") or r.get("KOD_PUSAT",""),
                                            "nama_pusat": pusat_map_surat.get(str(r.get("kod_pusat","") or "").upper().strip(), ""),
                                            "no_surat": r.get("no_surat","")
                                        })
                                    pdf_sek = generate_surat_kolektif_pdf_bytes_JPN(surat_list_s, kod_ppd, PPD_MAP.get(kod_ppd,""), f"SURAT LANTIKAN SEKOLAH ASAL {pilih_sekolah_surat} - {len(surat_list_s)} GURU - UNTUK SUP CETAK - JPN SELARAS")
                                    zip_sek = create_zip_pukal_dari_JPN(surat_list_s, kod_ppd, PPD_MAP.get(kod_ppd,""))
                                    if pdf_sek:
                                        st.session_state[f"pdf_sekolah_{pilih_sekolah_surat}"] = pdf_sek
                                    if zip_sek:
                                        st.session_state[f"zip_sekolah_{pilih_sekolah_surat}"] = zip_sek
                                    st.success(f"✅ PDF+ZIP Sekolah Asal {pilih_sekolah_surat} {len(surat_list_s)} surat berjaya dijana (JPN)!")
                                except Exception as e:
                                    st.error("Maaf, berlaku masalah semasa memproses. Sila cuba lagi.")
                    with c2:
                        if f"pdf_sekolah_{pilih_sekolah_surat}" in st.session_state:
                            pdf_s = st.session_state[f"pdf_sekolah_{pilih_sekolah_surat}"]
                            st.download_button(f"📥 PDF Sekolah Asal {pilih_sekolah_surat} ({len(guru_sekolah)}) - JPN", data=pdf_s, file_name=f"Surat_SekolahAsal_{pilih_sekolah_surat}_{kod_ppd}_{datetime.date.today()}_JPN.pdf", mime="application/pdf", use_container_width=True, key=f"dl_pdf_sekolah_{pilih_sekolah_surat}_v33")
                        if f"zip_sekolah_{pilih_sekolah_surat}" in st.session_state:
                            zip_s = st.session_state[f"zip_sekolah_{pilih_sekolah_surat}"]
                            st.download_button(f"📦 ZIP Sekolah Asal {pilih_sekolah_surat} ({len(guru_sekolah)}) - JPN", data=zip_s, file_name=f"ZIP_SekolahAsal_{pilih_sekolah_surat}_{kod_ppd}_{datetime.date.today()}_JPN.zip", mime="application/zip", use_container_width=True, key=f"dl_zip_sekolah_{pilih_sekolah_surat}_v33", type="primary")
                        if f"pdf_sekolah_{pilih_sekolah_surat}" in st.session_state:
                            st.info(f"📄 Surat ini akan dicetak oleh SUP {pilih_sekolah_surat} dan diberi kepada guru berkenaan (Template JPN selaras)")



        elif menu == "export":
            st.header("Export Laporan Negeri")
            try:
                res = supa.table("cadangan_sup").select("*").limit(10000).execute()
                df = pd.DataFrame(res.data or [])
                if not df.empty:
                    st.download_button("📥 Laporan Penuh Negeri (Excel)", to_excel(df), file_name=f"Laporan_JPN_Selangor_{datetime.date.today()}.xlsx", use_container_width=True, type="primary")
            except Exception as e:
                st.error(str(e))

        elif menu == "admin":
            st.header("⚙️ Status Sistem & Sambungan Pangkalan Data")
            if fly_cur == "status":
                for t in ["sekolah_master", "pusat_master", "guru_master", "cadangan_sup"]:
                    try:
                        res = supa.table(t).select("*", count="exact").limit(1).execute()
                        st.success(f"✅ {t}: {res.count} records")
                    except Exception as e:
                        st.error(f"❌ {t}: {e}")
            if fly_cur == "tahun":
                st.subheader(f"📅 Urus Tahun Peperiksaan (tahun dipilih sekarang: {tahun_aktif()})")
                st.caption("Pilih tahun di bahagian atas mana-mana page. Data guru, pusat, bilik kebal, cadangan SUP dan surat dibaca/disimpan ikut tahun dipilih.")
                st.markdown("#### 1) Status migrasi pangkalan data")
                _stat_m = status_migrasi_tahun()
                for _t, _ok in _stat_m.items():
                    if (not _ok) and _t == "surat_hantar_sekolah_asal":
                        st.info(f"ℹ️ {_t}: jadual pilihan - boleh diabaikan jika belum wujud")
                        continue
                    (st.success if _ok else st.error)(f"{'✅' if _ok else '❌'} {_t}: {'lajur tahun sedia' if _ok else 'lajur tahun BELUM ada - jalankan SQL di bawah'}")
                if st.button("🔄 Semak semula status", key="btn_semak_migrasi"):
                    st.cache_data.clear()
                    st.rerun()
                with st.expander("📋 SQL migrasi (jalankan SEKALI di Supabase → SQL Editor)", expanded=not all(v for k, v in _stat_m.items() if k != "surat_hantar_sekolah_asal")):
                    st.code(SQL_MIGRASI_TAHUN, language="sql")
                    st.caption("Data sedia ada automatik ditanda tahun 2026. Selepas SQL berjaya, tekan 'Semak semula status'.")
                st.markdown("---")
                st.markdown("#### 2) Salin data guru / pusat ke tahun baharu")
                st.caption("Cadangan SUP TIDAK disalin - sentiasa kosong bagi tahun baharu sehingga SUP buat cadangan. Nombor surat juga bermula semula.")
                _c1, _c2 = st.columns(2)
                with _c1:
                    _asal = st.selectbox("Salin DARI tahun", TAHUN_PILIHAN, index=0, key="salin_asal")
                with _c2:
                    _tuju = st.selectbox("Salin KE tahun", TAHUN_PILIHAN, index=1, key="salin_tuju")
                _jad = st.multiselect("Jadual untuk disalin", ["guru_master", "pusat_master", "bilik_kebal_master"], default=["guru_master", "pusat_master"], key="salin_jadual")
                st.caption("bilik_kebal_master: penempatan penyelia tahun asal turut tersalin - semak semula selepas salin.")
                _timpa = st.checkbox("Ganti data tahun tuju (PADAM data tahun tuju dahulu)", key="salin_timpa")
                if st.button(f"📥 Salin {_asal} → {_tuju}", type="primary", key="btn_salin_tahun"):
                    for _j in _jad:
                        try:
                            _ok, _msg = salin_data_tahun(_j, int(_asal), int(_tuju), bool(_timpa))
                            (st.success if _ok else st.warning)(_msg)
                        except Exception as _e:
                            st.error(f"{_j}: {_e}")
            if fly_cur == "table":
                st.markdown("---")
                st.subheader("Buat Table cadangan_sup jika belum ada")
                st.code("""
-- Run di Supabase SQL Editor jika cadangan_sup belum wujud:
CREATE TABLE IF NOT EXISTS cadangan_sup (
id BIGSERIAL PRIMARY KEY,
kod_ppd TEXT,
kod_sekolah TEXT,
ic_guru TEXT,
nama_guru TEXT,
kod_pusat TEXT,
jawatan_cadangan TEXT,
catatan TEXT,
status TEXT DEFAULT 'DICADANGKAN',
tarikh_cadang DATE,
created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE cadangan_sup ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "allow all" ON cadangan_sup;
CREATE POLICY "allow all" ON cadangan_sup FOR ALL USING (true) WITH CHECK (true);
""", language="sql")

# ================= FOOTER =================
st.markdown("<div class='app-footer'>Sistem Pelantikan Petugas SPM Selangor 2026 · Jabatan Pendidikan Negeri Selangor</div>".replace("2026", str(tahun_aktif())), unsafe_allow_html=True)
