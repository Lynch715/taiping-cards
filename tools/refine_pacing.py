#!/usr/bin/env python3
"""Redistribute chapter waiting within the existing approved win-rate intervals."""
from pathlib import Path
import json,subprocess,concurrent.futures
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'assets/reports/joint_v2';OUT=R/'round04/pacing';OUT.mkdir(parents=True,exist_ok=True)
targets={'tp_2_1':.956,'tp_2_2':.86,'tp_2_3':.86,'qing_2_1':.99,'qing_2_2':.94,'qing_2_3':.635,'qing_2_5':.635,'tp_6_1':.956,'tp_6_2':.86,'tp_6_3':.86,'tp_8_4':.73,'tp_8_5':.63}
tables=R/'round04/inputs/tables.json';rows=json.loads(tables.read_text())['stages'];(OUT/'targets.json').write_text(json.dumps(targets,indent=2))
def run(item):
 sid,value=item;i=next(i for i,r in enumerate(rows)if r['stage_id']==sid)
 with(OUT/(sid+'.log')).open('w')as f:subprocess.run(['node','--import','./app/node_modules/tsx/dist/loader.mjs','tools/joint_pacing.ts',f'profiles={R}/economy05_07/behavior.json',f'tables={tables}',f'start={i}',f'end={i+1}',f'target_rate={value}','n=2000',f'out={OUT}'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:list(pool.map(run,targets.items()))
print('Pacing refinements complete',flush=True)
