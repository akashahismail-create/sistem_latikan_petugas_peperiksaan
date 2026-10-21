import streamlit as st
import pandas as pd
from supabase import create_client
from io import BytesIO
import datetime

st.set_page_config(page_title="Pelantikan SPM Selangor 2026", layout="wide", page_icon="📚")

# ================= CONFIG - KEY BARU FULL =================
SUPABASE_URL = "https://gnmaijhugkkvxejvsotk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdubWFpamh1Z2trdnhlanZzb3RrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTI0ODc4OTcsImV4cCI6MjEwODA2Mzg5N30.1YWg71nCwnQzP-KUzTdHR4rZAVCAesbKVqvVC1-X6lw"

@st.cache_resource
def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supa = get_supabase()

KOD_DAERAH = ["BA","BB","BC","BD","BE","BF","BG","BH","BJ","BK"]
PPD_MAP = {"BA":"Klang","BB":"Kuala Langat","BC":"Kuala Selangor","BD":"Hulu Langat","BE":"Hulu Selangor","BF":"Sabak Bernam","BG":"Gombak","BH":"Petaling Perdana","BJ":"Sepang","BK":"Petaling Utama"}

# ================= HELPERS - FIX RLS + MULTI COLUMN SUPPORT =================
def safe_count(table_name):
    """Count dengan fallback kalau RLS block count exact"""
    try:
        res = supa.table(table_name).select("*", count="exact").limit(1).execute()
        if res.count is not None and res.count > 0:
            return res.count
        # Jika count 0 tapi data ada, try fetch
        if res.data and len(res.data) > 0:
            # Fetch lebih banyak untuk count
            res2 = supa.table(table_name).select("id").limit(1000).execute()
            if res2.data:
                # Kalau 1000, maksudnya lebih dari 1000, kita cuba count exact lagi dengan filter id>0
                if len(res2.data) == 1000:
                    return 1000  # at least
                return len(res2.data)
            return len(res.data)
        # Try full fetch without count
        res3 = supa.table(table_name).select("*").limit(1000).execute()
        return len(res3.data) if res3.data else 0
    except Exception as e:
        # Last fallback
        try:
            res = supa.table(table_name).select("*").limit(1000).execute()
            return len(res.data) if res.data else 0
        except:
            return 0

def get_sekolah(kod):
    # Support both kod_sekolah and Kod_Sekolah etc - try multiple
    for col in ["kod_sekolah", "kod_sekolah_tuan_rumah", "KOD_SEKOLAH"]:
        try:
            res = supa.table("sekolah_master").select("*").eq(col, kod.upper()).limit(1).execute()
            if res.data:
                row = res.data[0]
                # Normalize keys
                return {
                    "kod_sekolah": row.get("kod_sekolah") or row.get("KOD_SEKOLAH") or kod,
                    "nama_sekolah": row.get("nama_sekolah") or row.get("NAMA_SEKOLAH") or row.get("nama_pusat") or f"SEKOLAH {kod}",
                    "kod_ppd": row.get("kod_ppd") or row.get("KOD_PPD") or "BH",
                    "ppd": row.get("ppd") or row.get("PPD") or "Petaling Perdana",
                    "_raw": row
                }
        except:
            continue
    return {"kod_sekolah": kod, "nama_sekolah": f"SEKOLAH {kod}", "kod_ppd": "BH", "ppd": "Petaling Perdana"}

def get_guru_df(kod_sekolah):
    try:
        # Try both column names
        res = None
        for col in ["kod_sekolah", "KOD_SEKOLAH", "kod_sekolah_tuan_rumah"]:
            try:
                r = supa.table("guru_master").select("*").eq(col, kod_sekolah.upper()).limit(2000).execute()
                if r.data:
                    res = r
                    break
            except:
                continue
        if not res:
            res = supa.table("guru_master").select("*").eq("kod_sekolah", kod_sekolah.upper()).limit(2000).execute()
        
        rows=[]
        for r in res.data or []:
            d = r.get("data") or {}
            # Handle both JSON and flat
            rows.append({
                "id": r.get("id"),
                "NAMA GURU": r.get("nama_guru") or d.get("NAMA GURU","") or r.get("NAMA_GURU",""),
                "IC": r.get("ic_guru") or d.get("IC","") or r.get("IC",""),
                "JANTINA": d.get("JANTINA","") or r.get("jantina",""),
                "TELEFON": d.get("NO TELEFON GURU","") or d.get("TELEFON","") or r.get("no_telefon",""),
                "JAWATAN CADANGAN": d.get("JAWATAN CADANGAN","") or r.get("jawatan",""),
                "ALAMAT": d.get("ALAMAT RUMAH","") or r.get("alamat",""),
                "KOD SEKOLAH": r.get("kod_sekolah") or d.get("KOD SEKOLAH","") or kod_sekolah,
                "data_full": d if isinstance(d, dict) else {}
            })
        return pd.DataFrame(rows)
    except Exception as e:
        st.error(f"guru_master error: {e}")
        return pd.DataFrame()

def get_pusat_df():
    try:
        res = supa.table("pusat_master").select("*").limit(2000).execute()
        df = pd.DataFrame(res.data or [])
        if not df.empty:
            # Normalize column names: support no_pusat / kod_pusat / NO_PUSAT
            # Create unified view
            df_norm = df.copy()
            # Map to standard
            if "no_pusat" in df_norm.columns:
                df_norm["kod_pusat_std"] = df_norm["no_pusat"]
            elif "kod_pusat" in df_norm.columns:
                df_norm["kod_pusat_std"] = df_norm["kod_pusat"]
            elif "NO_PUSAT" in df_norm.columns:
                df_norm["kod_pusat_std"] = df_norm["NO_PUSAT"]
            else:
                df_norm["kod_pusat_std"] = df_norm.iloc[:,1] if len(df_norm.columns)>1 else ""
            
            if "nama_pusat" in df_norm.columns:
                df_norm["nama_pusat_std"] = df_norm["nama_pusat"]
            elif "NAMA_PUSAT" in df_norm.columns:
                df_norm["nama_pusat_std"] = df_norm["NAMA_PUSAT"]
            else:
                df_norm["nama_pusat_std"] = df_norm.get("nama_sekolah","")
        return df
    except Exception as e:
        st.error(f"pusat_master error: {e}")
        return pd.DataFrame()

