
import streamlit as st
import pandas as pd
import json
import datetime
import re
import io
import zipfile
from supabase import create_client

st.set_page_config(page_title="JPN - Ringan 360+", layout="wide")

@st.cache_resource
def get_supa():
    try:
        SUPABASE_URL = st.secrets["SUPABASE_URL"]
        SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    except:
        SUPABASE_URL = st.secrets.get("SUPABASE_URL")
        SUPABASE_KEY = st.secrets.get("SUPABASE_KEY")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supa = get_supa()

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

@st.cache_data(ttl=300, show_spinner=False)
def get_cadangan_df_cached():
    try:
        res = supa.table("cadangan_sup").select("*").limit(2000).execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Error cadangan: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=600, show_spinner=False)
def get_jpn_templates_cached():
    try:
        res = supa.table("surat_templates_jpn").select("*").execute()
        return {r["jawatan"].upper(): r["template_html"] for r in res.data} if res.data else {}
    except:
        return {}

DEFAULT_TEMPLATES = {
    "KETUA PENGAWAS": "<div style='border:3px double #000; padding:20px;'><h3>KETUA PENGAWAS - {{NAMA}} - {{PUSAT}}</h3><p>No: {{NO_SURAT}}</p></div>",
    "TIMBALAN KETUA PENGAWAS": "<div style='border:2px solid #000; padding:20px;'><h3>TKP - {{NAMA}} - {{PUSAT}}</h3></div>",
    "PENGAWAS PEPERIKSAAN": "<div style='border:2px solid #000; padding:20px;'><h3>PENGAWAS - {{NAMA}} - {{PUSAT}}</h3></div>",
    "JURU TULIS": "<div style='border:2px solid #4527a0; padding:20px;'><h3 style='color:#4527a0;'>JURU TULIS (Khas) - {{NAMA}} - {{PUSAT}} - {{PPD}}</h3><p>No: {{NO_SURAT}}</p></div>",
    "JURU BACA": "<div style='border:2px solid #006064; padding:20px;'><h3>JURU BACA (Khas) - {{NAMA}}</h3></div>",
    "KETUA PENGAWAS HOSPITAL": "<div style='border:2px solid #b71c1c; padding:20px;'><h3>KP HOSPITAL - {{NAMA}}</h3></div>",
    "PENGAWAS HOSPITAL": "<div style='border:2px solid #c62828; padding:20px;'><h3>PENGAWAS HOSPITAL - {{NAMA}}</h3></div>",
    "PENGAWAS PENGIRING": "<div style='border:2px solid #2e7d32; padding:20px;'><h3>PENGAWAS PENGIRING - {{NAMA}}</h3></div>",
    "PENGEMAS BILIK": "<div style='border:2px solid #e65100; padding:20px;'><h3>PENGEMAS BILIK (Khas) - {{NAMA}}</h3></div>",
    "PENYELIA KAWASAN": "<div style='border:2px solid #4a148c; padding:20px;'><h3>PENYELIA KAWASAN - {{NAMA}} - {{PPD}}</h3></div>",
    "SELENGGARA BILIK KEBAL": "<div style='border:2px solid #000; padding:20px;'><h3>SELENGGARA BILIK KEBAL - {{NAMA}}</h3></div>"
}

JAWATAN_LIST = list(DEFAULT_TEMPLATES.keys())

st.sidebar.title("JPN - RINGAN 360+")
st.sidebar.success("Pagination - Tak buffering")

menu = st.sidebar.radio("Menu JPN", ["Dashboard", "Kelulusan Pukal", "Template Surat", "Jana Surat Batch", "Export ZIP"])

if st.sidebar.button("Clear Cache"):
    st.cache_data.clear()
    st.rerun()

if menu == "Dashboard":
    st.header("Dashboard JPN")
    with st.spinner("Loading..."):
        df_cad = get_cadangan_df_cached()
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Cadangan", len(df_cad))
    with col2:
        lulus = len(df_cad[df_cad["STATUS"].astype(str).str.contains("LULUS", na=False)]) if not df_cad.empty and "STATUS" in df_cad.columns else 0
        st.metric("Lulus", lulus)
    if not df_cad.empty:
        st.dataframe(df_cad.groupby("KOD_PPD").size().reset_index(name="JUMLAH"), use_container_width=True)

