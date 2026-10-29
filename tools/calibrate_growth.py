#!/usr/bin/env python3
"""Calibrate CSV stage levels against the economy model's star/gear profiles at interpolated mean level."""
import argparse,concurrent.futures,csv,json,hashlib,math,statistics,time,copy
from pathlib import Path
from m1_scenarios import game_data,run_input,assumed_level
from battle_sim import ROOT,read_csv,wilson,base_stats
from stage_difficulty import target
R=ROOT/'assets/reports/progression/calibration';R.mkdir(parents=True,exist_ok=True)

def adjusted_team(team,mean):
 team=copy.deepcopy(team);stars=team['stars'];caps={1:35,2:50,3:65,4:80,5:95,6:100};delta=mean-statistics.mean(team['levels']);levels=[max(1,min(caps[s],l+delta)) for l,s in zip(team['levels'],stars)]
 for _ in range(20):
  left=mean*5-sum(levels)
  if abs(left)<1e-8:break
  free=[i for i,s in enumerate(stars) if (levels[i]<caps[s]-1e-8 if left>0 else levels[i]>1+1e-8)]
  if not free:raise ValueError('Insufficient star caps for profile')
  for i in free:levels[i]=max(1,min(caps[stars[i]],levels[i]+left/len(free)))
 floors=[math.floor(x+1e-8) for x in levels];remaining=round(mean*5)-sum(floors)
 for i in sorted(range(5),key=lambda i:levels[i]-floors[i],reverse=True):
  if remaining>0 and floors[i]<caps[stars[i]]:floors[i]+=1;remaining-=1
 assert remaining==0
 team['levels']=floors;return team

def power(d,team):
 total=0
 for i,id in enumerate(team['heroes']):
  items=team.get('gear',[[]]*5)[i];stats=base_stats(d.heroes[id],team['levels'][i],team['stars'][i],[d.equipment[x['equipmentId']] for x in items],[x['enhance'] for x in items],team.get('exclusives',[False]*5)[i],d.exclusives.get(id));main='int' if d.heroes[id]['troop']=='谋' else 'atk';total+=stats['hp']*.2+stats[main]*1.5+stats['def']+stats['res']+stats['speed']*10
 return math.floor(total*(1.08 if team.get('monarch') else 1)+.5)

def measure(d,row,teams,level,n,seed):
 ids=row['enemies'].split(',');camp=row['campaign'];enemy={'heroes':ids,'monarch':row['enemy_monarch'] or None,'faction':'qing' if camp=='taiping' else 'taiping','levels':[level]*5,'stars':[int(s) for s in row['enemy_stars'].split(';')],'exclusives':[int(s)>=4 for s in row['enemy_stars'].split(';')],'monarchStars':int(row['enemy_monarch_stars'] or 3),'monarchExclusive':int(row['enemy_monarch_stars'] or 3)>=4};wins=rounds=timeout=0
 for i in range(n):
  x=run_input(d,teams[i%len(teams)],enemy,row['terrain'],seed+i,{'allowDuplicates':True},False);wins+=x['winner']==0;rounds+=x['rounds'];timeout+=x['timeout']
 return {'wins':wins,'n':n,'rate':wins/n,'rounds':rounds/n,'timeout_rate':timeout/n,'wilson95':wilson(wins,n)}

