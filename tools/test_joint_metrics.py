import copy,unittest
from joint_metrics import summarize
class StrictJointGates(unittest.TestCase):
 def fixture(self):
  runs=[]
  for camp in ['taiping','qing']:
   for seed in [1,2]:runs.append({'campaign':camp,'seed':seed,'cleared':48,'max_daily_sweeps':30,'chapters':[{'chapter':i+1,'duration':d,'target_days':d,'max_stage_wait':1,'exp_remaining_ratio':.1,'remaining':{'silver':100,'iron':100},'produced':{'exp':1000},'exp_sources':{'idle':600,'first':250,'sweep':150}}for i,d in enumerate([1,1.5,2,2,2.5,3,3,3.5])],'entries':[{'chapter':ch,'mean_stars':stars,'team':{'heroes':['a','b','c','d','e'],'stars':[3]*5}}for ch,stars in [(4,2.6),(6,3.4),(8,4.4)]]})
  return {'mode':'battle','runs':runs,'count_per_campaign':2}
 def test_complete_reference_passes(self):self.assertTrue(summarize(self.fixture())['all_pass'])
 def test_resource_outlier_cannot_be_hidden_by_cohort_mean(self):
  d=self.fixture();d['runs'][0]['chapters'][0]['exp_remaining_ratio']=.25;g=summarize(d)['groups'][0];self.assertLess(g['exp_remaining_ratio_mean'],.2);self.assertFalse(g['exp_pass']);self.assertFalse(g['pass'])
 def test_one_long_wait_fails(self):
  d=self.fixture();d['runs'][0]['chapters'][6]['max_stage_wait']=2.25;self.assertFalse(summarize(d)['all_pass'])
 def test_star_entry_checks_every_account(self):
  d=self.fixture();d['runs'][0]['entries'][2]['mean_stars']=3.8;s=summarize(d)['entry_stars'][2];self.assertFalse(s['pass']);self.assertEqual(s['outliers'][0]['seed'],1)
 def test_sweep31_missing_entry_and_incomplete_progress_fail(self):
  for mode in ['sweeps','entry','progress']:
   d=self.fixture()
   if mode=='sweeps':d['runs'][0]['max_daily_sweeps']=31
   elif mode=='entry':d['runs'][0]['entries'].pop()
   else:d['runs'][0]['cleared']=47
   self.assertFalse(summarize(d)['all_pass'])
 def test_empty_single_campaign_duplicate_seed_or_profile_mode_cannot_claim_acceptance(self):
  for mode in ['empty','single','duplicate','profile','missing_batch']:
   d=self.fixture()
   if mode=='empty':d['runs']=[]
   elif mode=='single':d['runs']=[r for r in d['runs']if r['campaign']=='taiping']
   elif mode=='duplicate':d['runs'][1]['seed']=d['runs'][0]['seed']
   elif mode=='profile':d['mode']='profile'
   else:d['runs'].pop()
   self.assertFalse(summarize(d)['all_pass'])
 def test_continuous_resource_exhaustion_fails_but_an_isolated_zero_does_not(self):
  d=self.fixture();d['runs'][0]['session_wallets']=[{'silver':100,'iron':0}]*4
  self.assertFalse(summarize(d)['all_pass']);d['runs'][0]['session_wallets']=[{'silver':100,'iron':0},{'silver':100,'iron':20}]
  self.assertTrue(summarize(d)['all_pass'])
if __name__=='__main__':unittest.main()
