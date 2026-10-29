#!/usr/bin/env python3
import json,time,concurrent.futures
from pathlib import Path
from battle_sim import ROOT,read_csv
from m1_scenarios import game_data,stage_input,run_input
R=ROOT/'assets/reports/web_chapter2/calibration';R.mkdir(exist_ok=True,parents=True)
OLD=json.loads((ROOT/'assets/reports/m1/chapter1/difficulty.json').read_text())['stages']
def test_scale(scale):
 d=game_data()
 for h in d.heroes.values():
  if h['tags']=='杂兵':
   for k in ['tong','wu','zhi','su']:h[k]=round(h[k]*scale)
 out=[]
 for row in read_csv(ROOT/'data/stages.csv'):
  if row['chapter']!='1':continue
  prev=next(x for x in OLD if x['stage_id']==row['stage_id']);result={'stage_id':row['stage_id'],'target':prev['target'],'rates':{}}
  for lev in [8,11,14]:
   a,b=stage_input(d,row,prev['formation'],lev);wins=0
   for seed in range(804000,804096):wins+=run_input(d,a,b,row['terrain'],seed,{'allowDuplicates':True},False)['winner']==0
   result['rates'][str(lev)]=wins/96
  result['bracket']=result['rates']['8']>=prev['target'][0] and result['rates']['14']<=prev['target'][1];out.append(result)
 result={'scale':scale,'bracketed':sum(x['bracket'] for x in out),'stages':out};(R/f'pilot_{scale}.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True);return result
if __name__=='__main__':
 start=time.time()
 with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:results=list(pool.map(test_scale,[1.5,1.75,2,2.25,2.5]))
 (R/'npc_pilot.json').write_text(json.dumps({'results':results,'seconds':time.time()-start},indent=2));print('seconds',time.time()-start,flush=True)
