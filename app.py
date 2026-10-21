"""
FIX APIError - Pelantikan SPM 2026
- Kalau table sekolah_master belum wujud, tetap bagi login SUP untuk test
- Handle semua supabase error dengan try/except
"""

import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Pelantikan SPM Selangor 2026", layout="wide", page_icon="📚")

try:
    from supabase import create_client
except:
    create_client = None

SUPABASE_URL = "https://gnmaijhugkkvxejvsotk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdubWFpamhpZ2tra3Z4ZWp2c290ayIsInJvbGUiOiJhbm9uIiwiaWF0IjoxNzU5MTUzMjM4MiwiZXhwIjoyMDc0MTA5MjM4Mn0.1YWg71nCwnQzP-KUzTdHR4rZAVCAesbKVqvVC1-X6lw"

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

KOD_DAERAH = ["BA","BB","BC","BD","BE","BF","BG","BH","BJ","BK"]
PPD_MAP = {"BA":"Klang","BB":"Kuala Langat","BC":"Kuala Selangor","BD":"Hulu Langat","BE":"Hulu Selangor","BF":"Sabak Bernam","BG":"Gombak","BH":"Petaling Perdana","BJ":"Sepang","BK":"Petaling Utama"}

def safe_table(table_name):
    """Check table exists"""
    try:
        supa.table(table_name).select("*").limit(1).execute()
        return True
    except Exception as e:
        return False

def get_sekolah(kod_sekolah):
    try:
        res = supa.table("sekolah_master").select("*").eq("kod_sekolah", kod_sekolah.strip().upper()).limit(1).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        # Table belum wujud - return dummy untuk test
        st.warning(f"Table sekolah_master belum ada dalam Supabase - guna mode TEST. Error: {e}")
        # Dummy info
        kod = kod_sekolah.strip().upper()
        # Try guess PPD from kod
        ppd_guess = "BH"
        if kod.startswith("B"):
            # cari
            pass
        return {
            "kod_sekolah": kod,
            "nama_sekolah": f"SEKOLAH {kod} (TEST MODE)",
            "kod_ppd": ppd_guess,
            "ppd": PPD_MAP.get(ppd_guess,""),
            "senarai_pusat": ""
        }

