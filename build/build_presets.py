"""Assemble data/presets.json: one entry per metro with price, rent, tax, cap, gap, growth, and a source note."""
import json, statistics as st
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
S=json.load(open(ROOT / 'data/metro_stats.json'))
P=json.load(open(ROOT / 'data/prices_nar_q2_2026.json')); P["hon"]=1190000
med={f:round(st.median(v[f] for v in S.values()),4) for f in ("gap","apprHist","rentHist")}
CA="1% of purchase price plus voter-approved bonds (about 1.15% all-in for a new buyer); Prop 13 caps assessment growth at 2% a year. Check for Mello-Roos in newer suburbs."
M=[ # key, label, HUD FY2026 3BR rent, tax, cap, state note
 ("atl","Atlanta, GA",2182,0.00767,None,"Georgia effective rate 0.77%. FHFA's Atlanta price index ends in 2024, so its history runs through 2024."),
 ("bos","Boston, MA",3526,0.00948,None,"Massachusetts effective rate 0.95%; towns vary widely."),
 ("chi","Chicago, IL",2294,0.01793,None,"Illinois effective rate 1.79%, the highest in the country."),
 ("dal","Dallas, TX",2431,0.01245,0.10,"Texas effective rate 1.25%; new buyers usually pay more. Homestead appraisal increases capped at 10% a year."),
 ("den","Denver, CO",2734,0.00519,None,"Colorado effective rate 0.52%."),
 ("det","Detroit, MI",1724,0.01129,0.028,"Michigan effective rate 1.13%. Proposal A caps taxable value growth at 5% or inflation, whichever is lower (2.7% for 2026), until a sale; set to the model's 2.8% inflation."),
 ("hon","Honolulu, HI",3674,0.0032,None,"Price is the Honolulu Board of Realtors' Oahu single-family median for January to August 2026 ($1.19M; August alone was $1.24M). Tax: the owner-occupied rate is $3.50 per $1,000 after a $120,000 home exemption ($140,000 from July 2027), about 0.32% effective, with no assessment cap. Hawaii adds a seller-paid conveyance tax of 0.3% to 0.5% at these prices, so raise selling costs to about 6.4%. Condos run far cheaper (median $510,000) but carry high HOA and insurance costs."),
 ("hou","Houston, TX",2116,0.01245,0.10,"Texas effective rate 1.25%; new buyers usually pay more. Homestead appraisal increases capped at 10% a year."),
 ("la","Los Angeles, CA",3298,0.0115,0.02,CA),
 ("mia","Miami, FL",3127,0.0076,0.028,"Florida effective rate 0.76%. Save Our Homes caps homestead assessment growth at 3% or inflation, whichever is lower; set to the model's 2.8% inflation. Florida is considering further homestead changes in 2026."),
 ("min","Minneapolis, MN",2262,0.00987,None,"Minnesota effective rate 0.99%."),
 ("ny","New York, NY",3644,0.01227,None,"New York effective rate 1.23%. New York City has its own class 1 assessment caps (not modeled)."),
 ("phi","Philadelphia, PA",2170,0.01137,None,"Pennsylvania effective rate 1.14%."),
 ("sd","San Diego, CA",3998,0.0115,0.02,CA),
 ("sf","San Francisco, CA",4604,0.0115,0.02,CA),
 ("stl","St. Louis, MO",1568,0.00849,None,"Missouri effective rate 0.85%."),
 ("tpa","Tampa, FL",2527,0.0076,0.028,"Florida effective rate 0.76%. Save Our Homes caps homestead assessment growth at 3% or inflation, whichever is lower; set to the model's 2.8% inflation. Florida is considering further homestead changes in 2026."),
 ("dc","Washington, DC (Arlington, Fairfax)",2835,0.0112,None,"Fairfax County rate $1.12 per $100 (Arlington, Alexandria and Maryland suburbs differ). Rent history spliced across a 2018 BLS change; baseline 1997-2018."),
]
out={}
for k,label,rent,tax,cap,note in M:
    s=S.get(k); est=s is None
    v=s or med
    out[k]=dict(label=label, price=P[k], rent0=rent, propTax=tax, assessCap=cap, overval=round(v["gap"],4), apprHist=round(v["apprHist"],4),
                rentHist=round(v["rentHist"],4), histEstimated=est,
                note=note+(" Price-to-rent gap and growth rates are placeholders (median of covered metros) until this metro's history is added." if est else ""))
json.dump(out,open(ROOT / 'data/presets.json','w'),indent=1)
print("metros:",len(out)," with history:",sum(not v["histEstimated"] for v in out.values()), " placeholder medians:",med)
