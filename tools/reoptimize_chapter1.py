#!/usr/bin/env python3
import json,itertools,concurrent.futures,csv,shutil
from battle_sim import ROOT,read_csv
from m1_scenarios import game_data
from tune_chapter1 import measure,pilot_score,R
LEVELS={'tp_1_5':37,'tp_1_6':39,'qing_1_3':50}
def run(result):
 d=game_data();row=next(r for r in read_csv(ROOT/'data/stages.csv') if r['stage_id']==result['stage_id']);cards=next(r['cards'].split(';') for r in read_csv(ROOT/'data/starter_cards.csv') if r['campaign']==row['campaign']);level=LEVELS[row['stage_id']]
 ranked=sorted(((pilot_score(d,row,team,level,[717000+i for i in range(8)]),team) for team in itertools.permutations(cards,5)),key=lambda x:-x[0]);finalists=[]
 for _,team in ranked[:32]:finalists.append({'formation':list(team),**measure(d,row,team,level,512,718000)})
 finalists.sort(key=lambda q:-q['rate']);lineup=finalists[0]['formation'];lo,hi=result['target'];v=measure(d,row,lineup,level,2000,719000)
 result={**result,'reoptimized_at_level':level,'reoptimized_finalists':finalists,'formation':lineup,'enemy_level':level,'validation':v,'validation_seed':719000,'pass':lo<=v['rate']<=hi};(R/f"{row['stage_id']}.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'id':row['stage_id'],'level':level,'formation':lineup,'validation':v,'pass':result['pass']},ensure_ascii=False),flush=True);return result
if __name__=='__main__':
 p=R/'difficulty.json';shutil.copy2(p,R/'difficulty_round2.json');x=json.loads(p.read_text())
 with concurrent.futures.ProcessPoolExecutor(max_workers=3) as pool:changed={r['stage_id']:r for r in pool.map(run,[r for r in x['stages'] if not r['pass']])}
 x['stages']=[changed.get(r['stage_id'],r) for r in x['stages']];x['all_pass']=all(r['pass'] for r in x['stages']);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n');print('all_pass',x['all_pass'],flush=True)
 if x['all_pass']:
  p=ROOT/'data/stages.csv';rows=read_csv(p)
  for row in rows:row['enemy_level']=str(next(r['enemy_level'] for r in x['stages'] if r['stage_id']==row['stage_id']))
  with p.open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
  print('promoted enemy_level only',flush=True)