def get_cadangan_df(kod_ppd=None, kod_sekolah=None):
    try:
        q = supa.table("cadangan_sup").select("*")
        if kod_ppd:
            # Try both upper lower
            try:
                q = q.eq("kod_ppd", kod_ppd)
            except:
                q = q.eq("KOD_PPD", kod_ppd)
        if kod_sekolah:
            q = q.eq("kod_sekolah", kod_sekolah.upper())
        res = q.limit(5000).execute()
        return pd.DataFrame(res.data or [])
    except Exception as e:
        st.error(f"cadangan_sup error: {e}")
        return pd.DataFrame()

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# ================= SESSION =================
if "role" not in st.session_state:
    st.session_state.role=None

# ================= LOGIN PAGE =================
if st.session_state.role is None:
    st.title("📚 Sistem Pelantikan Petugas Peperiksaan Selangor 2026")
    st.caption(f"Supabase: {SUPABASE_URL} | Key: Active ✅")
    st.markdown("---")
    col1,col2,col3 = st.columns(3)
    with col1:
        st.subheader("🏫 SUP - Penyelia Sekolah")
        with st.container(border=True):
            kod = st.text_input("KOD SEKOLAH", value="BFT8002", key="sup_kod").upper()
            if st.button("Masuk SUP", use_container_width=True, type="primary"):
                info=get_sekolah(kod)
                st.session_state.role="SUP"
                st.session_state.kod=kod
                st.session_state.info=info
                st.rerun()
            st.caption("Contoh: BFT8002, BEA1234")
    with col2:
        st.subheader("🏢 PPD - Pejabat Pendidikan Daerah")
        with st.container(border=True):
            ppd=st.selectbox("PILIH PPD", KOD_DAERAH, format_func=lambda x: f"{x} - {PPD_MAP[x]}", key="ppd_kod")
            if st.button("Masuk PPD", use_container_width=True, type="primary"):
                st.session_state.role="PPD"
                st.session_state.kod=ppd
                st.rerun()
    with col3:
        st.subheader("🏛️ JPN - Jabatan Pendidikan Negeri")
        with st.container(border=True):
            st.write("Akses penuh semua PPD & Sekolah")
            if st.button("Masuk JPN", use_container_width=True, type="primary"):
                st.session_state.role="JPN"
                st.rerun()
    st.info("💡 Tip: Lepas login SUP, kau boleh Tambah Guru, Import Excel, Buang Guru, dan Cadang Petugas untuk hantar ke PPD.")
    st.stop()

