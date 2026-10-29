#!/usr/bin/env python3
"""Refine current enemy configs against new growth profiles; retain the previous historical roster audit."""
import argparse,json,subprocess,concurrent.futures,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def refine(profiles,out,workers=6,n=1000):
 out=Path(out);out.mkdir(parents=True,exist_ok=True);inputs=out.parent/'inputs';inputs.mkdir(parents=True,exist_ok=True);tables={k:json.loads((ROOT/f'app/src/core/data/{k}.json').read_text())for k in ['economy_chapters','star_up','stages','enemy_units']};tablefile=inputs/'tables.json';tablefile.write_text(json.dumps(tables,ensure_ascii=False))
 for p in(ROOT/'data').glob('*.csv'):shutil.copy2(p,inputs/p.name)
 for name in ['joint_refine.ts','joint_behavior.ts']:shutil.copy2(ROOT/'tools'/name,inputs/name)
 def run(i):
  with(out/f'job_{i:02}.log').open('w')as f:subprocess.run(['node','--import','./app/node_modules/tsx/dist/loader.mjs','tools/joint_refine.ts',f'profiles={profiles}',f'tables={tablefile}',f'start={i}',f'end={i+1}',f'n={n}',f'out={out}'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=workers)as pool:list(pool.map(run,range(96)))
 rows=[json.loads((out/(r['stage_id']+'.json')).read_text())for r in tables['stages']];report={'all_pass':all(r['pass']for r in rows),'profiles':str(profiles),'prior_historical_roster_audit':'round02','stages':rows};(out/'difficulty.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({'all_pass':report['all_pass'],'failed':[(r['stage_id'],r['validation']['rate'])for r in rows if not r['pass']]}),flush=True);return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--profiles',required=True);p.add_argument('--out',required=True);p.add_argument('--workers',type=int,default=6);p.add_argument('--n',type=int,default=1000);p.add_argument('--promote',action='store_true');a=p.parse_args();r=refine(a.profiles,a.out,a.workers,a.n)
 if a.promote and r['all_pass']:
  from joint_iteration import promote
  promote(r)
