"""One chapter gate: pace, at least10/12 short waits and a hard3-day maximum."""
import statistics
def acceptance(data):
 rows=[]
 for camp in ['taiping','qing']:
  runs=[r for r in data['runs']if r['campaign']==camp]
  for ch in range(1,9):
   samples=[(r,c)for r in runs for c in r['chapters']if c['chapter']==ch];complete=len(runs)==len(samples)==12 and all(r['cleared']==48 for r in runs)
   target=samples[0][1]['target_days']if samples else 0;mean=statistics.mean(c['duration']for _,c in samples)if samples else None
   maximum=max((c['max_stage_wait']for _,c in samples),default=None);short=sum(c['max_stage_wait']<=2 for _,c in samples);pace=mean is not None and target*.75<=mean<=target*1.25
   rows.append({'campaign':camp,'chapter':ch,'accounts':len(samples),'target_days':target,'mean_days':mean,'accounts_wait_le2':short,'max_wait_days':maximum,'pace_pass':pace,'pass':bool(complete and pace and short>=10 and maximum<=3),'old_pass':bool(complete and pace and short==12 and maximum<=2),'account_waits':[{'seed':r['seed'],'max_stage_wait':c['max_stage_wait'],'duration':c['duration']}for r,c in samples]})
 return {'chapters':rows,'pass_count':sum(r['pass']for r in rows),'old_pass_count':sum(r['old_pass']for r in rows),'total':16,'all_pass':all(r['pass']for r in rows)}
