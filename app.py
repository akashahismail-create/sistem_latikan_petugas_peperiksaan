import streamlit as st
import pandas as pd
from supabase import create_client
from io import BytesIO
import datetime, math, json, re

st.set_page_config(page_title="Pelantikan SPM Selangor 2026", layout="wide", page_icon="📚", initial_sidebar_state="collapsed")

# HIDE SIDEBAR COMPLETELY BUT KEEP LOOK LIKE SIDEBAR
st.markdown("""
<style>
    [data-testid="stSidebar"] {display: none !important;}
    [data-testid="stSidebarNav"] {display: none !important;}
    .stSidebar {display: none !important;}
    section[data-testid="stSidebar"] {display: none !important;}
    /* Custom left panel that looks like sidebar */
    .custom-sidebar {
        background: linear-gradient(180deg, #ffffff 0%, #f8f9fa 100%);
        border-radius: 12px;
        padding: 16px;
        border: 1px solid #e9ecef;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        height: fit-content;
        position: sticky;
        top: 10px;
    }
    .custom-sidebar h3 {
        font-size: 18px;
        color: #0d47a1;
        margin-bottom: 2px;
    }
    .sidebar-menu .stRadio > div {
        gap: 4px;
    }
</style>
""", unsafe_allow_html=True)

SUPABASE_URL = "https://gnmaijhugkkvxejvsotk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdubWFpamh1Z2trdnhlanZzb3RrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTI0ODc4OTcsImV4cCI6MjEwODA2Mzg5N30.1YWg71nCwnQzP-KUzTdHR4rZAVCAesbKVqvVC1-X6lw"

@st.cache_resource
def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)
supa = get_supabase()

KOD_DAERAH = ["BA", "BB", "BC", "BD", "BE", "BF", "BG", "BH", "BJ", "BK"]
PPD_MAP = {"BA":"Klang","BB":"Kuala Langat","BC":"Kuala Selangor","BD":"Hulu Langat","BE":"Hulu Selangor","BF":"Sabak Bernam","BG":"Gombak","BH":"Petaling Perdana","BJ":"Sepang","BK":"Petaling Utama"}

def kira_kelas_dari_calon(jumlah_calon):
    try:
        c = int(float(str(jumlah_calon).replace(",","").strip() or 0))
        if c <=0: return 0
        return math.ceil(c / 20)
    except: return 0

def kira_petugas_dari_kelas(jumlah_kelas):
    try: return int(jumlah_kelas) + 9
    except: return 0

def kira_sekolah_perlu_calonkan(jumlah_kelas):
    try: return kira_petugas_dari_kelas(jumlah_kelas) + 3
    except: return 0

