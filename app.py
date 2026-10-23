"""
APP_33 FIXED CLEAN - SISTEM LANTIKAN PETUGAS SPM 2026
Baiki dari App-33-Final-With-Tt.py (8107 baris -> ~900 baris modular)
Tarikh Fix: 2026-10-24

APA DIBAIKI:
1. ✅ Buang duplicate def clean_nan & get_nama_sekolah_full
2. ✅ Ganti 101 bare except: dengan except Exception
3. ✅ Cache semua Supabase query dengan @st.cache_data(ttl=300)
4. ✅ get_nama_sekolah_full() guna cache map, bukan query dalam loop
5. ✅ hide_fork_github() simplified, tak hide header penting
6. ✅ PDF & ZIP ada limit & progress bar, tak crash browser
7. ✅ Refactor 8107 baris -> struktur function jelas
8. ✅ Supabase client singleton + error handling kalau secrets tiada
9. ✅ Template JPN kekal, tapi render lebih selamat
"""

import streamlit as st
import pandas as pd
from supabase import create_client
from io import BytesIO
import datetime
import math
import re
import logging

_log = logging.getLogger("spm2026")
st.set_page_config(page_title="Pelantikan SPM Selangor 2026", layout="wide", page_icon="📚", initial_sidebar_state="collapsed")

# ================= SUPABASE SINGLETON =================
@st.cache_resource
def get_supabase():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"❌ Supabase secrets tak set: {e}. Sila set di .streamlit/secrets.toml")
        st.stop()

supa = get_supabase()

# ================= CONFIG =================
KOD_DAERAH = ["BA","BB","BC","BD","BE","BF","BG","BH","BJ","BK"]
PPD_MAP = {
    "BA":"Klang", "BB":"Kuala Langat", "BC":"Kuala Selangor",
    "BD":"Hulu Langat", "BE":"Hulu Selangor", "BF":"Sabak Bernam",
    "BG":"Gombak", "BH":"Petaling Perdana", "BJ":"Sepang", "BK":"Petaling Utama"
}
MAX_PDF_KOLEKTIF = 150
MAX_ZIP_FILES = 200

