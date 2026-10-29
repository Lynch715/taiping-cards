"""Final v0.4.2 gate: sixteen chapter upper bounds plus two campaign medians."""
import statistics
MIN_CAMPAIGN_MEDIAN=13.9
def acceptance(data):
 chapters=[];campaigns=[]
 for camp in ['taiping','qing']:
  runs=[r for r in data['runs']if r['campaign']==camp]
  complete=len(runs)==12 and len({r['seed']for r in runs})==12 and all(r['cleared']==48 and len(r['chapters'])==8 for r in runs)
  for ch in range(1,9):
   stats=[c for r in runs for c in r['chapters']if c['chapter']==ch];target=stats[0]['target_days']if stats else 0
   mean=statistics.mean(c['duration']for c in stats)if stats else None;maximum=max((c['max_stage_wait']for c in stats),default=None);short=sum(c['max_stage_wait']<=2 for c in stats)
   chapters.append({'campaign':camp,'chapter':ch,'accounts':len(stats),'target_days':target,'maximum_mean_days':target*1.25,'mean_days':mean,'accounts_wait_le2':short,'max_wait_days':maximum,'pass':bool(complete and len(stats)==12 and mean<=target*1.25 and short>=10 and maximum<=3)})
  days=[r['days']for r in runs if r['cleared']==48];median=statistics.median(days)if days else None
  campaigns.append({'campaign':camp,'accounts':len(days),'median_days':median,'minimum_median_days':MIN_CAMPAIGN_MEDIAN,'minimum_days':min(days)if days else None,'maximum_days':max(days)if days else None,'mean_days':statistics.mean(days)if days else None,'pass':bool(complete and median>=MIN_CAMPAIGN_MEDIAN)})
 return {'chapters':chapters,'campaigns':campaigns,'chapter_pass_count':sum(r['pass']for r in chapters),'campaign_pass_count':sum(r['pass']for r in campaigns),'all_pass':all(r['pass']for r in chapters+campaigns)}
