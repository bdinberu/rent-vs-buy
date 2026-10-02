"""Price-to-rent gaps and 1990-2025 growth rates from FHFA price indexes and BLS rent indexes (data/series/)."""
import math, statistics as st, json, os
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
D = str(ROOT / 'data/series') + '/'
def load(f, q2=False):
    out={}
    for l in open(D+f):
        p=l.split()
        if not p: continue
        out[int(p[0])]=st.mean(map(float,p[1:]))
    return out
def stats(hf, rf, cur=2025, base=(1990,2019), start=1990):
    h=load(hf); r=load(rf); yrs=sorted(set(h)&set(r))
    lr={y:math.log(h[y]/r[y]) for y in yrs}
    b=[lr[y] for y in yrs if base[0]<=y<=base[1]]
    cur=max(y for y in yrs if y<=cur)
    gap=math.exp(lr[cur]-st.mean(b))-1
    n=cur-start
    return dict(gap=gap, apprHist=(h[cur]/h[start])**(1/n)-1, rentHist=(r[cur]/r[start])**(1/n)-1, cur=cur, nbase=len(b))
M={"sd":("sd_hpi.txt","sd_rent.txt"),"sea":("sea_hpi.txt","sea_rent.txt"),"bos":("bos_hpi.txt","bos_rent.txt"),"den":("den_hpi.txt","den_rent.txt"),
   "dal":("dal_hpi.txt","dal_rent.txt"),"la":("la_hpi.txt","la_rent.txt"),"sf":("sf_hpi_q2.txt","sf_rent.txt"),"ny":("ny_hpi_q2.txt","ny_rent.txt"),
   "mia":("mia_hpi_q2.txt","mia_rent.txt"),"hon":("hon_hpi_q2.txt","hon_rent.txt"),"phi":("phi_hpi_q2.txt","phi_rent.txt"),"chi":("chi_hpi_q2.txt","chi_rent.txt"),
   "atl":("atl_hpi_q2.txt","atl_rent.txt"),"det":("det_hpi_q2.txt","det_rent.txt"),"hou":("hou_hpi_q2.txt","hou_rent.txt"),
   "min":("min_hpi_q2.txt","min_rent.txt"),"tpa":("tpa_hpi_q2.txt","tpa_rent.txt"),"stl":("stl_hpi_q2.txt","stl_rent.txt"),"anc":("anc_hpi_q2.txt","anc_rent.txt")}
out={}
for k,(hf,rf) in M.items():
    if os.path.exists(D+hf) and os.path.exists(D+rf):
        s=stats(hf,rf); out[k]=s
        print(f"{k:4s} gap {s['gap']:+6.1%}  price CAGR {s['apprHist']:.2%}  rent CAGR {s['rentHist']:.2%}  (through {s['cur']}, baseline yrs {s['nbase']})")
# Washington from the earlier spliced computation
out["dc"]=dict(gap=0.2191, apprHist=0.0504, rentHist=0.0344, cur=2024, nbase=22)
json.dump(out,open(ROOT / 'data/metro_stats.json','w'),indent=1)
