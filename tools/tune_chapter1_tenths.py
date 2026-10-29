#!/usr/bin/env python3
"""User-approved0.1 enemy_level granularity; no hero/skill changes."""
import json,csv,concurrent.futures,shutil
from battle_sim import ROOT,read_csv
from m1_scenarios import game_data
from tune_chapter1 import R,measure
RANGES={'tp_1_5':[36+i/10 for i in range(1,11)],'tp_1_6':[38+i/10 for i in range(1,11)]}
def run(x):
 d=game_data();row=next(r for r in read_csv(ROOT/'data/stages.csv') if r['stage_id']==x['stage_id']);lo,hi=x['target'];mid=(lo+hi)/2
 train=[{'level':lev,**measure(d,row,x['formation'],lev,1000,722000)} for lev in RANGES[x['stage_id']]];best=min(train,key=lambda q:abs(q['rate']-mid));v=measure(d,row,x['formation'],best['level'],3000,723000)
 result={**x,'approved_granularity':.1,'tenth_training':train,'enemy_level':best['level'],'validation_seed':723000,'validation':v,'pass':lo<=v['rate']<=hi};(R/f"{x['stage_id']}.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'id':x['stage_id'],'level':best['level'],'validation':v,'pass':result['pass']},ensure_ascii=False),flush=True);return result
if __name__=='__main__':
 p=R/'difficulty.json';shutil.copy2(p,R/'difficulty_integer_rounds.json');allx=json.loads(p.read_text());todo=[x for x in allx['stages'] if x['stage_id'] in RANGES]
 with concurrent.futures.ProcessPoolExecutor(max_workers=2) as pool:changed={r['stage_id']:r for r in pool.map(run,todo)}
 allx['stages']=[changed.get(x['stage_id'],x) for x in allx['stages']];allx['all_pass']=all(x['pass'] for x in allx['stages']);p.write_text(json.dumps(allx,ensure_ascii=False,indent=2)+'\n');print('all_pass',allx['all_pass'],flush=True)
 if allx['all_pass']:
  p=ROOT/'data/stages.csv';rows=read_csv(p)
  for row in rows:row['enemy_level']=str(next(x['enemy_level'] for x in allx['stages'] if x['stage_id']==row['stage_id']))
  with p.open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
  print('promoted12 enemy_levels',flush=True)
