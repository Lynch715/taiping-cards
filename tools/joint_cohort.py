#!/usr/bin/env python3
"""Independent, frozen-input account batches; no tuning and no source-data writes."""
import argparse,json,subprocess,concurrent.futures,hashlib,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(out,n=20,seed=151000,chunks=4,workers=4,attempts=3,mode="battle",feast="off"):
 out=Path(out);out.mkdir(parents=True,exist_ok=True);inp=out/'inputs';inp.mkdir(exist_ok=True)
 tables={k:json.loads((ROOT/f'app/src/core/data/{k}.json').read_text())for k in ['economy_chapters','star_up','stages','enemy_units','stage_level_overrides','feast']};tablefile=inp/'tables.json';tablefile.write_text(json.dumps(tables,ensure_ascii=False))
 for f in (ROOT/'data').glob('*.csv'):shutil.copy2(f,inp/f.name)
 for src in ['tools/joint_behavior.ts','tools/player_policy.ts','app/src/core/formation.ts','app/src/core/progression.ts','app/src/core/battle/engine.ts']:shutil.copy2(ROOT/src,inp/Path(src).name)
 jobs=[]
 for camp in ['taiping','qing']:
  for c in range(chunks):
   start=c*n//chunks;end=(c+1)*n//chunks
   if end>start:jobs.append((camp,c,end-start,seed+start+(0 if camp=='taiping'else 1000000)))
 def job(item):
  camp,c,count,s=item;name=f'{camp}_{c:02}';p=out/(name+'.json')
  with(out/(name+'.log')).open('w')as f:subprocess.run(['node','--import','./app/node_modules/tsx/dist/loader.mjs','tools/joint_behavior.ts',f'camp={camp}',f'n={count}',f'seed={s}',f'attempts={attempts}',f'mode={mode}',f'feast={feast}',f'tables={tablefile}',f'out={p}'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
  return str(p),json.loads(p.read_text())
 with concurrent.futures.ThreadPoolExecutor(max_workers=workers)as pool:batches=list(pool.map(job,jobs))
 result={**batches[0][1],'count_per_campaign':n,'seed':seed,'source_batches':[],'runs':[],'forecast_battles':0}
 for path,d in batches:
  result['source_batches'].append({'path':path,'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'input_sha256':d['input_sha256']});result['runs']+=d['runs'];result['forecast_battles']+=d['forecast_battles']
 (out/'behavior.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({'accounts':len(result['runs']),'complete':sum(r['cleared']==48 for r in result['runs']),'forecast_battles':result['forecast_battles']}),flush=True);return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--n',type=int,default=20);p.add_argument('--seed',type=int,default=151000);p.add_argument('--chunks',type=int,default=4);p.add_argument('--workers',type=int,default=4);p.add_argument('--attempts',type=int,default=3);p.add_argument('--feast',choices=['off','conservative','aggressive'],default='off');p.add_argument('--mode',choices=['battle','profile'],default='battle');a=p.parse_args();run(a.out,a.n,a.seed,a.chunks,a.workers,a.attempts,a.mode,a.feast)
