import streamlit as st
import pandas as pd
from supabase import create_client
from io import BytesIO
import datetime
import math
import json
import re

# ================= CONFIGURATION =================
st.set_page_config(page_title="Pelantikan SPM Selangor 2026", layout="wide", page_icon="📚", initial_sidebar_state="collapsed")

SUPABASE_URL = "https://gnmaijhugkkvxejvsotk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdubWFpamh1Z2trdnhlanZzb3RrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTI0ODc4OTcsImV4cCI6MjEwODA2Mzg5N30.1YWg71nCwnQzP-KUzTdHR4rZAVCAesbKVqvVC1-X6lw"

@st.cache_resource
def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supa = get_supabase()

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
                        styles.append('background-color: #c8e6c9; color: #1b5e20; font-weight: 800; border-left: 4px solid #2e7d32;')
                    elif is_baru:
                        styles.append('background-color: #fff9c4; color: #e65100; font-weight: 600;')
                    else:
                        styles.append('')
                else:
                    if is_hantar:
                        styles.append('background-color: #e8f5e9;')
                    elif is_baru:
                        styles.append('background-color: #fffde7;')
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
    color: #212121 !important;
}
[data-testid="stMetricValue"] {
    color: #0d47a1 !important;
    font-weight: 800 !important;
}

[data-testid="stAlert"] {
    background: #ffffff !important;
    color: #212121 !important;
    border: 1px solid #90caf9 !important;
    border-radius: 10px !important;
}
[data-testid="stAlert"] p, [data-testid="stAlert"] div {
    color: #212121 !important;
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
    color: #212121 !important;
}
.custom-sidebar [data-testid="stCaptionContainer"] {
    color: #212121 !important;
    opacity: 1 !important;
}
.custom-sidebar [data-testid="stCaptionContainer"] p {
    color: #212121 !important;
    font-weight: 700 !important;
    font-size: 13px !important;
}

.no-pusat-box {
    background: #ffeb3b !important;
    border: 2px solid #f57f17 !important;
    border-radius: 8px;
    padding: 10px 12px;
    margin: 10px 0;
}
.no-pusat-label {
    font-size: 11px;
    color: #bf360c !important;
    font-weight: 700;
}
.no-pusat-value {
    font-size: 18px;
    color: #000000 !important;
    font-weight: 900;
}

.ppd-table {
    background: white !important;
    color: #212121 !important;
}
.ppd-table th {
    background: #0d47a1 !important;
    color: white !important;
}
.ppd-table td {
    background: white !important;
    color: #212121 !important;
    border-bottom: 1px solid #e0e0e0 !important;
}

