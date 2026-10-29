#!/usr/bin/env python3
"""Economic tuning driver. The player model executes the actual shipped TS economy/battle code."""
import argparse,csv,json,subprocess,statistics,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'assets/reports/progression';R.mkdir(exist_ok=True)
def read(name):return list(csv.DictReader((ROOT/'data'/name).open(encoding='utf-8-sig',newline='')))
def write(name,rows):
 with (ROOT/'data'/name).open('w',newline='',encoding='utf-8')as f:w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
def model(mode,n,seed,label,attempts=3,chapters=8,legacy=False):
 subprocess.run(['python3',str(ROOT/'tools/export_data.py')],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
 target=R if legacy else ROOT/'assets/reports/joint_v2';target.mkdir(parents=True,exist_ok=True);out=target/(label+'.json');log=target/(label+'.log')
 with log.open('w')as f:subprocess.run(['node','--import','./app/node_modules/tsx/dist/loader.mjs','tools/economy_behavior.ts' if legacy else 'tools/joint_behavior.ts',f'mode={mode}',f'n={n}',f'seed={seed}',f'attempts={attempts}',f'chapters={chapters}',f'out={out}'],cwd=ROOT,check=True,stdout=f,stderr=subprocess.STDOUT)
 return json.loads(out.read_text())
def summarize(result):
 if result.get('runs') and 'entries' in result['runs'][0]:
  from joint_metrics import summarize as joint_summary
  return joint_summary(result)
 groups=[]
 for camp in ['taiping','qing']:
  for ch in range(1,9):
   rows=[c for r in result['runs'] if r['campaign']==camp for c in r['chapters'] if c['chapter']==ch]
   if not rows:groups.append({'campaign':camp,'chapter':ch,'n':0,'pass':False});continue
   target=rows[0]['target_days'];dur=[r['duration'] for r in rows];median=statistics.median(dur);means=statistics.mean(dur)
   groups.append({'campaign':camp,'chapter':ch,'n':len(rows),'target':target,'mean_days':means,'median_days':median,'min_days':min(dur),'max_days':max(dur),'pace_pass':target*.75<=means<=target*1.25,'within_pace_fraction':sum(target*.75<=x<=target*1.25 for x in dur)/len(dur),'max_stage_wait':max(r['max_stage_wait'] for r in rows),'exp_remaining_ratio_mean':statistics.mean(r['exp_remaining_ratio'] for r in rows),'exp_remaining_ratio_max':max(r['exp_remaining_ratio'] for r in rows),'silver_min':min(r['remaining']['silver'] for r in rows),'iron_min':min(r['remaining']['iron'] for r in rows),'stars_ready':all(r['stars_ready'] for r in rows),'pass':target*.75<=means<=target*1.25 and len(rows)==result['count_per_campaign'] and max(r['max_stage_wait'] for r in rows)<=2 and statistics.mean(r['exp_remaining_ratio'] for r in rows)<.2 and all(r['stars_ready'] for r in rows)})
 return groups
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--tune',action='store_true');p.add_argument('--legacy',action='store_true');p.add_argument('--mode',default='battle',choices=['profile','battle']);p.add_argument('--n',type=int,default=12);p.add_argument('--seed',type=int,default=42000);p.add_argument('--label',default='economy');p.add_argument('--chapters',type=int,default=8);a=p.parse_args()
 if not a.legacy and a.tune:
  subprocess.run(['python3',str(ROOT/'tools/joint_tune.py'),'--n',str(a.n),'--seed',str(a.seed),'--label',a.label,'--mode',a.mode,'--calibrate'],cwd=ROOT,check=True);raise SystemExit
 if not a.tune:
  data=model(a.mode,a.n,a.seed,a.label,chapters=a.chapters,legacy=a.legacy);groups=summarize(data);((R if a.legacy else ROOT/'assets/reports/joint_v2')/(a.label+'_summary.json')).write_text(json.dumps(groups,ensure_ascii=False,indent=2));print(json.dumps(groups,ensure_ascii=False));raise SystemExit
 p.error('Historical tuning is read-only; use the v0.2 joint tuner without --legacy')