# ================= SUP =================
if st.session_state.role=="SUP":
    kod=st.session_state.kod
    info=st.session_state.info
    st.sidebar.title(f"🏫 SUP {kod}")
    st.sidebar.caption(f"{info.get('nama_sekolah','')} | {info.get('kod_ppd','BH')} - {PPD_MAP.get(info.get('kod_ppd','BH'),'')}")

    menu=st.sidebar.radio("Menu SUP", ["📊 Dashboard","📋 Senarai Guru","➕ Tambah Guru","📤 Import Excel","🗑️ Buang Guru","🏫 Pusat Peperiksaan","📝 Cadangan Lantikan","📤 Hantar ke PPD","🚪 Log Keluar"])

    if menu=="🚪 Log Keluar":
        st.session_state.clear()
        st.rerun()

    df_guru = get_guru_df(kod)

    if menu=="📊 Dashboard":
        st.header(f"Dashboard SUP - {kod} {info.get('nama_sekolah','')}")
        c1,c2,c3,c4 = st.columns(4)
        with c1:
            st.metric("Jumlah Guru", len(df_guru))
        with c2:
            try:
                cnt=supa.table("guru_master").select("id", count="exact").execute()
                st.metric("Total Guru Selangor", cnt.count)
            except:
                st.metric("Total Guru Selangor", "-")
        with c3:
            try:
                pusat = get_pusat_df()
                st.metric("Pusat Peperiksaan", len(pusat))
            except:
                st.metric("Pusat", "-")
        with c4:
            try:
                cad = get_cadangan_df(kod_sekolah=kod)
                st.metric("Cadangan Dihantar", len(cad))
            except:
                st.metric("Cadangan", "0")
        st.markdown("---")
        st.subheader("Guru Terkini")
        if not df_guru.empty:
            st.dataframe(df_guru[["NAMA GURU","IC","TELEFON","JAWATAN CADANGAN"]], use_container_width=True, hide_index=True)
        else:
            st.warning("Belum ada guru. Sila Tambah Guru atau Import Excel.")

    elif menu=="📋 Senarai Guru":
        st.header(f"Senarai Guru - {kod}")
        if df_guru.empty:
            st.info("guru_master kosong untuk sekolah ini. Sila Tambah Guru atau Import Excel.")
            st.write(f"Total dalam sistem: {supa.table('guru_master').select('id', count='exact').execute().count} records")
        else:
            st.success(f"Ada {len(df_guru)} guru di {kod}")
            st.dataframe(df_guru[["NAMA GURU","IC","TELEFON","JAWATAN CADANGAN","ALAMAT"]], use_container_width=True, hide_index=True)
            st.download_button("📥 Export Excel", to_excel(df_guru), file_name=f"guru_{kod}.xlsx", use_container_width=True)

    elif menu=="➕ Tambah Guru":
        st.header(f"Tambah Guru - {kod}")
        with st.form("tambah_guru", clear_on_submit=True):
            col1,col2 = st.columns(2)
            with col1:
                nama=st.text_input("NAMA GURU *")
                ic=st.text_input("NO IC * (12 digit)")
                tel=st.text_input("NO TELEFON *")
                jantina=st.selectbox("JANTINA", ["LELAKI","PEREMPUAN"])
            with col2:
                jaw=st.selectbox("JAWATAN CADANGAN", ["Pengawas Peperiksaan","Ketua Pengawas","Pengawas Bertugas","Pembantu Peperiksaan"])
                alamat=st.text_area("ALAMAT RUMAH")
                pengalaman=st.text_input("PENGALAMAN (Tahun)")
            submit=st.form_submit_button("💾 Simpan Guru", use_container_width=True, type="primary")
            if submit:
                if not nama or not ic or not tel:
                    st.error("Nama, IC, Telefon wajib isi!")
                else:
                    data={"NAMA GURU":nama.upper(),"IC":ic,"NO TELEFON GURU":tel,"JANTINA":jantina,"JAWATAN CADANGAN":jaw,"ALAMAT RUMAH":alamat,"PENGALAMAN":pengalaman,"KOD SEKOLAH":kod, "TARIKH DAFTAR": str(datetime.date.today())}
                    try:
                        supa.table("guru_master").insert({"kod_ppd":info.get("kod_ppd","BH").lower(),"kod_sekolah":kod,"nama_guru":nama.upper(),"ic_guru":ic,"data":data}).execute()
                        st.success(f"✅ {nama.upper()} berjaya tambah ke {kod}!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Gagal: {e}")

    elif menu=="📤 Import Excel":
        st.header(f"Import Excel Guru - {kod}")
        st.info("Format Excel: NAMA GURU, IC, JANTINA, NO TELEFON GURU, EMAIL GURU, ALAMAT RUMAH, KOD SEKOLAH, KOD PPD | Untuk 60K, guna JPN > Import")
        st.download_button("📥 Download Template", to_excel(pd.DataFrame([{"NAMA GURU":"ALI BIN ABU","IC":"900101011234","NO TELEFON GURU":"0123456789","JANTINA":"LELAKI","JAWATAN CADANGAN":"Pengawas Peperiksaan","ALAMAT RUMAH":"NO 1 JLN...","KOD SEKOLAH":kod,"KOD PPD":info.get("kod_ppd","BH")}])), "template_guru.xlsx")
        uploaded = st.file_uploader("Upload Excel Guru", type=["xlsx","xls"])
        if uploaded:
            try:
                df_up = pd.read_excel(uploaded)
                st.write(f"Preview {len(df_up)} baris (60K akan ambil masa):")
                st.dataframe(df_up.head(20), use_container_width=True)
                batch_size = 500 if len(df_up) > 1000 else 1
                if st.button(f"Import {len(df_up)} guru (Batch {batch_size})", type="primary"):
                    bar = st.progress(0)
                    status = st.empty()
                    ok=0
                    # Batch mode for large file
                    if batch_size > 1:
                        for start in range(0, len(df_up), batch_size):
                            end = min(start+batch_size, len(df_up))
                            batch_df = df_up.iloc[start:end]
                            batch=[]
                            for _, row in batch_df.iterrows():
                                try:
                                    d={}
                                    for k,v in row.to_dict().items():
                                        d[k] = "" if pd.isna(v) else str(v)
                                    nama = d.get("NAMA GURU","").upper().strip()
                                    if not nama or nama=="NAN": continue
                                    kod_sek = d.get("KOD SEKOLAH", kod).upper().strip() or kod
                                    kod_ppd_val = d.get("KOD PPD", info.get("kod_ppd","BH")).lower().strip() or info.get("kod_ppd","BH").lower()
                                    batch.append({
                                        "kod_ppd": kod_ppd_val,
                                        "kod_sekolah": kod_sek,
                                        "nama_guru": nama,
                                        "ic_guru": d.get("IC",""),
                                        "data": d
                                    })
                                except: continue
                            if batch:
                                try:
                                    supa.table("guru_master").insert(batch).execute()
                                    ok+=len(batch)
                                except Exception as e:
                                    st.warning(f"Batch {start}-{end} error: {e}")
                            bar.progress(end/len(df_up))
                            status.write(f"Progress: {end}/{len(df_up)} | OK: {ok}")
                    else:
                        for i, row in df_up.iterrows():
                            try:
                                nama=str(row.get("NAMA GURU","")).upper()
                                ic=str(row.get("IC",""))
                                if not nama or nama=="NAN": continue
                                d = {k: ("" if pd.isna(v) else str(v)) for k,v in row.to_dict().items()}
                                d["KOD SEKOLAH"]=kod
                                supa.table("guru_master").insert({"kod_ppd":info.get("kod_ppd","BH").lower(),"kod_sekolah":kod,"nama_guru":nama,"ic_guru":ic,"data":d}).execute()
                                ok+=1
                            except Exception as e:
                                st.warning(f"Baris {i}: {e}")
                            bar.progress((i+1)/len(df_up))
                    st.success(f"✅ Berjaya import {ok}/{len(df_up)} guru!")
                    st.balloons()
            except Exception as e:
                st.error(f"Excel error: {e}")

    elif menu=="🗑️ Buang Guru":
        st.header(f"Buang Guru - {kod}")
        if df_guru.empty:
            st.info("Tiada guru untuk dibuang.")
        else:
            st.dataframe(df_guru[["NAMA GURU","IC","TELEFON"]], use_container_width=True)
            pilih=st.multiselect("Pilih IC untuk buang (boleh pilih banyak)", df_guru["IC"].tolist(), format_func=lambda x: f"{x} - {df_guru[df_guru['IC']==x]['NAMA GURU'].values[0] if not df_guru[df_guru['IC']==x].empty else x}")
            if pilih:
                st.warning(f"Kau nak buang {len(pilih)} guru: {', '.join(pilih)}")
                if st.button(f"🗑️ Confirm Buang {len(pilih)} Guru", type="primary"):
                    for ic in pilih:
                        try:
                            res=supa.table("guru_master").select("id").eq("ic_guru",ic).eq("kod_sekolah",kod).execute()
                            for r in res.data or []:
                                supa.table("guru_master").delete().eq("id",r["id"]).execute()
                        except Exception as e:
                            st.error(f"{ic}: {e}")
                    st.success(f"✅ Berjaya buang {len(pilih)} guru")
                    st.rerun()

    elif menu=="🏫 Pusat Peperiksaan":
        st.header("Senarai Pusat Peperiksaan")
        df_pusat = get_pusat_df()
        if df_pusat.empty:
            st.info("pusat_master kosong")
        else:
            st.dataframe(df_pusat, use_container_width=True)
            # Filter by sekolah punya PPD
            kod_ppd = info.get("kod_ppd","BH")
            st.subheader(f"Pusat di PPD {kod_ppd} - {PPD_MAP.get(kod_ppd,'')}")
            df_f = df_pusat[df_pusat.astype(str).apply(lambda x: x.str.contains(kod_ppd, case=False, na=False)).any(axis=1)] if not df_pusat.empty else df_pusat
            if not df_f.empty:
                st.dataframe(df_f, use_container_width=True)

    elif menu=="📝 Cadangan Lantikan":
        st.header(f"Cadangan Lantikan - {kod}")
        if df_guru.empty:
            st.warning("Tiada guru untuk dicadang. Tambah guru dulu.")
        else:
            df_pusat = get_pusat_df()
            pusat_list = df_pusat["kod_pusat"].tolist() if not df_pusat.empty and "kod_pusat" in df_pusat.columns else ["SPM001","SPM002"]
            with st.form("cadangan"):
                guru_pilih = st.multiselect("Pilih Guru untuk dicadangkan", df_guru["IC"].tolist(), format_func=lambda x: f"{df_guru[df_guru['IC']==x]['NAMA GURU'].values[0]} - {x}")
                pusat_pilih = st.selectbox("Pilih Pusat Peperiksaan", pusat_list)
                jawatan_cadang = st.selectbox("Jawatan Lantikan", ["Pengawas Peperiksaan","Ketua Pengawas","Pengawas Bertugas"])
                catatan = st.text_area("Catatan")
                submit = st.form_submit_button("📝 Simpan Cadangan", type="primary")
                if submit:
                    if not guru_pilih:
                        st.error("Pilih sekurang-kurangnya 1 guru")
                    else:
                        for ic in guru_pilih:
                            guru_row = df_guru[df_guru["IC"]==ic]
                            nama = guru_row["NAMA GURU"].values[0] if not guru_row.empty else ic
                            try:
                                supa.table("cadangan_sup").insert({
                                    "kod_ppd": info.get("kod_ppd","BH"),
                                    "kod_sekolah": kod,
                                    "ic_guru": ic,
                                    "nama_guru": nama,
                                    "kod_pusat": pusat_pilih,
                                    "jawatan_cadangan": jawatan_cadang,
                                    "catatan": catatan,
                                    "status": "DICADANGKAN",
                                    "tarikh_cadang": str(datetime.date.today())
                                }).execute()
                            except Exception as e:
                                st.error(f"Gagal {ic}: {e}")
                        st.success(f"✅ Berjaya cadang {len(guru_pilih)} guru ke pusat {pusat_pilih}")
                        st.balloons()

            st.markdown("---")
            st.subheader("Senarai Cadangan Sekolah Ini")
            df_cad = get_cadangan_df(kod_sekolah=kod)
            if df_cad.empty:
                st.info("Belum ada cadangan")
            else:
                st.dataframe(df_cad, use_container_width=True)
                st.download_button("📥 Export Cadangan", to_excel(df_cad), file_name=f"cadangan_{kod}.xlsx")

    elif menu=="📤 Hantar ke PPD":
        st.header(f"Hantar Cadangan ke PPD {info.get('kod_ppd','BH')}")
        df_cad = get_cadangan_df(kod_sekolah=kod)
        if df_cad.empty:
            st.warning("Belum ada cadangan. Pergi menu Cadangan Lantikan dulu.")
        else:
            st.dataframe(df_cad, use_container_width=True)
            st.info(f"Ada {len(df_cad)} cadangan akan dihantar ke PPD {info.get('kod_ppd','BH')} - {PPD_MAP.get(info.get('kod_ppd','BH'),'')}")
            if st.button("📤 Hantar Semua ke PPD", type="primary", use_container_width=True):
                try:
                    # Update status
                    for _, row in df_cad.iterrows():
                        supa.table("cadangan_sup").update({"status":"HANTAR KE PPD"}).eq("id", row["id"]).execute()
                    st.success(f"✅ Berjaya hantar {len(df_cad)} cadangan ke PPD!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Gagal hantar: {e}")

