
import streamlit as st
import pandas as pd
import json
import datetime
import re
import io
import zipfile
from supabase import create_client

# Supabase connection (same as PPD/SUP)
SUPABASE_URL = st.secrets.get("SUPABASE_URL") or "https://your-project.supabase.co"
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or "your-anon-key"
supa = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="JPN - Surat Lantikan & Kelulusan Pukal", layout="wide")

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

def get_cadangan_df():
    try:
        res = supa.table("cadangan_sup").select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Error get cadangan: {e}")
        return pd.DataFrame()

def get_pusat_df():
    try:
        res = supa.table("pusat_master").select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Error get pusat: {e}")
        return pd.DataFrame()

# Default templates per jawatan - JPN selaraskan
DEFAULT_TEMPLATES = {
    "KETUA PENGAWAS": """<html><head><meta charset="UTF-8"><style>body{font-family:Times New Roman; margin:40px;} .surat{border:3px double #000; padding:30px;} .header{text-align:center; border-bottom:3px double #000; padding-bottom:15px;} table.info{width:100%; margin:15px 0;} table.info td{padding:6px;} table.info td:first-child{width:180px; font-weight:bold;}</style></head><body><div class="surat"><div class="header"><h2>JABATAN PENDIDIKAN NEGERI SELANGOR</h2><h3>SURAT LANTIKAN KETUA PENGAWAS SPM 2026</h3><p>No: {{NO_SURAT}} | Tarikh: {{TARIKH}}</p></div><p><strong>Tuan/Puan {{NAMA}} ({{IC}})</strong></p><p>Dengan sukacitanya dimaklumkan Tuan/Puan dilantik sebagai <strong>KETUA PENGAWAS</strong> peperiksaan SPM 2026.</p><table class="info"><tr><td>Nama</td><td>: {{NAMA}}</td></tr><tr><td>IC</td><td>: {{IC}}</td></tr><tr><td>Jawatan</td><td>: KETUA PENGAWAS</td></tr><tr><td>Sekolah Asal</td><td>: {{SEKOLAH_ASAL}} - {{NAMA_SEKOLAH_ASAL}}</td></tr><tr><td>Pusat</td><td>: {{PUSAT}} - {{NAMA_PUSAT}}</td></tr><tr><td>PPD</td><td>: {{PPD}}</td></tr></table><p><strong>Tanggungjawab KP:</strong> Mengetuai semua petugas, memastikan kelancaran peperiksaan, bertanggungjawab ke atas bilik kebal dan kertas soalan.</p><p>Sekian, terima kasih.</p><div style="margin-top:60px;"><p>Yang benar,<br><br><br>_______________________<br><strong>Pengarah Pendidikan Negeri Selangor</strong></p></div></div></body></html>""",
    "TIMBALAN KETUA PENGAWAS": """<html><head><meta charset="UTF-8"><style>body{font-family:Times New Roman; margin:40px;} .surat{border:3px double #000; padding:30px;} .header{text-align:center; border-bottom:3px double #000;}</style></head><body><div class="surat"><div class="header"><h2>SURAT LANTIKAN TIMBALAN KETUA PENGAWAS SPM 2026</h2><p>No: {{NO_SURAT}}</p></div><p>Tuan/Puan {{NAMA}} ({{IC}}) dilantik sebagai TIMBALAN KETUA PENGAWAS di {{PUSAT}}.</p><p>Tugas: Membantu KP dan mengambil alih tugas KP jika tiada.</p></div></body></html>""",
    "PENGAWAS PEPERIKSAAN": """<html><head><meta charset="UTF-8"></head><body><div style="border:2px solid #000; padding:30px;"><h2 style="text-align:center;">SURAT LANTIKAN PENGAWAS PEPERIKSAAN SPM 2026</h2><p>Tuan/Puan {{NAMA}} dilantik sebagai PENGAWAS PEPERIKSAAN di {{PUSAT}}.</p><p>Tugas: Mengawas peperiksaan dalam dewan/bilik.</p><p>No Surat: {{NO_SURAT}} | PPD: {{PPD}}</p></div></body></html>""",
    "JURU TULIS": """<html><body><div style="border:2px solid #4527a0; padding:30px;"><h2 style="color:#4527a0;">SURAT LANTIKAN JURU TULIS SPM 2026 (Pengawas Khas)</h2><p>Tuan/Puan {{NAMA}} dilantik sebagai JURU TULIS untuk calon berkeperluan khas di {{PUSAT}}.</p><p>Tugas: Menulis jawapan bagi pihak calon OKU/calon khas. Lantikan ini adalah tambahan, tidak termasuk dalam 19 petugas biasa.</p><p>No: {{NO_SURAT}}</p></div></body></html>""",
    "JURU BACA": """<html><body><div style="border:2px solid #006064; padding:30px;"><h2 style="color:#006064;">SURAT LANTIKAN JURU BACA SPM 2026 (Pengawas Khas)</h2><p>Tuan/Puan {{NAMA}} dilantik sebagai JURU BACA di {{PUSAT}}.</p><p>Tugas: Membacakan soalan kepada calon berkeperluan khas.</p></div></body></html>""",
    "KETUA PENGAWAS HOSPITAL": """<html><body><div style="border:2px solid #b71c1c; padding:30px;"><h2>SURAT LANTIKAN KETUA PENGAWAS HOSPITAL SPM 2026</h2><p>Tuan/Puan {{NAMA}} dilantik sebagai KETUA PENGAWAS HOSPITAL di {{PUSAT}}.</p></div></body></html>""",
    "PENGAWAS HOSPITAL": """<html><body><div style="border:2px solid #c62828; padding:30px;"><h2>SURAT LANTIKAN PENGAWAS HOSPITAL SPM 2026</h2><p>Tuan/Puan {{NAMA}} dilantik sebagai PENGAWAS HOSPITAL di {{PUSAT}}.</p></div></body></html>""",
    "PENGAWAS PENGIRING": """<html><body><div style="border:2px solid #2e7d32; padding:30px;"><h2>SURAT LANTIKAN PENGAWAS PENGIRING SPM 2026</h2><p>Tuan/Puan {{NAMA}} dilantik sebagai PENGAWAS PENGIRING di {{PUSAT}}.</p></div></body></html>""",
    "PENGEMAS BILIK": """<html><body><div style="border:2px solid #e65100; padding:30px;"><h2>SURAT LANTIKAN PENGEMAS BILIK SPM 2026 (Pengawas Khas)</h2><p>Tuan/Puan {{NAMA}} dilantik sebagai PENGEMAS BILIK di {{PUSAT}}.</p><p>Tugas: Mengemas dan menyediakan bilik peperiksaan.</p></div></body></html>""",
    "PENYELIA KAWASAN": """<html><body><div style="border:2px solid #4a148c; padding:30px;"><h2>SURAT LANTIKAN PENYELIA KAWASAN SPM 2026</h2><p>Tuan/Puan {{NAMA}} dilantik sebagai PENYELIA KAWASAN daerah {{PPD}}.</p></div></body></html>""",
    "SELENGGARA BILIK KEBAL": """<html><body><div style="border:2px solid #000; padding:30px;"><h2>SURAT LANTIKAN SELENGGARA BILIK KEBAL SPM 2026</h2><p>Tuan/Puan {{NAMA}} dilantik sebagai SELENGGARA BILIK KEBAL di {{PUSAT}}.</p></div></body></html>"""
}

