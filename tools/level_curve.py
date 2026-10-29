#!/usr/bin/env python3
"""v0.4.2 fixed-calendar curve, scoped late-stage calibration and paired cohorts."""
import csv,json,statistics,subprocess,concurrent.futures,shutil,hashlib,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'assets/reports/economy_v042'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def writecsv(p,rows,fields=None):
 with Path(p).open('w',newline='',encoding='utf-8')as f:
  w=csv.DictWriter(f,fieldnames=fields or list(rows[0]));w.writeheader();w.writerows(rows)
def calendar():
 out=R/'calendar';inp=out/'inputs';inp.mkdir(parents=True,exist_ok=True)
 for src in ['tools/target_calendar.ts','tools/target_calendar_rules.ts','tools/player_policy.ts','app/src/core/progression.ts','app/src/core/formation.ts']:
  shutil.copy2(ROOT/src,inp/Path(src).name)
 def job(item):
  camp,seed=item;name=f'{camp}_{seed}';p=out/(name+'.json')
  with(out/(name+'.log')).open('w')as f:
   subprocess.run(['node','--import','./app/node_modules/tsx/dist/loader.mjs','tools/target_calendar.ts',f'camp={camp}',f'seed={seed}','n=1',f'tables={inp}/tables.json',f'out={p}'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
  return read(p)['runs'][0]
 jobs=[(camp,134000+i+(1000000 if camp=='qing'else 0))for camp in ['taiping','qing']for i in range(12)]
 with concurrent.futures.ThreadPoolExecutor(max_workers=6)as pool:runs=list(pool.map(job,jobs))
 report={'mode':'fixed-target-calendar','feast':'off','runs':runs};(out/'profiles.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('Calendar captured24 accounts',flush=True);prepare()
def prepare():
 report=read(R/'calendar/profiles.json');assert len(report['runs'])==24;details=[];overrides=[]
 ids=[s['stage_id']for s in read(R/'calendar/inputs/tables.json')['stages']if s['chapter']>=5]
 for sid in ids:
  samples=[{'seed':r['seed'],**p}for r in report['runs']for p in r['profiles']if p['stage_id']==sid];assert len(samples)==12
  for p in samples:assert p['cleared_before']==(p['chapter']-1)*6+p['order']-1 and sid not in p['completed_rewards']
  mean=round(statistics.median(p['mean_level']for p in samples),8)
  overrides.append({'stage_id':sid,'assumed_level':mean,'source_accounts':12,'source':'v0.4.2 target-calendar median; no feast; 12 same-faction accounts'})
  details.append({'stage_id':sid,'target_day':samples[0]['day'],'median_level':mean,'minimum_level':min(p['mean_level']for p in samples),'maximum_level':max(p['mean_level']for p in samples),'samples':[{'seed':p['seed'],'mean_level':p['mean_level'],'mean_stars':p['mean_stars'],'day':p['day']}for p in samples]})
 writecsv(R/'candidate_stage_level_overrides.csv',overrides);(R/'curve.json').write_text(json.dumps(details,ensure_ascii=False,indent=2));writecsv(R/'curve.csv',[{k:v for k,v in d.items()if k!='samples'}for d in details]);tables=read(R/'calendar/inputs/tables.json');tables['stage_level_overrides']=overrides;(R/'candidate_tables.json').write_text(json.dumps(tables,ensure_ascii=False));print('48 stage medians fixed',flush=True)
def calibrate():
 out=R/'calibration';out.mkdir(exist_ok=True);ids=[r['stage_id']for r in read(R/'curve.json')]
 def job(sid):
  with(out/(sid+'.log')).open('w')as f:
   subprocess.run(['node','--import','./app/node_modules/tsx/dist/loader.mjs','tools/curve_calibrate.ts',f'profiles={R}/calendar/profiles.json',f'tables={R}/candidate_tables.json',f'stage={sid}','n=2400',f'out={out}'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
  x=read(out/(sid+'.json'));print(sid,x['pass'],x['enemy_level'],round(x['validation']['rate'],4),flush=True);return x
 with concurrent.futures.ThreadPoolExecutor(max_workers=6)as pool:stages=list(pool.map(job,ids))
 report={'all_pass':all(x['pass']for x in stages),'stages':stages};(out/'difficulty.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));assert report['all_pass'],'Difficulty targets not all met';promote()
def promote():
 report=read(R/'calibration/difficulty.json');assert report['all_pass']and len(report['stages'])==48
 rows=list(csv.DictReader((R/'v040_stages.csv').open()));lookup={r['stage_id']:r for r in report['stages']}
 for row in rows:
  if int(row['chapter'])<5:continue
  x=lookup[row['stage_id']];assert row['enemies'].split(',')==x['enemies']and row['enemy_monarch']==x['enemy_monarch']
  row.update(enemy_level=str(x['enemy_level']),enemy_stars=';'.join(map(str,x['enemy_stars'])),enemy_monarch_stars=str(x['enemy_monarch_stars'])if row['enemy_monarch']else'',recommended_power=str(x['recommended_power']))
 writecsv(ROOT/'data/stages.csv',rows);shutil.copy2(R/'candidate_stage_level_overrides.csv',ROOT/'data/stage_level_overrides.csv');subprocess.run(['python3','tools/export_data.py'],cwd=ROOT,check=True)
 print('Promoted late48 stages; first48 kept from v0.4.0',flush=True)
def replay():
 from joint_cohort import run
 def job(profile):return run(R/profile/'replay',12,134000,12,3,3,'battle',profile)
 with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:list(pool.map(job,['conservative','aggressive']))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['calendar','prepare','calibrate','promote','replay','all']);a=p.parse_args()
 if a.mode=='all':calendar();calibrate();replay()
 else:globals()[a.mode]()