def get_sekolah(kod):
    for col in ["kod_sekolah", "kod_sekolah_tuan_rumah", "KOD_SEKOLAH"]:
        try:
            res = supa.table("sekolah_master").select("*").eq(col, kod.upper()).limit(1).execute()
            if res.data:
                row = res.data[0]
                return {"kod_sekolah": row.get("kod_sekolah") or row.get("KOD_SEKOLAH") or kod, "nama_sekolah": row.get("nama_sekolah") or row.get("NAMA_SEKOLAH") or f"SEKOLAH {kod}", "kod_ppd": row.get("kod_ppd") or row.get("KOD_PPD") or "BH", "ppd": row.get("ppd") or row.get("PPD") or "Petaling Perdana", "_raw": row}
        except: continue
    return {"kod_sekolah": kod, "nama_sekolah": f"SEKOLAH {kod}", "kod_ppd": "BH", "ppd": "Petaling Perdana"}

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
        rows=[]
        for r in res.data or []:
            d = r.get("data") or {}
            if isinstance(d, str):
                try: d=json.loads(d)
                except: d={}
            def _nk(x): return re.sub(r"[^A-Z0-9]", "", str(x).upper())
            _dn, _rn = {}, {}
            for _k,_v in d.items():
                if _v is not None and not isinstance(_v,(dict,list)) and str(_v).strip().lower() not in ("","none","null","nan","n/a","-"):
                    _dn.setdefault(_nk(_k), str(_v).strip())
            for _k,_v in r.items():
                if _v is not None and not isinstance(_v,(dict,list)) and str(_v).strip().lower() not in ("","none","null","nan","n/a","-"):
                    _rn.setdefault(_nk(_k), str(_v).strip())
            def get_val(*keys, default=""):
                for k in keys:
                    nk=_nk(k)
                    if nk in _dn: return _dn[nk]
                    if nk in _rn: return _rn[nk]
                return default
            rows.append({
                "NAMA GURU": get_val("NAMA GURU","nama_guru"),
                "IC": get_val("IC","ic_guru"),
                "JANTINA": get_val("JANTINA","jantina"),
                "POSKOD_RUMAH": get_val("POSKOD RUMAH","POSKOD_RUMAH","poskod_rumah"),
                "ALAMAT_RUMAH": get_val("ALAMAT RUMAH","ALAMAT_RUMAH","alamat_rumah"),
                "TELEFON_GURU": get_val("TELEFON GURU","NO TELEFON GURU","TELEFON_GURU","telefon_guru","TELEFON"),
                "TELEFON": get_val("TELEFON GURU","telefon_guru","TELEFON"),
                "EMAIL_GURU": get_val("EMAIL GURU","EMAIL_GURU","email_guru"),
                "JAWATAN CADANGAN": get_val("JAWATAN CADANGAN","JAWATAN_CADANGAN","jawatan_cadangan"),
                "PENGALAMAN_SPM": get_val("PENGALAMAN SPM","PENGALAMAN_SPM","pengalaman_spm"),
                "KOD_SEKOLAH_ASAL": get_val("KOD SEKOLAH ASAL","KOD_SEKOLAH_ASAL","kod_sekolah_asal") or kod_sekolah.upper(),
                "NAMA_SEKOLAH_ASAL": get_val("NAMA SEKOLAH ASAL","NAMA_SEKOLAH_ASAL","nama_sekolah_asal"),
                "NO_PUSAT_ASAL": get_val("NO PUSAT ASAL","NO_PUSAT_ASAL","no_pusat_asal") or "BA142",
            })
        return pd.DataFrame(rows)
    except Exception as e:
        st.error(f"Error guru: {e}")
        return pd.DataFrame()

def get_cadangan_df(kod_ppd=None, kod_sekolah=None):
    try:
        try:
            if kod_sekolah:
                res = supa.table("cadangan_sup").select("*").eq("kod_sekolah", kod_sekolah.upper()).limit(5000).execute()
                if not res.data:
                    res = supa.table("cadangan_sup").select("*").eq("kod_sekolah_asal", kod_sekolah.upper()).limit(5000).execute()
                if not res.data:
                    res = supa.table("cadangan_sup").select("*").limit(5000).execute()
            elif kod_ppd:
                res = supa.table("cadangan_sup").select("*").eq("kod_ppd", kod_ppd.upper()).limit(5000).execute()
                if not res.data:
                    res = supa.table("cadangan_sup").select("*").limit(5000).execute()
            else:
                res = supa.table("cadangan_sup").select("*").limit(5000).execute()
        except:
            res = supa.table("cadangan_sup").select("*").limit(5000).execute()
        df = pd.DataFrame(res.data or [])
        return df
    except Exception as e:
        st.error(f"Error cadangan: {e}")
        return pd.DataFrame()

def get_pusat_df():
    try:
        res = supa.table("pusat_master").select("*").limit(1000).execute()
        return pd.DataFrame(res.data or [])
    except: return pd.DataFrame()

def to_excel(df):
    output = BytesIO()
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        return output.getvalue()
    except:
        try:
            output.write(df.to_csv(index=False).encode('utf-8-sig'))
            return output.getvalue()
        except:
            return b""

