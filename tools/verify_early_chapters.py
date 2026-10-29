#!/usr/bin/env python3
"""Independent new-seed verification of the accepted chapter 1/2 configuration."""
import json,concurrent.futures,copy
from pathlib import Path
from calibrate_growth import measure,power
from stage_difficulty import target
from m1_scenarios import game_data
from battle_sim import ROOT,read_csv
R=ROOT/'assets/reports/chapters_3_8/early_verification';R.mkdir(parents=True,exist_ok=True)
def run(row):
 ref=json.loads((ROOT/'assets/reports/progression/calibration'/(row['stage_id']+'.json')).read_text());d=game_data();offset=(0 if row['campaign']=='taiping'else 100000)+int(row['chapter'])*10000+int(row['order'])*1000;ref['target']=list(target(row));ref['validation']=measure(d,row,ref['profiles'],float(row['enemy_level']),4000,9600000+offset);ref['validation_seed']=9600000+offset;ref['validation_source']='New seed; accepted chapter1/2 growth configurations unchanged';ref['pass']=ref['target'][0]<=ref['validation']['rate']<=ref['target'][1];assert ref['recommended_power']==int(row['recommended_power']);assert ref['enemy_level']==float(row['enemy_level']);(R/(row['stage_id']+'.json')).write_text(json.dumps(ref,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:ref[k]for k in ['stage_id','validation','pass']}),flush=True);return ref
if __name__=='__main__':
 rows=[r for r in read_csv(ROOT/'data/stages.csv')if int(r['chapter'])<=2]
 with concurrent.futures.ProcessPoolExecutor(max_workers=2)as pool:results=list(pool.map(run,rows))
 (R/'difficulty.json').write_text(json.dumps({'all_pass':all(r['pass']for r in results),'stages':results},ensure_ascii=False,indent=2)+'\n')