JAWATAN_LIST = list(DEFAULT_TEMPLATES.keys())

st.sidebar.title("🏛️ JPN SELANGOR")
st.sidebar.info("🔒 PPD & SUP LOCKED\nFile ini standalone - tak kacau PPD/SUP")

menu = st.sidebar.radio("Menu JPN", [
    "📊 Dashboard JPN",
    "✅ Kelulusan Pukal",
    "📄 Template Surat Lantikan (JPN Selaraskan)",
    "🖨️ Jana Surat Lantikan Mengikut Jawatan",
    "📦 Export & ZIP Keseluruhan + Daerah"
])

if menu == "📊 Dashboard JPN":
    st.header("📊 Dashboard JPN - Keseluruhan Negeri")
    df_cad = get_cadangan_df()
    df_pusat = get_pusat_df()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Jumlah Pusat", len(df_pusat))
    with col2:
        st.metric("Jumlah Cadangan", len(df_cad) if not df_cad.empty else 0)
    with col3:
        lulus = len(df_cad[df_cad["STATUS"].astype(str).str.contains("LULUS", na=False)]) if not df_cad.empty and "STATUS" in df_cad.columns else 0
        st.metric("Telah Lulus", lulus)
    with col4:
        belum = len(df_cad) - lulus if not df_cad.empty else 0
        st.metric("Belum Lulus", belum)
    
    st.markdown("---")
    if not df_cad.empty and "KOD_PPD" in df_cad.columns:
        ringkas = df_cad.groupby("KOD_PPD").agg(JUMLAH=("KOD_PPD","size"), LULUS=("STATUS", lambda x: sum("LULUS" in str(s).upper() for s in x))).reset_index()
        st.dataframe(ringkas, use_container_width=True)

