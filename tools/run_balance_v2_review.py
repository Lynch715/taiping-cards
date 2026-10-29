#!/usr/bin/env python3
"""Run a frozen before/after holdout, equipment profiles and39 item ablations."""
import argparse,concurrent.futures,hashlib,json,subprocess,sys,time
from pathlib import Path
from battle_sim import ROOT,Data,evaluate,exclusive_skills
from balance_diagnostics import exclusive_diagnostics,monarch_choices,constraint_audit
R=ROOT/'assets/reports/balance_v2'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def runtime_hashes():return {n:sha(ROOT/'tools'/n) for n in ['battle_sim.py','balance_diagnostics.py','run_balance_v2_review.py']}
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def worker(kind,phase,after_dir):
 directory=R/'before/data' if phase=='before' else Path(after_dir);d=Data(directory)
 for h in d.heroes.values():
  *_,unknown=exclusive_skills(d,h,True)
  if unknown:raise ValueError((h['id'],unknown))
 runtime=runtime_hashes();start=time.time()
 if kind=='main':
  x=evaluate(d,n=2000,lineups=1600,opponents=16,seed=20263199);save(R/f'{phase}_metrics.json',x)
 elif kind=='exclusives':
  x=exclusive_diagnostics(d,n=200,duels=120,seed=20263191);x['runtime_sha256']=runtime;save(R/f'{phase}_exclusives.json',x)
 elif kind=='monarchs':
  x=monarch_choices(d,formations=150,opponents=10,seed=20263193);x['runtime_sha256']=runtime;save(R/f'{phase}_monarch_choices.json',x)
 elif kind=='sensitivity':
  total=0
  for gear in ['圣兵','勇营','洋械','铁骑','江防',None]:
   x=evaluate(d,n=500,lineups=200,opponents=6,seed=20263192,stars=3 if gear else 4,gear_set=gear,use_exclusives=gear is None)
   save(R/'sensitivity'/f'{phase}_{gear or "4star"}.json',x);total+=x['total_games'];print(phase,gear or '4star',x['total_games'],'games',flush=True)
  x={'total_games':total}
 assert runtime==runtime_hashes(),'Numerical runtime changed during a frozen job'
 print(json.dumps(dict(phase=phase,kind=kind,games=x['total_games'],seconds=round(time.time()-start,2)),ensure_ascii=False),flush=True)
 return x['total_games']

def main():
 p=argparse.ArgumentParser();p.add_argument('--after-dir',type=Path,default=R/'trials/12_cixi_policy/data');p.add_argument('--worker',choices=['main','exclusives','monarchs','sensitivity']);p.add_argument('--phase',choices=['before','after']);a=p.parse_args()
 if a.worker:worker(a.worker,a.phase,a.after_dir);return
 assert constraint_audit(Data(a.after_dir))['all_valid']
 protocol=dict(holdout_seeds=dict(main=20263199,exclusives=20263191,sensitivity=20263192,monarchs=20263193),after_dir=str(a.after_dir),main=dict(n=2000,lineups=1600,opponents=16),exclusives=dict(team_pairs=200,duel_pairs=120),monarch_selection_target='Per-faction top10% lineups, cutoff ties split; explicitly selected by user',runtime_sha256=runtime_hashes(),source_sha256={phase:{q.name:sha(q) for q in directory.glob('*.csv')} for phase,directory in [('before',R/'before/data'),('after',a.after_dir)]})
 save(R/'frozen_protocol.json',protocol);jobs=[(kind,phase) for kind in ['main','exclusives','sensitivity','monarchs'] for phase in ['before','after']]
 def launch(job):
  kind,phase=job;log=R/f'holdout_{phase}_{kind}.log'
  with log.open('w') as stream:subprocess.run([sys.executable,__file__,'--worker',kind,'--phase',phase,'--after-dir',str(a.after_dir)],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,check=True)
  print('DONE',phase,kind,flush=True);return dict(phase=phase,kind=kind,log=str(log.relative_to(ROOT)))
 completed=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
  futures=[pool.submit(launch,j) for j in jobs]
  for f in concurrent.futures.as_completed(futures):completed.append(f.result())
 assert protocol['runtime_sha256']==runtime_hashes()
 save(R/'holdout_jobs.json',completed);print('All8 frozen jobs complete',flush=True)
if __name__=='__main__':main()
