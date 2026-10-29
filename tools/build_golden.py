#!/usr/bin/env python3
import json,hashlib,argparse
from battle_sim import ROOT,pools,read_csv
from rng import Mulberry32
from m1_scenarios import game_data,stage_input,run_input
p=argparse.ArgumentParser();p.add_argument('--output',default='assets/reports/m1/golden');p.add_argument('--chapters',default='1');p.add_argument('--calibration-dir');args=p.parse_args()
R=ROOT/args.output;R.mkdir(parents=True,exist_ok=True)
d=game_data();rng=Mulberry32(607100);cases=[];stages=[r for r in read_csv(ROOT/'data/stages.csv') if r['chapter'] in args.chapters.split(',')];starters=read_csv(ROOT/'data/starter_cards.csv')
# Chapter cases verify duplicate NPC identities, asymmetric levels/initial stars and earned rewards.
for row in stages:
 own=next(x for x in starters if x['campaign']==row['campaign']);formation=own['cards'].split(';')[:5];a,b=stage_input(d,row,formation)
 if args.calibration_dir:
  formation=json.loads((ROOT/args.calibration_dir/(row['stage_id']+'.json')).read_text())['formation'];a,b=stage_input(d,row,formation)
 cases.append({'id':row['stage_id'],'a':a,'b':b,'terrain':row['terrain'],'seed':607000+len(cases),'options':{'allowDuplicates':True}})
for i in range(100-len(stages)):
 mixed=i%5==0
 a_ids=rng.sample([h['id'] for h in d.heroes.values() if h['position']!='君主' and h['tags']!='杂兵' and (mixed or h['faction'] in ['taiping','dual'])],5)
 b_ids=rng.sample([h['id'] for h in d.heroes.values() if h['position']!='君主' and h['tags']!='杂兵' and (mixed or h['faction'] in ['qing','dual'])],5)
 a={'heroes':a_ids,'monarch':rng.choice(pools(d,'taiping',lords=True)),'faction':'taiping'};b={'heroes':b_ids,'monarch':rng.choice(pools(d,'qing',lords=True)),'faction':'qing'}
 opt={'stars':4 if i%3==0 else 3,'level':10 if i%7==0 else 50}
 if i%6==0:opt['gearSet']=['圣兵','勇营','洋械','铁骑','江防'][i//6%5]
 if i%3==0:opt['exclusives']=True
 if i%17==0:opt['exclusiveOwners']=[[0,a_ids[0]]];opt['exclusiveEffects']=False
 cases.append({'id':f'golden_{i+len(stages)+1:03}','a':a,'b':b,'terrain':['陆战','水战','攻城','守城'][i%4],'seed':rng.randrange(2**32),'options':opt})
lines=0
for case in cases:
 expected=run_input(d,case['a'],case['b'],case['terrain'],case['seed'],case['options']);case['expected']=expected;lines+=len(expected['trace'])
(R/'fixtures.json').write_text(json.dumps(cases,ensure_ascii=False,separators=(',',':'))+'\n')
(R/'manifest.json').write_text(json.dumps({'cases':len(cases),'log_lines':lines,'rng':'mulberry32','python_sha256':hashlib.sha256((ROOT/'tools/battle_sim.py').read_bytes()).hexdigest()},ensure_ascii=False,indent=2)+'\n')
print(len(cases),lines)

vectors=[]
for seed in [0,1,4294967295,4294967296,'太平天国']:
 r=Mulberry32(seed);vectors.append({'seed':seed,'draws':[r.random() for _ in range(16)],'sample':r.sample(list(range(10)),5)})
(R/'rng_vectors.json').write_text(json.dumps(vectors,ensure_ascii=False,indent=2)+'\n')