elif menu == "✅ Kelulusan Pukal":
    st.header("✅ Kelulusan Pukal JPN")
    df_cad = get_cadangan_df()
    if df_cad.empty:
        st.warning("Tiada data")
        st.stop()
    
    ppd_list = sorted(df_cad["KOD_PPD"].dropna().astype(str).str.upper().unique().tolist()) if "KOD_PPD" in df_cad.columns else []
    
    col1, col2 = st.columns(2)
    with col1:
        pilih_ppd = st.selectbox("Pilih PPD", ["SEMUA"] + ppd_list)
    with col2:
        pilih_status = st.selectbox("Status", ["DICADANGKAN", "SEMUA"])
    
    df_f = df_cad.copy()
    if pilih_ppd != "SEMUA" and "KOD_PPD" in df_f.columns:
        df_f = df_f[df_f["KOD_PPD"].astype(str).str.upper() == pilih_ppd]
    if pilih_status == "DICADANGKAN" and "STATUS" in df_f.columns:
        df_f = df_f[df_f["STATUS"].astype(str).str.upper().str.contains("CADANG", na=False)]
    
    st.metric(f"Jumlah untuk diluluskan - {pilih_ppd}", len(df_f))
    st.dataframe(df_f[["NAMA_GURU","IC_GURU","JAWATAN_CADANGAN","KOD_SEKOLAH_ASAL","KOD_PUSAT","KOD_PPD","STATUS"]].head(100), use_container_width=True)
    
    if st.button(f"✅ LULUSKAN {len(df_f)} - {pilih_ppd}", type="primary", use_container_width=True):
        try:
            count = 0
            for _, r in df_f.iterrows():
                id_r = r.get("id")
                if id_r:
                    supa.table("cadangan_sup").update({"status": "LULUS JPN - MENUNGGU SURAT JPN"}).eq("id", id_r).execute()
                    count += 1
            st.success(f"✅ {count} diluluskan JPN")
            st.balloons()
        except Exception as e:
            st.error(str(e))

