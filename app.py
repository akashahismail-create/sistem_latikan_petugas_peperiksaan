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

# ================= HELPERS =================
def get_sekolah(kod):
    try:
        res = supa.table("sekolah_master").select("*").eq("kod_sekolah", kod.upper()).limit(1).execute()
        if res.data:
            return res.data[0]
    except Exception as e:
        st.error(f"sekolah_master error: {e}")
    return {"kod_sekolah": kod, "nama_sekolah": f"SEKOLAH {kod}", "kod_ppd": "BH", "ppd": "Petaling Perdana"}

def get_guru_df(kod_sekolah):
    try:
        res = supa.table("guru_master").select("*").eq("kod_sekolah", kod_sekolah.upper()).limit(2000).execute()
        rows=[]
        for r in res.data or []:
            d = r.get("data") or {}
            rows.append({
                "id": r.get("id"),
                "NAMA GURU": r.get("nama_guru") or d.get("NAMA GURU",""),
                "IC": r.get("ic_guru") or d.get("IC",""),
                "JANTINA": d.get("JANTINA",""),
                "TELEFON": d.get("NO TELEFON GURU","") or d.get("TELEFON",""),
                "JAWATAN CADANGAN": d.get("JAWATAN CADANGAN",""),
                "ALAMAT": d.get("ALAMAT RUMAH",""),
                "KOD SEKOLAH": r.get("kod_sekolah"),
                "data_full": d
            })
        return pd.DataFrame(rows)
    except Exception as e:
        st.error(f"guru_master error: {e}")
        return pd.DataFrame()

def get_pusat_df():
    try:
        res = supa.table("pusat_master").select("*").limit(2000).execute()
        return pd.DataFrame(res.data or [])
    except Exception as e:
        st.error(f"pusat_master error: {e}")
        return pd.DataFrame()

def get_cadangan_df(kod_ppd=None, kod_sekolah=None):
    try:
        q = supa.table("cadangan_sup").select("*")
        if kod_ppd:
            q = q.eq("kod_ppd", kod_ppd)
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
        st.header("Semua Sekolah Master")
        try:
            res=supa.table("sekolah_master").select("*").limit(5000).execute()
            df=pd.DataFrame(res.data or [])
            st.dataframe(df, use_container_width=True)
            st.download_button("Export Sekolah", to_excel(df), file_name="sekolah_master.xlsx")
        except Exception as e:
            st.error(str(e))

    elif menu=="🏫 Pusat Master":
        st.header("Pusat Master")
        try:
            res=supa.table("pusat_master").select("*").limit(5000).execute()
            df=pd.DataFrame(res.data or [])
            st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(str(e))
        st.markdown("---")
        st.subheader("Upload Pusat Master Baru")
        up=st.file_uploader("Upload Excel Pusat", type=["xlsx"])
        if up:
            df_up=pd.read_excel(up)
            st.dataframe(df_up.head(), use_container_width=True)
            if st.button("Import Pusat"):
                for _, row in df_up.iterrows():
                    try:
                        supa.table("pusat_master").insert(row.to_dict()).execute()
                    except Exception as e:
                        st.warning(str(e))
                st.success("Import selesai")

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