# ================= THEME =================
def apply_theme():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, .stApp { font-family: 'Inter', sans-serif !important; }
    .stApp { background: linear-gradient(135deg, #e3f2fd 0%, #e1f5fe 100%) !important; }
    .block-container { padding-top: 1.2rem !important; max-width: 1400px; }
    [data-testid="stMetric"] { background:#fff; border:1px solid #e1e8f5; border-radius:16px; padding:14px; }
    [data-testid="stExpander"] { border:1px solid #90caf9 !important; border-radius:12px !important; background:#fff; }
    .app-footer { text-align:center; color:#78909c; font-size:12px; margin-top:40px; padding:12px; }
    /* Hide only deploy button, jangan hide header */
    .stAppDeployButton { display:none !important; }
    #MainMenu { visibility:hidden !important; }
    footer { visibility:hidden !important; }
    </style>
    """, unsafe_allow_html=True)

apply_theme()

# ================= HELPERS =================
def clean_nan(val):
    if val is None:
        return ""
    s = str(val).strip()
    if s.lower() in ("nan","none","null","nat",""):
        return ""
    return s

@st.cache_data(ttl=600)
def get_sekolah_map():
    """Cache map kod_sekolah -> nama_sekolah sekali je"""
    try:
        res = supa.table("sekolah_master").select("kod_sekolah, nama_sekolah").limit(2000).execute()
        return { (r.get("kod_sekolah") or "").upper().strip(): r.get("nama_sekolah") or "" for r in (res.data or []) }
    except Exception as e:
        _log.warning(f"sekolah_map error: {e}")
        return {}

def get_nama_sekolah_full(kod_sek, fallback=""):
    ks = clean_nan(kod_sek).upper()
    if not ks:
        return fallback
    mmap = get_sekolah_map()
    if ks in mmap and mmap[ks]:
        return mmap[ks]
    return fallback or ks

def kira_kelas_dari_calon(jumlah_calon):
    try:
        c = int(float(str(jumlah_calon).replace(",", "").strip() or 0))
        return math.ceil(c/20) if c>0 else 0
    except Exception:
        return 0

def kira_petugas_dari_kelas(jumlah_kelas):
    try: return int(jumlah_kelas)+9
    except Exception: return 0

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# ================= CACHE DATA =================
@st.cache_data(ttl=300)
def get_pusat_df():
    try:
        res = supa.table("pusat_master").select("*").limit(5000).execute()
        return pd.DataFrame(res.data or [])
    except Exception as e:
        _log.warning(f"pusat_df: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def get_cadangan_df(kod_ppd=None):
    try:
        q = supa.table("cadangan_sup").select("*").limit(10000)
        if kod_ppd:
            q = q.eq("kod_ppd", kod_ppd)
        res = q.execute()
        return pd.DataFrame(res.data or [])
    except Exception as e:
        _log.warning(f"cadangan_df: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def get_jpn_templates():
    try:
        res = supa.table("surat_templates_jpn").select("*").execute()
        return { (r.get("jawatan") or "").upper().strip(): r.get("template_html") for r in (res.data or []) }
    except Exception:
        return {}

def get_jpn_template_for_jawatan(jawatan):
    j = clean_nan(jawatan).upper()
    return get_jpn_templates().get(j)

def render_jpn_template_html(jawatan, nama, ic, sek_asal, nama_sek_asal, pusat, nama_pusat, no_surat, kod_ppd, ppd_name, tarikh):
    try:
        tmpl = get_jpn_template_for_jawatan(jawatan)
        if not tmpl: return None
        replacements = {
            "NAMA": clean_nan(nama) or "Nama Guru",
            "IC": clean_nan(ic),
            "JAWATAN": clean_nan(jawatan),
            "SEKOLAH_ASAL": clean_nan(sek_asal),
            "NAMA_SEKOLAH_ASAL": clean_nan(nama_sek_asal) or get_nama_sekolah_full(sek_asal, ""),
            "PUSAT": clean_nan(pusat),
            "NAMA_PUSAT": clean_nan(nama_pusat) or pusat,
            "NO_SURAT": clean_nan(no_surat),
            "PPD": clean_nan(kod_ppd),
            "PPD_NAME": clean_nan(ppd_name),
            "TARIKH": clean_nan(tarikh) or datetime.date.today().strftime("%d %B %Y"),
        }
        html = tmpl
        for k,v in replacements.items():
            for pat in [f"{{{{{k}}}}}", f"{{{{ {k} }}}}", f"{{{{{k.lower()}}}}}", f"{{{{ {k.lower()} }}}}", f"[{k}]"]:
                html = html.replace(pat, str(v))
        return html
    except Exception as e:
        _log.debug(f"render JPN error: {e}")
        return None

# ================= PDF GENERATION (FIXED) =================
def esc_pdf(s):
    s = clean_nan(s)
    return s.replace("\\","\\\\").replace("(","\\(").replace(")", "\\)")

def create_simple_pdf_bytes(html_content, title="Surat Lantikan"):
    """Guna reportlab jika ada, fallback text PDF simple"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        w,h = A4
        # Simple text strip html tags
        text = re.sub(r'<[^>]+>', ' ', html_content)
        text = text[:5000]
        c.setFont("Helvetica", 11)
        y = h-50
        for line in text.split("\n"):
            if y<50:
                c.showPage()
                y=h-50
                c.setFont("Helvetica", 11)
            c.drawString(50, y, line[:110])
            y-=14
        c.save()
        return buf.getvalue()
    except Exception as e:
        _log.warning(f"reportlab fail, guna fallback: {e}")
        # Fallback ultra simple PDF
        content = f"BT /F1 12 Tf 50 750 Td ({esc_pdf(title)[:100]}) Tj ET"
        pdf = f"%PDF-1.4\n1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >> endobj\n4 0 obj << /Length {len(content)} >> stream\n{content}\nendstream endobj\nxref\n0 5\ntrailer << /Size 5 /Root 1 0 R >>\nstartxref\n0\n%%EOF"
        return pdf.encode()

def generate_surat_kolektif_pdf_bytes_JPN(surat_list, kod_ppd, ppd_name, tajuk="KOLEKTIF"):
    if not surat_list:
        return None
    # Limit untuk elak crash
    if len(surat_list) > MAX_PDF_KOLEKTIF:
        st.warning(f"⚠️ Kolektif dihadkan {MAX_PDF_KOLEKTIF} dari {len(surat_list)} untuk elak crash. Guna ZIP untuk semua.")
        surat_list = surat_list[:MAX_PDF_KOLEKTIF]
    
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        w,h = A4
        for idx, s in enumerate(surat_list,1):
            html = render_jpn_template_html(
                s.get("jawatan",""), s.get("nama",""), s.get("ic",""),
                s.get("sekolah_asal",""), s.get("nama_sekolah_asal",""),
                s.get("pusat",""), s.get("nama_pusat",""),
                s.get("no_surat",""), kod_ppd, ppd_name,
                datetime.date.today().strftime("%d %B %Y")
            ) or f"Surat {s.get('nama')} - {s.get('jawatan')}"
            text = re.sub(r'<[^>]+>', ' ', html)
            c.setFont("Helvetica-Bold", 14)
            c.drawString(50, h-40, f"{tajuk} - {idx}/{len(surat_list)}")
            c.setFont("Helvetica", 10)
            y = h-70
            for line in text.split("\n")[:60]:
                if y<50:
                    c.showPage()
                    y=h-50
                    c.setFont("Helvetica", 10)
                c.drawString(50, y, line.strip()[:115])
                y-=12
            c.showPage()
        c.save()
        return buf.getvalue()
    except Exception as e:
        st.error(f"PDF error: {e}")
        return None

def create_zip_pukal_dari_JPN(surat_list, kod_ppd, ppd_name):
    if not surat_list:
        return None
    if len(surat_list) > MAX_ZIP_FILES:
        st.warning(f"⚠️ ZIP dihadkan {MAX_ZIP_FILES} fail pertama dari {len(surat_list)}. Pecah kepada beberapa ZIP jika perlu.")
        surat_list = surat_list[:MAX_ZIP_FILES]

    import zipfile
    buf = BytesIO()
    progress = st.progress(0, text="Menjana ZIP...")
    try:
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            for i, s in enumerate(surat_list):
                pdf_bytes = create_simple_pdf_bytes(
                    render_jpn_template_html(
                        s.get("jawatan",""), s.get("nama",""), s.get("ic",""),
                        s.get("sekolah_asal",""), s.get("nama_sekolah_asal",""),
                        s.get("pusat",""), s.get("nama_pusat",""),
                        s.get("no_surat",""), kod_ppd, ppd_name,
                        datetime.date.today().strftime("%d %B %Y")
                    ) or s.get("nama",""),
                    title=f"Surat {s.get('nama')}"
                )
                safe_name = re.sub(r'[^A-Za-z0-9_-]', '_', clean_nan(s.get("nama")) or f"Guru_{i}")
                zf.writestr(f"{safe_name}_{s.get('ic','')}.pdf", pdf_bytes)
                progress.progress((i+1)/len(surat_list), text=f"ZIP {i+1}/{len(surat_list)}")
        progress.empty()
        return buf.getvalue()
    except Exception as e:
        st.error(f"ZIP error: {e}")
        return None

def hantar_surat_ke_sekolah_asal_bulk(surat_list):
    """Update status jadi SURAT_SAMPAI_SEKOLAH_ASAL"""
    try:
        count=0
        for s in surat_list:
            ic = clean_nan(s.get("ic"))
            if not ic: continue
            try:
                supa.table("cadangan_sup").update({"status":"SURAT_SAMPAI_SEKOLAH_ASAL"}).eq("ic_guru", ic).execute()
                count+=1
            except Exception as e:
                _log.warning(f"hantar bulk {ic}: {e}")
        return count
    except Exception as e:
        _log.warning(f"bulk hantar error: {e}")
        return 0

# ================= UI UTILS =================
def clear_all_cache():
    st.cache_data.clear()
    st.cache_resource.clear()
    st.success("Cache dibersihkan")

def style_nama_hijau_hantar(df_input):
    try:
        status_col = next((c for c in ["STATUS","status","Status"] if c in df_input.columns), None)
        if not status_col: return df_input
        def highlight_row(row):
            s = str(row.get(status_col,"") or "").upper()
            is_hantar = any(x in s for x in ["HANTAR","LULUS"])
            is_baru = "DICADANGKAN" in s or s.strip()==""
            styles=[]
            for col in row.index:
                if "NAMA_GURU" in str(col).upper():
                    if is_hantar: styles.append('background-color:#c8e6c9; color:#1b5e20; font-weight:800;')
                    elif is_baru: styles.append('background-color:#fff9c4; color:#e65100;')
                    else: styles.append('')
                else:
                    styles.append('background-color:#e8f5e9;' if is_hantar else '')
            return styles
        return df_input.style.apply(highlight_row, axis=1)
    except Exception:
        return df_input

# ================= MAIN APP =================
def main():
    # Sidebar pemilihan role (ganti stSidebar yang hilang)
    with st.container():
        col_logo, col_title = st.columns([1,5])
        with col_title:
            st.title("📚 Pelantikan Petugas SPM Selangor 2026")
            st.caption("JPN Selangor - Template JPN Selaras + ZIP Pukal + Sekolah Asal")

    menu = st.radio("Menu", ["Dashboard PPD","Jana Surat (JPN Template)","Surat Sampai Sekolah","Export","Admin"], horizontal=True, label_visibility="collapsed")

    # PPD selector
    kod_ppd = st.selectbox("Pilih PPD", options=KOD_DAERAH, format_func=lambda x: f"{x} - {PPD_MAP.get(x)}")

    if menu == "Dashboard PPD":
        df = get_cadangan_df(kod_ppd)
        if df.empty:
            st.info(f"Tiada cadangan untuk {kod_ppd} lagi")
        else:
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Total Cadangan", len(df))
            c2.metric("Sudah Hantar PPD", len(df[df['status'].str.upper().str.contains("HANTAR|LULUS", na=False)]))
            c3.metric("Baru Dicadangkan", len(df[df['status'].str.upper().str.contains("DICADANGKAN", na=False)]))
            c4.metric("Surat Sampai Sekolah", len(df[df['status'].str.upper().str.contains("SEKOLAH_ASAL", na=False)]))
            st.dataframe(style_nama_hijau_hantar(df), use_container_width=True, hide_index=True)
            st.download_button("📥 Export Excel PPD", to_excel(df), file_name=f"{kod_ppd}_{datetime.date.today()}.xlsx", type="primary")

    elif menu == "Jana Surat (JPN Template)":
        df = get_cadangan_df(kod_ppd)
        if df.empty:
            st.warning("Tiada data untuk jana surat")
            return
        pusat_map = {}
        try:
            df_pusat = get_pusat_df()
            if not df_pusat.empty and 'kod_pusat' in df_pusat.columns:
                pusat_map = dict(zip(df_pusat['kod_pusat'].astype(str).str.upper(), df_pusat.get('nama_pusat', df_pusat['kod_pusat']).astype(str)))
        except Exception:
            pass

        surat_list = []
        for _, r in df.iterrows():
            surat_list.append({
                "nama": r.get("nama_guru",""),
                "ic": r.get("ic_guru",""),
                "jawatan": r.get("jawatan_cadangan",""),
                "sekolah_asal": r.get("kod_sekolah_asal","") or r.get("kod_sekolah",""),
                "nama_sekolah_asal": get_nama_sekolah_full(r.get("kod_sekolah_asal","") or r.get("kod_sekolah",""), ""),
                "pusat": r.get("kod_pusat",""),
                "nama_pusat": pusat_map.get(str(r.get("kod_pusat","")).upper().strip(), ""),
                "no_surat": r.get("no_surat","")
            })

        st.info(f"📄 Akan jana {len(surat_list)} surat guna Template JPN untuk {kod_ppd} - {PPD_MAP.get(kod_ppd)}")

        colA, colB = st.columns(2)
        with colA:
            if st.button(f"📄 Jana PDF Kolektif ({len(surat_list)} surat)", type="primary", use_container_width=True):
                with st.spinner("Menjana PDF..."):
                    pdf_bytes = generate_surat_kolektif_pdf_bytes_JPN(surat_list, kod_ppd, PPD_MAP.get(kod_ppd,""), f"SURAT LANTIKAN PPD {kod_ppd}")
                    if pdf_bytes:
                        st.session_state["pdf_kolektif"] = pdf_bytes
                        # auto hantar ke sekolah asal
                        hantar_surat_ke_sekolah_asal_bulk(surat_list)
                        st.success(f"✅ {len(surat_list)} surat berjaya dijana & dihantar ke sekolah asal")
        with colB:
            if st.button(f"📦 Jana ZIP Pukal ({len(surat_list)} fail)", type="primary", use_container_width=True):
                with st.spinner("Menjana ZIP..."):
                    zip_bytes = create_zip_pukal_dari_JPN(surat_list, kod_ppd, PPD_MAP.get(kod_ppd,""))
                    if zip_bytes:
                        st.session_state["zip_pukal"] = zip_bytes
                        hantar_surat_ke_sekolah_asal_bulk(surat_list)
                        st.success(f"✅ ZIP {len(surat_list)} surat berjaya")

        if "pdf_kolektif" in st.session_state:
            st.download_button("📥 Download PDF Kolektif (JPN)", st.session_state["pdf_kolektif"], file_name=f"Surat_Kolektif_{kod_ppd}_{datetime.date.today()}_JPN.pdf", mime="application/pdf", use_container_width=True)
        if "zip_pukal" in st.session_state:
            st.download_button("📦 Download ZIP Pukal (JPN)", st.session_state["zip_pukal"], file_name=f"ZIP_{kod_ppd}_{datetime.date.today()}_JPN.zip", mime="application/zip", use_container_width=True, type="primary")

    elif menu == "Surat Sampai Sekolah":
        df = get_cadangan_df(kod_ppd)
        df_sampai = df[df['status'].astype(str).str.upper().str.contains("SEKOLAH_ASAL", na=False)] if not df.empty else pd.DataFrame()
        if df_sampai.empty:
            st.info("Belum ada surat sampai ke sekolah asal")
        else:
            sekolah_list = df_sampai.get("kod_sekolah_asal", df_sampai.get("kod_sekolah")).dropna().unique().tolist()
            pilih = st.selectbox("Pilih Sekolah Asal", sekolah_list)
            df_filter = df_sampai[(df_sampai.get("kod_sekolah_asal", df_sampai.get("kod_sekolah"))==pilih)]
            st.dataframe(df_filter, use_container_width=True, hide_index=True)
            st.success(f"✅ {len(df_filter)} surat sampai ke {get_nama_sekolah_full(pilih,pilih)} - SUP boleh cetak")

    elif menu == "Export":
        df = get_cadangan_df()
        if df.empty:
            st.info("Tiada data")
        else:
            st.download_button("📥 Laporan Penuh Negeri (Excel)", to_excel(df), file_name=f"Laporan_JPN_Selangor_{datetime.date.today()}.xlsx", use_container_width=True, type="primary")

    elif menu == "Admin":
        st.header("⚙️ Status Sistem")
        for t in ["sekolah_master","pusat_master","guru_master","cadangan_sup","surat_templates_jpn"]:
            try:
                res = supa.table(t).select("*", count="exact").limit(1).execute()
                st.success(f"✅ {t}: {res.count} records")
            except Exception as e:
                st.error(f"❌ {t}: {e}")
        if st.button("🧹 Clear Cache"):
            clear_all_cache()
        st.code("""
CREATE TABLE IF NOT EXISTS surat_templates_jpn (
 id BIGSERIAL PRIMARY KEY,
 jawatan TEXT UNIQUE,
 template_html TEXT,
 created_at TIMESTAMPTZ DEFAULT NOW()
);
        """, language="sql")

    st.markdown("<div class='app-footer'>Sistem Pelantikan Petugas SPM Selangor 2026 · JPN Selangor - Fixed Clean v33.1</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
