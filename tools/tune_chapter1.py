#!/usr/bin/env python3
"""M1: exhaustive7P5 screening, independent tuning and held-out difficulty tests."""
import csv,json,itertools,concurrent.futures,hashlib,statistics
from battle_sim import ROOT,Battle,read_csv,wilson
from m1_scenarios import game_data,stage_input,run_input
R=ROOT/'assets/reports/m1/chapter1';R.mkdir(parents=True,exist_ok=True)
def target(row):
 o=int(row['order'])
 return (.95,1) if o==1 else (.5,.65) if row['stage_id']=='qing_1_3' else (.85,.95) if o<4 else (.7,.85) if o<6 else (.55,.7)
def measure(d,row,lineup,level,n,seed):
 a,b=stage_input(d,row,lineup,level);wins=0;turns=0
 for i in range(n):
  x=run_input(d,a,b,row['terrain'],seed+i,{'allowDuplicates':True},False);wins+=x['winner']==0;turns+=x['rounds']
 return {'wins':wins,'n':n,'rate':wins/n,'rounds':turns/n,'wilson95':wilson(wins,n)}
def pilot_score(d,row,lineup,level,seeds):
 a,b=stage_input(d,row,lineup,level);wins=0;margin=0
 for seed in seeds:
  battle=Battle(d,[a['heroes'],b['heroes']],lords=(a['monarch'],b['monarch']),assigned=(a['faction'],b['faction']),terrain=row['terrain'],seed=seed,unit_levels=[a['levels'],b['levels']],unit_stars=[a['stars'],b['stars']],allow_duplicates=True)
  x=battle.run();wins+=x['winner']==0
  margin+=sum(u.hp/u.max_hp for u in battle.teams[0].actors)-sum(u.hp/u.max_hp for u in battle.teams[1].actors)
 return wins/len(seeds)+margin/len(seeds)*.001

def tune(row):
 d=game_data();cards=next(r['cards'].split(';') for r in read_csv(ROOT/'data/starter_cards.csv') if r['campaign']==row['campaign']);low,high=target(row);mid=(low+high)/2 if low<.95 else .985
 # Find a competitive level, then screen every legal ordered5-person formation.
 lineup=cards[:5];level=int(float(row['enemy_level']));pilot=[]
 for level in range(5,51):
  x=measure(d,row,lineup,level,24,710000);pilot.append({'level':level,**x})
  if x['rate']<.7:break
 ranked=[]
 for team in itertools.permutations(cards,5):ranked.append((pilot_score(d,row,team,level,[711000+i for i in range(4)]),team))
 ranked.sort(key=lambda q:-q[0]);finalists=[]
 for _,team in ranked[:24]:finalists.append((measure(d,row,team,level,96,712000)['rate'],team))
 finalists.sort(key=lambda q:-q[0]);lineup=list(finalists[0][1]);training=[]
 # Independent tune seeds, without looking at the final held-out battles.
 for lev in range(1,61):
  x=measure(d,row,lineup,lev,256,713000);training.append({'level':lev,**x})
  if x['rate']<low-.12:break
 chosen=min(training,key=lambda q:(0 if low<=q['rate']<=high else min(abs(q['rate']-low),abs(q['rate']-high))+1,abs(q['rate']-mid)))
 validation=measure(d,row,lineup,chosen['level'],2000,714000)
 result={'stage_id':row['stage_id'],'name':row['name'],'campaign':row['campaign'],'target':[low,high],'original_level':int(float(row['enemy_level'])),'enemy_level':chosen['level'],'formation':lineup,'ordered_formations_screened':len(ranked),'screening_seeds':[711000+i for i in range(4)],'finalist_n':96,'training':training,'validation_seed':714000,'validation':validation,'pass':low<=validation['rate']<=high,'claim':'Best empirical formation after exhaustive2520-order screening and24-finalist recheck; not a proof of theoretical optimum'}
 (R/f"{row['stage_id']}.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['stage_id','enemy_level','formation','validation','pass']},ensure_ascii=False),flush=True);return result
if __name__=='__main__':
 rows=read_csv(ROOT/'data/stages.csv');(R/'stages_before.csv').write_bytes((ROOT/'data/stages.csv').read_bytes())
 with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:results=list(pool.map(tune,rows))
 out={'all_pass':all(r['pass'] for r in results),'stages':results};(R/'difficulty.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print('all_pass',out['all_pass'],flush=True)
 # Do not promote unmet levels silently; a separate review handles coarse integer steps.
