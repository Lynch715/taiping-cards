"""Pair identical accounts; a temporary unaffordable offer alone is not a slowdown."""
def assess(baseline,trial):
 old={(r['campaign'],r['seed']):r for r in baseline['runs']};rows=[];offers=[]
 for run in trial['runs']:
  ref=old[run['campaign'],run['seed']]
  denied=[e for e in run['early_feast_offers']if not e['affordable']and e['reference_affordable']]
  offers.extend({'campaign':run['campaign'],'seed':run['seed'],**e}for e in denied)
  for ch in [1,2]:
   a=next(c for c in ref['chapters']if c['chapter']==ch);b=next(c for c in run['chapters']if c['chapter']==ch)
   am=sum(h['level']for h in a['main'])/5;bm=sum(h['level']for h in b['main'])/5
   relevant=[e for e in denied if e['chapter']<=ch and e['day']<=b['day']]
   later=b['day']>a['day']+1e-9;same_day=abs(b['day']-a['day'])<=1e-9;lower_same_day=same_day and bm<am-1e-9
   rows.append({'campaign':run['campaign'],'seed':run['seed'],'chapter':ch,'base_completion_day':a['day'],'trial_completion_day':b['day'],'base_mean_level':am,'trial_mean_level':bm,'price_blocked_offers':len(relevant),'later_completion':later,'lower_level_same_day':lower_same_day,'growth_slowed_after_price_block':bool(relevant and(later or lower_same_day))})
 return {'pass':not any(r['growth_slowed_after_price_block']for r in rows),'affected_accounts':len({(r['campaign'],r['seed'])for r in rows if r['growth_slowed_after_price_block']}),'temporarily_blocked_accounts':len({(r['campaign'],r['seed'])for r in offers}),'rows':rows,'blocked_offers':offers}