def get_guru_by_sekolah(kod_sekolah):
    try:
        res = supa.table("guru_master").select("*").eq("kod_sekolah", kod_sekolah.strip().upper()).limit(60000).execute()
        rows=[]
        for r in res.data or []:
            d = r.get("data") or {}
            rows.append({
                "id": r.get("id"),
                "KOD SEKOLAH": r.get("kod_sekolah") or d.get("KOD SEKOLAH"),
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
    except Exception as e:
        st.error(f"Error baca guru_master: {e}")
        return pd.DataFrame()

# ========== LOGIN SIMPLE ==========
if "role" not in st.session_state:
    st.session_state.role = None

if st.session_state.role is None:
    st.markdown("<h1 style='text-align:center'>📚 Pelantikan SPM Selangor 2026</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center'>Login Simple - Test Mode</p>", unsafe_allow_html=True)
    # Check tables
    with st.expander("🔍 Check Supabase Tables", expanded=True):
        for t in ["sekolah_master","pusat_master","guru_master","cadangan_sup","penempatan_ppd"]:
            exists = safe_table(t)
            if exists:
                st.success(f"✅ {t} wujud")
            else:
                st.error(f"❌ {t} BELUM WUJUD - Sila run supabase_SCHEMA_CLEAN.sql dalam Supabase SQL Editor")
        st.info("Kalau ada ❌, app masih boleh login tapi guna TEST MODE. Sila run SQL dulu untuk full function.")
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
                st.session_state.role = "SUP"
                st.session_state.kod_sekolah = kod_s
                st.session_state.sekolah_info = sek
                st.rerun()
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
    info = st.session_state.sekolah_info or {}
    nama_s = info.get("nama_sekolah","")
    kod_ppd_s = info.get("kod_ppd","BH")
    
    st.sidebar.title(f"SUP {kod_s}")
    if nama_s:
        st.sidebar.caption(nama_s)
    menu = st.sidebar.radio("Menu", ["Senarai Guru","Tambah Guru","Buang Guru","Cadangan & Hantar","Log Keluar"])
    
    if menu == "Log Keluar":
        st.session_state.clear()
        st.rerun()
    
    if menu == "Senarai Guru":
        st.header(f"Senarai Guru - {kod_s} {nama_s}")
        df_guru = get_guru_by_sekolah(kod_s)
        if df_guru.empty:
            st.info("Belum ada guru. Cek guru_master ada data tak? Atau tambah baru.")
        else:
            st.metric("Jumlah Guru", len(df_guru))
            st.dataframe(df_guru[["NAMA GURU","IC","JANTINA","NO TELEFON","JAWATAN CADANGAN","POSKOD"]], use_container_width=True, hide_index=True)
    
    elif menu == "Tambah Guru":
        st.header(f"Tambah Guru Baru - {kod_s}")
        with st.form("tambah_guru"):
            c1,c2 = st.columns(2)
            with c1:
                nama = st.text_input("NAMA GURU *")
                ic = st.text_input("IC *")
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
                    st.error("Nama, IC, Alamat wajib")
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
                    try:
                        res_exist = supa.table("guru_master").select("id").eq("ic_guru", ic).limit(1).execute()
                        if res_exist.data:
                            supa.table("guru_master").update({"nama_guru": nama.upper(), "ic_guru": ic, "kod_sekolah": kod_s, "kod_ppd": kod_ppd_s.lower(), "data": data}).eq("id", res_exist.data[0]["id"]).execute()
                            st.success(f"✅ Kemaskini {nama}")
                        else:
                            supa.table("guru_master").insert({"kod_ppd": kod_ppd_s.lower(), "kod_sekolah": kod_s, "nama_guru": nama.upper(), "ic_guru": ic, "data": data}).execute()
                            st.success(f"✅ Tambah {nama}")
                    except Exception as e:
                        st.error(f"Gagal simpan: {e}")
    
    elif menu == "Buang Guru":
        st.header(f"Buang Guru - {kod_s}")
        df_guru = get_guru_by_sekolah(kod_s)
        if df_guru.empty:
            st.info("Tiada guru")
        else:
            label = {row["IC"]: f"{row['NAMA GURU']} | {row['IC']}" for _, row in df_guru.iterrows()}
            pilih = st.multiselect("Pilih guru", list(label.keys()), format_func=lambda x: label.get(x,x))
            sah = st.checkbox("Ya, buang terus")
            if st.button(f"🗑️ Buang {len(pilih)}", disabled=not (pilih and sah), use_container_width=True):
                try:
                    for ic in pilih:
                        res = supa.table("guru_master").select("id").eq("kod_sekolah", kod_s).eq("ic_guru", ic).execute()
                        if not res.data:
                            res = supa.table("guru_master").select("id").eq("ic_guru", ic).execute()
                        for r in res.data or []:
                            supa.table("guru_master").delete().eq("id", r["id"]).execute()
                    st.success(f"✅ {len(pilih)} dibuang")
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal buang: {e}")
    
    elif menu == "Cadangan & Hantar":
        st.header(f"Cadangan Petugas - {kod_s}")
        st.info("Akan sambung lepas Senarai Guru ok")

elif st.session_state.role == "PPD":
    kod_ppd = st.session_state.kod_ppd
    st.sidebar.title(f"PPD {kod_ppd}")
    menu = st.sidebar.radio("Menu", ["Cadangan Sekolah","Log Keluar"])
    if menu == "Log Keluar":
        st.session_state.clear()
        st.rerun()
    if menu == "Cadangan Sekolah":
        st.header(f"Cadangan PPD {kod_ppd}")
        try:
            res = supa.table("cadangan_sup").select("*").eq("kod_ppd", kod_ppd).limit(60000).execute()
            df = pd.DataFrame(res.data or [])
            st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"Table cadangan_sup belum wujud: {e}")

elif st.session_state.role == "JPN":
    st.sidebar.title("JPN")
    menu = st.sidebar.radio("Menu", ["Check Tables","Log Keluar"])
    if menu == "Log Keluar":
        st.session_state.clear()
        st.rerun()
    if menu == "Check Tables":
        st.header("Status Tables")
        for t in ["sekolah_master","pusat_master","guru_master","cadangan_sup"]:
            try:
                res = supa.table(t).select("*").limit(1).execute()
                st.success(f"✅ {t}: {len(res.data)} sample")
            except Exception as e:
                st.error(f"❌ {t}: {e}")
