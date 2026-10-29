#!/usr/bin/env python3
"""Replay each campaign as soon as all its bounded calibration records pass."""
import json,time,subprocess,concurrent.futures,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--calibration',required=True);p.add_argument('--out',required=True);p.add_argument('--n',type=int,default=4);p.add_argument('--seed',type=int,default=128000);a=p.parse_args();cal=Path(a.calibration);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 def run(camp):
  base=json.loads((cal.parent/'inputs/tables.json').read_text());rows=[r for r in base['stages']if r['campaign']==camp]
  while True:
   records={r['stage_id']:json.loads((cal/(r['stage_id']+'.json')).read_text())for r in rows if(cal/(r['stage_id']+'.json')).exists()}
   if len(records)==48 and all(r['pass']for r in records.values()):break
   time.sleep(5)
  for r in base['stages']:
   if r['stage_id']not in records:continue
   x=records[r['stage_id']];r['enemy_monarch']=x.get('enemy_monarch',r['enemy_monarch']);r.update(enemy_level=x['enemy_level'],enemies=','.join(x['enemies']),enemy_stars=';'.join(map(str,x['enemy_stars'])),enemy_monarch_stars=x['enemy_monarch_stars'],recommended_power=x['recommended_power'])
  tables=out/(camp+'_tables.json');tables.write_text(json.dumps(base,ensure_ascii=False));result=out/(camp+'.json')
  with(out/(camp+'.log')).open('w')as f:subprocess.run(['node','--import','./app/node_modules/tsx/dist/loader.mjs','tools/joint_behavior.ts',f'camp={camp}',f'n={a.n}',f'seed={a.seed}',f'tables={tables}',f'out={result}'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
  return json.loads(result.read_text())
 with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:batches=list(pool.map(run,['taiping','qing']))
 combined={**batches[0],'runs':[],'source_batches':[],'forecast_battles':0}
 for camp,batch in zip(['taiping','qing'],batches):
  combined['source_batches'].append({'campaign':camp,'path':str(out/(camp+'.json')),'input_sha256':batch['input_sha256']});combined['forecast_battles']+=batch['forecast_battles'];combined['runs']+=batch['runs']
 (out/'behavior.json').write_text(json.dumps(combined,ensure_ascii=False,indent=2));print('Both campaign replays complete',flush=True)
if __name__=='__main__':main()