def tune(args):
 row,profiles,*settings=args;settings=settings[0] if settings else {};out=Path(settings.get('out',R));out.mkdir(parents=True,exist_ok=True);started=time.time();d=game_data();sid=row['stage_id'];desired=assumed_level(int(row['chapter']),int(row['order']));teams=[adjusted_team(p['team'],desired) for p in profiles];teams.sort(key=lambda t:power(d,t));teams=[teams[min(len(teams)-1,round(i*(len(teams)-1)/3))] for i in range(4)]
 fingerprint=hashlib.sha256(((json.dumps(teams,sort_keys=True)+json.dumps({k:v for k,v in row.items() if k not in ['enemy_level','recommended_power']},sort_keys=True)+''.join(hashlib.sha256((ROOT/'data'/n).read_bytes()).hexdigest() for n in ['heroes.csv','skills.csv','bonds.csv','equipment.csv','exclusive_equipment.csv','enemy_units.csv']))+hashlib.sha256((ROOT/'tools/m1_scenarios.py').read_bytes()).hexdigest()+hashlib.sha256((ROOT/'tools/battle_sim.py').read_bytes()).hexdigest()+json.dumps(settings,sort_keys=True)).encode()).hexdigest();file=out/(sid+'.json')
 if file.exists():
  try:old=json.loads(file.read_text())
  except json.JSONDecodeError:old={}
  if old.get('fingerprint')==fingerprint and old.get('target')==list(target(row)) and old['pass']:print('resume '+sid,flush=True);return old
 offset=(0 if row['campaign']=='taiping' else 100000)+int(row['chapter'])*10000+int(row['order'])*1000;lo,hi=target(row);mid=.98 if lo>=.95 else (lo+hi)/2
 initial_stars=row['enemy_stars'];initial_monarch_stars=row['enemy_monarch_stars']
 if settings.get('raise_stars',False):
  row['enemy_stars']=';'.join(str(min(6,int(s)+1)) for s in row['enemy_stars'].split(';'))
  if row['enemy_monarch']:row['enemy_monarch_stars']=str(min(6,int(row['enemy_monarch_stars'] or 3)+1))
 if int(row['chapter'])>=3 and not settings.get('fixed_stars',False):
  for upgrade in range(6):
   probe=measure(d,row,teams,100,192,900000+offset)
   too_easy=probe['rate']>hi or (lo>=.95 and probe['rate']>=.995)
   stars=[int(s) for s in row['enemy_stars'].split(';')]
   if not too_easy or all(s==6 for s in stars):break
   row['enemy_stars']=';'.join(str(min(6,s+1)) for s in stars)
   if row['enemy_monarch']:row['enemy_monarch_stars']=str(min(6,int(row['enemy_monarch_stars'] or 3)+1))
 left,right=1.,100.;training=[]
 for _ in range(11):
  level=round((left+right)/2,1)
  if any(t['level']==level for t in training):break
  result=measure(d,row,teams,level,96,1100000+offset);training.append({'level':level,**result})
  if result['rate']>mid:left=level
  else:right=level
  if right-left<.11:break
 center=min(training,key=lambda t:abs(t['rate']-mid))['level'];fine=[{'level':l,**measure(d,row,teams,l,384,1300000+offset)} for l in sorted({round(max(1,min(100,center+i/10)),1) for i in [-2,-1,0,1,2]})];chosen=min(fine,key=lambda t:(not lo<=t['rate']<=hi,abs(t['rate']-mid)));n=2000 if int(row['chapter'])<=2 else 1000
 validation=measure(d,row,teams,chosen['level'],n,1600000+offset)
 repairs=[]
 if not lo<=validation['rate']<=hi:
  repairs.append({'original':validation,'level':chosen['level']});fine=[{'level':l,**measure(d,row,teams,l,1024,1900000+offset)} for l in sorted({round(max(1,min(100,chosen['level']+i/10)),1) for i in range(-5,6)})];chosen=min(fine,key=lambda t:(not lo<=t['rate']<=hi,abs(t['rate']-mid)));validation=measure(d,row,teams,chosen['level'],n,2200000+offset)
 if not lo<=validation['rate']<=hi:
  repairs.append({'second_holdout':validation,'level':chosen['level']})
  left,right=max(1,chosen['level']-5),min(100,chosen['level']+5)
  for _ in range(8):
   l=round((left+right)/2,1);v=measure(d,row,teams,l,768,2500000+offset)
   if v['rate']>mid:left=l
   else:right=l
   if right-left<.11:break
  center=round((left+right)/2,1);fine=[{'level':l,**measure(d,row,teams,l,1024,2800000+offset)} for l in sorted({round(max(1,min(100,center+i/10)),1) for i in [-2,-1,0,1,2]})];chosen=min(fine,key=lambda t:(not lo<=t['rate']<=hi,abs(t['rate']-mid)));validation=measure(d,row,teams,chosen['level'],n,3100000+offset)
 result={'stage_id':sid,'name':row['name'],'campaign':row['campaign'],'chapter':int(row['chapter']),'order':int(row['order']),'history_result':row['history_result'],'initial_enemy_stars':initial_stars,'initial_enemy_monarch_stars':initial_monarch_stars,'target':[lo,hi],'assumed_mean_level':desired,'profiles':teams,'recommended_power':math.floor(statistics.mean(power(d,t) for t in teams)+.5),'enemy_level':chosen['level'],'enemy_stars':[int(s) for s in row['enemy_stars'].split(';')],'enemy_monarch_stars':int(row['enemy_monarch_stars'] or 3),'training':training,'fine':fine,'validation':validation,'repairs':repairs,'pass':lo<=validation['rate']<=hi,'fingerprint':fingerprint,'seconds':time.time()-started};temp=file.with_suffix('.tmp');temp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');temp.replace(file);print(json.dumps({k:result[k] for k in ['stage_id','enemy_level','validation','pass','seconds']}),flush=True);return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--profiles',required=True);p.add_argument('--stages',type=Path,default=ROOT/'data/stages.csv');p.add_argument('--workers',type=int,default=4);p.add_argument('--chapters',default='1,2,3,4,5,6,7,8');p.add_argument('--out',type=Path,default=R);p.add_argument('--fixed-stars',action='store_true');p.add_argument('--raise-stars-for',default='',help='Explicitly approved stage IDs to raise by one star, capped at six');p.add_argument('--promote',action='store_true');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);source=json.loads(Path(a.profiles).read_text());profilemap={}
 for run in source['runs']:
  for profile in run['profiles']:profilemap.setdefault(profile['stage_id'],[]).append(profile)
 rows=[r for r in read_csv(a.stages) if r['chapter'] in a.chapters.split(',')];assert all(r['stage_id'] in profilemap for r in rows),'Some economic profiles did not reach all stages'
 raised=set(filter(None,a.raise_stars_for.split(',')));assert raised<={r['stage_id'] for r in rows},'Unknown stage ID in --raise-stars-for'
 with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers)as pool:results=list(pool.map(tune,[(r,profilemap[r['stage_id']],{'out':str(a.out),'fixed_stars':a.fixed_stars,**({'raise_stars':True} if r['stage_id'] in raised else {})}) for r in rows]))
 report={'all_pass':all(r['pass'] for r in results),'profiles_source':a.profiles,'profiles_sha256':hashlib.sha256(Path(a.profiles).read_bytes()).hexdigest(),'fixed_stars':a.fixed_stars,'stages':results};(a.out/'difficulty.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 if a.promote and report['all_pass']:
  rows=read_csv(ROOT/'data/stages.csv');lookup={r['stage_id']:r for r in results}
  for row in rows:
   if row['stage_id'] in lookup:
    for key in ['enemy_level','recommended_power']:row[key]=str(lookup[row['stage_id']][key])
    row['enemy_stars']=';'.join(map(str,lookup[row['stage_id']]['enemy_stars']))
    if row['enemy_monarch']:row['enemy_monarch_stars']=str(lookup[row['stage_id']]['enemy_monarch_stars'])
  with (ROOT/'data/stages.csv').open('w',newline='',encoding='utf-8')as f:w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
 print('all_pass',report['all_pass'],flush=True)
