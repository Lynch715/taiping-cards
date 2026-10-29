#!/usr/bin/env python3
"""Economic coordinate iteration. --calibrate interleaves bounded enemy calibration between economy runs."""
import argparse,json,csv,subprocess,statistics
from pathlib import Path
from joint_metrics import summarize
from joint_iteration import calibrate,promote
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'assets/reports/joint_v2'
def read(name):return list(csv.DictReader((ROOT/'data'/name).open()))
def write(name,rows):
 with(ROOT/'data'/name).open('w',newline='')as f:w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
def run_model(label,n,seed,mode='battle'):
 from joint_cohort import run
 subprocess.run(['python3','tools/export_data.py'],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
 out=R/label;data=run(out,n=n,seed=seed,chunks=2,workers=4,mode=mode)
 return out/'behavior.json',data
def tune_income(metrics):
 rows=read('economy_chapters.csv');changes=[];wanted={'idle':.60,'first':.25,'sweep':.15};keys={'idle':'idle_exp_per_hour','first':'first_clear_exp','sweep':'sweep_exp'}
 for row in rows:
  chapter=int(row['chapter']);groups=[g for g in metrics['groups']if g['chapter']==chapter and g['n']];
  if not groups:continue
  duration=statistics.mean(g['mean_days']for g in groups);target=float(row['target_days']);overall=max(.65,min(1.5,(max(.2,duration)/target)**.6));shares={k:statistics.mean(v['sources'][k]for v in groups)for k in wanted};scales={k:max(.75,min(1.3,(wanted[k]/max(.03,shares[k]))**.5))for k in wanted};norm=sum(shares[k]*scales[k]for k in wanted)
  for k,col in keys.items():
   old=int(row[col]);row[col]=str(max(10,round(old*overall*scales[k]/max(.1,norm)/10)*10));changes.append({'chapter':chapter,'field':col,'before':old,'after':int(row[col])})
  for kind in keys:
   exp=keys[kind];silver='idle_silver_per_hour'if kind=='idle'else 'first_clear_silver'if kind=='first'else 'sweep_silver';row[silver]=str(int(row[exp])*2)
  row['idle_iron_per_hour']=str(max(1,round(int(row['idle_exp_per_hour'])*.05)));row['first_clear_iron']=str(max(1,round(int(row['first_clear_exp'])*.05)))
 # Soul adjustments are explicit and reviewed in the iteration record; never change the required 50-shard rule.
 # Entry-star supply is reviewed after pacing changes; a fast chapter can explain an early-star shortfall.
 write('economy_chapters.csv',rows);return changes
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--n',type=int,default=4);p.add_argument('--seed',type=int,default=124000);p.add_argument('--label',default='coordinate');p.add_argument('--steps',type=int,default=4);p.add_argument('--mode',choices=['profile','battle'],default='battle');p.add_argument('--calibrate',action='store_true');a=p.parse_args();history=[]
 for step in range(a.steps):
  label=f'{a.label}_{step:02}';path,data=run_model(label,a.n,a.seed,a.mode);metrics=summarize(data);record={'step':step,'path':str(path),'metrics':metrics};history.append(record);(R/(a.label+'_tuning.json')).write_text(json.dumps(history,ensure_ascii=False,indent=2));print(json.dumps({'step':step,'all_pass':metrics['all_pass'],'days':[[round(g['mean_days'],3)for g in metrics['groups']if g['campaign']==c]for c in ['taiping','qing']],'star_failures':sum(len(s['outliers'])for s in metrics['entry_stars'])}),flush=True)
  if metrics['all_pass']:break
  if step==a.steps-1:break
  record['changes']=tune_income(metrics)
  if a.calibrate:
   profilepath,_=run_model(label+'_profile',a.n,a.seed,'profile');report=calibrate(profilepath,R/(label+'_calibration'))
   if not report['all_pass']:raise RuntimeError('Difficulty did not pass; economy iteration preserved, no partial stage promotion')
   promote(report)
