"""Generate random scenarios with the Python reference model (tests/model.py)."""
import json, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from model import run, DEFAULTS
random.seed(7)
cases=[]
for k in range(600):
    p=dict(DEFAULTS)
    p.update(price=random.choice([250000,500000,900000,1500000]), down=random.choice([0.05,0.1,0.2,0.3]),
             rate=random.uniform(0.03,0.09), term=random.choice([15,30]), appr=random.uniform(-0.01,0.07),
             invRet=random.uniform(0.02,0.12), rent0=random.uniform(1200,6000), rentGrowth=random.uniform(0.01,0.06),
             filing=random.choice(['single','mfj']), stateLocalTax=random.choice([0,8000,30000]),
             otherItem=random.choice([0,5000]), hoa=random.choice([0,300]), itemize=random.choice([True,False]),
             horizon=random.randint(1,50), cgRate=random.choice([0,0.15,0.2]),
             propTax=random.uniform(0.003,0.018), divYield=random.choice([0,0.011,0.02]))
    if random.random()<0.5: p.update(priceMode='revert', overval=random.uniform(-0.2,0.6), halfLife=random.choice([2,5,11,24,40]))
    if random.random()<0.4: p.update(assessCap=random.choice([0.02,0.028,0.05,0.10]))
    r=run(p)
    cases.append(dict(p=p, py=dict(owner=r['owner_nw'], renter=r['renter_nw'], fullInt=r['full_int'], pmt=r['pmt'], pmi=r['full_pmi'])))
json.dump(cases, open(HERE / 'cases.json', 'w'))
print(f'Wrote {len(cases)} reference cases from the Python model')
