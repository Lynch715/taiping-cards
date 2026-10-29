#!/usr/bin/env python3
"""v0.4.1: eight scoped encounters only, fixed24 accounts and one joint chapter acceptance rule."""
import csv,json,hashlib,statistics,subprocess,concurrent.futures,shutil,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'assets/reports/economy_v041';BASE=ROOT/'assets/reports/joint_v2/round04/replay/behavior.json'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def writecsv(p,rows,fields=None):
 with Path(p).open('w',newline='',encoding='utf-8')as f:w=csv.DictWriter(f,fieldnames=fields or list(rows[0]));w.writeheader();w.writerows(rows)
def prepare():
 old=read(BASE);new=read(R/'baseline_capture/behavior.json');index={(r['campaign'],r['seed']):r for r in new['runs']};compared=[]
 for run in old['runs']:
  actual=index[run['campaign'],run['seed']]
  assert {k:v for k,v in actual.items()if k!='first_challenges'}==run,('Baseline behavior changed',run['campaign'],run['seed'])
  assert len(actual['first_challenges'])==48
  compared.append({'campaign':run['campaign'],'seed':run['seed'],'identical_except_new_records':True})
 (R/'baseline_identity.json').write_text(json.dumps(compared,indent=2))
 scope=read(R/'scope.json')['targets'];levels=[];details={}
 for sid in scope:
  samples=[{'seed':r['seed'],**p}for r in new['runs']for p in r['first_challenges']if p['stage_id']==sid];assert len(samples)==12
  median=round(statistics.median(s['mean_level']for s in samples),8);levels.append({'stage_id':sid,'assumed_level':median,'source_accounts':12,'source':'v0.4.0 first challenge median; baseline_capture/behavior.json'});details[sid]={'median':median,'samples':[{'seed':s['seed'],'day':s['day'],'mean_level':s['mean_level'],'mean_stars':s['mean_stars']}for s in samples]}
 writecsv(R/'candidate_stage_level_overrides.csv',levels);candidate=read(R/'baseline_capture/inputs/tables.json');candidate['stage_level_overrides']=levels;(R/'candidate_tables.json').write_text(json.dumps(candidate,ensure_ascii=False,indent=2));(R/'first_challenge_medians.json').write_text(json.dumps(details,ensure_ascii=False,indent=2));
 source={**new,'runs':[{**r,'profiles':r['first_challenges']}for r in new['runs']]};(R/'first_challenge_profiles.json').write_text(json.dumps(source,ensure_ascii=False))
 print('First-challenge medians:',{k:v['median']for k,v in details.items()},flush=True)
def calibrate(n=2000):
 out=R/'calibration';out.mkdir(exist_ok=True);scope=read(R/'scope.json')['targets']
 def job(sid):
  with(out/(sid+'.log')).open('w')as f:subprocess.run(['node','--import','./app/node_modules/tsx/dist/loader.mjs','tools/closeout_calibrate.ts',f'profiles={R}/first_challenge_profiles.json',f'tables={R}/candidate_tables.json',f'stage={sid}',f'n={n}',f'out={out}'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=6)as pool:list(pool.map(job,scope))
 records=[read(out/(sid+'.json'))for sid in scope];report={'all_pass':all(r['pass']for r in records),'stages':records};(out/'difficulty.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('Calibration',[(r['stage_id'],r['pass'],r['enemy_level'],r['validation']['rate'])for r in records],flush=True);return report
def promote(report):
 assert report['all_pass'];p=ROOT/'data/stages.csv';rows=list(csv.DictReader(p.open()));old={r['stage_id']:r for r in csv.DictReader((R/'before/data/stages.csv').open())};lookup={r['stage_id']:r for r in report['stages']}
 for row in rows:
  sid=row['stage_id']
  if sid not in lookup:assert row==old[sid];continue
  x=lookup[sid];assert x['enemies']==row['enemies'].split(',')and x['enemy_monarch']==row['enemy_monarch'];row.update(enemy_level=str(x['enemy_level']),enemy_stars=';'.join(map(str,x['enemy_stars'])),enemy_monarch_stars=str(x['enemy_monarch_stars'])if row['enemy_monarch']else'',recommended_power=str(x['recommended_power']))
 writecsv(p,rows);shutil.copy2(R/'candidate_stage_level_overrides.csv',ROOT/'data/stage_level_overrides.csv')
 for name,h in read(R/'before/manifest.json').items():
  if name.startswith('data/')and name!='data/stages.csv':assert sha(ROOT/name)==h,('Protected table changed',name)
 subprocess.run(['python3','tools/export_data.py'],cwd=ROOT,check=True);print('Promoted scoped stages; protected tables unchanged',flush=True)
def joint_metrics(data):
 rows=[]
 for camp in ['taiping','qing']:
  runs=[r for r in data['runs']if r['campaign']==camp]
  for ch in range(1,9):
   stats=[c for r in runs for c in r['chapters']if c['chapter']==ch];target=stats[0]['target_days']if stats else None;mean=statistics.mean(c['duration']for c in stats)if stats else None;wait=max((c['max_stage_wait']for c in stats),default=None);passed=len(runs)==12 and len(stats)==12 and all(r['cleared']==48 for r in runs)and target*.75<=mean<=target*1.25 and wait<=2
   rows.append({'campaign':camp,'chapter':ch,'accounts':len(stats),'target_days':target,'mean_days':mean,'max_stage_wait':wait,'pass':passed})
 return {'chapters':rows,'joint_pass_count':sum(r['pass']for r in rows),'total':16,'all_pass':all(r['pass']for r in rows)}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','calibrate','promote']);p.add_argument('--n',type=int,default=2000);a=p.parse_args()
 if a.mode=='prepare':prepare()
 elif a.mode=='calibrate':calibrate(a.n)
 else:promote(read(R/'calibration/difficulty.json'))