# ================= PPD =================
elif st.session_state.role=="PPD":
    kod_ppd=st.session_state.kod
    st.sidebar.title(f"🏢 PPD {kod_ppd}")
    st.sidebar.caption(f"{PPD_MAP.get(kod_ppd,'')}")

    menu=st.sidebar.radio("Menu PPD", ["📊 Dashboard PPD","🏫 Sekolah dalam PPD","📋 Cadangan SUP","✅ Kelulusan","📥 Export","🚪 Log Keluar"])

    if menu=="🚪 Log Keluar":
        st.session_state.clear()
        st.rerun()

    if menu=="📊 Dashboard PPD":
        st.header(f"Dashboard PPD {kod_ppd} - {PPD_MAP.get(kod_ppd,'')}")
        try:
            cnt_sekolah = supa.table("sekolah_master").select("kod_sekolah", count="exact").eq("kod_ppd", kod_ppd).execute()
            cnt_guru = supa.table("guru_master").select("id", count="exact").eq("kod_ppd", kod_ppd.lower()).execute()
            cnt_cadang = supa.table("cadangan_sup").select("id", count="exact").eq("kod_ppd", kod_ppd).execute()
            c1,c2,c3 = st.columns(3)
            c1.metric("Sekolah", cnt_sekolah.count)
            c2.metric("Guru", cnt_guru.count)
            c3.metric("Cadangan", cnt_cadang.count)
        except Exception as e:
            st.error(f"Error dashboard: {e}")

    elif menu=="🏫 Sekolah dalam PPD":
        st.header(f"Senarai Sekolah PPD {kod_ppd}")
        try:
            res=supa.table("sekolah_master").select("*").eq("kod_ppd", kod_ppd).limit(2000).execute()
            df=pd.DataFrame(res.data or [])
            st.dataframe(df, use_container_width=True)
            st.download_button("Export Sekolah", to_excel(df), file_name=f"sekolah_{kod_ppd}.xlsx")
        except Exception as e:
            st.error(str(e))

    elif menu=="📋 Cadangan SUP":
        st.header(f"Cadangan dari SUP - PPD {kod_ppd}")
        df_cad = get_cadangan_df(kod_ppd=kod_ppd)
        if df_cad.empty:
            st.info("Belum ada cadangan dari SUP")
        else:
            st.dataframe(df_cad, use_container_width=True)
            st.download_button("Export Cadangan", to_excel(df_cad), file_name=f"cadangan_PPD_{kod_ppd}.xlsx")

    elif menu=="✅ Kelulusan":
        st.header(f"Kelulusan PPD {kod_ppd}")
        df_cad = get_cadangan_df(kod_ppd=kod_ppd)
        if df_cad.empty:
            st.info("Tiada cadangan")
        else:
            st.dataframe(df_cad, use_container_width=True)
            pilih_id = st.multiselect("Pilih ID untuk lulus", df_cad["id"].tolist() if "id" in df_cad.columns else [])
            col1,col2 = st.columns(2)
            with col1:
                if st.button("✅ Lulus Terpilih", type="primary"):
                    for i in pilih_id:
                        try:
                            supa.table("cadangan_sup").update({"status":"LULUS PPD"}).eq("id",i).execute()
                        except Exception as e:
                            st.error(str(e))
                    st.success("Lulus berjaya")
                    st.rerun()
            with col2:
                if st.button("❌ Tolak Terpilih"):
                    for i in pilih_id:
                        try:
                            supa.table("cadangan_sup").update({"status":"TOLAK PPD"}).eq("id",i).execute()
                        except Exception as e:
                            st.error(str(e))
                    st.success("Tolak berjaya")
                    st.rerun()

    elif menu=="📥 Export":
        st.header(f"Export Data PPD {kod_ppd}")
        df_cad = get_cadangan_df(kod_ppd=kod_ppd)
        if not df_cad.empty:
            st.download_button("📥 Export Cadangan PPD (Excel)", to_excel(df_cad), file_name=f"laporan_PPD_{kod_ppd}_{datetime.date.today()}.xlsx", use_container_width=True)
        try:
            res=supa.table("guru_master").select("*").eq("kod_ppd", kod_ppd.lower()).limit(5000).execute()
            df_guru=pd.DataFrame(res.data or [])
            if not df_guru.empty:
                st.download_button("📥 Export Guru PPD (Excel)", to_excel(df_guru), file_name=f"guru_PPD_{kod_ppd}.xlsx", use_container_width=True)
        except Exception as e:
            st.error(str(e))

