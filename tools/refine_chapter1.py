#!/usr/bin/env python3
import json,concurrent.futures,csv,shutil
from battle_sim import ROOT,read_csv
from m1_scenarios import game_data
from tune_chapter1 import measure,R

def refine(result):
 d=game_data();row=next(r for r in read_csv(ROOT/'data/stages.csv') if r['stage_id']==result['stage_id']);lo,hi=result['target'];mid=(lo+hi)/2
 training=[{'level':level,**measure(d,row,result['formation'],level,1000,715000)} for level in range(max(1,result['enemy_level']-2),result['enemy_level']+4)]
 chosen=min(training,key=lambda q:(0 if lo<=q['rate']<=hi else min(abs(q['rate']-lo),abs(q['rate']-hi))+1,abs(q['rate']-mid)))
 validation=measure(d,row,result['formation'],chosen['level'],2000,716000)
 result={**result,'prior_validation':result['validation'],'refinement_training':training,'enemy_level':chosen['level'],'validation_seed':716000,'validation':validation,'pass':lo<=validation['rate']<=hi}
 (R/f"{row['stage_id']}.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False),flush=True);return result
if __name__=='__main__':
 source=R/'difficulty.json';shutil.copy2(source,R/'difficulty_round1.json');x=json.loads(source.read_text());failed=[r for r in x['stages'] if not r['pass']]
 with concurrent.futures.ProcessPoolExecutor(max_workers=3) as pool:fixed={r['stage_id']:r for r in pool.map(refine,failed)}
 x['stages']=[fixed.get(r['stage_id'],r) for r in x['stages']];x['all_pass']=all(r['pass'] for r in x['stages']);source.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n');print('all_pass',x['all_pass'],flush=True)
 if x['all_pass']:
  p=ROOT/'data/stages.csv';rows=read_csv(p)
  for row in rows:row['enemy_level']=str(next(r['enemy_level'] for r in x['stages'] if r['stage_id']==row['stage_id']))
  with p.open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
  print('promoted enemy_level only',flush=True)
