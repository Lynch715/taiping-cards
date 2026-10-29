import unittest
from curve_metrics import acceptance
class CurveGate(unittest.TestCase):
 def sample(self):
  days=[1,1.5,2,2,2.5,3,3,3.5]
  return {'runs':[{'campaign':camp,'seed':seed,'cleared':48,'chapters':[{'chapter':i+1,'duration':d,'target_days':d,'max_stage_wait':1}for i,d in enumerate(days)]}for camp in ['taiping','qing']for seed in range(12)]}
 def test_all_pass(self):self.assertEqual(acceptance(self.sample())['pass_count'],16)
 def test_ten_accounts_within_two_and_two_at_three_pass_only_new_gate(self):
  d=self.sample()
  for r in d['runs'][:2]:r['chapters'][5]['max_stage_wait']=3
  m=acceptance(d);self.assertEqual(m['pass_count'],16);self.assertEqual(m['old_pass_count'],15)
 def test_nine_short_or_any_over_three_fails(self):
  for count,wait in [(3,2.25),(1,3.25)]:
   d=self.sample()
   for r in d['runs'][:count]:r['chapters'][5]['max_stage_wait']=wait
   self.assertEqual(acceptance(d)['pass_count'],15)
 def test_mean_pace_is_still_required(self):
  d=self.sample()
  for r in d['runs'][:12]:r['chapters'][5]['duration']=4
  self.assertEqual(acceptance(d)['pass_count'],15)
 def test_missing_account_or_unfinished_cannot_pass(self):
  for missing in [True,False]:
   d=self.sample()
   if missing:d['runs'].pop()
   else:d['runs'][0]['cleared']=47
   self.assertFalse(acceptance(d)['all_pass'])
if __name__=='__main__':unittest.main()
