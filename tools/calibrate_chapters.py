#!/usr/bin/env python3
"""Ordered-roster search, 0.1-level tuning and independent validation for chapters 1/2."""
import argparse,csv,json,itertools,time,hashlib,concurrent.futures
from battle_sim import ROOT,Battle,read_csv,wilson
from m1_scenarios import game_data,stage_input,run_input
R=ROOT/'assets/reports/web_chapter2/calibration';R.mkdir(exist_ok=True,parents=True)
def target(row):
 o=int(row['order']);sid=row['stage_id']
 if sid in {'qing_1_3','qing_2_3','qing_2_5'}:return .5,.65
 return (.95,1) if o==1 else (.85,.95) if o<4 else (.7,.85) if o<6 else (.55,.7)
def available(row):
 own=next(s for s in read_csv(ROOT/'data/starter_cards.csv') if s['campaign']==row['campaign'])
 previous=[r for r in read_csv(ROOT/'data/stages.csv') if r['campaign']==row['campaign'] and (int(r['chapter']),int(r['order']))<(int(row['chapter']),int(row['order']))]
 return list(dict.fromkeys(own['cards'].split(';')+[r['reward_unlock'] for r in previous if r['reward_unlock']]))
def measure(d,row,team,level,n,seed):
 a,b=stage_input(d,row,team,level);wins=0;rounds=0;timeouts=0
 for i in range(n):
  x=run_input(d,a,b,row['terrain'],seed+i,{'allowDuplicates':True},False);wins+=x['winner']==0;rounds+=x['rounds'];timeouts+=x['timeout']
 return {'wins':wins,'n':n,'rate':wins/n,'rounds':rounds/n,'timeout_rate':timeouts/n,'wilson95':wilson(wins,n)}
def score(d,row,team,level,seeds):
 a,b=stage_input(d,row,team,level);wins=0;margin=0
 for seed in seeds:
  battle=Battle(d,[a['heroes'],b['heroes']],lords=(a['monarch'],b['monarch']),assigned=(a['faction'],b['faction']),terrain=row['terrain'],seed=seed,unit_levels=[a['levels'],b['levels']],unit_stars=[a['stars'],b['stars']],allow_duplicates=True)
  x=battle.run();wins+=x['winner']==0;margin+=sum(u.hp/u.max_hp for u in battle.teams[0].actors)-sum(u.hp/u.max_hp for u in battle.teams[1].actors)
 return wins/len(seeds)+margin/len(seeds)*.002

def tune(row):
 start=time.time();d=game_data();cards=available(row);sid=row['stage_id'];number=int(row['chapter']);offset=(0 if row['campaign']=='taiping' else 20000)+number*1000+int(row['order'])*100
 lo,hi=target(row);mid=.98 if lo>=.95 else (lo+hi)/2
 fingerprint=hashlib.sha256((json.dumps(cards)+''.join(hashlib.sha256((ROOT/'data'/n).read_bytes()).hexdigest() for n in ['heroes.csv','skills.csv','bonds.csv','enemy_units.csv'])).encode()).hexdigest()
 file=R/(sid+'.json')
 if file.exists():
  saved=json.loads(file.read_text())
  if saved.get('fingerprint')==fingerprint and saved.get('pass'):print('resume '+sid,flush=True);return saved
 old=json.loads((ROOT/'assets/reports/m1/chapter1/difficulty.json').read_text())['stages'];team=next(x['formation'] for x in old if x['stage_id']==(sid if number==1 else row['campaign'].replace('taiping','tp')+'_1_6'))
 # Find a challenging screening level instead of ranking thousands of guaranteed wins.
 low,high=(8.,14.) if number==1 else (10.,55.)
 left,right=low,high
 for _ in range(6):
  lev=round((left+right)/2,1);m=measure(d,row,team,lev,32,810000+offset)
  if m['rate']>.7:left=lev
  else:right=lev
 rank_level=round((left+right)/2,1)
 ranked=sorted(((score(d,row,t,rank_level,[820000+offset+i for i in range(2)]),t) for t in itertools.permutations(cards,5)),key=lambda q:-q[0])
 print(json.dumps({'stage':sid,'phase':'screened','pool':len(cards),'ordered':len(ranked),'rank_level':rank_level}),flush=True)
 finalists=[]
 for _,t in ranked[:32]:finalists.append({'formation':list(t),**measure(d,row,t,rank_level,96,830000+offset)})
 finalists.sort(key=lambda q:-q['rate']);deep=[]
 for c in finalists[:8]:deep.append({'formation':c['formation'],**measure(d,row,c['formation'],rank_level,512,840000+offset)})
 deep.sort(key=lambda q:-q['rate']);team=deep[0]['formation']
 # Training and final holdout seeds are disjoint from all screening seeds.
 left,right=low,high;training=[]
 for _ in range(10):
  lev=round((left+right)/2,1)
  if any(x['level']==lev for x in training):break
  m=measure(d,row,team,lev,256,850000+offset);training.append({'level':lev,**m})
  if m['rate']>mid:left=lev
  else:right=lev
  if right-left<.11:break
 center=min(training,key=lambda x:abs(x['rate']-mid))['level'];levels=sorted({round(min(high,max(low,center+i/10)),1) for i in [-2,-1,0,1,2]})
 fine=[{'level':lev,**measure(d,row,team,lev,1000,860000+offset)} for lev in levels]
 chosen=min(fine,key=lambda x:(0 if lo<=x['rate']<=hi else 1,abs(x['rate']-mid)))
 validation=measure(d,row,team,chosen['level'],2000,870000+offset)
 result={'stage_id':sid,'name':row['name'],'campaign':row['campaign'],'chapter':number,'order':int(row['order']),'player_level':10 if number==1 else 20,'target':[lo,hi],'pool':cards,'ordered_formations_screened':len(ranked),'rank_level':rank_level,'screen_seeds':[820000+offset+i for i in range(2)],'finalists':finalists,'deep_finalists':deep,'formation':team,'training':training,'fine_training':fine,'enemy_level':chosen['level'],'validation':validation,'validation_seed':870000+offset,'pass':lo<=validation['rate']<=hi,'fingerprint':fingerprint,'seconds':time.time()-start,'claim':'Best empirical candidate after exhaustive ordered-pool screening and independent finalist checks; no theoretical optimum claim'}
 file.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['stage_id','enemy_level','validation','pass','seconds']}),flush=True);return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--chapter',type=int,choices=[1,2],required=True);p.add_argument('--workers',type=int,default=4);p.add_argument('--promote',action='store_true');a=p.parse_args()
 rows=[r for r in read_csv(ROOT/'data/stages.csv') if int(r['chapter'])==a.chapter]
 with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers)as pool:results=list(pool.map(tune,rows))
 report={'chapter':a.chapter,'all_pass':all(x['pass'] for x in results),'stages':results};(R/f'chapter{a.chapter}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 if a.promote and report['all_pass']:
  path=ROOT/'data/stages.csv';allrows=read_csv(path);levels={x['stage_id']:x['enemy_level'] for x in results}
  for row in allrows:
   if row['stage_id'] in levels:row['enemy_level']=str(levels[row['stage_id']])
  with path.open('w',encoding='utf-8',newline='')as f:w=csv.DictWriter(f,fieldnames=allrows[0]);w.writeheader();w.writerows(allrows)
  print('promoted chapter '+str(a.chapter)+' enemy_level only',flush=True)
 print('all_pass',report['all_pass'],flush=True)