elif menu == "📄 Template Surat Lantikan (JPN Selaraskan)":
    st.header("📄 Template Surat Lantikan Mengikut Jawatan - JPN Selaraskan")
    st.warning("⚠️ Surat lama PPD akan diganti dengan template JPN ini (setiap jawatan berbeza)")
    
    # Load from DB
    try:
        res = supa.table("surat_templates_jpn").select("*").execute()
        db_templates = {r["jawatan"].upper(): r["template_html"] for r in res.data} if res.data else {}
    except:
        db_templates = {}
        st.info("Table surat_templates_jpn belum wujud - guna session state")
    
    pilih_jawatan = st.selectbox("Pilih Jawatan", JAWATAN_LIST)
    
    current = db_templates.get(pilih_jawatan.upper()) or st.session_state.get("jpn_templates", {}).get(pilih_jawatan) or DEFAULT_TEMPLATES.get(pilih_jawatan, "")
    
    st.markdown(f"### Edit Template: {pilih_jawatan}")
    edited = st.text_area("HTML Template", value=current, height=400, key=f"edit_{pilih_jawatan}")
    
    st.markdown("**Placeholder:** {{NAMA}}, {{IC}}, {{JAWATAN}}, {{SEKOLAH_ASAL}}, {{PUSAT}}, {{NO_SURAT}}, {{PPD}}, {{TARIKH}}")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Simpan Template JPN", type="primary", use_container_width=True):
            try:
                # Save to DB
                try:
                    existing = supa.table("surat_templates_jpn").select("id").eq("jawatan", pilih_jawatan).execute()
                    if existing.data:
                        supa.table("surat_templates_jpn").update({"template_html": edited, "updated_at": str(datetime.datetime.now())}).eq("jawatan", pilih_jawatan).execute()
                    else:
                        supa.table("surat_templates_jpn").insert({"jawatan": pilih_jawatan, "template_html": edited}).execute()
                    st.success(f"✅ {pilih_jawatan} disimpan ke DB")
                except Exception as e:
                    if "jpn_templates" not in st.session_state:
                        st.session_state.jpn_templates = {}
                    st.session_state.jpn_templates[pilih_jawatan] = edited
                    st.success(f"✅ {pilih_jawatan} disimpan (session) - DB belum ada: {e}")
            except Exception as e:
                st.error(str(e))
    
    with col2:
        if st.button("👁️ Preview", use_container_width=True):
            dummy = {"NAMA": "ALI BIN ABU", "IC": "800101-10-1234", "JAWATAN": pilih_jawatan, "SEKOLAH_ASAL": "BEA0001", "NAMA_SEKOLAH_ASAL": "SK CONTOH", "PUSAT": "BA001", "NAMA_PUSAT": "SMK CONTOH", "NO_SURAT": f"JPN.SPM2026/{pilih_jawatan[:3]}/0001", "PPD": "PETALING UTAMA", "TARIKH": str(datetime.date.today())}
            html = edited
            for k,v in dummy.items():
                html = html.replace("{{"+k+"}}", v).replace("{{ "+k+" }}", v)
            st.markdown(html, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### Semua Template Status")
    status_list = []
    for j in JAWATAN_LIST:
        t = db_templates.get(j.upper()) or st.session_state.get("jpn_templates", {}).get(j) or DEFAULT_TEMPLATES.get(j, "")
        status_list.append({"JAWATAN": j, "PANJANG": len(t), "STATUS": "✅ Ada" if len(t)>50 else "❌ Tiada"})
    st.dataframe(pd.DataFrame(status_list), use_container_width=True)

elif menu == "🖨️ Jana Surat Lantikan Mengikut Jawatan":
    st.header("🖨️ Jana Surat Lantikan Mengikut Jawatan - JPN")
    
    df_cad = get_cadangan_df()
    if df_cad.empty:
        st.warning("Tiada data")
        st.stop()
    
    df_lulus = df_cad[df_cad["STATUS"].astype(str).str.contains("LULUS", na=False)] if "STATUS" in df_cad.columns else df_cad
    
    st.metric("Jumlah Lulus (Perlu Surat)", len(df_lulus))
    
    # Load templates
    try:
        res = supa.table("surat_templates_jpn").select("*").execute()
        templates = {r["jawatan"].upper(): r["template_html"] for r in res.data} if res.data else {}
    except:
        templates = {k.upper(): v for k,v in st.session_state.get("jpn_templates", {}).items()}
        if not templates:
            templates = {k.upper(): v for k,v in DEFAULT_TEMPLATES.items()}
    
    jawatan_opts = sorted(df_lulus["JAWATAN_CADANGAN"].dropna().unique().tolist()) if "JAWATAN_CADANGAN" in df_lulus.columns else JAWATAN_LIST
    pilih_j = st.selectbox("Pilih Jawatan Untuk Jana", ["SEMUA JAWATAN"] + jawatan_opts)
    
    df_jana = df_lulus if pilih_j == "SEMUA JAWATAN" else df_lulus[df_lulus["JAWATAN_CADANGAN"] == pilih_j]
    
    st.metric(f"Jumlah Akan Dijana - {pilih_j}", len(df_jana))
    
    if st.button(f"🖨️ Jana {len(df_jana)} Surat - {pilih_j}", type="primary", use_container_width=True):
        progress = st.progress(0)
        surat_list = []
        for i, (_, r) in enumerate(df_jana.iterrows()):
            nama = r.get("NAMA_GURU") or ""
            ic = r.get("IC_GURU") or ""
            jawatan = r.get("JAWATAN_CADANGAN") or pilih_j
            sek = r.get("KOD_SEKOLAH_ASAL") or ""
            pusat = r.get("KOD_PUSAT") or ""
            ppd = r.get("KOD_PPD") or ""
            id_r = r.get("id")
            
            tmpl = templates.get(str(jawatan).upper().strip()) or DEFAULT_TEMPLATES.get(str(jawatan).upper().strip(), DEFAULT_TEMPLATES["PENGAWAS PEPERIKSAAN"])
            
            no_surat = f"JPN.{ppd}.SPM2026/{str(jawatan)[:3].upper()}/{str(id_r)[-4:].upper()}" if id_r else f"JPN.{ppd}.SPM2026/0001"
            
            html = tmpl
            rep = {"NAMA": str(nama), "IC": str(ic), "JAWATAN": str(jawatan), "SEKOLAH_ASAL": str(sek), "NAMA_SEKOLAH_ASAL": str(sek), "PUSAT": str(pusat), "NAMA_PUSAT": str(pusat), "NO_SURAT": no_surat, "PPD": str(ppd), "TARIKH": str(datetime.date.today())}
            for k,v in rep.items():
                html = html.replace("{{"+k+"}}", v).replace("{{ "+k+" }}", v)
            
            surat_list.append({"nama": nama, "ic": ic, "jawatan": jawatan, "pusat": pusat, "ppd": ppd, "id": id_r, "html": html, "no_surat": no_surat})
            
            # Save to DB
            try:
                if id_r:
                    supa.table("cadangan_sup").update({"status": f"LULUS JPN - SURAT {jawatan} DIJANA", "no_surat": no_surat}).eq("id", id_r).execute()
                    # Also save html to data json
                    try:
                        existing = supa.table("cadangan_sup").select("data").eq("id", id_r).limit(1).execute()
                        old = existing.data[0].get("data") or {} if existing.data else {}
                        if isinstance(old, str):
                            try: old = json.loads(old)
                            except: old = {}
                        old.update({"surat_html_jpn": html, "surat_no_jpn": no_surat, "surat_jawatan": jawatan})
                        supa.table("cadangan_sup").update({"data": old}).eq("id", id_r).execute()
                    except:
                        pass
            except:
                pass
            
            progress.progress((i+1)/len(df_jana))
        
        st.session_state.surat_list_jpn = surat_list
        st.success(f"✅ {len(surat_list)} surat {pilih_j} dijana (template JPN)")
        st.balloons()
        
        # Preview 2
        for s in surat_list[:2]:
            with st.expander(f"{s['nama']} - {s['jawatan']}"):
                st.markdown(s['html'], unsafe_allow_html=True)

elif menu == "📦 Export & ZIP Keseluruhan + Daerah":
    st.header("📦 Export Keseluruhan & ZIP - JPN")
    
    df_cad = get_cadangan_df()
    if df_cad.empty:
        st.warning("Tiada data")
        st.stop()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Jumlah Semua", len(df_cad))
        st.download_button("📥 Excel Semua", to_excel(df_cad), "export_keseluruhan_jpn.xlsx", use_container_width=True)
    with col2:
        df_lulus = df_cad[df_cad["STATUS"].astype(str).str.contains("LULUS", na=False)] if "STATUS" in df_cad.columns else df_cad
        st.metric("Jumlah Lulus", len(df_lulus))
        st.download_button("📥 Excel Lulus", to_excel(df_lulus), "export_lulus_jpn.xlsx", use_container_width=True)
    
    st.markdown("---")
    st.markdown("### 📦 ZIP Surat Lantikan")
    
    surat_list = st.session_state.get("surat_list_jpn", [])
    if not surat_list:
        st.warning("⚠️ Belum jana surat. Pergi ke 'Jana Surat Lantikan' dulu")
        # Try load from DB
        try:
            df_with_surat = df_cad[df_cad["STATUS"].astype(str).str.contains("SURAT", na=False)] if "STATUS" in df_cad.columns else pd.DataFrame()
            st.info(f"Ada {len(df_with_surat)} rekod dengan surat dalam DB - boleh jana ZIP dari DB jika perlu")
        except:
            pass
    else:
        st.success(f"✅ {len(surat_list)} surat sedia")
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📦 ZIP Keseluruhan (Semua Daerah)", type="primary", use_container_width=True):
                zip_buf = io.BytesIO()
                with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for s in surat_list:
                        fname = f"{s['ppd']}_{s['pusat']}_{s['jawatan']}_{s['nama']}".replace(" ", "_").replace("/", "_")[:100]
                        zf.writestr(f"{fname}.html", s['html'])
                zip_buf.seek(0)
                st.download_button("📥 Download ZIP Keseluruhan", zip_buf.getvalue(), f"ZIP_Keseluruhan_JPN_{datetime.date.today()}.zip", "application/zip", use_container_width=True)
        
        with c2:
            ppd_list = sorted(list(set([s['ppd'] for s in surat_list if s['ppd']])))
            pilih_ppd_zip = st.selectbox("Pilih Daerah", ppd_list)
            if st.button(f"📦 ZIP Daerah {pilih_ppd_zip}", type="primary", use_container_width=True):
                filt = [s for s in surat_list if s['ppd'] == pilih_ppd_zip]
                zip_buf = io.BytesIO()
                with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for s in filt:
                        fname = f"{s['pusat']}_{s['jawatan']}_{s['nama']}".replace(" ", "_")[:100]
                        zf.writestr(f"{fname}.html", s['html'])
                zip_buf.seek(0)
                st.download_button(f"📥 Download ZIP {pilih_ppd_zip}", zip_buf.getvalue(), f"ZIP_{pilih_ppd_zip}_{datetime.date.today()}.zip", "application/zip", use_container_width=True)
    
    st.markdown("---")
    st.markdown("### 📋 Ringkasan Jawatan x Daerah")
    if not df_cad.empty and "JAWATAN_CADANGAN" in df_cad.columns and "KOD_PPD" in df_cad.columns:
        ringkas = df_cad.groupby(["KOD_PPD", "JAWATAN_CADANGAN"]).size().reset_index(name="JUMLAH")
        st.dataframe(ringkas, use_container_width=True)
        st.download_button("📥 Export Ringkasan", to_excel(ringkas), "ringkasan_jawatan_daerah.xlsx", use_container_width=True)
