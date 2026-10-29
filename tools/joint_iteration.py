#!/usr/bin/env python3
"""Run bounded calibration jobs and publish a candidate only when all96 stages pass."""
import argparse,json,csv,concurrent.futures,subprocess,hashlib,statistics,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'assets/reports/joint_v2'
def calibrate(profiles,out,workers=4,n=1000):
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 seed=R/'stage_seed.json'
 if not seed.exists():seed.write_bytes((ROOT/'app/src/core/data/stages.json').read_bytes())
 inputs=out.parent/'inputs';inputs.mkdir(parents=True,exist_ok=True)
 for p in (ROOT/'data').glob('*.csv'):shutil.copy2(p,inputs/p.name)
 tables={k:json.loads((ROOT/f'app/src/core/data/{k}.json').read_text())for k in ['economy_chapters','star_up','stages','enemy_units']}
 tablefile=inputs/'tables.json';tablefile.write_text(json.dumps(tables,ensure_ascii=False))
 for name in ['joint_calibrate.ts','joint_behavior.ts']:shutil.copy2(ROOT/'tools'/name,inputs/name)
 for name in ['formation.ts','battle/engine.ts']:
  dest=inputs/Path(name).name;shutil.copy2(ROOT/'app/src/core'/name,dest)
 def run(i):
  start=i;end=i+1;log=out/f'job_{i:02}.log'
  with log.open('w')as f:subprocess.run(['node','--import','./app/node_modules/tsx/dist/loader.mjs','tools/joint_calibrate.ts',f'profiles={profiles}',f'tables={tablefile}',f'stages={seed}',f'start={start}',f'end={end}',f'n={n}',f'out={out}'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=workers)as pool:list(pool.map(run,range(96)))
 results=[json.loads((out/(row['stage_id']+'.json')).read_text())for row in json.loads(seed.read_text())]
 report={'all_pass':all(r['pass']for r in results),'profiles':str(profiles),'stages':results};(out/'difficulty.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 return report

def promote(report):
 assert report['all_pass'];rows=list(csv.DictReader((ROOT/'data/stages.csv').open()));lookup={r['stage_id']:r for r in report['stages']}
 for row in rows:
  r=lookup[row['stage_id']];assert r['level_bounds'][0]<=r['enemy_level']<=r['level_bounds'][1]
  row['enemy_level']=str(r['enemy_level']);row['recommended_power']=str(r['recommended_power']);row['enemies']=','.join(r['enemies']);row['enemy_stars']=';'.join(map(str,r['enemy_stars']))
  row['enemy_monarch']=r.get('enemy_monarch',row['enemy_monarch']);row['enemy_monarch_stars']=str(r['enemy_monarch_stars'])if row['enemy_monarch']else''
 with (ROOT/'data/stages.csv').open('w',newline='')as f:w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
 subprocess.run(['python3','tools/export_data.py'],cwd=ROOT,check=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--profiles',required=True);p.add_argument('--out',required=True);p.add_argument('--workers',type=int,default=4);p.add_argument('--n',type=int,default=1000);p.add_argument('--promote',action='store_true');a=p.parse_args();result=calibrate(a.profiles,a.out,a.workers,a.n);print(json.dumps({'all_pass':result['all_pass'],'failed':[r['stage_id']for r in result['stages']if not r['pass']]}),flush=True)
 if a.promote and result['all_pass']:promote(result)