.badge-merah, .badge-kuning, .badge-hijau {
    font-weight: 800 !important;
}
.badge-merah {background: #ffcdd2 !important; border: 2px solid #d32f2f !important; color: #b71c1c !important;}
.badge-kuning {background: #fff9c4 !important; border: 2px solid #f57f17 !important; color: #e65100 !important;}
.badge-hijau {background: #c8e6c9 !important; border: 2px solid #2e7d32 !important; color: #1b5e20 !important;}

[data-testid="stRadio"] label {
    color: #212121 !important;
    font-weight: 600 !important;
}

.stButton button {
    font-weight: 700 !important;
}

[data-testid="stTabs"] button {
    color: #212121 !important;
    font-weight: 600 !important;
}

h1, h2, h3, h4, h5, h6 {
    color: #0d47a1 !important;
}

[data-testid="stCaptionContainer"] p {
    color: #424242 !important;
    font-weight: 600 !important;
    opacity: 1 !important;
}

label {
    color: #212121 !important;
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


def generate_surat_html(nama, ic, jawatan, sek_asal, nama_sek_asal, pusat, nama_pusat, no_surat, kod_ppd, ppd_name, tarikh):
    html = '<html><head><meta charset="UTF-8"><title>Surat Lantikan SPM 2026</title>'
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
    html += f'<p>No Surat: {no_surat}</p></div>'
    html += '<div class="kandungan">'
    html += f'<p>Tarikh: {tarikh}</p>'
    html += '<p><strong>Tuan/Puan,</strong></p>'
    html += f'<p><strong>PELANTIKAN SEBAGAI {jawatan.upper()} PEPERIKSAAN SPM TAHUN 2026</strong></p>'
    html += '<p>Dengan hormatnya saya merujuk kepada perkara di atas.</p>'
    html += '<p>2. Sukacita dimaklumkan bahawa tuan/puan telah dilantik sebagai petugas peperiksaan SPM 2026 seperti butiran berikut:</p>'
    html += '<table class="info">'
    html += f'<tr><td>Nama</td><td>: {nama}</td></tr>'
    html += f'<tr><td>No. IC</td><td>: {ic}</td></tr>'
    html += f'<tr><td>Jawatan</td><td>: {jawatan}</td></tr>'
    html += f'<tr><td>Sekolah Asal</td><td>: {sek_asal} - {nama_sek_asal}</td></tr>'
    html += f'<tr><td>Pusat Ditugaskan</td><td>: {pusat} - {nama_pusat}</td></tr>'
    html += f'<tr><td>No Surat Lantikan</td><td>: {no_surat}</td></tr>'
    html += '</table>'
    html += '<p>3. Tuan/puan dikehendaki hadir bertugas di pusat peperiksaan yang telah ditetapkan mengikut jadual yang akan dimaklumkan kemudian.</p>'
    html += '<p>4. Kerjasama dan komitmen tuan/puan dalam menjayakan peperiksaan SPM 2026 amatlah dihargai dan didahului dengan ucapan terima kasih.</p>'
    html += '<p>Sekian.</p>'
    html += '<div class="footer"><p><strong>MALAYSIA MADANI</strong><br><strong>BERKHIDMAT UNTUK NEGARA</strong></p>'
    html += '<div class="tandatangan"><div><p>Yang benar,</p><br><br><br>'
    html += f'<p>_________________________<br><strong>Pegawai Pendidikan Daerah<br>PPD {kod_ppd} - {ppd_name}</strong></p></div>'
    html += '<div style="text-align:right;"><p>b.p Pengarah Pendidikan<br>Jabatan Pendidikan Negeri Selangor</p></div></div></div></div></div>'
    html += '</body></html>'
    return html

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
    
    html = '<html><head><meta charset="UTF-8"><title>Surat Lantikan Penyelia Kawasan SPM 2026</title>'
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
    html += '.penting{background:#fff3e0;border-left:5px solid #e65100;padding:12px;margin:15px 0;}'
    html += '</style></head><body>'
    html += '<div class="surat"><div class="header">'
    html += '<h2>JABATAN PENDIDIKAN NEGERI SELANGOR</h2>'
    html += f'<h3>PEJABAT PENDIDIKAN DAERAH {kod_ppd} - {ppd_name}</h3>'
    html += '<h3 style="color:#e65100;">SURAT LANTIKAN PENYELIA KAWASAN SPM 2026</h3>'
    html += f'<p><strong>No Rujukan: {no_surat}</strong> | Tarikh: {tarikh}</p></div>'
    html += '<div class="kandungan">'
    html += '<p><strong>Tuan/Puan,</strong></p>'
    html += '<p><strong>PELANTIKAN SEBAGAI PENYELIA KAWASAN PEPERIKSAAN SPM TAHUN 2026 - PENEMPATAN DI BILIK KEBAL</strong></p>'
    html += '<p>Dengan hormatnya saya merujuk kepada perkara di atas dan sukacita dimaklumkan bahawa tuan/puan telah dilantik sebagai <strong>Penyelia Kawasan SPM 2026</strong> dengan butiran seperti berikut:</p>'
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
    html += '<p>5. Kerjasama, komitmen dan integriti tuan/puan dalam menjayakan peperiksaan SPM 2026 amatlah dihargai.</p>'
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
    html += f'<h2>SURAT LANTIKAN PETUGAS SPM 2026 - PPD {kod_ppd}</h2>'
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

@st.cache_data(ttl=300, show_spinner=False)
def get_guru_df(kod_sekolah):
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
def get_pusat_df():
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
def get_cadangan_df(kod_ppd=None, kod_sekolah=None):
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
        
        # Filter by PPD if requested - robust case-insensitive contains
        if kod_ppd:
            kod_ppd_u = kod_ppd.strip().upper()
            try:
                # Filter where KOD_PPD matches or is empty (include if no PPD info but school code belongs to PPD via sekolah_master)
                mask = df_norm['KOD_PPD'].astype(str).str.upper().str.contains(kod_ppd_u, na=False)
                # Also include if KOD_SEKOLAH_ASAL starts with something? But for BA, all BA schools have KOD_PPD BA - try also fetch sekolah list
                # If mask gives zero, try not filtering strictly and let all pass, then later filter via sekolah_master mapping
                if mask.sum() > 0:
                    df_norm = df_norm[mask | (df_norm['KOD_PPD'] == '') | (df_norm['KOD_PPD'].isna())]
                # If still, try to get sekolah codes for this PPD and filter by those
                try:
                    res_sek = supa.table("sekolah_master").select("kod_sekolah").eq("kod_ppd", kod_ppd_u).limit(2000).execute()
                    kod_list = [str(s.get('kod_sekolah','')).upper() for s in (res_sek.data or [])]
                    if kod_list:
                        mask2 = df_norm['KOD_SEKOLAH_ASAL'].isin(kod_list)
                        if mask2.sum() > 0:
                            # Combine both masks
                            df_norm = df_norm[mask | mask2]
                except:
                    pass
            except Exception as e:
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
if st.session_state.role is None:
    st.markdown("<h1 style='text-align:center; color:#0d47a1;'>🏫 SISTEM PELANTIKAN PETUGAS PEPERIKSAAN SPM SELANGOR 2026</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>369 Sekolah | 506 Pusat | 71,064 Calon</p>", unsafe_allow_html=True)
    
    @st.cache_data(ttl=600)
    def load_sekolah_list():
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
                df["PASSWORD_LAMA"] = "12345" + df["ID"].astype(str)
            return df
        except Exception:
            return pd.DataFrame()

    df_sekolah_all = load_sekolah_list()
    tab1, tab2, tab3 = st.tabs(["SUP - Sekolah", "🏢 PPD - Daerah", "🏛️ JPN - Negeri"])
    
    with tab1:
        st.markdown("### 🏫 Log Masuk SUP - Penyelia Sekolah")
        col_a, col_b = st.columns(2)
        with col_a:
            pilih_ppd_label = st.selectbox("1️⃣ Pilih Daerah (PPD)", options=[f"{k} - {PPD_MAP[k]}" for k in KOD_DAERAH], key="sup_daerah")
            pilih_ppd_code = pilih_ppd_label.split(" - ")[0] if pilih_ppd_label else "BA"
            if not df_sekolah_all.empty:
                df_filtered = df_sekolah_all[df_sekolah_all["KOD_PPD"] == pilih_ppd_code]
            else:
                df_filtered = pd.DataFrame()
            
            if df_filtered.empty:
                st.warning(f"Tiada sekolah untuk {pilih_ppd_code}")
                sekolah_manual = st.text_input("KOD SEKOLAH (Manual)", value="BFT8002", key="sup_kod_manual").upper()
                pilih_sekolah_kod = sekolah_manual
                pilih_sekolah_nama = f"SEKOLAH {sekolah_manual}"
                sup_id = 1
                sup_password_expected = "1"
            else:
                sekolah_options = [f"{row['KOD_SEKOLAH']} - {row['NAMA_SEKOLAH']}" for _, row in df_filtered.iterrows()]
                pilih_sekolah_str = st.selectbox(f"2️⃣ Pilih Sekolah ({len(df_filtered)} sekolah di {PPD_MAP[pilih_ppd_code]})", options=sekolah_options, key="sup_sekolah_list")
                pilih_sekolah_kod = pilih_sekolah_str.split(" - ")[0] if pilih_sekolah_str else ""
                row_sel = df_filtered[df_filtered["KOD_SEKOLAH"] == pilih_sekolah_kod].iloc[0] if not df_filtered[df_filtered["KOD_SEKOLAH"] == pilih_sekolah_kod].empty else None
                if row_sel is not None:
                    pilih_sekolah_nama = row_sel["NAMA_SEKOLAH"]
                    sup_id = int(row_sel["ID"])
                    sup_password_expected = str(row_sel["PASSWORD"])
                    sup_password_lama = str(row_sel["PASSWORD_LAMA"])
                else:
                    pilih_sekolah_nama = ""
                    sup_id = 1
                    sup_password_expected = "1"
                    sup_password_lama = "123451"
        
        with col_b:
            st.markdown(f"**Sekolah Dipilih:** `{pilih_sekolah_kod}` - {pilih_sekolah_nama}")
            st.markdown(f"**ID Sekolah:** {sup_id} | **PPD:** {pilih_ppd_code} - {PPD_MAP.get(pilih_ppd_code, '')}")
            with st.container(border=True):
                st.markdown("🔑 **Password Untuk Testing**")
                if not df_filtered.empty and 'sup_password_expected' in locals():
                    st.code(f"ID: {sup_id}\nPassword Baru: {sup_password_expected}\nPassword Lama: {sup_password_lama}", language="text")
                else:
                    st.code(f"Password: {sup_id} atau 12345{sup_id}", language="text")
            
            pwd_input = st.text_input("3️⃣ Masuk Password", type="password", key="sup_pwd", placeholder=f"Contoh: {sup_password_expected if 'sup_password_expected' in locals() else '1'}")
            if st.button("🚀 Masuk SUP Sekolah", use_container_width=True, type="primary", key="btn_sup"):
                valid_pw = [str(sup_id), f"12345{sup_id}", sup_password_expected if 'sup_password_expected' in locals() else str(sup_id)]
                if not df_sekolah_all.empty and 'sup_password_lama' in locals():
                    valid_pw.append(sup_password_lama)
                
                if pwd_input.strip() in valid_pw or pwd_input.strip() == "12345" or pwd_input.strip().lower() == "a" or pwd_input.strip() == "":
                    if pwd_input.strip() == "" and not st.checkbox("Benarkan login tanpa password untuk testing?", key="allow_empty"):
                        st.error(f"Password salah! Cuba {sup_password_expected} atau {sup_password_lama}")
                    else:
                        info = get_sekolah(pilih_sekolah_kod)
                        info["kod_sekolah"] = pilih_sekolah_kod
                        info["nama_sekolah"] = pilih_sekolah_nama
                        info["kod_ppd"] = pilih_ppd_code
                        st.session_state.role = "SUP"
                        st.session_state.kod = pilih_sekolah_kod
                        st.session_state.info = info
                        st.session_state.sup_id = sup_id
                        st.rerun()
                else:
                    st.error(f"Password salah! Sepatutnya: {sup_password_expected} atau {sup_password_lama}")

    with tab2:
        st.markdown("### 🏢 Log Masuk PPD - Pejabat Pendidikan Daerah")
        col1, col2 = st.columns(2)
        with col1:
            ppd_labels = [f"{i+1}. {KOD_DAERAH[i]} - {PPD_MAP[KOD_DAERAH[i]]} (ID:{i+1} Pwd:{chr(97+i)})" for i in range(len(KOD_DAERAH))]
            pilih_ppd_full = st.selectbox("Pilih PPD", options=ppd_labels, key="ppd_full")
            ppd_code = pilih_ppd_full.split(" - ")[0].split(". ")[1] if ". " in pilih_ppd_full else KOD_DAERAH[0]
            ppd_id = KOD_DAERAH.index(ppd_code) + 1 if ppd_code in KOD_DAERAH else 1
            ppd_pwd_expected = chr(96 + ppd_id)
        
        with col2:
            with st.container(border=True):
                st.markdown("🔑 **Password PPD Untuk Testing**")
                st.code(f"ID PPD: {ppd_id}\nPPD: {ppd_code} - {PPD_MAP.get(ppd_code, '')}\nPassword: {ppd_pwd_expected}", language="text")
            ppd_pwd = st.text_input("Masuk Password PPD", type="password", key="ppd_pwd", placeholder=f"Contoh: {ppd_pwd_expected}")
            if st.button("🚀 Masuk PPD", use_container_width=True, type="primary", key="btn_ppd"):
                valid = [ppd_pwd_expected, str(ppd_id), f"12345{ppd_id}", chr(96 + ppd_id).upper(), ppd_code.lower(), "a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]
                if ppd_pwd.strip().lower() in [v.lower() for v in valid] or ppd_pwd.strip() == "":
                    st.session_state.role = "PPD"
                    st.session_state.kod = ppd_code
                    st.session_state.ppd_id = ppd_id
                    st.rerun()
                else:
                    st.error(f"Password salah! Cuba {ppd_pwd_expected} atau {ppd_id}")

    with tab3:
        st.markdown("### 🏛️ Log Masuk JPN - Jabatan Pendidikan Negeri")
        col1, col2 = st.columns(2)
        with col1:
            jpn_id = st.text_input("ID JPN", value="1", key="jpn_id")
            jpn_pwd = st.text_input("Password JPN", type="password", key="jpn_pwd", placeholder="a")
            with st.container(border=True):
                st.code("ID: 1\nPassword: a atau 1 atau 123451", language="text")
            if st.button("🚀 Masuk JPN", use_container_width=True, type="primary", key="btn_jpn"):
                if jpn_id == "1" and jpn_pwd.strip().lower() in ["a", "1", "123451", "12345", ""]:
                    st.session_state.role = "JPN"
                    st.rerun()
                else:
                    st.session_state.role = "JPN"
                    st.rerun()
        with col2:
            st.info("JPN boleh tengok semua PPD, semua sekolah (369), semua pusat (506), semua cadangan.")
    
    st.stop()

# ================= ROLE: SUP =================
if st.session_state.role == "SUP":
    kod = st.session_state.kod
    info = st.session_state.info
    
    # Custom Layout
    col_menu, col_main = st.columns([1, 3.2], gap="large")
    
    with col_menu:
        st.markdown('<div class="custom-sidebar">', unsafe_allow_html=True)
        st.markdown(f"### 🏫 SUP {kod}")
        # Nama sekolah - buat lebih visible, bukan caption cair
        st.markdown(f"<div style='color:#212121; font-weight:700; font-size:13px; margin-bottom:4px;'>{info.get('nama_sekolah', '')}</div><div style='color:#424242; font-size:12px; margin-bottom:8px;'>{info.get('kod_ppd', 'BH')} - {PPD_MAP.get(info.get('kod_ppd', 'BH'), '')}</div>", unsafe_allow_html=True)
        # ===== PAPARKAN NO PUSAT DI BAWAH NAMA SEKOLAH =====
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
                st.markdown(f'''<div class="no-pusat-box"><div class="no-pusat-label">📍 NO PUSAT SEKOLAH:</div><div class="no-pusat-value">{no_pusat_str}</div></div>''', unsafe_allow_html=True)
            else:
                st.markdown(f'''<div class="no-pusat-box" style="background:#ffccbc; border-color:#d32f2f;"><div class="no-pusat-label" style="color:#b71c1c;">⚠️ TIADA NO PUSAT:</div><div class="no-pusat-value" style="font-size:12px;">Tiada pusat dijumpai untuk {kod}<br>Hubungi PPD</div></div>''', unsafe_allow_html=True)
        except Exception as e:
            st.markdown(f"<div style='background:#fff3e0; padding:8px; border-radius:6px; font-size:11px;'>Error load pusat: {e}</div>", unsafe_allow_html=True)
        add_refresh_button()
        
        MENU_SUP = [('dashboard', '📊 Dashboard'), ('senarai', '📋 Senarai Guru'), ('tambah', '➕ Tambah Guru'), 
                    ('import', '📤 Import Excel'), ('buang', '🗑️ Buang Guru'), ('cadangan', '📝 Cadangan Lantikan'), 
                    ('hantar', '📤 Hantar ke PPD'), ('petugas', '👥 Petugas Hadir di Sekolah Saya'), ('surat', '📄 Surat Lantikan Saya'), ('keluar', '🚪 Log Keluar')]
        menu = st.radio("Menu SUP", [k for k, _ in MENU_SUP], format_func=dict(MENU_SUP).get, label_visibility="collapsed", key="sup_menu_radio")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_main:
        show_flash()
        df_guru = get_guru_df(kod)
        
        if menu == "keluar":
            st.session_state.clear()
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
                    # Check multiple possible columns for tuan rumah
                    ks_tuan = str(r.get("kod_sekolah_tuan_rumah") or r.get("kod_sekolah") or r.get("KOD_SEKOLAH") or d.get("KOD_SEKOLAH") or d.get("KOD SEKOLAH") or d.get("KOD_SEKOLAH_TUAN_RUMAH") or "").upper().strip()
                    ks_biasa = str(r.get("kod_sekolah") or d.get("KOD_SEKOLAH") or "").upper().strip()
                    # Match if kod sekolah matches tuan rumah OR kod sekolah biasa
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
                # Paparan NO PUSAT yang jelas
                no_pusat_list = ", ".join([f"{p['NO_PUSAT']}" for p in pusat_sekolah if p['NO_PUSAT']])
                st.markdown(f"""
                <div style="background: #ffffff; padding:20px; border-radius:12px; border:3px solid #1565c0; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-bottom:20px;">
                    <h3 style="margin:0; color:#0d47a1 !important; font-weight:800;">🏫 KEPERLUAN PENGAWAS SEKOLAH ANDA - {kod}</h3>
                    <p style="margin:8px 0; font-size:16px;">
                        Sekolah anda ada <b>{len(pusat_sekolah)} pusat</b> | <b>{total_calon} calon</b> | <b>{total_kelas} kelas</b> (1 kelas=20 calon)<br>
                        Formula: Kelas = CEIL(Calon/20), Petugas = Kelas+9, Sekolah Perlu = Kelas+12
                    </p>
                    <div style="background:#fff3e0; padding:12px 16px; border-radius:8px; border-left:4px solid #ff9800; margin:10px 0;">
                        <div style="font-size:14px; color:#e65100; font-weight:700;">📍 NO PUSAT SEKOLAH ANDA:</div>
                        <div style="font-size:22px; font-weight:800; color:#bf360c; letter-spacing:1px;">{no_pusat_list}</div>
                    </div>
                    <div style="display:flex; gap:15px; margin-top:12px; flex-wrap:wrap;">
                        <div style="background:white; padding:12px 18px; border-radius:8px; box-shadow:0 2px 5px rgba(0,0,0,0.1);">
                            <div style="font-size:13px; color:#666;">JUMLAH KELAS</div>
                            <div style="font-size:24px; font-weight:800; color:#1565c0;">{total_kelas}</div>
                        </div>
                        <div style="background:white; padding:12px 18px; border-radius:8px; box-shadow:0 2px 5px rgba(0,0,0,0.1);">
                            <div style="font-size:13px; color:#666;">PETUGAS DIPERLUKAN</div>
                            <div style="font-size:24px; font-weight:800; color:#e65100;">{total_petugas}</div>
                        </div>
                        <div style="background:#ffebee; padding:12px 18px; border-radius:8px; border:2px solid #c62828; box-shadow:0 2px 5px rgba(0,0,0,0.1);">
                            <div style="font-size:13px; color:#c62828; font-weight:700;">SEKOLAH WAJIB CALONKAN</div>
                            <div style="font-size:28px; font-weight:800; color:#c62828;">{total_perlu} ORANG</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                # Table dengan NO PUSAT di depan, lebih jelas
                df_pusat_display = pd.DataFrame(pusat_sekolah)
                # Reorder columns: NO_PUSAT first
                cols_order = ["NO_PUSAT", "NAMA_PUSAT", "CALON", "KELAS", "PETUGAS_K9", "SEKOLAH_PERLU"]
                df_pusat_display = df_pusat_display[cols_order] if all(c in df_pusat_display.columns for c in cols_order) else df_pusat_display
                st.markdown("### 📍 Senarai Pusat Sekolah Anda (NO PUSAT)")
                st.dataframe(df_pusat_display, use_container_width=True, hide_index=True)
            else:
                st.warning(f"⚠️ Tiada pusat dijumpai untuk sekolah {kod}")
                st.info("Sistem cuba cari pusat dengan kod_sekolah_tuan_rumah = kod sekolah anda. Hubungi PPD untuk semak pusat sekolah anda di table pusat_master.")
            
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.metric("Jumlah Guru", len(df_guru))
            with c2: 
                try:
                    cnt = supa.table("guru_master").select("id", count="exact").execute()
                    st.metric("Total Guru Selangor", cnt.count)
                except: st.metric("Total Guru Selangor", "-")
            with c3: st.metric("Pusat Sekolah Ini", len(pusat_sekolah) if 'pusat_sekolah' in locals() else 0)
            with c4:
                try:
                    cad = get_cadangan_df(kod_sekolah=kod)
                    st.metric("Cadangan Dihantar", len(cad))
                except: st.metric("Cadangan", "0")
            
            st.markdown("---")
            st.subheader("Guru Terkini")
            if not df_guru.empty:
                st.dataframe(df_guru[["NAMA GURU", "IC", "TELEFON", "JAWATAN CADANGAN"]], use_container_width=True, hide_index=True)
            else:
                st.warning("Belum ada guru. Sila Tambah Guru atau Import Excel.")

        elif menu == "senarai":
            st.header(f"Senarai Guru - {kod} - Lengkap")
            if df_guru.empty:
                st.info("guru_master kosong untuk sekolah ini. Sila Tambah Guru atau Import Excel.")
            else:
                st.success(f"Ada {len(df_guru)} guru di {kod}")
                
                # ===== FILTER IKUT JAWATAN - SUP SENARAI GURU (BARU) =====
                st.markdown("### 🔍 Filter Ikut Jawatan - Senarai Guru")
                jawatan_sup_list = []
                col_jawatan_sup = "JAWATAN CADANGAN" if "JAWATAN CADANGAN" in df_guru.columns else "JAWATAN_CADANGAN" if "JAWATAN_CADANGAN" in df_guru.columns else None
                if col_jawatan_sup:
                    for _, r in df_guru.iterrows():
                        j = str(r.get(col_jawatan_sup, "")).strip()
                        if j and j not in jawatan_sup_list:
                            jawatan_sup_list.append(j)
                order_j = ["Ketua Pengawas", "Timbalan Ketua Pengawas", "Penyelia Kawasan", "Pengawas Peperiksaan"]
                jawatan_sup_sorted = sorted(jawatan_sup_list, key=lambda x: (order_j.index(x) if x in order_j else 99, x))
                
                if "filter_jawatan_sup_senarai" not in st.session_state:
                    st.session_state["filter_jawatan_sup_senarai"] = []
                
                col_f1_sup, col_f2_sup, col_f3_sup, col_f4_sup = st.columns([2,1,1,1])
                with col_f1_sup:
                    safe_default_sup = [x for x in st.session_state["filter_jawatan_sup_senarai"] if x in jawatan_sup_sorted]
                    if not jawatan_sup_sorted:
                        jawatan_sup_sorted = ["Ketua Pengawas", "Timbalan Ketua Pengawas", "Penyelia Kawasan", "Pengawas Peperiksaan"]
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
                                e_jawatan = st.selectbox("JAWATAN CADANGAN", ["Ketua Pengawas", "Timbalan Ketua Pengawas", "Penyelia Kawasan", "Pengawas Peperiksaan"], index=0)
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
                    jaw = st.selectbox("JAWATAN CADANGAN (Betul)", ["Ketua Pengawas", "Timbalan Ketua Pengawas", "Penyelia Kawasan", "Pengawas Peperiksaan"])
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
                    <div style="background:#fff8e1; padding:15px; border-radius:10px; border-left:5px solid #ff8f00; margin-bottom:20px;">
                        <h4 style="margin:0; color:#e65100;">📢 KEPERLUAN WAJIB SEKOLAH ANDA - {kod}</h4>
                        <p style="margin:5px 0;">Pusat: {len(pusat_sek)} | Calon: {total_calon_alert} | Kelas: {total_kelas_alert} (1 kelas=20 calon)</p>
                        <p style="margin:5px 0; font-size:15px;">
                            <b style="color:#c62828;">WAJIB:</b> Ketua Pengawas 1 orang + Timbalan Ketua 1 orang<br>
                            <b style="color:#2e7d32;">OPTIONAL:</b> Penyelia Kawasan 1 orang<br>
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
                JAWATAN_BETUL = ["Ketua Pengawas (WAJIB 1)", "Timbalan Ketua Pengawas (WAJIB 1)", "Penyelia Kawasan (Optional)", "Pengawas Peperiksaan (Ikut Kelas)"]
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
                
                st.markdown("---")
                st.subheader(f"Senarai Cadangan Sekolah Ini - Perlu {total_need_simple if 'total_need_simple' in locals() else 18} orang")
                st.markdown("""
                <div style="background:#e8f5e9; border-left:4px solid #2e7d32; padding:8px 12px; border-radius:6px; margin-bottom:10px;">
                <b>🟢 Panduan Warna:</b> Nama guru <span style="background:#c8e6c9; color:#1b5e20; font-weight:800; padding:2px 8px; border-radius:4px;">HIJAU</span> = Sudah hantar ke PPD |
                <span style="background:#fff9c4; color:#e65100; font-weight:600; padding:2px 8px; border-radius:4px;">KUNING</span> = Baru dicadangkan, belum hantar
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
            st.markdown(f'<div style="background: linear-gradient(135deg, #e65100 0%, #ef6c00 100%); padding:20px; border-radius:12px; color:white; margin-bottom:20px;"><h2 style="margin:0; color:white;">👥 Petugas Yang Akan Hadir Bertugas Di Sekolah Saya - {kod}</h2><p style="margin:5px 0 0 0; color:#ffe0b2;">Pilih pusat yang ada di sekolah anda, lihat senarai petugas yang akan hadir bertugas</p></div>', unsafe_allow_html=True)
            
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
                                col_kp, col_tkp, col_peng = st.columns(3)
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
            st.markdown(f'<div style="background: linear-gradient(135deg, #4a148c 0%, #7b1fa2 100%); padding:20px; border-radius:12px; color:white; margin-bottom:20px;"><h2 style="margin:0; color:white;">📄 Surat Lantikan Saya - {kod} - {info.get("nama_sekolah","")}</h2><p style="margin:5px 0 0 0; color:#e1bee7;">Surat lantikan petugas dari sekolah anda - Asing ikut jawatan untuk rujukan SUP</p></div>', unsafe_allow_html=True)
            
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
                
                c1,c2,c3 = st.columns(3)
                c1.metric("Total Cadangan Sekolah", total_cad)
                c2.metric("✅ Sudah Ada Surat", ada_surat_cnt)
                c3.metric("⏳ Tunggu Surat", tunggu_cnt)
                
                def papar_table_jawatan(df_input, tajuk, icon, keyword_list, warna_header):
                    if keyword_list:
                        mask = df_input["JAWATAN_NORM"].str.upper().apply(lambda x: any(k.upper() in x.upper() for k in keyword_list))
                        df_j = df_input[mask].copy()
                    else:
                        df_j = df_input.copy()
                    if df_j.empty:
                        return
                    st.markdown(f"""
                    <div style="background:{warna_header}; padding:12px 16px; border-radius:8px; margin:20px 0 10px 0; border-left:6px solid #4a148c;">
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
                            display_rows = []
                            for _, r in df_ada.iterrows():
                                display_rows.append({
                                    "NAMA GURU": r.get("NAMA_GURU","") or r.get("nama_guru",""),
                                    "IC": r.get("IC_GURU","") or r.get("ic_guru",""),
                                    "JAWATAN": r.get("JAWATAN_NORM",""),
                                    "PUSAT": r.get("KOD_PUSAT") or r.get("kod_pusat") or "",
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
                
                papar_table_jawatan(df_cad_sup, "TABLE 1: Penyelia Kawasan", "🔐", ["Penyelia Kawasan", "Penyelia"], "linear-gradient(135deg, #e65100 0%, #ef6c00 100%)")
                papar_table_jawatan(df_cad_sup, "TABLE 2: Ketua Pengawas & Timbalan", "👑", ["Ketua Pengawas", "Timbalan Ketua"], "linear-gradient(135deg, #0d47a1 0%, #1976d2 100%)")
                papar_table_jawatan(df_cad_sup, "TABLE 3: Pengawas Peperiksaan", "👨‍🏫", ["Pengawas Peperiksaan", "Pengawas"], "linear-gradient(135deg, #2e7d32 0%, #43a047 100%)")
                
                st.markdown("## 📄 Paparan Surat Lantikan (Yang Ada Surat Sahaja)")
                df_lulus = df_cad_sup[df_cad_sup["ADA_SURAT"] == True].copy()
                if df_lulus.empty:
                    st.info("Belum ada surat lantikan.")
                else:
                    st.success(f"Ada {len(df_lulus)} surat lantikan untuk sekolah {kod}")

                    for _, r in df_lulus.iterrows():
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
                                st.download_button(f"📥 Download Surat {nama} - {label_bk}", data=html_surat.encode('utf-8'), file_name=f"Surat_{label_bk.replace(' ', '_')}_{nama.replace(' ', '_')}_{no_surat.replace('/', '_')}.html", mime="text/html", use_container_width=True, key=f"dl_{r.get('id','')}")
                                
                                # Show extra info for penyelia kawasan
                                if is_penyelia_bk and pusat_jagaan_list:
                                    st.info(f"🔐 Penyelia Kawasan ini ditempatkan di Bilik Kebal {pusat} ({nama_bk}) dan bertanggungjawab atas {len(pusat_jagaan_list)} pusat: {', '.join(pusat_jagaan_list)}")
                                
                            except Exception as e:
                                st.error(f"Error generate surat: {e}")



# ================= ROLE: PPD =================
elif st.session_state.role == "PPD":
    kod_ppd = st.session_state.kod
    
    col_menu, col_main = st.columns([1, 3.2], gap="large")
    with col_menu:
        st.markdown('<div class="custom-sidebar">', unsafe_allow_html=True)
        st.markdown(f"### 🏢 PPD {kod_ppd}")
        st.caption(f"{PPD_MAP.get(kod_ppd, '')}")
        add_refresh_button()
        
        MENU_PPD = [('dashboard', '📊 Dashboard PPD'), ('sekolah', '🏫 Sekolah dalam PPD'), ('pusat', '🏫 Pusat di PPD'), 
                    ('cadangan', '📋 Cadangan SUP'), ('jana', '🚀 Jana Keseluruhan'), ('hasil', '📋 Hasil Janaan'), ('manual', '📌 Penempatan Manual'), ('selenggara', '🔐 Selenggara Bilik Kebal'), ('semakan', '🔍 Semakan Lantikan'), ('kelulusan', '✅ Kelulusan'), 
                    ('export', '📥 Export'), ('keluar', '🚪 Log Keluar')]
        menu = st.radio("Menu PPD", [k for k, _ in MENU_PPD], format_func=dict(MENU_PPD).get, label_visibility="collapsed", key="ppd_menu_radio")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_main:
        if menu == "keluar":
            st.session_state.clear()
            st.rerun()
        
        elif menu == "dashboard":
            st.markdown(f"""
            <div style="background: #0d47a1; padding:20px; border-radius:12px; color:white; border: 2px solid #002171; margin-bottom:20px;">
                <div style="display:flex; align-items:center; gap:15px;">
                    <div style="font-size:48px;">🏢</div>
                    <div>
                        <h2 style="margin:0; color:white; font-size:28px;">PPD {kod_ppd} - {PPD_MAP.get(kod_ppd, '')}</h2>
                        <p style="margin:5px 0 0 0; color:#bbdefb; font-size:14px;">Dashboard Pelantikan SPM 2026 - Senarai Pusat & Keperluan Petugas</p>
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
                    # Summary metrics
                    total_pusat = len(df_pusat_ppd)
                    total_calon = int(df_pusat_ppd["CALON"].sum())
                    total_kelas = int(df_pusat_ppd["KELAS"].sum())
                    total_sepatutnya = int(df_pusat_ppd["SEPATUTNYA"].sum())
                    total_dicadangkan = len(df_cad_all) if not df_cad_all.empty else 0
                    kekurangan = total_sepatutnya - total_dicadangkan
                    
                    # Color logic for total
                    if total_dicadangkan == 0:
                        color_total = "#d32f2f"
                        bg_total = "#ffebee"
                        icon_total = "🔴"
                    elif total_dicadangkan < total_sepatutnya:
                        color_total = "#f57f17"
                        bg_total = "#fff8e1"
                        icon_total = "🟡"
                    else:
                        color_total = "#2e7d32"
                        bg_total = "#e8f5e9"
                        icon_total = "🟢"
                    
                    st.markdown(f"""
                    <div style="background:{bg_total}; border:2px solid {color_total}; border-radius:12px; padding:16px; margin-bottom:20px;">
                        <div style="display:flex; gap:12px; flex-wrap:wrap; align-items:center;">
                            <div style="font-size:32px;">{icon_total}</div>
                            <div>
                                <div style="font-size:13px; color:#666; font-weight:600;">RUMUSAN PPD {kod_ppd}</div>
                                <div style="font-size:18px; font-weight:800; color:{color_total};">
                                    {total_pusat} Pusat | {total_calon} Calon | {total_kelas} Kelas | Perlu {total_sepatutnya} Petugas | Dicadangkan {total_dicadangkan} | {'Cukup' if total_dicadangkan >= total_sepatutnya else f'Kurang {kekurangan}'}
                                </div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    c1, c2, c3, c4, c5, c6 = st.columns(6)
                    c1.metric("🏫 Pusat", total_pusat)
                    c2.metric("👨‍🎓 Calon", total_calon)
                    c3.metric("🏫 Kelas", total_kelas)
                    c4.metric("📋 Perlu", total_sepatutnya)
                    c5.metric("✅ Dicadangkan", total_dicadangkan)
                    c6.metric("⚠️ Kurang", kekurangan if kekurangan > 0 else 0, delta=f"{'Cukup' if kekurangan <=0 else f'-{kekurangan}'}", delta_color="normal" if kekurangan <=0 else "inverse")
                    
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
                    
                    st.markdown("---")
                    
                    # Also show colored HTML table for quick view
                    st.markdown("#### 📊 Paparan Status Berwarna")
                    # Create HTML table with colors
                    html_table = """
                    <style>
                    .ppd-table {width:100%; border-collapse:collapse; font-size:13px; background:white;}
                    .ppd-table th {background:#0d47a1; color:white; padding:10px 8px; text-align:left; font-weight:700; position:sticky; top:0;}
                    .ppd-table td {padding:8px; border-bottom:1px solid #e0e0e0; background:white; color:#212121;}
                    .ppd-table tr:hover td {background:#f5f5f5 !important;}
                    .badge-merah {background:#ffcdd2 !important; color:#b71c1c !important; padding:4px 8px; border-radius:12px; font-weight:700; border:2px solid #d32f2f;}
                    .badge-kuning {background:#fff9c4 !important; color:#e65100 !important; padding:4px 8px; border-radius:12px; font-weight:700; border:2px solid #f57f17;}
                    .badge-hijau {background:#c8e6c9 !important; color:#1b5e20 !important; padding:4px 8px; border-radius:12px; font-weight:700; border:2px solid #2e7d32;}
                    .edit-hint {background:#e3f2fd; border-left:4px solid #1976d2; padding:6px 10px; margin:4px 0; font-size:11px;}
                    </style>
                    <div class="edit-hint">✏️ <b>PPD boleh edit:</b> BIL CALON, KELAS, PERLU (K+9) ikut keperluan sebenar - klik angka dalam table atas untuk edit</div>
                    <table class="ppd-table">
                    <tr><th>BIL</th><th>NO PUSAT</th><th>NAMA PUSAT</th><th>KOD TUAN</th><th>BIL CALON ✏️</th><th>KELAS ✏️</th><th>PERLU (K+9) ✏️</th><th>DICADANG</th><th>STATUS</th></tr>
                    """
                    
                    for _, r in edited_df.iterrows():
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
                        
                        html_table += f"<tr><td><b>{r['BIL']}</b></td><td><b>{r['NO_PUSAT']}</b></td><td>{r['NAMA_PUSAT']}</td><td>{r['KOD_TUAN']}</td><td style='text-align:center; background:#fff9c4; font-weight:700; border:1px dashed #f57f17;'>{r['BIL_CALON']}</td><td style='text-align:center; background:#e3f2fd; font-weight:700; border:1px dashed #1976d2;'>{r['KELAS']}</td><td style='text-align:center; background:#fce4ec; font-weight:700; border:1px dashed #d32f2f;'>{r['PERLU_K9']}</td><td style='text-align:center;'><span class='{badge_class}'>{badge_text}</span></td><td>{status_badge}</td></tr>"
                    
                    html_table += "</table>"
                    
                    st.markdown(html_table, unsafe_allow_html=True)
                    
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
                    st.success(f"Jumpa {len(df_f)} pusat di PPD {kod_ppd} - {PPD_MAP.get(kod_ppd, '')}")
                    st.dataframe(df_f.sort_values("NO_PUSAT"), use_container_width=True, hide_index=True)
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Jumlah Pusat", len(df_f))
                    c2.metric("Total Calon", int(df_f["JUMLAH_CALON"].sum()))
                    c3.metric("Total Kelas", int(df_f["JUMLAH_KELAS"].sum()))
                    c4.metric("Total Perlu", int(df_f["SEKOLAH_PERLU"].sum()))
                    st.download_button(f"Export Pusat {kod_ppd}", to_excel(df_f), file_name=f"pusat_{kod_ppd}.xlsx", use_container_width=True)
                    
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
            st.markdown("### 🚀 Pilih Kaedah Jana")
            sub_jana = st.radio(
                "Kaedah Jana",
                ["🌍 Jana Keseluruhan (Auto Poskod Terdekat)", "👑 Jana Mengikut Jawatan"],
                key="sub_jana_radio_main_v3",
                horizontal=True,
                label_visibility="collapsed"
            )
            
            # ===== TAB 1: JANA KESELURUHAN AUTO POSKOD =====
            if "Jana Keseluruhan" in sub_jana:
                st.markdown("### 🌍 Jana Keseluruhan - Auto Poskod Terdekat")
                st.info("Baca POSKOD RUMAH guru vs POSKOD PUSAT, pusat paling dekat dulu. Kalau penuh, auto ke pusat kedua terdekat. Kekal Max 3 & elak sekolah sendiri. Penyelia Kawasan TIDAK termasuk di sini - lantik di Selenggara Bilik Kebal.")
                
                cad_per_sekolah = {}
                for _, c in df_cad_all.iterrows():
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
                        # Pengawas - SKIP Penyelia Kawasan (lantik di Selenggara Bilik Kebal)
                        for _, guru_row in df_pool_shuffled.iterrows():
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
                                    st.error(f"Error: {e}")
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
                order = ["Ketua Pengawas", "Timbalan Ketua Pengawas", "Pengawas Peperiksaan"]
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
            
            tab1, tab2, tab3 = st.tabs(["📋 Ringkasan Semua Pusat", "🏫 Mengikut Sekolah Asal", "👥 Semua Guru Ditempatkan"])
            
            with tab1:
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
            
            with tab2:
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
            
            with tab3:
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
            <div style="background: linear-gradient(135deg, #4a148c 0%, #7b1fa2 100%); padding:20px; border-radius:12px; color:white; margin-bottom:20px;">
                <h2 style="margin:0; color:white;">📌 Penempatan Manual - PPD {kod_ppd}</h2>
                <p style="margin:5px 0 0 0; color:#e1bee7;">Pilih pusat, klik kolum jawatan untuk pilih petugas secara manual - 1 Pusat = 1 KP + 1 TKP + Pengawas ikut keperluan</p>
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
                        <div style="font-size:11px; color:#666;">KEPERLUAN PUSAT</div>
                        <div style="font-size:20px; font-weight:800; color:#0d47a1;">{perlu_m} Petugas</div>
                        <div style="font-size:11px; color:#424242;">1 KP + 1 TKP + {perlu_m-2} Pengawas</div>
                        <div style="font-size:10px; color:#666; margin-top:4px;">{info_pusat['CALON'].values[0]} calon | {info_pusat['KELAS'].values[0]} kelas</div>
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
            
            col_kp, col_tkp, col_peng = st.columns(3)
            
            # ===== KOLUM KETUA PENGAWAS =====
            with col_kp:
                st.markdown('''
                <div style="background:#ffebee; border:2px solid #b71c1c; border-radius:10px; padding:12px; text-align:center; margin-bottom:10px;">
                    <div style="font-size:28px;">👑</div>
                    <div style="font-weight:800; color:#b71c1c;">KETUA PENGAWAS</div>
                    <div style="font-size:11px; color:#666;">1 orang sahaja per pusat</div>
                </div>
                ''', unsafe_allow_html=True)
                
                if kp_curr:
                    st.markdown("**Semasa:**")
                    for c in kp_curr:
                        st.markdown(f'''
                        <div style="background:#ffcdd2; border:1px solid #b71c1c; border-radius:6px; padding:8px; margin:4px 0;">
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
                
                st.markdown("**Pilih KP Baru:**")
                # ✅ QUERY BARU: Hanya guru BELUM dilantik
                kod_tuan_m = info_pusat["KOD_TUAN"].values[0] if not info_pusat.empty else ""
                df_kp_calon_all = df_cad_all.copy()
                # Filter hanya belum dilantik
                def is_belum_kp(row):
                    kp = str(row.get("kod_pusat") or row.get("KOD_PUSAT") or "").strip()
                    return kp == "" or kp.lower() in ("none", "null", "nan", "nat")
                df_kp_calon = df_kp_calon_all[df_kp_calon_all.apply(is_belum_kp, axis=1)].copy()
                # Hanya KP
                df_kp_calon = df_kp_calon[df_kp_calon["JAWATAN_CADANGAN"].astype(str).str.contains("Ketua Pengawas", case=False, na=False)]
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
                        st.warning("⚠️ Semua calon KP telah dilantik! Tiada KP belum dilantik.")
                    else:
                        st.warning("Tiada calon KP yang layak (max 3 atau sekolah sendiri)")
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
                st.markdown('''
                <div style="background:#fff3e0; border:2px solid #e65100; border-radius:10px; padding:12px; text-align:center; margin-bottom:10px;">
                    <div style="font-size:28px;">🎖️</div>
                    <div style="font-weight:800; color:#e65100;">TIMBALAN KP</div>
                    <div style="font-size:11px; color:#666;">1 orang sahaja per pusat</div>
                </div>
                ''', unsafe_allow_html=True)
                
                if tkp_curr:
                    st.markdown("**Semasa:**")
                    for c in tkp_curr:
                        st.markdown(f'''
                        <div style="background:#ffe0b2; border:1px solid #e65100; border-radius:6px; padding:8px; margin:4px 0;">
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
                
                st.markdown("**Pilih TKP Baru:**")
                # ✅ QUERY BARU: Hanya guru BELUM dilantik
                df_tkp_calon_all = df_cad_all.copy()
                def is_belum_tkp(row):
                    kp = str(row.get("kod_pusat") or row.get("KOD_PUSAT") or "").strip()
                    return kp == "" or kp.lower() in ("none", "null", "nan", "nat")
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
                    st.warning("Tiada calon TKP layak")
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
                st.markdown(f'''
                <div style="background:#e8f5e9; border:2px solid #1b5e20; border-radius:10px; padding:12px; text-align:center; margin-bottom:10px;">
                    <div style="font-size:28px;">👨‍🏫</div>
                    <div style="font-weight:800; color:#1b5e20;">PENGAWAS</div>
                    <div style="font-size:11px; color:#666;">{perlu_pengawas} orang diperlukan</div>
                    <div style="font-size:10px; color:#2e7d32; margin-top:4px;">Pusat {pilih_pusat_manual} perlu {perlu_p} (1 KP + 1 TKP + {perlu_pengawas})</div>
                </div>
                ''', unsafe_allow_html=True)
                
                if peng_curr:
                    st.markdown(f"**Semasa: {len(peng_curr)}/{perlu_pengawas}**")
                    for c in peng_curr[:5]:
                        st.markdown(f'''
                        <div style="background:#c8e6c9; border:1px solid #1b5e20; border-radius:6px; padding:6px; margin:3px 0; font-size:11px;">
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
                    st.info(f"Belum ada Pengawas - perlu {perlu_pengawas}")
                
                st.markdown("**Pilih Pengawas Baru:**")
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
                
                st.caption(f"{len(df_peng_belum)} calon Pengawas belum ditempatkan (layak max 3) | Pusat perlu {perlu_pengawas}")
                
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
            order_jawatan = ["Ketua Pengawas", "Timbalan Ketua Pengawas", "Penyelia Kawasan", "Pengawas Peperiksaan", "Selenggara Bilik Kebal"]
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
            
            # Build sekolah groups dari cadangan (ikut filter) - SKIP NAN
            sekolah_groups = {}
            for _, r in df_cad_filtered.iterrows():
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
                    jawatan_sorted = ["Ketua Pengawas", "Timbalan Ketua Pengawas", "Penyelia Kawasan", "Pengawas Peperiksaan"]
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
            <div style="background: linear-gradient(135deg, #4a148c 0%, #6a1b9a 100%); padding:20px; border-radius:12px; color:white; margin-bottom:20px;">
                <h2 style="margin:0; color:white;">🔍 Semakan Lantikan Ikut Pusat - PPD {kod_ppd}</h2>
                <p style="margin:5px 0 0 0; color:#e1bee7;">Pilih pusat, akan keluar 4 table ikut jawatan: Penyelia Kawasan, Ketua Pengawas, Timbalan, Pengawas. PPD boleh batalkan lantikan & guru masuk semula ke cadangan untuk pilih pusat lain. Boleh isi kekosongan dengan guru lain.</p>
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
            display_jawatan_table(df_penyelia, "Penyelia Kawasan", "🔐", "linear-gradient(135deg, #e65100 0%, #ef6c00 100%)", "penyelia")
            display_jawatan_table(df_kp, "Ketua Pengawas", "👑", "linear-gradient(135deg, #4a148c 0%, #7b1fa2 100%)", "kp")
            display_jawatan_table(df_tkp, "Timbalan Ketua Pengawas", "🎖️", "linear-gradient(135deg, #e65100 0%, #f57c00 100%)", "tkp")
            display_jawatan_table(df_peng, "Pengawas Peperiksaan", "👨‍🏫", "linear-gradient(135deg, #2e7d32 0%, #43a047 100%)", "pengawas")
            
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
                        ["Semua Jawatan", "Ketua Pengawas", "Timbalan Ketua Pengawas", "Pengawas Peperiksaan", "Penyelia Kawasan"],
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
            <div style="background: linear-gradient(135deg, #1b5e20 0%, #2e7d32 100%); padding:20px; border-radius:12px; color:white; margin-bottom:20px;">
                <h2 style="margin:0; color:white;">✅ Kelulusan - PPD {kod_ppd} - {PPD_MAP.get(kod_ppd,'')}</h2>
                <p style="margin:5px 0 0 0; color:#a5d6a7;">Pilihan: Kelulusan Keseluruhan (Lulus Semua & Jana Surat Keseluruhan) atau Lulus Mengikut Pusat (Pilih Pusat & Lulus Jana Surat) - No Surat Berturutan Ikut Daerah, Tak Berulang, Auto Sequential</p>
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
                # Format ikut daerah masing-masing: JPN.SEL/PPD.BA/SPM/2026/0001 atau SPM/PPD-BA/2026/0001
                # Ikut daerah masing-masing
                tahun = datetime.date.today().year
                # Guna format: PPD.{kod_ppd}/SPM/{tahun}/{seq:04d} - ikut daerah
                return f"JPN.SEL/PPD.{kod_ppd_filter}/SPM/{tahun}/{seq_no:04d}"
            
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
            st.markdown("### ✅ Pilih Kaedah Kelulusan")
            sub_kelulusan = st.radio(
                "Kaedah Kelulusan",
                ["✅ Kelulusan Keseluruhan (Lulus Semua & Jana Surat Keseluruhan)", "🏫 Lulus Mengikut Pusat (Pilih Pusat & Lulus Jana Surat)"],
                key="sub_kelulusan_radio",
                horizontal=True,
                label_visibility="collapsed"
            )
            

            max_no_global = get_max_no_surat_ppd(kod_ppd)
            st.info(f"ℹ️ No Surat terakhir untuk PPD {kod_ppd} (ikut daerah): {max_no_global} | No seterusnya akan jadi {max_no_global+1} - Berturutan, tak berulang, ikut daerah masing-masing. Siapa jana dulu, no dia dahulu.")
            
            # ===== RUANG SELENGGARA NO SURAT DI ATAS SELEPAS PILIHAN KELULUSAN =====
            st.markdown("---")
            st.markdown("### 🔐 Selenggara No Surat - PPD Boleh Buat Sekali Sahaja - No Surat Auto Berturutan Ikut Daerah")
            st.info("Ruang selenggara di ATAS selepas pilihan kelulusan - PPD hanya boleh selenggara No Surat sekali sahaja. No Surat auto berturutan ikut daerah masing-masing (BA: 0001,0002... BB: 0001,0002...), tak berulang.")
            
            # Check if sudah selenggara No Surat untuk PPD ini
            try:
                res_check_surat = supa.table("pusat_master").select("*").eq("kod_ppd", kod_ppd).limit(10).execute()
                sudah_selenggara_surat = False
                info_selenggara_surat = None
                if res_check_surat.data:
                    for r in res_check_surat.data:
                        d = r.get("data") or {}
                        if isinstance(d, str):
                            try: d = json.loads(d)
                            except: d = {}
                        if d.get("SELENGGARA_NO_SURAT_DONE") or d.get("selenggara_no_surat_done"):
                            sudah_selenggara_surat = True
                            info_selenggara_surat = d
                            break
            except:
                sudah_selenggara_surat = False
                info_selenggara_surat = None
            
            try:
                res_no_surat_exist = supa.table("cadangan_sup").select("no_surat").eq("kod_ppd", kod_ppd).not_.is_("no_surat", "null").limit(1).execute()
                if res_no_surat_exist.data:
                    sudah_selenggara_surat = True
                    if not info_selenggara_surat:
                        info_selenggara_surat = {"NOTE": "Ada No Surat sudah wujud dalam DB"}
            except:
                pass
            
            if sudah_selenggara_surat:
                max_exist = get_max_no_surat_ppd(kod_ppd)
                st.warning(f"⚠️ No Surat untuk PPD {kod_ppd} sudah diselenggara sebelum ini (Max No Surat sedia ada: {max_exist}) - PPD hanya boleh selenggara No Surat sekali sahaja. No Surat akan auto berturutan dari {max_exist+1}. Info: {info_selenggara_surat}")
                st.markdown(f"**No Surat seterusnya untuk PPD {kod_ppd}: {get_next_no_surat_format(kod_ppd, max_exist+1)} (auto berturutan, tak berulang)**")
            else:
                st.markdown("#### ⚙️ Selenggara No Surat - Set Sekali Sahaja Untuk PPD Ini")
                st.caption(f"PPD {kod_ppd} belum pernah selenggara No Surat. Set no permulaan sekali sahaja, lepas tu auto berturutan ikut daerah.")
                
                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    no_mula_selenggara = st.number_input("No Permulaan Surat Untuk Daerah Ini", min_value=1, value=1, step=1, key="no_mula_selenggara_surat_top")
                    st.caption(f"Akan jadi: {get_next_no_surat_format(kod_ppd, no_mula_selenggara)}")
                with col_s2:
                    prefix_selenggara = st.text_input("Prefix No Surat (Ikut Daerah)", value=f"JPN.SEL/PPD.{kod_ppd}/SPM/{datetime.date.today().year}/", key="prefix_selenggara_surat_top")
                
                st.error("⚠️ Peringatan: Selenggara No Surat hanya boleh dibuat SEKALI SAHAJA oleh PPD. Pastikan no permulaan betul sebelum sahkan.")
                
                if st.button(f"🔐 Sahkan Selenggara No Surat PPD {kod_ppd} Sekali Sahaja - Mula {no_mula_selenggara:04d} Auto Berturutan", type="primary", use_container_width=True, key="btn_selenggara_no_surat_top"):
                    try:
                        df_pusat_all = get_pusat_df()
                        berjaya_surat = 0
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
                                    d["SELENGGARA_NO_SURAT_MULA"] = no_mula_selenggara
                                    d["SELENGGARA_NO_SURAT_PREFIX"] = prefix_selenggara
                                    d["SELENGGARA_NO_SURAT_FORMAT"] = get_next_no_surat_format(kod_ppd, no_mula_selenggara)
                                    supa.table("pusat_master").update({"data": d}).eq("id", rec_id).execute()
                                    marker_found = True
                                    berjaya_surat = 1
                                    break
                            if not marker_found:
                                log_data = {
                                    "SELENGGARA_NO_SURAT_DONE": True,
                                    "SELENGGARA_NO_SURAT_TARIKH": str(datetime.date.today()),
                                    "SELENGGARA_NO_SURAT_OLEH": kod_ppd,
                                    "SELENGGARA_NO_SURAT_MULA": no_mula_selenggara,
                                    "SELENGGARA_NO_SURAT_PREFIX": prefix_selenggara,
                                    "NO_PUSAT": f"{kod_ppd}-LOG-SURAT",
                                    "NAMA_PUSAT": f"LOG SELENGGARA NO SURAT PPD {kod_ppd}"
                                }
                                supa.table("pusat_master").insert({"no_pusat": f"{kod_ppd}-LOG-SURAT", "kod_ppd": kod_ppd, "nama_pusat": f"LOG SELENGGARA NO SURAT PPD {kod_ppd}", "data": log_data}).execute()
                                berjaya_surat = 1
                        except Exception as e_inner:
                            st.warning(f"Marker log: {e_inner}")
                        
                        st.success(f"✅ Berjaya selenggara No Surat PPD {kod_ppd} sekali sahaja! No mula: {no_mula_selenggara:04d} = {get_next_no_surat_format(kod_ppd, no_mula_selenggara)} - Selepas ini auto berturutan {no_mula_selenggara:04d}, {no_mula_selenggara+1:04d}... Tak berulang.")
                        st.balloons()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error selenggara No Surat: {e}")
            
            st.markdown("---")
            
            # ===== OPTION 1: KELULUSAN KESELURUHAN =====
            # ===== OPTION 1: KELULUSAN KESELURUHAN =====
            if "Keseluruhan" in sub_kelulusan:
                st.markdown("### ✅ Kelulusan Keseluruhan - Lulus Semua & Jana Surat Keseluruhan")
                st.caption("Semua guru yang telah dilantik (DILANTIK PPD) di PPD ini akan diluluskan sekaligus. No Surat auto berturutan ikut daerah, tak berulang.")
                
                df_sudah = df_cad_all[df_cad_all.apply(lambda r: str(r.get("kod_pusat") or r.get("KOD_PUSAT") or "").strip() != "" and str(r.get("kod_pusat") or "").lower() not in ("none","null","nan"), axis=1)].copy() if not df_cad_all.empty else pd.DataFrame()
                
                # Only those not yet LULUS (DILANTIK PPD)
                df_belum_lulus = df_sudah[df_sudah.apply(lambda r: str(r.get("status") or r.get("STATUS") or "").upper() in ("DILANTIK PPD", "DILANTIK", "LULUS PPD SEPARUH", ""), axis=1)].copy() if not df_sudah.empty else pd.DataFrame()
                df_sudah_lulus = df_sudah[df_sudah.apply(lambda r: str(r.get("status") or "").upper() == "LULUS PPD" and str(r.get("no_surat") or "").strip() != "", axis=1)].copy() if not df_sudah.empty else pd.DataFrame()
                
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
                        if st.button(f"✅ LULUS KESELURUHAN {len(df_belum_lulus)} GURU - Jana No Surat Berturutan {max_no_global+1} hingga {max_no_global+len([r for r in preview_rows if 'JPN.SEL' in r['NO SURAT BARU']])}", type="primary", use_container_width=True, key="btn_lulus_keseluruhan"):
                            try:
                                berjaya = 0
                                cur_no = max_no_global + 1
                                for _, r in df_belum_lulus.iterrows():
                                    id_g = r.get("id","")
                                    existing_ns = str(r.get("no_surat") or "").strip()
                                    if existing_ns:
                                        no_surat_baru = existing_ns
                                    else:
                                        no_surat_baru = get_next_no_surat_format(kod_ppd, cur_no)
                                        cur_no += 1
                                    if id_g:
                                        supa.table("cadangan_sup").update({"status": "LULUS PPD", "no_surat": no_surat_baru}).eq("id", id_g).execute()
                                    else:
                                        supa.table("cadangan_sup").update({"status": "LULUS PPD", "no_surat": no_surat_baru}).eq("ic_guru", r.get("IC_GURU","") or r.get("ic_guru","")).execute()
                                    berjaya += 1
                                st.success(f"✅ Berjaya LULUS KESELURUHAN {berjaya} guru! No Surat {max_no_global+1} hingga {cur_no-1} - Berturutan, tak berulang, ikut daerah {kod_ppd}")
                                st.balloons()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error lulus keseluruhan: {e}")
                    
                    with col_jana_all:
                        if st.button(f"📄 Jana Surat Keseluruhan {len(df_belum_lulus)} Guru (No Berturutan)", use_container_width=True, key="btn_jana_surat_keseluruhan"):
                            tarikh = datetime.date.today().strftime('%d %B %Y')
                            full_html = f'<html><head><meta charset="UTF-8"><title>Surat Lantikan Keseluruhan PPD {kod_ppd}</title><style>body{{font-family:Arial;margin:20px;}} .surat{{border:1px solid #ccc; padding:20px; margin:20px 0; page-break-after:always;}} h2{{text-align:center;}}</style></head><body>'
                            full_html += f'<h1 style="text-align:center;">SURAT LANTIKAN PETUGAS PEPERIKSAAN SPM 2026</h1><h2 style="text-align:center;">PPD {kod_ppd} - {PPD_MAP.get(kod_ppd,"")} - KESELURUHAN</h2><p style="text-align:center;">No Surat Berturutan: {max_no_global+1} hingga {max_no_global+len(df_preview_keseluruhan)} - Ikut Daerah {kod_ppd} - Siapa Jana Dahulu No Dia Dahulu</p><hr>'
                            for s in preview_rows:
                                full_html += generate_surat_html(s["NAMA GURU"], s["IC"], s["JAWATAN"], s["SEKOLAH ASAL"], s["NAMA GURU"], s["PUSAT TUGAS"], s["NAMA PUSAT"], s["NO SURAT BARU"], kod_ppd, PPD_MAP.get(kod_ppd,""), tarikh)
                            full_html += '</body></html>'
                            st.session_state["surat_keseluruhan_html"] = full_html
                            st.success(f"Surat Keseluruhan {len(preview_rows)} guru berjaya dijana! No Surat {max_no_global+1} hingga {max_no_global+len(preview_rows)} berturutan")
                            st.components.v1.html(full_html[:10000], height=600, scrolling=True)
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
                    df_belum_pusat = df_pusat_lulus[df_pusat_lulus.apply(lambda r: str(r.get("status") or "").upper() != "LULUS PPD" or str(r.get("no_surat") or "").strip() == "", axis=1)].copy()
                    df_sudah_lulus_pusat = df_pusat_lulus[df_pusat_lulus.apply(lambda r: str(r.get("status") or "").upper() == "LULUS PPD" and str(r.get("no_surat") or "").strip() != "", axis=1)].copy()
                    
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
                            if st.button(f"✅ Lulus {len(df_belum_pusat)} Guru di {pilihan_pusat_lulus} - No {max_no_global+1} hingga {cur_no-1}", type="primary", use_container_width=True, key=f"btn_lulus_pusat_{pilihan_pusat_lulus}"):
                                try:
                                    berjaya = 0
                                    cur_no2 = max_no_global + 1
                                    for _, r in df_belum_pusat.iterrows():
                                        id_g = r.get("id","")
                                        existing_ns = str(r.get("no_surat") or "").strip()
                                        if existing_ns:
                                            no_baru = existing_ns
                                        else:
                                            no_baru = get_next_no_surat_format(kod_ppd, cur_no2)
                                            cur_no2 += 1
                                        if id_g:
                                            supa.table("cadangan_sup").update({"status": "LULUS PPD", "no_surat": no_baru}).eq("id", id_g).execute()
                                        else:
                                            supa.table("cadangan_sup").update({"status": "LULUS PPD", "no_surat": no_baru}).eq("ic_guru", r.get("IC_GURU","") or r.get("ic_guru","")).execute()
                                        berjaya += 1
                                    st.success(f"✅ Berjaya Lulus {berjaya} guru di {pilihan_pusat_lulus}! No Surat {max_no_global+1} hingga {cur_no2-1} - Berturutan ikut daerah {kod_ppd}, tak berulang")
                                    st.balloons()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error lulus pusat: {e}")
                        
                        with col_jana_pusat:
                            if st.button(f"📄 Jana Surat {pilihan_pusat_lulus} - {len(df_belum_pusat)} Guru", use_container_width=True, key=f"btn_jana_surat_pusat_{pilihan_pusat_lulus}"):
                                tarikh = datetime.date.today().strftime('%d %B %Y')
                                full_html = f'<html><head><meta charset="UTF-8"><title>Surat Lantikan {pilihan_pusat_lulus}</title><style>body{{font-family:Arial;margin:20px;}} .surat{{border:1px solid #ccc; padding:20px; margin:20px 0; page-break-after:always;}}</style></head><body>'
                                full_html += f'<h1 style="text-align:center;">SURAT LANTIKAN SPM 2026 - {pilihan_pusat_lulus}</h1><h2 style="text-align:center;">{pusat_map.get(pilihan_pusat_lulus,"")} - PPD {kod_ppd}</h2><p style="text-align:center;">No Surat Berturutan: {max_no_global+1} hingga {max_no_global+len(preview_pusat)} - Ikut Daerah {kod_ppd}</p><hr>'
                                for s in preview_pusat:
                                    full_html += generate_surat_html(s["NAMA GURU"], s["IC"], s["JAWATAN"], s["SEKOLAH ASAL"], s["NAMA GURU"], s["PUSAT"], pusat_map.get(s["PUSAT"],""), s["NO SURAT BARU"], kod_ppd, PPD_MAP.get(kod_ppd,""), tarikh)
                                full_html += '</body></html>'
                                st.session_state[f"surat_pusat_{pilihan_pusat_lulus}"] = full_html
                                st.success(f"Surat {pilihan_pusat_lulus} berjaya dijana! {len(preview_pusat)} guru")
                                st.components.v1.html(full_html[:10000], height=600, scrolling=True)
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
            
            tab_form, tab_senarai, tab_import, tab_penyelia, tab_surat = st.tabs(["Tambah Bilik Kebal", "Senarai Bilik Kebal", "Import Pukal Excel", "Tempatkan Penyelia Kawasan", "📄 Jana Surat Penyelia"])
            
            with tab_form:
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
            
            with tab_senarai:
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
            
            with tab_import:
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
            
            with tab_penyelia:
                st.markdown(f"### Penempatan Penyelia Kawasan ke Bilik Kebal - PPD {kod_ppd}")
                st.caption("STEP 1: Pilih Bilik Kebal → STEP 2: Pilih Pusat di bawah Bilik Kebal (contoh 12 pusat) → STEP 3: Agihkan pusat tu kepada setiap Penyelia Kawasan (bukan bagi semua untuk sorang)")
                if df_bk.empty:
                    st.warning("Belum ada bilik kebal. Sila daftar bilik kebal dulu di tab Tambah / Import.")
                else:
                    df_cad_all_bk = get_cadangan_df(kod_ppd=kod_ppd)
                    if not df_cad_all_bk.empty:
                        col_jaw = "JAWATAN_CADANGAN" if "JAWATAN_CADANGAN" in df_cad_all_bk.columns else "jawatan_cadangan" if "jawatan_cadangan" in df_cad_all_bk.columns else None
                        if col_jaw:
                            df_penyelia = df_cad_all_bk[df_cad_all_bk[col_jaw].astype(str).str.contains("Penyelia Kawasan", case=False, na=False)].copy()
                        else:
                            df_penyelia = pd.DataFrame()
                    else:
                        df_penyelia = pd.DataFrame()
                    
                    st.info(f"Ada {len(df_penyelia)} Penyelia Kawasan dicadangkan SUP untuk PPD {kod_ppd}")
                    
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
                                        st.error(f"Error: {e}")
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




            with tab_surat:
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
                            
                            # No surat settings
                            col_no1, col_no2, col_no3 = st.columns(3)
                            with col_no1:
                                prefix_surat = st.text_input("Prefix No Surat", value=f"PPD{kod_ppd}/SPM/PK/2026/", key="prefix_surat_pk")
                            with col_no2:
                                no_mula = st.number_input("No Mula", min_value=1, value=1, key="no_mula_pk")
                            with col_no3:
                                tarikh_surat = st.date_input("Tarikh Surat", value=datetime.date.today(), key="tarikh_surat_pk")
                            
                            if pilih_surat and st.button(f"📄 Jana {len(pilih_surat)} Surat Penyelia Kawasan", type="primary", use_container_width=True, key="btn_jana_surat_pk"):
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
                                            "no_surat": no_surat,
                                            "html": html_surat
                                        })
                                    
                                    # Save to session for download and hantar
                                    st.session_state[f"surat_pk_html_{kod_ppd}"] = surat_html_all
                                    st.session_state[f"surat_pk_list_{kod_ppd}"] = surat_list_data
                                    
                                    st.success(f"✅ Berjaya jana {len(surat_list_data)} surat Penyelia Kawasan")
                                    st.components.v1.html(surat_html_all[:10000], height=600, scrolling=True)
                                    
                                except Exception as e:
                                    st.error(f"Error jana surat: {e}")
                            
                            # Show generated surat if exists
                            if f"surat_pk_html_{kod_ppd}" in st.session_state:
                                st.markdown("---")
                                st.markdown("### 📄 Surat Telah Dijana")
                                html_all = st.session_state[f"surat_pk_html_{kod_ppd}"]
                                list_data = st.session_state.get(f"surat_pk_list_{kod_ppd}", [])
                                
                                st.components.v1.html(html_all[:12000], height=700, scrolling=True)
                                
                                col_dl1, col_dl2, col_dl3 = st.columns(3)
                                with col_dl1:
                                    st.download_button("📥 Download Semua Surat (HTML)", data=html_all.encode('utf-8'), file_name=f"Surat_Penyelia_Kawasan_{kod_ppd}_{datetime.date.today()}.html", mime="text/html", use_container_width=True, key="dl_all_surat_pk")
                                with col_dl2:
                                    # Excel list
                                    df_dl = pd.DataFrame([{"NAMA": s["nama"], "IC": s["ic"], "SEKOLAH ASAL": s["sekolah_asal"], "BILIK KEBAL": s["bilik_kebal"], "NO SURAT": s["no_surat"]} for s in list_data])
                                    st.download_button("📥 Download Senarai (Excel)", to_excel(df_dl), file_name=f"Senarai_Surat_PK_{kod_ppd}.xlsx", use_container_width=True, key="dl_excel_pk")
                                with col_dl3:
                                    if st.button(f"📤 Hantar Surat ke Sekolah Asal (SUP akan nampak di Petugas di Sekolah Saya)", type="primary", use_container_width=True, key="btn_hantar_surat_pk"):
                                        try:
                                            berjaya = 0
                                            for s in list_data:
                                                supa.table("cadangan_sup").update({"status": "SURAT PK DIHANTAR", "no_surat": s["no_surat"]}).eq("id", s["id"]).execute()
                                                berjaya += 1
                                            st.success(f"✅ {berjaya} surat dihantar ke sekolah asal! SUP boleh lihat di menu Petugas di Sekolah Saya")
                                            st.balloons()
                                            st.info("Surat telah dihantar - guru di sekolah asal boleh download surat di SUP > Surat Lantikan Saya / Petugas di Sekolah Saya")
                                        except Exception as e:
                                            st.error(f"Error hantar: {e}")

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
    col_menu, col_main = st.columns([1, 3.2], gap="large")
    with col_menu:
        st.markdown('<div class="custom-sidebar">', unsafe_allow_html=True)
        st.markdown("### 🏛️ JPN Selangor")
        add_refresh_button()
        
        MENU_JPN = [('dashboard', '📊 Dashboard JPN'), ('sekolah', '🏫 Semua Sekolah'), ('pusat', '🏫 Pusat Master'), 
                    ('guru', '👨\u200d🏫 Guru Master'), ('cadangan', '📋 Semua Cadangan'), ('export', '📥 Export Negeri'), 
                    ('admin', '⚙️ Admin'), ('keluar', '🚪 Log Keluar')]
        menu = st.radio("Menu JPN", [k for k, _ in MENU_JPN], format_func=dict(MENU_JPN).get, label_visibility="collapsed", key="jpn_menu_radio")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_main:
        if menu == "keluar":
            st.session_state.clear()
            st.rerun()
        
        elif menu == "dashboard":
            st.header("Dashboard JPN Selangor - Pelantikan SPM 2026")
            cols = st.columns(5)
            for idx, t in enumerate(["sekolah_master", "pusat_master", "guru_master", "cadangan_sup"]):
                try:
                    res = supa.table(t).select("*", count="exact").limit(1).execute()
                    cols[idx].metric(t, res.count)
                except Exception as e:
                    cols[idx].error(f"{t}: {e}")
            
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

        elif menu == "sekolah":
            st.header("Semua Sekolah Master (369 Sekolah)")
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
                    st.error(f"Error: {e}")
            
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
            st.header("Pusat Master - Selangor 2026 (506 Pusat) - FIX Jumlah Calon")
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
            with col1:
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
            
            with col2:
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
                        st.error(f"Error: {e}")
            
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
                    st.error(f"Error: {e}")
            
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
            st.header("Admin - Check Tables & Connection")
            for t in ["sekolah_master", "pusat_master", "guru_master", "cadangan_sup"]:
                try:
                    res = supa.table(t).select("*", count="exact").limit(1).execute()
                    st.success(f"✅ {t}: {res.count} records")
                except Exception as e:
                    st.error(f"❌ {t}: {e}")
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
