"""
PELANTIKAN PETUGAS PEPERIKSAAN SELANGOR 2026 - CLEAN REBUILD
- Semua data dalam Supabase, tiada folder data/ dalam GitHub
- Login simple untuk test
- Supabase: https://gnmaijhugkkvxejvsotk.supabase.co
"""

import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Pelantikan SPM Selangor 2026", layout="wide", page_icon="📚")

# Supabase
try:
    from supabase import create_client
except:
    create_client = None

SUPABASE_URL = "https://gnmaijhugkkvxejvsotk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdubWFpamhhZ2dra3Z4ZWp2c290ayIsInJvbGUiOiJhbm9uIiwiaWF0IjoxNzQ3MTk5MDY2LCJleHAiOjIwNjI3NzUwNjZ9.1YWg71nCwnQzP-KUzTdHR4rZAVCAesbKVqvVC1-X6lw"

try:
    if "SUPABASE_URL" in st.secrets:
        SUPABASE_URL = st.secrets["SUPABASE_URL"]
    if "SUPABASE_ANON_KEY" in st.secrets:
        SUPABASE_KEY = st.secrets["SUPABASE_ANON_KEY"]
    if "SUPABASE_KEY" in st.secrets:
        SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except:
    pass

@st.cache_resource
def get_supabase():
    if create_client is None:
        return None
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supa = get_supabase()
if supa is None:
    st.error("Supabase client tidak ada - pip install supabase")
    st.stop()

KOD_DAERAH = ["BA","BB","BC","BD","BE","BF","BG","BH","BJ","BK"]
PPD_MAP = {"BA":"Klang","BB":"Kuala Langat","BC":"Kuala Selangor","BD":"Hulu Langat","BE":"Hulu Selangor","BF":"Sabak Bernam","BG":"Gombak","BH":"Petaling Perdana","BJ":"Sepang","BK":"Petaling Utama"}

def norm_ic(x):
    d = re.sub(r"\D","",str(x))
    return d.zfill(12) if d else ""

def get_sekolah(kod_sekolah):
    res = supa.table("sekolah_master").select("*").eq("kod_sekolah", kod_sekolah.strip().upper()).limit(1).execute()
    return res.data[0] if res.data else None

def get_guru_by_sekolah(kod_sekolah):
    res = supa.table("guru_master").select("*").eq("kod_sekolah", kod_sekolah.strip().upper()).limit(60000).execute()
    rows=[]
    for r in res.data or []:
        d = r.get("data") or {}
        rows.append({
            "id": r.get("id"),
            "KOD SEKOLAH": r.get("kod_sekolah") or d.get("KOD SEKOLAH") or d.get("KOD SEKOLAH ASAL"),
            "NAMA GURU": r.get("nama_guru") or d.get("NAMA GURU") or "",
            "IC": r.get("ic_guru") or d.get("IC") or "",
            "JANTINA": d.get("JANTINA") or "",
            "NO TELEFON": d.get("NO TELEFON GURU") or d.get("NO TELEFON") or "",
            "EMAIL": d.get("EMAIL GURU") or "",
            "ALAMAT": d.get("ALAMAT RUMAH") or "",
            "POSKOD": d.get("POSKOD RUMAH") or "",
            "JAWATAN CADANGAN": d.get("JAWATAN CADANGAN") or "Pengawas Peperiksaan",
            "PENGALAMAN": d.get("PENGALAMAN SPM") or "0",
            "DATA": d
        })
    return pd.DataFrame(rows)

def get_cadangan_by_sekolah(kod_sekolah):
    res = supa.table("cadangan_sup").select("*").eq("kod_sekolah_asal", kod_sekolah.strip().upper()).limit(60000).execute()
    return pd.DataFrame(res.data or [])

# ========== LOGIN SIMPLE ==========
if "role" not in st.session_state:
    st.session_state.role = None

if st.session_state.role is None:
    st.markdown("<h1 style='text-align:center'>📚 Pelantikan SPM Selangor 2026</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center'>Login Simple - Test Mode (Semua data dari Supabase)</p>", unsafe_allow_html=True)
    st.markdown("---")
    col1,col2,col3 = st.columns(3)
    with col1:
        st.subheader("🏫 SUP Sekolah")
        kod_s = st.text_input("KOD SEKOLAH", placeholder="Contoh: BFT8002").upper()
        if st.button("Masuk sebagai SUP", use_container_width=True):
            if not kod_s:
                st.warning("Masukkan kod sekolah")
            else:
                sek = get_sekolah(kod_s)
                if sek or True: # benarkan walau tiada dalam sekolah_master untuk test
                    st.session_state.role = "SUP"
                    st.session_state.kod_sekolah = kod_s
                    st.session_state.sekolah_info = sek
                    st.rerun()
                else:
                    st.error(f"Kod {kod_s} tak jumpa dalam sekolah_master")
    with col2:
        st.subheader("🏢 PPD")
        kod_ppd = st.selectbox("Pilih PPD", KOD_DAERAH, format_func=lambda x: f"{x} - {PPD_MAP.get(x,x)}")
        if st.button("Masuk sebagai PPD", use_container_width=True):
            st.session_state.role = "PPD"
            st.session_state.kod_ppd = kod_ppd
            st.rerun()
    with col3:
        st.subheader("🏛️ JPN")
        pwd = st.text_input("Password JPN", type="password", placeholder="jpn2026")
        if st.button("Masuk sebagai JPN", use_container_width=True):
            if pwd == "jpn2026" or pwd == "":
                st.session_state.role = "JPN"
                st.rerun()
            else:
                st.error("Password salah")
    st.stop()

