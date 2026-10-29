#!/usr/bin/env python3
"""Frozen v0.4.2 curve; a pure price intervention and two logging identity controls."""
import json,csv,concurrent.futures,subprocess,shutil,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'assets/reports/economy_v042_closeout';BASE=ROOT/'assets/reports/economy_v042/conservative/replay'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run():
 for path,h in read(R/'before/manifest.json').items():
  if path.startswith('data/'):assert sha(ROOT/path)==h,'Frozen table changed: '+path
 for group in ['control','price_x3']:
  inp=R/group/'inputs';shutil.copytree(BASE/'inputs',inp,dirs_exist_ok=True);tables=read(inp/'tables.json')
  for src in ['tools/joint_behavior.ts','tools/player_policy.ts','app/src/core/progression.ts','app/src/core/formation.ts','app/src/core/battle/engine.ts']:shutil.copy2(ROOT/src,inp/Path(src).name)
  if group=='price_x3':
   for row in tables['feast']:
    if row['profile']=='conservative':row['silver']*=3
   rows=list(csv.DictReader((inp/'feast.csv').open()))
   for row in rows:
    if row['profile']=='conservative':row['silver']=str(int(row['silver'])*3)
   with(inp/'feast.csv').open('w',newline='')as f:w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
  (inp/'tables.json').write_text(json.dumps(tables,ensure_ascii=False))
 jobs=[('control',c,134000+(1000000 if c=='qing'else 0))for c in ['taiping','qing']]+[('price_x3',c,134000+i+(1000000 if c=='qing'else 0))for c in ['taiping','qing']for i in range(12)]
 def job(item):
  group,camp,seed=item;out=R/group/f'{camp}_{seed}.json'
  with out.with_suffix('.log').open('w')as f:
   subprocess.run(['node','--import','./app/node_modules/tsx/dist/loader.mjs','tools/joint_behavior.ts',f'camp={camp}',f'seed={seed}','n=1','feast=conservative','trace_early=1',f'reference_divisor={3 if group=="price_x3"else 1}',f'tables={R}/{group}/inputs/tables.json',f'out={out}'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
  d=read(out);print(json.dumps({'group':group,'campaign':camp,'seed':seed,'cleared':d['runs'][0]['cleared'],'days':d['runs'][0]['days']}),flush=True);return group,out,d
 with concurrent.futures.ThreadPoolExecutor(max_workers=6)as pool:finished=list(pool.map(job,jobs))
 baseline=read(BASE/'behavior.json');identities=[]
 for _,p,d in (x for x in finished if x[0]=='control'):
  current=d['runs'][0];old=next(r for r in baseline['runs']if(r['campaign'],r['seed'])==(current['campaign'],current['seed']));assert {k:v for k,v in current.items()if k!='early_feast_offers'}==old,'Logging changed behavior'
  identities.append({'campaign':current['campaign'],'seed':current['seed'],'identical_except_new_observation':True})
 (R/'logging_identity.json').write_text(json.dumps(identities,indent=2))
 batch=[x for x in finished if x[0]=='price_x3'];result={**batch[0][2],'count_per_campaign':12,'seed':134000,'comparison':'conservative-price-x3','runs':[],'forecast_battles':0,'source_batches':[]}
 for _,p,d in batch:result['runs']+=d['runs'];result['forecast_battles']+=d['forecast_battles'];result['source_batches'].append({'path':str(p.relative_to(ROOT)),'sha256':sha(p)})
 assert len(result['runs'])==24;(R/'price_x3/behavior.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print('Completed24 price-only comparisons and2 logging identity controls',flush=True)
if __name__=='__main__':run()
