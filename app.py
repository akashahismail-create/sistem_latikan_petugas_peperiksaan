import streamlit as st
import pandas as pd
from supabase import create_client

st.set_page_config(page_title="Pelantikan SPM Selangor 2026", layout="wide")

SUPABASE_URL = "https://gnmaijhugkkvxejvsotk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdubWFpamh1Z2trdnhlanZzb3RrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTI0ODc4OTcsImV4cCI6MjEwODA2Mzg5N30.1YWg71nCwnQzP-KUzTdHR4rZAVCAesbKVqvVC1-X6lw"

@st.cache_resource
def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supa = get_supabase()

KOD_DAERAH = ["BA","BB","BC","BD","BE","BF","BG","BH","BJ","BK"]
PPD_MAP = {"BA":"Klang","BB":"Kuala Langat","BC":"Kuala Selangor","BD":"Hulu Langat","BE":"Hulu Selangor","BF":"Sabak Bernam","BG":"Gombak","BH":"Petaling Perdana","BJ":"Sepang","BK":"Petaling Utama"}

def get_sekolah(kod):
    try:
        res = supa.table("sekolah_master").select("*").eq("kod_sekolah", kod.upper()).limit(1).execute()
        if res.data:
            return res.data[0]
    except Exception as e:
        st.error(f"sekolah_master error: {e}")
    return {"kod_sekolah": kod, "nama_sekolah": f"SEKOLAH {kod}", "kod_ppd": "BH"}

def get_guru(kod):
    try:
        res = supa.table("guru_master").select("*").eq("kod_sekolah", kod.upper()).limit(1000).execute()
        rows=[]
        for r in res.data or []:
            d = r.get("data") or {}
            rows.append({
                "NAMA GURU": r.get("nama_guru") or d.get("NAMA GURU",""),
                "IC": r.get("ic_guru") or d.get("IC",""),
                "TELEFON": d.get("NO TELEFON GURU",""),
                "JAWATAN": d.get("JAWATAN CADANGAN","")
            })
        return pd.DataFrame(rows)
    except Exception as e:
        st.error(f"guru_master error: {e}")
        return pd.DataFrame()

if "role" not in st.session_state:
    st.session_state.role=None

if st.session_state.role is None:
    st.title("📚 Pelantikan SPM Selangor 2026")
    st.caption(f"URL: {SUPABASE_URL}")
    st.success("✅ KEY full active - takde STRIPPED")
    col1,col2,col3 = st.columns(3)
    with col1:
        st.subheader("🏫 SUP")
        kod = st.text_input("KOD SEKOLAH", value="BFT8002").upper()
        if st.button("Masuk SUP", use_container_width=True):
            st.session_state.role="SUP"
            st.session_state.kod=kod
            st.session_state.info=get_sekolah(kod)
            st.rerun()
    with col2:
        st.subheader("🏢 PPD")
        ppd=st.selectbox("PPD", KOD_DAERAH, format_func=lambda x: f"{x}-{PPD_MAP[x]}")
        if st.button("Masuk PPD", use_container_width=True):
            st.session_state.role="PPD"
            st.session_state.kod=ppd
            st.rerun()
    with col3:
        st.subheader("🏛️ JPN")
        if st.button("Masuk JPN", use_container_width=True):
            st.session_state.role="JPN"
            st.rerun()
    st.stop()

if st.session_state.role=="SUP":
    kod=st.session_state.kod
    info=st.session_state.info
    st.sidebar.title(f"SUP {kod}")
    st.sidebar.caption(info.get("nama_sekolah",""))
    menu=st.sidebar.radio("Menu",["Senarai Guru","Tambah Guru","Buang Guru","Log Keluar"])
    if menu=="Log Keluar":
        st.session_state.clear()
        st.rerun()
    if menu=="Senarai Guru":
        st.header(f"Senarai Guru - {kod} {info.get('nama_sekolah','')}")
        df=get_guru(kod)
        if df.empty:
            st.info("guru_master kosong - 60K hilang. Sila Tambah Guru baru untuk test.")
            try:
                cnt=supa.table("guru_master").select("id", count="exact").execute()
                st.write(f"Total guru_master: {cnt.count} records")
            except Exception as e:
                st.error(f"Count error: {e}")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)
    elif menu=="Tambah Guru":
        st.header(f"Tambah Guru - {kod}")
        with st.form("tambah"):
            nama=st.text_input("NAMA GURU")
            ic=st.text_input("IC")
            tel=st.text_input("TELEFON")
            jaw=st.selectbox("JAWATAN",["Pengawas Peperiksaan","Ketua Pengawas"])
            alamat=st.text_area("ALAMAT")
            submit=st.form_submit_button("Simpan")
            if submit:
                data={"NAMA GURU":nama.upper(),"IC":ic,"NO TELEFON GURU":tel,"JAWATAN CADANGAN":jaw,"ALAMAT RUMAH":alamat,"KOD SEKOLAH":kod}
                try:
                    supa.table("guru_master").insert({"kod_ppd":info.get("kod_ppd","BH").lower(),"kod_sekolah":kod,"nama_guru":nama.upper(),"ic_guru":ic,"data":data}).execute()
                    st.success(f"✅ {nama} berjaya tambah!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Gagal: {e}")
    elif menu=="Buang Guru":
        st.header("Buang Guru")
        df=get_guru(kod)
        if not df.empty:
            pilih=st.multiselect("Pilih IC untuk buang", df["IC"].tolist())
            if st.button(f"Buang {len(pilih)}"):
                for ic in pilih:
                    try:
                        res=supa.table("guru_master").select("id").eq("ic_guru",ic).execute()
                        for r in res.data or []:
                            supa.table("guru_master").delete().eq("id",r["id"]).execute()
                        st.success(f"Buang {ic} ok")
                    except Exception as e:
                        st.error(str(e))
                st.rerun()
elif st.session_state.role=="PPD":
    st.header(f"PPD {st.session_state.kod}")
    try:
        res=supa.table("cadangan_sup").select("*").eq("kod_ppd", st.session_state.kod).execute()
        st.dataframe(pd.DataFrame(res.data or []), use_container_width=True)
    except Exception as e:
        st.error(str(e))
    if st.sidebar.button("Log Keluar"):
        st.session_state.clear()
        st.rerun()
elif st.session_state.role=="JPN":
    st.header("JPN - Check Tables")
    for t in ["sekolah_master","pusat_master","guru_master"]:
        try:
            res=supa.table(t).select("*", count="exact").limit(1).execute()
            st.success(f"✅ {t}: {res.count} records")
        except Exception as e:
            st.error(f"❌ {t}: {e}")
    if st.sidebar.button("Log Keluar"):
        st.session_state.clear()
        st.rerun()
