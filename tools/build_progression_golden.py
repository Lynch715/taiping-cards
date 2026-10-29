#!/usr/bin/env python3
import json,copy,hashlib,argparse
from pathlib import Path
from battle_sim import ROOT,read_csv
from m1_scenarios import game_data,run_input,INITIAL
parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=ROOT/'assets/reports/progression/golden');parser.add_argument('--calibration',type=Path,default=ROOT/'assets/reports/progression/calibration');parser.add_argument('--fallback-calibration',type=Path);args=parser.parse_args();R=args.out;R.mkdir(exist_ok=True,parents=True);D=game_data();cases=[];rows=read_csv(ROOT/'data/stages.csv')
for i,row in enumerate(rows):
 refpath=args.calibration/(row['stage_id']+'.json');refpath=refpath if refpath.exists() or not args.fallback_calibration else args.fallback_calibration/(row['stage_id']+'.json');ref=json.loads(refpath.read_text());a=copy.deepcopy(ref['profiles'][i%len(ref['profiles'])]);ids=row['enemies'].split(',');b={'heroes':ids,'monarch':row['enemy_monarch'] or None,'faction':'qing' if row['campaign']=='taiping' else 'taiping','levels':[ref['enemy_level']]*5,'stars':[int(s) for s in row['enemy_stars'].split(';')],'exclusives':[int(s)>=4 for s in row['enemy_stars'].split(';')],'monarchStars':int(row['enemy_monarch_stars'] or 3),'monarchExclusive':int(row['enemy_monarch_stars'] or 3)>=4};cases.append({'id':row['stage_id'],'a':a,'b':b,'terrain':row['terrain'],'seed':8400000+i,'options':{'allowDuplicates':True}})
starters=read_csv(ROOT/'data/starter_cards.csv');caps={1:35,2:50,3:65,4:80,5:95,6:100}
for i,terrain in enumerate(['陆战','水战','攻城','守城']):
 teams=[]
 for side,own in enumerate(starters):
  ids=own['cards'].split(';')[:5];stars=[4,1,6,3,2];gear=[]
  for j,id in enumerate(ids):
   setname=['圣兵','勇营','江防','铁骑','洋械'][(i+j+side)%5];items=[]
   for k,slot in enumerate(['兵刃','甲胄','坐骑','兵书']):
    row=next(r for r in D.equipment.values() if r['set']==setname and r['slot']==slot and r['quality']==['粗','制','精','珍','绝'][(i+j+k)%5]);items.append({'equipmentId':row['equip_id'],'enhance':(i+j+k)% (int(row['enhance_max'])+1)})
   gear.append(items)
  teams.append({'heroes':ids,'monarch':own['monarch'],'faction':own['campaign'],'stars':stars,'levels':[min(caps[s],35+i*8+j) for j,s in enumerate(stars)],'gear':gear,'exclusives':[s>=4 for s in stars],'monarchStars':4,'monarchExclusive':True})
 cases.append({'id':'mixed_gear_'+str(i),'a':teams[0],'b':teams[1],'terrain':terrain,'seed':8500000+i,'options':{}})
for case in cases:case['expected']=run_input(D,case['a'],case['b'],case['terrain'],case['seed'],case['options'])
assert len(cases)==100
(R/'fixtures.json').write_text(json.dumps(cases,ensure_ascii=False,separators=(',',':'))+'\n');(R/'manifest.json').write_text(json.dumps({'cases':100,'stage_cases':96,'mixed_equipment_cases':4,'log_lines':sum(len(c['expected']['trace']) for c in cases),'python_sha256':hashlib.sha256((ROOT/'tools/battle_sim.py').read_bytes()).hexdigest()},indent=2)+'\n')
print('100 cases,',sum(len(c['expected']['trace']) for c in cases),'lines')
