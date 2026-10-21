"""
Fix jumlah_calon yang hilang dalam pusat_master
- Baca pusat_2026.csv (506 pusat)
- Update existing records in Supabase by no_pusat
- Tambah column kalau belum ada

Cara guna:
pip install supabase pandas
python fix_jumlah_calon.py
"""

import pandas as pd
from supabase import create_client
import time

SUPABASE_URL = "https://gnmaijhugkkvxejvsotk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdubWFpamh1Z2trdnhlanZzb3RrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTI0ODc4OTcsImV4cCI6MjEwODA2Mzg5N30.1YWg71nCwnQzP-KUzTdHR4rZAVCAesbKVqvVC1-X6lw"

supa = create_client(SUPABASE_URL, SUPABASE_KEY)

print("Baca pusat_2026.csv...")
try:
    df = pd.read_csv("pusat_2026.csv")
except:
    df = pd.read_csv("pusat_2026.csv", encoding='latin1')

print(f"Total {len(df)} pusat")
print(df.head(3)[["NO_PUSAT","NAMA_PUSAT","JUMLAH_CALON","JUMLAH_KELAS"]].to_string())

print("\nUpdate pusat_master...")
ok=0
fail=0
for idx, row in df.iterrows():
    try:
        no_pusat = str(row.get("NO_PUSAT","")).strip().upper()
        if not no_pusat:
            continue
        j_calon = int(float(str(row.get("JUMLAH_CALON","0")).strip() or 0))
        j_kelas = int(float(str(row.get("JUMLAH_KELAS","0")).strip() or 0))
        petugas = int(float(str(row.get("PETUGAS_NEEDED","0")).strip() or 0))
        
        # Try update by no_pusat, then kod_pusat
        updated=False
        for col in ["no_pusat", "kod_pusat"]:
            try:
                res = supa.table("pusat_master").update({
                    "jumlah_calon": j_calon,
                    "jumlah_kelas": j_kelas,
                    "calon": j_calon,
                    "bilik": j_kelas,
                    "petugas_needed": petugas,
                    "JUMLAH_CALON": j_calon,  # try uppercase too
                }).eq(col, no_pusat).execute()
                if res.data:
                    updated=True
                    ok+=1
                    break
            except Exception as e:
                # Column mungkin tak wujud, try tambah column dulu via data json
                pass
        
        if not updated:
            # Try update data field merge - fetch then update data
            try:
                existing = supa.table("pusat_master").select("*").eq("no_pusat", no_pusat).limit(1).execute()
                if not existing.data:
                    existing = supa.table("pusat_master").select("*").eq("kod_pusat", no_pusat).limit(1).execute()
                if existing.data:
                    cur = existing.data[0]
                    cur_data = cur.get("data") or {}
                    if isinstance(cur_data, str):
                        import json
                        try:
                            cur_data = json.loads(cur_data)
                        except:
                            cur_data={}
                    cur_data["JUMLAH_CALON"] = str(j_calon)
                    cur_data["JUMLAH_KELAS"] = str(j_kelas)
                    cur_data["PETUGAS_NEEDED"] = str(petugas)
                    cur_data["CALON"] = str(j_calon)
                    # Update data column
                    supa.table("pusat_master").update({"data": cur_data}).eq("id", cur["id"]).execute()
                    ok+=1
                else:
                    fail+=1
            except Exception as e:
                print(f"Fail {no_pusat}: {e}")
                fail+=1
                
        if idx % 50 == 0:
            print(f"Progress {idx+1}/{len(df)} OK {ok} Fail {fail}")
        time.sleep(0.1)
    except Exception as e:
        print(f"Row error {idx}: {e}")
        fail+=1

print(f"\nSELESAI! OK {ok}/{len(df)} Fail {fail}")

# Verify
res = supa.table("pusat_master").select("*").limit(5).execute()
print("\nSample after fix:")
for r in res.data[:3]:
    print(f"{r.get('no_pusat')} - calon: {r.get('jumlah_calon')} / {r.get('calon')} / data JUMLAH_CALON: {(r.get('data') or {}).get('JUMLAH_CALON')}")
