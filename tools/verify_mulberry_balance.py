#!/usr/bin/env python3
import json,concurrent.futures,hashlib
from pathlib import Path
from battle_sim import Data,ROOT,evaluate
from run_monarch_precision_v2 import aggregate
R=ROOT/'assets/reports/m1/mulberry_balance'
def job(kind):
 d=Data();x=evaluate(d,n=2000 if kind=='main' else 1,lineups=1600 if kind=='main' else 2000,opponents=16,seed=20263199 if kind=='main' else 20263201+int(kind)*100)
 (R/f'{kind}.json').write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n');print('DONE',kind,flush=True)
if __name__=='__main__':
 R.mkdir(parents=True,exist_ok=True)
 with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:list(pool.map(job,['main','0','1','2','3']))
 parts=[json.loads((R/f'{i}.json').read_text()) for i in range(4)];x=aggregate(parts,Data());(R/'monarchs.json').write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
 from battle_report_v2 import targets,valid
 main=json.loads((R/'main.json').read_text());main['monarchs']=x['monarchs'];rows=targets(main,Data());result={'rng':'mulberry32','total_games':main['total_games']+x['total_games'],'all_pass':all(valid(v,lo,hi,k) for _,v,lo,hi,_,k,_ in rows),'metrics':{n:{'value':v,'target':goal,'pass':valid(v,lo,hi,k)} for n,v,lo,hi,goal,k,_ in rows},'source_sha256':main['input_sha256'],'simulator_sha256':main['simulator_sha256']}
 (R/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False),flush=True)
