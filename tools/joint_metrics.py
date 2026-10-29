"""Strict v0.2 account-level gates; pace is a per-campaign cohort mean, not every player's exact clock."""
import statistics
STAR_TARGETS={4:2.5,6:3.5,8:4.5}
def summarize(result):
 groups=[]
 for camp in ['taiping','qing']:
  runs=[r for r in result['runs']if r['campaign']==camp]
  if not runs:continue
  for chapter in range(1,9):
   rows=[c for r in runs for c in r['chapters']if c['chapter']==chapter]
   if not rows:groups.append({'campaign':camp,'chapter':chapter,'n':0,'pass':False});continue
   mean=statistics.mean(c['duration']for c in rows);target=rows[0]['target_days'];wait=max(c['max_stage_wait']for c in rows);exp=max(c['exp_remaining_ratio']for c in rows);income={k:statistics.mean(c['exp_sources'][k]/max(1,c['produced']['exp'])for c in rows)for k in ['idle','first','sweep']}
   groups.append({'campaign':camp,'chapter':chapter,'n':len(rows),'target':target,'mean_days':mean,'median_days':statistics.median(c['duration']for c in rows),'min_days':min(c['duration']for c in rows),'max_days':max(c['duration']for c in rows),'pace_pass':target*.75<=mean<=target*1.25,'max_stage_wait':wait,'wait_pass':wait<=2,'exp_remaining_ratio_mean':statistics.mean(c['exp_remaining_ratio']for c in rows),'exp_remaining_ratio_max':exp,'exp_pass':exp<.2,'sources':income,'silver_min':min(c['remaining']['silver']for c in rows),'iron_min':min(c['remaining']['iron']for c in rows),'pass':len(rows)==len(runs)and target*.75<=mean<=target*1.25 and wait<=2 and exp<.2})
 stars=[]
 for camp in ['taiping','qing']:
  runs=[r for r in result['runs']if r['campaign']==camp]
  if not runs:continue
  for chapter,target in STAR_TARGETS.items():
   rows=[{'seed':r['seed'],**e}for r in runs for e in r['entries']if e['chapter']==chapter];values=[e['mean_stars']for e in rows];outliers=[{'seed':e['seed'],'mean_stars':e['mean_stars'],'heroes':e['team']['heroes'],'stars':e['team']['stars']}for e in rows if abs(e['mean_stars']-target)>.50000001];stars.append({'campaign':camp,'chapter':chapter,'target':target,'n':len(values),'min':min(values)if values else None,'mean':statistics.mean(values)if values else None,'max':max(values)if values else None,'outliers':outliers,'pass':len(values)==len(runs)and not outliers})
 resources={}
 for kind in ['silver','iron']:
  minimum=None;longest=0;zero=0
  for run in result['runs']:
   streak=0
   for wallet in run.get('session_wallets',[c['remaining']for c in run['chapters']]):
    value=wallet[kind];minimum=value if minimum is None else min(minimum,value);streak=streak+1 if value==0 else 0;longest=max(longest,streak);zero+=int(value==0)
  resources[kind]={'minimum':minimum,'zero_sessions':zero,'max_consecutive_zero_sessions':longest,'pass':minimum is not None and longest<4}
 expected=result.get('count_per_campaign')
 coverage=len(groups)==16 and len(stars)==6 and bool(result['runs']) and all(len({r['seed']for r in result['runs']if r['campaign']==camp})==len([r for r in result['runs']if r['campaign']==camp])and (expected is None or len([r for r in result['runs']if r['campaign']==camp])==expected)for camp in ['taiping','qing'])
 actual=result.get('mode')=='battle'
 return {'groups':groups,'entry_stars':stars,'resources':resources,'actual_battle_mode':actual,'complete_campaign_coverage':coverage,'all_complete':coverage and all(r['cleared']==48 for r in result['runs']),'max_daily_sweeps':max((r['max_daily_sweeps']for r in result['runs']),default=0),'all_pass':actual and coverage and all(g['pass']for g in groups)and all(s['pass']for s in stars)and all(r['cleared']==48 for r in result['runs'])and all(r['max_daily_sweeps']<=30 for r in result['runs'])and all(v['pass']for v in resources.values())}
