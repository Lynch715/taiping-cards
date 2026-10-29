#!/usr/bin/env python3
"""Read-only independent fixed-configuration validation on fresh growth profiles."""
import argparse,json,subprocess,concurrent.futures,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def verify(profiles,out,workers=6,n=1000):
 out=Path(out);out.mkdir(parents=True,exist_ok=True);inputs=out/'inputs';inputs.mkdir(exist_ok=True)
 tables={k:json.loads((ROOT/f'app/src/core/data/{k}.json').read_text())for k in ['economy_chapters','star_up','stages','enemy_units']};tablefile=inputs/'tables.json';tablefile.write_text(json.dumps(tables,ensure_ascii=False))
 for p in (ROOT/'data').glob('*.csv'):shutil.copy2(p,inputs/p.name)
 def run(i):
  with(out/f'job_{i:02}.log').open('w')as f:subprocess.run(['node','--import','./app/node_modules/tsx/dist/loader.mjs','tools/joint_verify.ts',f'profiles={profiles}',f'tables={tablefile}',f'start={i*4}',f'end={(i+1)*4}',f'n={n}',f'out={out}'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=workers)as pool:list(pool.map(run,range(24)))
 rows=[json.loads((out/(r['stage_id']+'.json')).read_text())for r in tables['stages']];result={'all_pass':all(r['pass']for r in rows),'profiles':str(profiles),'stages':rows};(out/'difficulty.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({'all_pass':result['all_pass'],'failed':[(r['stage_id'],r['validation']['rate'])for r in rows if not r['pass']]}),flush=True);return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--profiles',required=True);p.add_argument('--out',required=True);p.add_argument('--workers',type=int,default=6);p.add_argument('--n',type=int,default=1000);a=p.parse_args();verify(a.profiles,a.out,a.workers,a.n)