# ================= JPN =================
elif st.session_state.role=="JPN":
    st.sidebar.title("🏛️ JPN Selangor")
    menu=st.sidebar.radio("Menu JPN", ["📊 Dashboard JPN","🏫 Semua Sekolah","🏫 Pusat Master","👨‍🏫 Guru Master","📋 Semua Cadangan","📥 Export Negeri","⚙️ Admin","🚪 Log Keluar"])

    if menu=="🚪 Log Keluar":
        st.session_state.clear()
        st.rerun()

    if menu=="📊 Dashboard JPN":
        st.header("Dashboard JPN Selangor - Pelantikan SPM 2026")
        cols = st.columns(5)
        for idx, t in enumerate(["sekolah_master","pusat_master","guru_master","cadangan_sup"]):
            try:
                res=supa.table(t).select("*", count="exact").limit(1).execute()
                cols[idx].metric(t, res.count)
            except Exception as e:
                cols[idx].error(f"{t}: {e}")
        # PPD breakdown
        st.markdown("---")
        st.subheader("Breakdown Ikut PPD")
        rows=[]
        for ppd in KOD_DAERAH:
            try:
                c1=supa.table("sekolah_master").select("kod_sekolah", count="exact").eq("kod_ppd", ppd).execute()
                c2=supa.table("guru_master").select("id", count="exact").eq("kod_ppd", ppd.lower()).execute()
                c3=supa.table("cadangan_sup").select("id", count="exact").eq("kod_ppd", ppd).execute()
                rows.append({"PPD":f"{ppd} - {PPD_MAP[ppd]}","Sekolah":c1.count,"Guru":c2.count,"Cadangan":c3.count})
            except:
                rows.append({"PPD":ppd,"Sekolah":0,"Guru":0,"Cadangan":0})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    elif menu=="🏫 Semua Sekolah":
        st.header("Semua Sekolah Master (369 Sekolah)")
        try:
            res=supa.table("sekolah_master").select("*", count="exact").limit(5000).execute()
            df_count = res.count
            res2=supa.table("sekolah_master").select("*").limit(1000).execute()
            df=pd.DataFrame(res2.data or [])
            st.write(f"Total dalam Supabase: **{df_count}** sekolah")
            if not df.empty:
                st.dataframe(df, use_container_width=True)
                st.download_button("📥 Export Sekolah Master", to_excel(df), file_name="sekolah_master.xlsx")
            else:
                st.warning("sekolah_master kosong - belum push dari pusat_2026.csv. Sila import di bawah.")
        except Exception as e:
            st.error(f"sekolah_master error: {e}")
            st.code("""
CREATE TABLE IF NOT EXISTS sekolah_master (
  id BIGSERIAL PRIMARY KEY,
  kod_sekolah TEXT UNIQUE,
  nama_sekolah TEXT,
  kod_ppd TEXT,
  data JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE sekolah_master ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "allow all" ON sekolah_master;
CREATE POLICY "allow all" ON sekolah_master FOR ALL USING (true) WITH CHECK (true);
            """, language="sql")

        st.markdown("---")
        st.subheader("📤 Import Sekolah Master dari Pusat & Guru")
        st.info("File sekolah digenerate dari pusat_2026.csv (506 pusat = 369 sekolah unik) + guru 60K. Upload SEKOLAH_MASTER_FINAL_2026.xlsx untuk push masuk sekolah_master.")
        st.download_button("📥 Download SEKOLAH_MASTER_FINAL_2026.xlsx (369 sekolah)", open("/mnt/data/SEKOLAH_MASTER_FINAL_2026.xlsx","rb").read() if __import__("os").path.exists("/mnt/data/SEKOLAH_MASTER_FINAL_2026.xlsx") else b"", "SEKOLAH_MASTER_FINAL_2026.xlsx")
        
        up_sek = st.file_uploader("Upload Sekolah Master Excel (KOD SEKOLAH, NAMA SEKOLAH, KOD PPD)", type=["xlsx","csv"], key="sekolah_up")
        if up_sek:
            try:
                if up_sek.name.endswith(".csv"):
                    try:
                        df_up=pd.read_csv(up_sek)
                    except:
                        up_sek.seek(0)
                        df_up=pd.read_csv(up_sek, encoding='latin1')
                else:
                    df_up=pd.read_excel(up_sek)
                st.write(f"Preview {len(df_up)} sekolah:")
                st.dataframe(df_up.head(30), use_container_width=True)
                if st.button(f"🚀 Import {len(df_up)} Sekolah ke Supabase", type="primary", use_container_width=True):
                    bar=st.progress(0)
                    stat=st.empty()
                    ok=0
                    # Delete old first
                    try:
                        supa.table("sekolah_master").delete().gt("id",0).execute()
                        st.write("Old sekolah_master cleared")
                    except: pass
                    BATCH=200
                    for start in range(0, len(df_up), BATCH):
                        end=min(start+BATCH, len(df_up))
                        bdf=df_up.iloc[start:end]
                        batch=[]
                        for _, row in bdf.iterrows():
                            try:
                                kod = str(row.get("KOD SEKOLAH","") or row.get("kod_sekolah","") or row.get("KOD_SEKOLAH","")).strip().upper()
                                if not kod: continue
                                nama = str(row.get("NAMA SEKOLAH","") or row.get("nama_sekolah","") or row.get("NAMA_PUSAT","")).strip().upper()
                                kod_ppd = str(row.get("KOD PPD","") or row.get("kod_ppd","") or row.get("PPD_CODE","") or "BH").strip().upper()
                                batch.append({
                                    "kod_sekolah": kod,
                                    "nama_sekolah": nama,
                                    "kod_ppd": kod_ppd,
                                    "data": {k: ("" if pd.isna(v) else str(v)) for k,v in row.to_dict().items()}
                                })
                            except: continue
                        if batch:
                            try:
                                supa.table("sekolah_master").insert(batch).execute()
                                ok+=len(batch)
                            except Exception as e:
                                st.warning(f"Batch {start}-{end}: {e}")
                        bar.progress(end/len(df_up))
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
                res=supa.table("pusat_master").select("*").limit(1000).execute()
                df_p = pd.DataFrame(res.data or [])
                if df_p.empty:
                    st.error("pusat_master kosong, import pusat dulu")
                else:
                    # Extract unique kod_sekolah from pusat data
                    sekolah_list=[]
                    seen=set()
                    for _, r in df_p.iterrows():
                        d = r.get("data") or {}
                        kod_sek = d.get("KOD_SEKOLAH","") or r.get("kod_sekolah","") or ""
                        kod_sek = str(kod_sek).upper().strip()
                        if not kod_sek or kod_sek in seen: continue
                        seen.add(kod_sek)
                        sekolah_list.append({
                            "kod_sekolah": kod_sek,
                            "nama_sekolah": r.get("nama_pusat","") or d.get("NAMA_PUSAT",""),
                            "kod_ppd": r.get("kod_ppd","BH"),
                            "data": {"KOD SEKOLAH": kod_sek, "NAMA SEKOLAH": r.get("nama_pusat",""), "KOD PPD": r.get("kod_ppd","BH")}
                        })
                    # Insert
                    if sekolah_list:
                        try:
                            supa.table("sekolah_master").delete().gt("id",0).execute()
                        except: pass
                        for i in range(0, len(sekolah_list), 200):
                            supa.table("sekolah_master").insert(sekolah_list[i:i+200]).execute()
                        st.success(f"✅ Generated {len(sekolah_list)} sekolah dari pusat_master!")
                        st.rerun()
            except Exception as e:
                st.error(f"Error generate: {e}")

    elif menu=="🏫 Pusat Master":
        st.header("Pusat Master - Selangor 2026 (506 Pusat)")
        try:
            # Use safe_count + fetch
            total = safe_count("pusat_master")
            res = supa.table("pusat_master").select("*").limit(1000).execute()
            df = pd.DataFrame(res.data or [])
            st.write(f"Total Pusat Sedia Ada: **{total}** / 506 pusat (Supabase ada 506, App baca {len(df)})")
            if total==0 and len(df)==0:
                st.warning("pusat_master nampak kosong di app tapi ada 506 di Supabase - RLS policy block! Run SQL di bawah di Supabase SQL Editor")
                st.code("""
-- Fix RLS untuk pusat_master - Run ini di Supabase SQL Editor:
ALTER TABLE pusat_master ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "allow all" ON pusat_master;
CREATE POLICY "allow all" ON pusat_master FOR ALL USING (true) WITH CHECK (true);

-- Sama untuk sekolah_master:
ALTER TABLE sekolah_master ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "allow all" ON sekolah_master;
CREATE POLICY "allow all" ON sekolah_master FOR ALL USING (true) WITH CHECK (true);

-- Dan guru_master:
ALTER TABLE guru_master ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "allow all" ON guru_master;
CREATE POLICY "allow all" ON guru_master FOR ALL USING (true) WITH CHECK (true);
                """, language="sql")
            if not df.empty:
                # Show normalized
                st.dataframe(df.head(200), use_container_width=True)
                st.download_button("📥 Export Pusat Master", to_excel(df), file_name="pusat_master.xlsx")
            else:
                st.warning("pusat_master kosong - sila import pusat_2026.csv (506 pusat) ATAU fix RLS dulu")
        except Exception as e:
            st.error(f"pusat_master error: {e}")
            st.code("""
CREATE TABLE IF NOT EXISTS pusat_master (
  id BIGSERIAL PRIMARY KEY,
  kod_pusat TEXT,
  nama_pusat TEXT,
  kod_ppd TEXT,
  ppd TEXT,
  alamat TEXT,
  bilik INT,
  calon INT,
  data JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE pusat_master ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "allow all" ON pusat_master;
CREATE POLICY "allow all" ON pusat_master FOR ALL USING (true) WITH CHECK (true);
            """, language="sql")

        st.markdown("---")
        col1,col2 = st.columns(2)
        with col1:
            st.subheader("➕ Tambah Pusat Manual")
            with st.form("tambah_pusat"):
                kod_pusat=st.text_input("KOD PUSAT * (cth: BA001)")
                nama_pusat=st.text_input("NAMA PUSAT *")
                kod_ppd_pusat=st.selectbox("KOD PPD", KOD_DAERAH, format_func=lambda x: f"{x}-{PPD_MAP[x]}")
                alamat_pusat=st.text_area("ALAMAT PUSAT")
                bilik=st.number_input("BIL BILIK", min_value=1, value=10)
                calon=st.number_input("BIL CALON", min_value=1, value=200)
                submit_pusat=st.form_submit_button("💾 Simpan Pusat", type="primary", use_container_width=True)
                if submit_pusat:
                    if not kod_pusat or not nama_pusat:
                        st.error("Kod & Nama Pusat wajib!")
                    else:
                        try:
                            supa.table("pusat_master").insert({
                                "kod_pusat": kod_pusat.upper(),
                                "nama_pusat": nama_pusat.upper(),
                                "kod_ppd": kod_ppd_pusat,
                                "ppd": PPD_MAP.get(kod_ppd_pusat,""),
                                "alamat": alamat_pusat,
                                "bilik": bilik,
                                "calon": calon,
                                "data": {"KOD PUSAT":kod_pusat.upper(),"NAMA PUSAT":nama_pusat.upper(),"KOD PPD":kod_ppd_pusat,"ALAMAT":alamat_pusat,"BILIK":bilik,"CALON":calon}
                            }).execute()
                            st.success(f"✅ Pusat {kod_pusat} berjaya tambah!")
                            st.balloons()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Gagal: {e}")

        with col2:
            st.subheader("📤 Import Excel/CSV Pusat (Batch)")
            st.info("Support: pusat_2026.csv (NO_PUSAT format) & Excel KOD PUSAT format | 506 pusat")
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                st.download_button("📥 Template Pusat", to_excel(pd.DataFrame([{"KOD PUSAT":"BA001","NAMA PUSAT":"SMK DATO HAMZAH","KOD PPD":"BA","ALAMAT PUSAT":"Jalan Dato Hamzah","BILIK":10,"CALON":250}])), "TEMPLATE_PUSAT.xlsx")
            with col_t2:
                st.download_button("📥 Sample pusat_2026.csv", open("/mnt/data/pusat_2026.csv","rb").read() if __import__("os").path.exists("/mnt/data/pusat_2026.csv") else b"", "pusat_2026_sample.csv")
            
            up=st.file_uploader("Upload Excel/CSV Pusat (Excel atau CSV)", type=["xlsx","csv"], key="pusat_up")
            if up:
                try:
                    if up.name.endswith(".csv"):
                        try:
                            df_up=pd.read_csv(up)
                        except:
                            up.seek(0)
                            df_up=pd.read_csv(up, encoding='latin1')
                    else:
                        df_up=pd.read_excel(up)
                    st.write(f"Preview {len(df_up)} pusat:")
                    st.dataframe(df_up.head(20), use_container_width=True)
                    if st.button(f"🚀 Import {len(df_up)} Pusat (Batch 200)", type="primary", use_container_width=True):
                        bar=st.progress(0)
                        stat=st.empty()
                        ok=0
                        BATCH=200
                        # PPD name to code map for CSV
                        ppd_name_map = {"klang":"BA","kuala langat":"BB","kuala selangor":"BC","hulu langat":"BD","hulu selangor":"BE","sabak bernam":"BF","gombak":"BG","petaling perdana":"BH","sepang":"BJ","petaling utama":"BK"}
                        for start in range(0, len(df_up), BATCH):
                            end=min(start+BATCH, len(df_up))
                            bdf=df_up.iloc[start:end]
                            batch=[]
                            for _, row in bdf.iterrows():
                                try:
                                    d={}
                                    for k,v in row.to_dict().items():
                                        d[k] = "" if pd.isna(v) else str(v)
                                    # Support both formats: NO_PUSAT or KOD PUSAT
                                    kod_p = d.get("NO_PUSAT","") or d.get("KOD PUSAT","") or d.get("kod_pusat","")
                                    kod_p = kod_p.upper().strip()
                                    if not kod_p: continue
                                    # KOD PPD logic
                                    kod_ppd_val = d.get("KOD PPD","") or d.get("KOD_PPD","") or d.get("PPD_CODE","")
                                    if not kod_ppd_val:
                                        ppd_raw = d.get("PPD","").lower()
                                        for name,code in ppd_name_map.items():
                                            if name in ppd_raw:
                                                kod_ppd_val=code
                                                break
                                        if not kod_ppd_val:
                                            kod_ppd_val="BH"
                                    kod_ppd_val = kod_ppd_val.upper().strip()
                                    nama_p = d.get("NAMA_PUSAT","") or d.get("NAMA PUSAT","") or kod_p
                                    bilik_val = d.get("JUMLAH_KELAS","") or d.get("BILIK","") or "10"
                                    calon_val = d.get("JUMLAH_CALON","") or d.get("CALON","") or "200"
                                    try: bilik_int = int(float(bilik_val))
                                    except: bilik_int = 10
                                    try: calon_int = int(float(calon_val))
                                    except: calon_int = 200
                                    batch.append({
                                        "kod_pusat": kod_p,
                                        "nama_pusat": nama_p.upper(),
                                        "kod_ppd": kod_ppd_val,
                                        "ppd": d.get("PPD","") or PPD_MAP.get(kod_ppd_val,""),
                                        "alamat": d.get("KOD_SEKOLAH","") or d.get("ALAMAT PUSAT","") or d.get("ALAMAT",""),
                                        "bilik": bilik_int,
                                        "calon": calon_int,
                                        "data": d
                                    })
                                except: continue
                            if batch:
                                try:
                                    supa.table("pusat_master").insert(batch).execute()
                                    ok+=len(batch)
                                except Exception as e:
                                    st.warning(f"Batch {start}-{end}: {e}")
                            bar.progress(end/len(df_up))
                            stat.write(f"Progress {end}/{len(df_up)} | OK {ok}")
                        st.success(f"✅ Selesai import {ok}/{len(df_up)} pusat! Total 506")
                        st.balloons()
                        st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        st.markdown("---")
        if st.button("🗑️ Kosongkan Semua Pusat (Hati-hati!)", type="secondary"):
            try:
                # Supabase need delete with filter, we delete all with gt 0
                supa.table("pusat_master").delete().gt("id",0).execute()
                st.success("Semua pusat dipadam")
                st.rerun()
            except Exception as e:
                st.error(str(e))

    elif menu=="👨‍🏫 Guru Master":
        st.header("Guru Master Seluruh Negeri")
        st.subheader("📤 Import MASTER 60K Guru Selangor")
        st.info("Upload file MASTER-GURU-SELANGOR-2026.xlsx (60K) di sini untuk restore balik data yang hilang. Guna batch 500 untuk laju.")
        up_master = st.file_uploader("Upload MASTER 60K Excel", type=["xlsx"], key="master60k")
        if up_master:
            try:
                df_m = pd.read_excel(up_master, sheet_name=0)
                st.write(f"File ada {len(df_m)} baris. Column: {list(df_m.columns)}")
                st.dataframe(df_m.head(10), use_container_width=True)
                if st.button(f"🚀 Import {len(df_m)} Guru ke Supabase (Batch 500)", type="primary", use_container_width=True):
                    bar = st.progress(0)
                    stat = st.empty()
                    ok=0
                    BATCH=500
                    for start in range(0, len(df_m), BATCH):
                        end = min(start+BATCH, len(df_m))
                        bdf = df_m.iloc[start:end]
                        batch=[]
                        for _, row in bdf.iterrows():
                            try:
                                d={}
                                for k,v in row.to_dict().items():
                                    d[k] = "" if pd.isna(v) else str(v)
                                nama = d.get("NAMA GURU","").upper().strip()
                                if not nama or nama=="NAN": continue
                                batch.append({
                                    "kod_ppd": d.get("KOD PPD","").lower().strip(),
                                    "kod_sekolah": d.get("KOD SEKOLAH","").upper().strip(),
                                    "nama_guru": nama,
                                    "ic_guru": d.get("IC",""),
                                    "data": d
                                })
                            except: continue
                        if batch:
                            try:
                                supa.table("guru_master").insert(batch).execute()
                                ok+=len(batch)
                            except Exception as e:
                                st.error(f"Batch {start}-{end} error: {e}")
                        bar.progress(end/len(df_m))
                        stat.write(f"Imported {end}/{len(df_m)} | OK {ok}")
                    st.success(f"✅ Selesai import {ok}/{len(df_m)} guru!")
                    st.balloons()
            except Exception as e:
                st.error(f"Error: {e}")

        st.markdown("---")
        st.subheader("Data Sedia Ada")
        try:
            res=supa.table("guru_master").select("*", count="exact").limit(5000).execute()
            df=pd.DataFrame(res.data or [])
            st.write(f"Total dalam Supabase: {res.count} records")
            if not df.empty:
                st.dataframe(df.head(100), use_container_width=True)
                st.download_button("Export Guru Master (5000)", to_excel(df), file_name="guru_master_full.xlsx")
        except Exception as e:
            st.error(str(e))

    elif menu=="📋 Semua Cadangan":
        st.header("Semua Cadangan Seluruh Negeri")
        try:
            res=supa.table("cadangan_sup").select("*").limit(10000).execute()
            df=pd.DataFrame(res.data or [])
            st.dataframe(df, use_container_width=True)
            if not df.empty:
                st.download_button("Export Semua Cadangan", to_excel(df), file_name=f"cadangan_negeri_{datetime.date.today()}.xlsx")
        except Exception as e:
            st.error(str(e))

    elif menu=="📥 Export Negeri":
        st.header("Export Laporan Negeri")
        try:
            res=supa.table("cadangan_sup").select("*").limit(10000).execute()
            df=pd.DataFrame(res.data or [])
            if not df.empty:
                st.download_button("📥 Laporan Penuh Negeri (Excel)", to_excel(df), file_name=f"Laporan_JPN_Selangor_{datetime.date.today()}.xlsx", use_container_width=True, type="primary")
        except Exception as e:
            st.error(str(e))

    elif menu=="⚙️ Admin":
        st.header("Admin - Check Tables & Connection")
        st.code(f"URL: {SUPABASE_URL}\nKEY: {SUPABASE_KEY[:20]}...{SUPABASE_KEY[-10:]} (Active)")
        for t in ["sekolah_master","pusat_master","guru_master","cadangan_sup"]:
            try:
                res=supa.table(t).select("*", count="exact").limit(1).execute()
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
