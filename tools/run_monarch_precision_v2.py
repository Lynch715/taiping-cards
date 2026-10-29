#!/usr/bin/env python3
"""Four independent2,000-lineup blocks; pool their top-decile monarch statistics."""
import concurrent.futures,hashlib,json,subprocess,sys,time
from collections import Counter
from pathlib import Path
from battle_sim import ROOT,Data,evaluate,pools,top_weights
R=ROOT/'assets/reports/balance_v2'
NAMES=['battle_sim.py','balance_diagnostics.py','run_balance_v2_review.py','run_monarch_precision_v2.py']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def hashes():return {n:sha(ROOT/'tools'/n) for n in NAMES}
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def aggregate(parts,data):
 assert len({json.dumps(x['input_sha256'],sort_keys=True) for x in parts})==1
 rows=[]
 for i,part in enumerate(parts):
  for row in part['top_lineups']['rows']:rows.append({**row,'id':len(rows),'part':i})
 monarchs={}
 for camp in ['taiping','qing']:
  own=[r for r in rows if r['faction']==camp];take,chosen=top_weights(own);counts=Counter()
  for row,w in chosen:counts[row['lord']]+=w
  monarchs[camp]={'sampled_lineups':len(own),'top_count':take,'denominator':'Top10% within own faction, pooled independent blocks; cutoff ties split',
   'cards':{h:{'count':counts[h],'rate':counts[h]/take} for h in pools(data,camp,lords=True)}}
 return {'seed':20263201,'shard_seeds':[x['seed'] for x in parts],'total_games':sum(x['total_games'] for x in parts),'parameters':{'paired_fixtures_per_scenario':1,'lineups':len(rows),'opponents':16},
  'input_sha256':parts[0]['input_sha256'],'simulator_sha256':parts[0]['simulator_sha256'],'monarchs':monarchs,
  'top_lineups':{'rows':sorted(rows,key=lambda r:-r['rate'])},'scope':'Monarch precision only. Four independent2000-lineup blocks;32 games per lineup against its block. Global top10% weighted after pooling. Duplicate roster draws across independent blocks are allowed. Auxiliary n=1 combat estimates discarded.'}
def main():
 after=R/'trials/12_cixi_policy/data';args=sys.argv[1:]
 if args:
  phase,index=args[0],int(args[1]);directory=R/'before/data' if phase=='before' else after;frozen=hashes();start=time.time()
  x=evaluate(Data(directory),n=1,lineups=2000,opponents=16,seed=20263201+index*100)
  assert frozen==hashes();save(R/'monarch_precision_parts'/f'{phase}_{index}.json',x)
  print(json.dumps({'phase':phase,'part':index,'games':x['total_games'],'seconds':round(time.time()-start,2)}),flush=True);return
 protocol={'seed':20263201,'shard_seeds':[20263201+i*100 for i in range(4)],'lineups':8000,'opponents':16,'runtime_sha256':hashes(),
  'reason':'After failed11 large sampleCixi18.18%, strengthen Cixi once then freeze12; one independent4-block sample, no seed search or optional extension.',
  'sampling':'Four independent blocks of2000 candidates;32 games per candidate against its block. Pool8000 rates before per-faction top10%. Roster repeats across independent blocks permitted.',
  'before_dir':str(R/'before/data'),'after_dir':str(after)}
 save(R/'monarch_precision_protocol.json',protocol)
 def run(job):
  phase,index=job
  with (R/f'monarch_precision_{phase}_{index}.log').open('w') as stream:subprocess.run([sys.executable,__file__,phase,str(index)],stdout=stream,stderr=subprocess.STDOUT,check=True,cwd=ROOT)
  print('DONE',phase,index,flush=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(run,[(p,i) for i in range(4) for p in ['before','after']]))
 for phase in ['before','after']:
  parts=[json.loads((R/'monarch_precision_parts'/f'{phase}_{i}.json').read_text()) for i in range(4)];x=aggregate(parts,Data(R/'before/data' if phase=='before' else after));x['runtime_sha256']=protocol['runtime_sha256'];save(R/f'{phase}_monarch_precision.json',x)
 assert protocol['runtime_sha256']==hashes();print('Precision extension complete',flush=True)
if __name__=='__main__':main()