# ========== SUP ==========
if st.session_state.role == "SUP":
    kod_s = st.session_state.kod_sekolah
    info = st.session_state.sekolah_info
    nama_s = info.get("nama_sekolah","") if info else ""
    kod_ppd_s = info.get("kod_ppd","BH") if info else "BH"
    
    st.sidebar.title(f"SUP {kod_s}")
    if nama_s:
        st.sidebar.caption(nama_s)
    menu = st.sidebar.radio("Menu", ["Senarai Guru","Tambah Guru","Buang Guru","Cadangan & Hantar","Log Keluar"])
    
    if menu == "Log Keluar":
        st.session_state.clear()
        st.rerun()
    
    if menu == "Senarai Guru":
        st.header(f"Senarai Guru - {kod_s} {nama_s}")
        st.caption(f"Data dari Supabase guru_master WHERE kod_sekolah = {kod_s}")
        df_guru = get_guru_by_sekolah(kod_s)
        if df_guru.empty:
            st.info("Belum ada guru untuk sekolah ini. Pergi Tambah Guru.")
        else:
            st.metric("Jumlah Guru", len(df_guru))
            st.dataframe(df_guru[["NAMA GURU","IC","JANTINA","NO TELEFON","JAWATAN CADANGAN","POSKOD"]], use_container_width=True, hide_index=True)
    
    elif menu == "Tambah Guru":
        st.header(f"Tambah Guru Baru - {kod_s}")
        st.caption("Terus INSERT ke guru_master")
        with st.form("tambah_guru"):
            c1,c2 = st.columns(2)
            with c1:
                nama = st.text_input("NAMA GURU *")
                ic = st.text_input("IC *", placeholder="901231-10-1234")
                jantina = st.selectbox("JANTINA", ["L","P"])
                telefon = st.text_input("NO TELEFON *")
            with c2:
                email = st.text_input("EMAIL")
                alamat = st.text_area("ALAMAT RUMAH *")
                poskod = st.text_input("POSKOD *", value="46000")
                jawatan = st.selectbox("JAWATAN CADANGAN", ["Ketua Pengawas","Timbalan Ketua Pengawas","Pengawas Peperiksaan"])
            submit = st.form_submit_button("💾 Simpan ke Supabase", use_container_width=True)
            if submit:
                if not nama or not ic or not alamat:
                    st.error("Nama, IC, Alamat wajib isi")
                else:
                    data = {
                        "KOD SEKOLAH": kod_s,
                        "NAMA SEKOLAH": nama_s,
                        "KOD PPD": kod_ppd_s,
                        "NAMA GURU": nama.upper(),
                        "IC": ic,
                        "JANTINA": jantina,
                        "NO TELEFON GURU": telefon,
                        "EMAIL GURU": email,
                        "ALAMAT RUMAH": alamat,
                        "POSKOD RUMAH": poskod,
                        "JAWATAN CADANGAN": jawatan,
                        "PENGALAMAN SPM": "0"
                    }
                    # Check exist
                    res_exist = supa.table("guru_master").select("id").eq("ic_guru", ic).limit(1).execute()
                    if res_exist.data:
                        supa.table("guru_master").update({"nama_guru": nama.upper(), "ic_guru": ic, "kod_sekolah": kod_s, "kod_ppd": kod_ppd_s.lower(), "data": data}).eq("id", res_exist.data[0]["id"]).execute()
                        st.success(f"✅ Guru {nama} dikemaskini dalam guru_master")
                    else:
                        supa.table("guru_master").insert({"kod_ppd": kod_ppd_s.lower(), "kod_sekolah": kod_s, "nama_guru": nama.upper(), "ic_guru": ic, "data": data}).execute()
                        st.success(f"✅ Guru {nama} ditambah ke guru_master")
                        st.balloons()
    
    elif menu == "Buang Guru":
        st.header(f"Buang Guru - {kod_s}")
        df_guru = get_guru_by_sekolah(kod_s)
        if df_guru.empty:
            st.info("Tiada guru")
        else:
            label = {row["IC"]: f"{row['NAMA GURU']} | {row['IC']}" for _, row in df_guru.iterrows()}
            pilih = st.multiselect("Pilih guru untuk dibuang", list(label.keys()), format_func=lambda x: label.get(x,x))
            sah = st.checkbox("Ya, saya nak buang terus dari Supabase")
            if st.button(f"🗑️ Buang {len(pilih)} guru", disabled=not (pilih and sah), use_container_width=True):
                for ic in pilih:
                    # Cari id
                    res = supa.table("guru_master").select("id").eq("kod_sekolah", kod_s).eq("ic_guru", ic).execute()
                    if not res.data:
                        res = supa.table("guru_master").select("id").eq("ic_guru", ic).execute()
                    for r in res.data or []:
                        supa.table("guru_master").delete().eq("id", r["id"]).execute()
                st.success(f"✅ {len(pilih)} guru dibuang dari guru_master")
                st.rerun()
    
    elif menu == "Cadangan & Hantar":
        st.header(f"Cadangan Petugas - {kod_s}")
        df_guru = get_guru_by_sekolah(kod_s)
        if df_guru.empty:
            st.info("Tiada guru - tambah dulu")
        else:
            df_guru["PILIH"] = False
            edited = st.data_editor(df_guru[["PILIH","NAMA GURU","IC","JAWATAN CADANGAN"]], use_container_width=True, hide_index=True, num_rows="dynamic")
            ticked = edited[edited["PILIH"]==True]
            if st.button(f"📤 Hantar {len(ticked)} cadangan ke PPD", type="primary", use_container_width=True, disabled=len(ticked)==0):
                # Padam lama
                supa.table("cadangan_sup").delete().eq("kod_sekolah_asal", kod_s).execute()
                # Insert baru
                batch=[]
                for _, r in ticked.iterrows():
                    batch.append({
                        "kod_ppd": kod_ppd_s,
                        "kod_sekolah_asal": kod_s,
                        "nama_sekolah_asal": nama_s,
                        "nama_guru": r["NAMA GURU"],
                        "ic": r["IC"],
                        "jantina": df_guru[df_guru["IC"]==r["IC"]]["JANTINA"].values[0] if not df_guru[df_guru["IC"]==r["IC"]].empty else "",
                        "jawatan_cadangan": r["JAWATAN CADANGAN"],
                        "status": "Dicadang"
                    })
                if batch:
                    supa.table("cadangan_sup").insert(batch).execute()
                st.success(f"✅ {len(batch)} guru dihantar ke PPD {kod_ppd_s}")