# Refresh component for custom left panel
def refresh_component():
    st.markdown("### 🔄 Refresh Data")
    st.caption(f"Last: {datetime.datetime.now().strftime('%d/%m %H:%M:%S')}")
    if st.button("🔄 REFRESH - Baca Data Baru", use_container_width=True, type="primary", key=f"refresh_{st.session_state.role}_{datetime.datetime.now().microsecond}"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.toast("✅ Data refreshed!")
        st.rerun()
    st.caption("Tekan selepas SUP buat pertukaran")
    st.markdown("---")

# ================= LOGIN =================
if "role" not in st.session_state:
    st.session_state.role=None

if st.session_state.role is None:
    st.markdown("<h1 style='text-align:center; color:#0d47a1;'>🏫 PELANTIKAN SPM SELANGOR 2026</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>369 Sekolah | 506 Pusat | 71,064 Calon</p>", unsafe_allow_html=True)
    
    @st.cache_data(ttl=600)
    def load_sekolah_list():
        try:
            res = supa.table("sekolah_master").select("*").limit(1000).execute()
            rows=[]
            for r in res.data or []:
                kod = r.get("kod_sekolah") or r.get("KOD_SEKOLAH") or ""
                nama = r.get("nama_sekolah") or r.get("NAMA_SEKOLAH") or ""
                kod_ppd = r.get("kod_ppd") or r.get("KOD_PPD") or "BH"
                if kod and nama:
                    rows.append({"KOD_SEKOLAH": kod.upper().strip(), "NAMA_SEKOLAH": nama.upper().strip(), "KOD_PPD": kod_ppd.upper().strip(), "PPD": PPD_MAP.get(kod_ppd.upper().strip(), "")})
            df=pd.DataFrame(rows)
            if not df.empty:
                order_map={k:i for i,k in enumerate(KOD_DAERAH)}
                df["order"]=df["KOD_PPD"].map(order_map)
                df=df.sort_values(["order","NAMA_SEKOLAH"]).reset_index(drop=True)
                df["ID"]=df.index+1
                df["PASSWORD"]=df["ID"].astype(str)
            return df
        except: return pd.DataFrame()
    
    df_sekolah_all=load_sekolah_list()
    tab1,tab2,tab3=st.tabs(["SUP","PPD","JPN"])
    
    with tab1:
        col_a,col_b=st.columns(2)
        with col_a:
            pilih_ppd_label=st.selectbox("Pilih Daerah", options=[f"{k} - {PPD_MAP[k]}" for k in KOD_DAERAH], key="sup_daerah")
            pilih_ppd_code=pilih_ppd_label.split(" - ")[0]
            df_filtered=df_sekolah_all[df_sekolah_all["KOD_PPD"]==pilih_ppd_code] if not df_sekolah_all.empty else pd.DataFrame()
            if df_filtered.empty:
                sekolah_manual=st.text_input("KOD SEKOLAH", value="BFT0003").upper()
                pilih_sekolah_kod=sekolah_manual
                pilih_sekolah_nama=f"SEKOLAH {sekolah_manual}"
                sup_id=1
            else:
                sekolah_options=[f"{row['KOD_SEKOLAH']} - {row['NAMA_SEKOLAH']}" for _,row in df_filtered.iterrows()]
                pilih_sekolah_str=st.selectbox(f"Pilih Sekolah ({len(df_filtered)})", options=sekolah_options)
                pilih_sekolah_kod=pilih_sekolah_str.split(" - ")[0]
                row_sel=df_filtered[df_filtered["KOD_SEKOLAH"]==pilih_sekolah_kod].iloc[0] if not df_filtered[df_filtered["KOD_SEKOLAH"]==pilih_sekolah_kod].empty else None
                pilih_sekolah_nama=row_sel["NAMA_SEKOLAH"] if row_sel is not None else ""
                sup_id=int(row_sel["ID"]) if row_sel is not None else 1
        with col_b:
            pwd_input=st.text_input("Password", type="password", placeholder=f"{sup_id}")
            if st.button("Masuk SUP", type="primary", use_container_width=True):
                info=get_sekolah(pilih_sekolah_kod)
                info["kod_sekolah"]=pilih_sekolah_kod
                info["nama_sekolah"]=pilih_sekolah_nama
                info["kod_ppd"]=pilih_ppd_code
                st.session_state.role="SUP"
                st.session_state.kod=pilih_sekolah_kod
                st.session_state.info=info
                st.rerun()
    with tab2:
        col1,col2=st.columns(2)
        with col1:
            ppd_labels=[f"{KOD_DAERAH[i]} - {PPD_MAP[KOD_DAERAH[i]]}" for i in range(len(KOD_DAERAH))]
            pilih_ppd_full=st.selectbox("Pilih PPD", options=ppd_labels)
            ppd_code=pilih_ppd_full.split(" - ")[0]
        with col2:
            ppd_pwd=st.text_input("Password PPD", type="password")
            if st.button("Masuk PPD", type="primary", use_container_width=True):
                st.session_state.role="PPD"
                st.session_state.kod=ppd_code
                st.rerun()
    with tab3:
        if st.button("Masuk JPN", type="primary"):
            st.session_state.role="JPN"
            st.session_state.kod="JPN"
            st.rerun()
    st.stop()

# ================= SUP LAYOUT TANPA SIDEBAR =================
if st.session_state.role=="SUP":
    kod=st.session_state.kod
    info=st.session_state.info
    # Custom left panel
    col_menu, col_main = st.columns([1, 3.2], gap="large")
    with col_menu:
        st.markdown('<div class="custom-sidebar">', unsafe_allow_html=True)
        st.markdown(f"### 🏫 SUP {kod}")
        st.caption(f"{info.get('nama_sekolah','')[:30]} | {info.get('kod_ppd','')} - {PPD_MAP.get(info.get('kod_ppd',''),'')}")
        refresh_component()
        MENU_SUP = [('dashboard','📊 Dashboard'),('senarai','📋 Senarai Guru'),('tambah','➕ Tambah Guru'),('import','📤 Import Excel'),('buang','🗑️ Buang Guru'),('cadangan','📝 Cadangan Lantikan'),('hantar','📤 Hantar ke PPD'),('keluar','🚪 Log Keluar')]
        menu=st.radio("Menu SUP", [k for k,_ in MENU_SUP], format_func=dict(MENU_SUP).get, label_visibility="collapsed", key="sup_menu")
        st.markdown('</div>', unsafe_allow_html=True)
    with col_main:
        if menu=="keluar":
            st.session_state.clear()
            st.rerun()
        df_guru=get_guru_df(kod)
        if menu=="dashboard":
            st.header(f"Dashboard SUP - {kod} {info.get('nama_sekolah','')}")
            c1,c2,c3,c4=st.columns(4)
            c1.metric("Jumlah Guru", len(df_guru))
            try:
                cad=get_cadangan_df(kod_sekolah=kod)
                c2.metric("Cadangan", len(cad))
            except: c2.metric("Cadangan",0)
            st.dataframe(df_guru[["NAMA GURU","IC","TELEFON"]].head(20) if not df_guru.empty else pd.DataFrame(), use_container_width=True)
        elif menu=="senarai":
            st.header(f"Senarai Guru - {kod} Lengkap")
            if df_guru.empty:
                st.info("Tiada guru")
            else:
                st.success(f"Ada {len(df_guru)} guru")
                cols=[c for c in ["NAMA GURU","IC","JANTINA","POSKOD_RUMAH","ALAMAT_RUMAH","TELEFON_GURU","EMAIL_GURU","JAWATAN CADANGAN","KOD_SEKOLAH_ASAL","NO_PUSAT_ASAL"] if c in df_guru.columns]
                st.dataframe(df_guru[cols] if cols else df_guru, use_container_width=True)
                st.download_button("Export Excel", to_excel(df_guru), file_name=f"guru_{kod}.xlsx")
        elif menu=="cadangan":
            st.header(f"Cadangan Lantikan - {kod}")
            if df_guru.empty:
                st.warning("Tiada guru")
            else:
                guru_pilih=st.multiselect("Pilih Guru", df_guru["IC"].tolist(), format_func=lambda x: f"{df_guru[df_guru['IC']==x]['NAMA GURU'].values[0]} - {x}")
                jawatan=st.selectbox("Jawatan", ["Ketua Pengawas","Timbalan Ketua Pengawas","Penyelia Kawasan","Pengawas Peperiksaan"])
                pengalaman=st.text_input("Pengalaman SPM", "3")
                if guru_pilih:
                    preview=[]
                    for ic in guru_pilih[:10]:
                        r=df_guru[df_guru["IC"]==ic]
                        if not r.empty:
                            rr=r.iloc[0]
                            preview.append({"IC":ic,"NAMA":rr["NAMA GURU"][:20],"JANTINA":rr["JANTINA"] or "-","POSKOD":rr["POSKOD_RUMAH"] or "-","ALAMAT":rr["ALAMAT_RUMAH"][:20] or "-","TELEFON":rr["TELEFON_GURU"] or "-","EMAIL":rr["EMAIL_GURU"] or "-"})
                    st.dataframe(pd.DataFrame(preview), use_container_width=True)
                if st.button(f"Simpan {len(guru_pilih)} guru", type="primary"):
                    if not guru_pilih:
                        st.error("Pilih guru")
                    else:
                        ok=0
                        for ic in guru_pilih:
                            gr=df_guru[df_guru["IC"]==ic]
                            if gr.empty: continue
                            g=gr.iloc[0]
                            data={"kod_ppd": info.get('kod_ppd','BA').upper(),"kod_sekolah":kod.upper(),"kod_sekolah_asal":kod.upper(),"nama_sekolah_asal":info.get('nama_sekolah',''),"ic_guru":ic,"nama_guru":g["NAMA GURU"],"jantina":g["JANTINA"] or "L","poskod_rumah":g["POSKOD_RUMAH"] or "","alamat_rumah":g["ALAMAT_RUMAH"] or "","telefon_guru":g["TELEFON_GURU"] or "","email_guru":g["EMAIL_GURU"] or "","jawatan_cadangan":jawatan,"pengalaman_spm":pengalaman,"no_pusat_asal":"BA142","kod_pusat":"BA142","status":"DICADANGKAN","tarikh_cadang":str(datetime.date.today())}
                            try:
                                supa.table("cadangan_sup").insert(data).execute()
                                ok+=1
                            except:
                                try:
                                    supa.table("cadangan_sup").update(data).eq("ic_guru",ic).eq("kod_sekolah",kod.upper()).execute()
                                    ok+=1
                                except Exception as e:
                                    st.error(f"{ic}: {e}")
                        if ok>0:
                            st.success(f"Berjaya {ok} guru - Tekan REFRESH di kiri untuk lihat!")
                            st.balloons()
                            st.rerun()
            st.markdown("---")
            st.subheader("Senarai Cadangan Sekolah Ini")
            df_cad=get_cadangan_df(kod_sekolah=kod)
            if df_cad.empty:
                st.info("Belum ada cadangan")
            else:
                st.dataframe(df_cad, use_container_width=True)
                # Batal
                if "id" in df_cad.columns:
                    batal=st.multiselect("Batal (selagi belum lulus)", df_cad["id"].tolist())
                    if st.button("Batal Terpilih"):
                        for bid in batal:
                            supa.table("cadangan_sup").delete().eq("id",bid).execute()
                        st.success("Batal ok")
                        st.rerun()
        elif menu=="hantar":
            st.header(f"Hantar ke PPD {info.get('kod_ppd','BA')} - Table cadangan_sup")
            df_cad=get_cadangan_df(kod_sekolah=kod)
            if df_cad.empty:
                st.warning("Belum ada cadangan")
            else:
                st.info(f"Ada {len(df_cad)} cadangan - Semua ada POSKOD & ALAMAT lengkap!")
                st.dataframe(df_cad, use_container_width=True)
                if st.button("📤 Hantar Semua ke PPD", type="primary", use_container_width=True):
                    for _,row in df_cad.iterrows():
                        try:
                            supa.table("cadangan_sup").update({"status":"HANTAR KE PPD","kod_ppd":info.get('kod_ppd','BA').upper()}).eq("id",row["id"]).execute()
                        except:
                            supa.table("cadangan_sup").update({"status":"HANTAR KE PPD"}).eq("id",row["id"]).execute()
                    st.success(f"Hantar {len(df_cad)} ke PPD!")
                    st.rerun()

elif st.session_state.role=="PPD":
    kod_ppd=st.session_state.kod
    col_menu, col_main = st.columns([1, 3.2], gap="large")
    with col_menu:
        st.markdown('<div class="custom-sidebar">', unsafe_allow_html=True)
        st.markdown(f"### 🏢 PPD {kod_ppd}")
        st.caption(f"{PPD_MAP.get(kod_ppd,'')}")
        refresh_component()
        menu=st.radio("Menu PPD", ["📊 Dashboard PPD","🏫 Pusat di PPD","📋 Cadangan SUP","✅ Kelulusan","📥 Export","🚪 Log Keluar"], label_visibility="collapsed", key="ppd_menu")
        st.markdown('</div>', unsafe_allow_html=True)
    with col_main:
        if menu=="🚪 Log Keluar":
            st.session_state.clear()
            st.rerun()
        if menu=="📊 Dashboard PPD":
            st.header(f"Dashboard PPD {kod_ppd} - {PPD_MAP.get(kod_ppd,'')}")
            try:
                cnt_sekolah=supa.table("sekolah_master").select("kod_sekolah", count="exact").eq("kod_ppd", kod_ppd).execute()
                cnt_guru=supa.table("guru_master").select("id", count="exact").eq("kod_ppd", kod_ppd.lower()).execute()
                cnt_cadang=supa.table("cadangan_sup").select("id", count="exact").eq("kod_ppd", kod_ppd).execute()
                c1,c2,c3=st.columns(3)
                c1.metric("Sekolah", cnt_sekolah.count)
                c2.metric("Guru", cnt_guru.count)
                c3.metric("Cadangan", cnt_cadang.count)
            except Exception as e:
                st.error(str(e))
        elif menu=="📋 Cadangan SUP":
            st.header(f"Cadangan dari SUP - PPD {kod_ppd}")
            df_cad=get_cadangan_df(kod_ppd=kod_ppd)
            if df_cad.empty:
                st.info("Belum ada cadangan")
            else:
                st.dataframe(df_cad, use_container_width=True)
                st.download_button("Export", to_excel(df_cad), file_name=f"cadangan_PPD_{kod_ppd}.xlsx")
        elif menu=="✅ Kelulusan":
            st.header(f"Kelulusan PPD {kod_ppd}")
            df_cad=get_cadangan_df(kod_ppd=kod_ppd)
            if df_cad.empty:
                st.info("Tiada cadangan")
            else:
                st.dataframe(df_cad, use_container_width=True)
                pilih_id=st.multiselect("Pilih ID untuk lulus", df_cad["id"].tolist() if "id" in df_cad.columns else [])
                if st.button("✅ Lulus Terpilih", type="primary"):
                    for i in pilih_id:
                        supa.table("cadangan_sup").update({"status":"LULUS PPD"}).eq("id",i).execute()
                    st.success("Lulus berjaya")
                    st.rerun()

elif st.session_state.role=="JPN":
    col_menu, col_main = st.columns([1, 3.2], gap="large")
    with col_menu:
        st.markdown('<div class="custom-sidebar">', unsafe_allow_html=True)
        st.markdown("### 🏛️ JPN Selangor")
        refresh_component()
        menu=st.radio("Menu JPN", ["📊 Dashboard JPN","📋 Semua Cadangan","📥 Export Negeri","⚙️ Admin","🚪 Log Keluar"], label_visibility="collapsed", key="jpn_menu")
        st.markdown('</div>', unsafe_allow_html=True)
    with col_main:
        if menu=="🚪 Log Keluar":
            st.session_state.clear()
            st.rerun()
        if menu=="📊 Dashboard JPN":
            st.header("Dashboard JPN Selangor")
            cols=st.columns(4)
            for idx,t in enumerate(["sekolah_master","pusat_master","guru_master","cadangan_sup"]):
                try:
                    res=supa.table(t).select("*", count="exact").limit(1).execute()
                    cols[idx].metric(t, res.count)
                except: cols[idx].error(t)
        elif menu=="📋 Semua Cadangan":
            st.header("Semua Cadangan Seluruh Negeri")
            res=supa.table("cadangan_sup").select("*").limit(10000).execute()
            df=pd.DataFrame(res.data or [])
            st.dataframe(df, use_container_width=True)
            if not df.empty:
                st.download_button("Export", to_excel(df), file_name=f"cadangan_negeri_{datetime.date.today()}.xlsx")
