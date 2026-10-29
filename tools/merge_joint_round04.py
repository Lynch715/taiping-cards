#!/usr/bin/env python3
from pathlib import Path
import json,time,shutil,hashlib
from joint_iteration import promote
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'assets/reports/joint_v2/round04';base=R/'calibration'
while not(base/'difficulty.json').exists()or not(R/'pacing/tp_6_3.json').exists():time.sleep(2)
report=json.loads((base/'difficulty.json').read_text());original={s['stage_id']:s for s in report['stages']};overrides={}
for folder in ['pacing','numeric_repairs','elite_repair']:
 for p in(R/folder).glob('*.json'):
  x=json.loads(p.read_text())
  if not isinstance(x,dict)or 'stage_id'not in x:continue
  overrides[x['stage_id']]=x
elite={r['stage_id']:r for r in json.loads((R/'elite_repair/tables.json').read_text())['stages']}
for sid in ['tp_7_3','tp_7_5','tp_8_6']:
 x=overrides[sid];x['enemy_monarch']=elite[sid]['enemy_monarch'];x['steps'].insert(0,{'kind':'elite_template_after_historical_roster_and_star_bound_audit','prior_failed_rate':original[sid]['validation']['rate'],'source':'joint_v2/history_notes.md','ordinary_npc_scale':1.5})
 if sid=='tp_7_3':x['steps'].insert(0,{'kind':'historical_actor_trial_rejected','id':'qing_zhang_shusheng','source':'round04/roster_repair/tp_7_3.json','reason':'Replacement weakened the original three-commander army'})
 if sid=='tp_7_5':x['steps'].insert(0,{'kind':'historical_actor_added','id':'qing_gordon','source':'https://fzg.changzhou.gov.cn/html/fzg/1970/QMHQODDK_0805/20565.html','regular_template_trial':'round04/gordon_only/tp_7_5.json'})
for sid,x in overrides.items():
 x['prior_round04_result']={'source':f'round04/initial/{sid}.json','enemy_level':original[sid]['enemy_level'],'rate':original[sid]['validation']['rate']}
rows=[overrides.get(s['stage_id'],s)for s in report['stages']];fail=[(s['stage_id'],s['validation']['rate'])for s in rows if not s['pass']];print('Merged failures:',fail,flush=True)
if fail:raise SystemExit(1)
backup=R/'initial';backup.mkdir(exist_ok=True)
for sid in overrides:
 if not(backup/(sid+'.json')).exists():shutil.copy2(base/(sid+'.json'),backup/(sid+'.json'))
for sid,x in overrides.items():(base/(sid+'.json')).write_text(json.dumps(x,ensure_ascii=False,indent=2))
report.update(all_pass=True,stages=rows,pacing_overrides=list(overrides),source_iteration='economy05_07');(base/'difficulty.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));promote(report)
marker={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in(ROOT/'data').glob('*.csv')};(R/'ready_for_replay.json').write_text(json.dumps(marker,indent=2));print('Promoted96; replay may start',flush=True)