# ========== PPD ==========
elif st.session_state.role == "PPD":
    kod_ppd = st.session_state.kod_ppd
    st.sidebar.title(f"PPD {kod_ppd} - {PPD_MAP.get(kod_ppd)}")
    menu = st.sidebar.radio("Menu", ["Cadangan Sekolah","Penempatan","Log Keluar"])
    if menu == "Log Keluar":
        st.session_state.clear()
        st.rerun()
    if menu == "Cadangan Sekolah":
        st.header(f"Cadangan dari Sekolah PPD {kod_ppd}")
        res = supa.table("cadangan_sup").select("*").eq("kod_ppd", kod_ppd).limit(60000).execute()
        df = pd.DataFrame(res.data or [])
        if df.empty:
            st.info("Belum ada cadangan")
        else:
            st.metric("Jumlah Cadangan", len(df))
            st.dataframe(df, use_container_width=True, hide_index=True)
    elif menu == "Penempatan":
        st.header(f"Penempatan PPD {kod_ppd}")
        st.info("Akan bina selepas test SUP ok")

# ========== JPN ==========
elif st.session_state.role == "JPN":
    st.sidebar.title("JPN Selangor")
    menu = st.sidebar.radio("Menu", ["Sekolah Master","Pusat Master","Guru Master 60K","Log Keluar"])
    if menu == "Log Keluar":
        st.session_state.clear()
        st.rerun()
    if menu == "Sekolah Master":
        st.header("sekolah_master (dari SENARAI_ID-SUP_BY_DAERAH.xlsx)")
        res = supa.table("sekolah_master").select("*").limit(1000).execute()
        st.dataframe(pd.DataFrame(res.data or []), use_container_width=True)
    if menu == "Pusat Master":
        st.header("pusat_master (dari 506)")
        res = supa.table("pusat_master").select("*").limit(1000).execute()
        st.dataframe(pd.DataFrame(res.data or []), use_container_width=True)
    if menu == "Guru Master 60K":
        st.header("guru_master 60K")
        res = supa.table("guru_master").select("kod_ppd, kod_sekolah, nama_guru, ic_guru").limit(100).execute()
        st.dataframe(pd.DataFrame(res.data or []), use_container_width=True)
        st.caption("Full 60K dalam Supabase - ini preview 100 je")