elif menu == "Kelulusan Pukal":
    st.header("Kelulusan Pukal - Batch 50")
    df_cad = get_cadangan_df_cached()
    if df_cad.empty:
        st.warning("Tiada data")
        st.stop()
    ppd_list = sorted(df_cad["KOD_PPD"].dropna().astype(str).str.upper().unique().tolist()) if "KOD_PPD" in df_cad.columns else []
    pilih_ppd = st.selectbox("PPD", ["SEMUA"] + ppd_list)
    df_f = df_cad if pilih_ppd=="SEMUA" else df_cad[df_cad["KOD_PPD"].astype(str).str.upper()==pilih_ppd]
    st.metric(f"Jumlah {pilih_ppd}", len(df_f))
    
    per_page = st.selectbox("Per Page", [50, 100, 200], index=0)
    total = len(df_f)
    pages = (total // per_page) + (1 if total % per_page else 0)
    page = st.number_input(f"Halaman 1-{pages}", 1, max(1,pages), 1)
    df_page = df_f.iloc[(page-1)*per_page: page*per_page]
    st.dataframe(df_page[["NAMA_GURU","JAWATAN_CADANGAN","KOD_PUSAT","KOD_PPD","STATUS"]], use_container_width=True)
    
    if st.button(f"LULUSKAN {len(df_page)} (Halaman {page})", type="primary", use_container_width=True):
        for _, r in df_page.iterrows():
            id_r = r.get("id")
            if id_r:
                supa.table("cadangan_sup").update({"status": "LULUS JPN"}).eq("id", id_r).execute()
        st.cache_data.clear()
        st.success(f"{len(df_page)} lulus")
    
    if st.button(f"LULUSKAN SEMUA {len(df_f)} (Batch 50 - ada rehat)", type="secondary", use_container_width=True):
        progress = st.progress(0)
        count=0
        for i in range(0, len(df_f), 50):
            batch = df_f.iloc[i:i+50]
            for _, r in batch.iterrows():
                id_r = r.get("id")
                if id_r:
                    supa.table("cadangan_sup").update({"status": "LULUS JPN"}).eq("id", id_r).execute()
                    count+=1
            progress.progress(min((i+50)/len(df_f), 1.0))
            import time
            time.sleep(0.5)
        st.cache_data.clear()
        st.success(f"{count} lulus")

elif menu == "Template Surat":
    st.header("Template Surat - 11 Jawatan")
    templates = get_jpn_templates_cached()
    pilih = st.selectbox("Jawatan", JAWATAN_LIST)
    current = templates.get(pilih.upper()) or DEFAULT_TEMPLATES.get(pilih, "")
    edited = st.text_area(f"Template {pilih}", value=current, height=300)
    if st.button("Simpan", type="primary"):
        try:
            existing = supa.table("surat_templates_jpn").select("id").eq("jawatan", pilih).execute()
            if existing.data:
                supa.table("surat_templates_jpn").update({"template_html": edited}).eq("jawatan", pilih).execute()
            else:
                supa.table("surat_templates_jpn").insert({"jawatan": pilih, "template_html": edited}).execute()
            st.cache_data.clear()
            st.success(f"{pilih} disimpan")
        except Exception as e:
            st.error(str(e))

elif menu == "Jana Surat Batch":
    st.header("Jana Surat - Batch (Tak buffering)")
    df_cad = get_cadangan_df_cached()
    df_lulus = df_cad[df_cad["STATUS"].astype(str).str.contains("LULUS", na=False)] if not df_cad.empty and "STATUS" in df_cad.columns else df_cad
    templates = get_jpn_templates_cached()
    if not templates:
        templates = {k.upper(): v for k,v in DEFAULT_TEMPLATES.items()}
    jawatan_opts = sorted(df_lulus["JAWATAN_CADANGAN"].dropna().unique().tolist()) if "JAWATAN_CADANGAN" in df_lulus.columns else JAWATAN_LIST
    pilih_j = st.selectbox("Jawatan", ["SEMUA"] + jawatan_opts)
    df_jana = df_lulus if pilih_j=="SEMUA" else df_lulus[df_lulus["JAWATAN_CADANGAN"]==pilih_j]
    st.metric(f"Akan Jana {pilih_j}", len(df_jana))
    batch_size = st.selectbox("Batch", [10,20,50], index=2)
    if st.button(f"Jana {len(df_jana)} Surat", type="primary"):
        surat_list=[]
        progress = st.progress(0)
        for idx in range(0, len(df_jana), batch_size):
            batch = df_jana.iloc[idx:idx+batch_size]
            for _, r in batch.iterrows():
                nama = r.get("NAMA_GURU") or ""
                jawatan = r.get("JAWATAN_CADANGAN") or pilih_j
                pusat = r.get("KOD_PUSAT") or ""
                ppd = r.get("KOD_PPD") or ""
                id_r = r.get("id")
                tmpl = templates.get(str(jawatan).upper().strip(), "")
                no_surat = f"JPN.{ppd}.SPM2026/{str(id_r)[-4:].upper()}" if id_r else "JPN/0001"
                html = tmpl
                for k,v in {"NAMA": nama, "JAWATAN": jawatan, "PUSAT": pusat, "NO_SURAT": no_surat, "PPD": ppd}.items():
                    html = html.replace("{{"+k+"}}", str(v))
                surat_list.append({"nama": nama, "jawatan": jawatan, "pusat": pusat, "ppd": ppd, "html": html, "no_surat": no_surat, "id": id_r})
            progress.progress(min((idx+batch_size)/len(df_jana), 1.0))
            import time
            time.sleep(0.3)
        st.session_state.surat_list_jpn = surat_list
        st.success(f"{len(surat_list)} surat dijana")

elif menu == "Export ZIP":
    st.header("Export & ZIP")
    df_cad = get_cadangan_df_cached()
    st.download_button("Excel Semua", to_excel(df_cad), "export_jpn.xlsx")
    surat_list = st.session_state.get("surat_list_jpn", [])
    if not surat_list:
        st.warning("Belum jana surat")
    else:
        st.success(f"{len(surat_list)} surat sedia")
        if st.button("ZIP Keseluruhan"):
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
                for s in surat_list:
                    fname = f"{s['ppd']}_{s['pusat']}_{s['jawatan']}_{s['nama']}".replace(" ", "_")[:100]
                    zf.writestr(f"{fname}.html", s['html'])
            zip_buf.seek(0)
            st.download_button("Download ZIP", zip_buf.getvalue(), f"ZIP_JPN_{datetime.date.today()}.zip", "application/zip")
